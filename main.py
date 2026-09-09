import re
from urllib.parse import parse_qs, urlparse

import httpx

from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.message_components import Music
from astrbot.api.star import Star, register
from astrbot.core import logger

from .kugou import parse_kugou_card
from .netease import get_netease_song, search_netease, search_netease_multi
from .qqcard import parse_qq_card

MUSIC_DOMAINS = (
    "music.163.com",
    "163cn.tv",
    "y.qq.com",
    "kugou.com",
)
_EVENT_STATE_KEY = "astrbot_plugin_music_card.state"
_URL_TRAILING_CHARS = ".,!?;:)]}，。！？；：）》”’"


def _clean_url(url):
    """Remove punctuation commonly attached to a URL.

    Args:
        url: URL text extracted from a message.

    Returns:
        URL text without trailing message punctuation.
    """
    return url.rstrip(_URL_TRAILING_CHARS)


def _extract_urls(text):
    """Extract HTTP(S) URLs from message text.

    Args:
        text: Message text to scan.

    Returns:
        Cleaned URLs in their original order.
    """
    return [
        _clean_url(url)
        for url in re.findall(r"https?://[^\s<>]+", text or "", re.IGNORECASE)
    ]


def _music_domain(url):
    """Return the supported music domain for a URL.

    Args:
        url: URL to inspect.

    Returns:
        Canonical supported domain, or an empty string for other hosts.
    """
    try:
        hostname = (urlparse(url).hostname or "").lower()
    except (TypeError, ValueError):
        return ""
    for domain in MUSIC_DOMAINS:
        if hostname == domain or hostname.endswith(f".{domain}"):
            return domain
    return ""


def _is_music_url(url):
    """Check whether a URL belongs to a supported music service.

    Args:
        url: URL to inspect.

    Returns:
        True when the URL host is supported.
    """
    return bool(_music_domain(url))


def _netease_song_id(url):
    """Extract a song ID from a NetEase song URL.

    Args:
        url: NetEase URL, including URLs using a hash fragment.

    Returns:
        Numeric song ID, or None for albums, playlists, and invalid URLs.
    """
    if _music_domain(url) not in {"music.163.com", "163cn.tv"}:
        return None
    parsed = urlparse(_clean_url(url))
    path = parsed.path.lower()
    params = parse_qs(parsed.query)
    fragment_path, separator, fragment_query = parsed.fragment.partition("?")
    if separator:
        if fragment_path:
            path = fragment_path.lower()
        for key, values in parse_qs(fragment_query).items():
            params.setdefault(key, values)
    elif fragment_path and "song" in fragment_path.lower():
        path = f"{path}{fragment_path}".lower()
    if "/song" not in path:
        return None
    song_id = params.get("id", [None])[0]
    return song_id if song_id and song_id.isdigit() else None


@register("astrbot_plugin_music_card", "Sihnbaobao", "音乐链接转网易云卡片", "1.3.11")
class MusicCardPlugin(Star):
    def __init__(self, context, config=None):
        super().__init__(context)

    def _event_state(self, event):
        """Get or initialize state scoped to the current message event.

        Args:
            event: Current AstrBot message event.

        Returns:
            Mutable state used by the LLM tools during this event.
        """
        state = event.get_extra(_EVENT_STATE_KEY)
        if not isinstance(state, dict):
            state = {"card_sent": False, "card_in_flight": False, "search_count": 0}
            event.set_extra(_EVENT_STATE_KEY, state)
        return state

    # ── 消息发送 ──

    async def _send(self, event, song_id):
        """Send a native NetEase music segment through OneBot.

        Args:
            event: Current message event.
            song_id: Numeric NetEase song ID.

        Raises:
            Exception: Propagates adapter or OneBot send failures.
        """
        song_id_text = str(song_id).strip()
        if not song_id_text.isdigit() or int(song_id_text) <= 0:
            raise ValueError("歌曲 ID 必须为正整数")
        music = Music(_type="163", id=int(song_id_text))
        # Pydantic v1 treats the leading-underscore field as private, but the
        # OneBot serializer reads it from __dict__ to emit data.type.
        if getattr(music, "_type", None) != "163":
            music.__dict__["_type"] = "163"
        await event.send(MessageChain([music]))

    async def _netease_card(self, event, song_id):
        """Send a native NetEase music card.

        Args:
            event: Current message event.
            song_id: Numeric NetEase song ID.

        Returns:
            Tuple of success flag and a user-facing failure reason.
        """
        song_id = str(song_id).strip()
        if not song_id.isdigit():
            logger.warning(f"163卡:无效歌曲ID={song_id}")
            return False, "歌曲 ID 无效"

        try:
            song = await get_netease_song(song_id)
        except Exception as e:
            logger.warning(f"163卡:歌曲信息查询失败({e})")
            return False, "歌曲信息查询失败,请稍后重试"

        if not song:
            logger.warning(f"163卡:歌曲不存在 id={song_id},不发卡片")
            return False, "歌曲不存在"

        try:
            await self._send(event, song_id)
        except Exception as e:
            logger.warning(f"163卡片发送失败({e})")
            return False, "OneBot 音乐卡片发送失败"

        self._event_state(event)["card_sent"] = True
        logger.info(f"163卡:id={song_id}")
        return True, ""

    # ── 链接处理 ──

    def _card_info(self, event):
        """Parse a music JSON card from an incoming message.

        Args:
            event: Current message event.

        Returns:
            Description text, supported URLs, and a music-card flag.
        """
        for seg in event.get_messages():
            if getattr(seg, "type", None) != "Json":
                continue
            data = getattr(seg, "data", None)
            if not isinstance(data, dict):
                continue

            candidate_urls = []

            def _walk(node):
                if isinstance(node, dict):
                    for key, value in node.items():
                        if key.lower() in (
                            "jumpurl",
                            "jump_url",
                            "musicurl",
                            "music_url",
                            "url",
                        ):
                            if isinstance(value, str) and value.lower().startswith(
                                ("http://", "https://")
                            ):
                                candidate_urls.append(_clean_url(value))
                        _walk(value)
                elif isinstance(node, list):
                    for item in node:
                        _walk(item)

            _walk(data)
            music_urls = list(
                dict.fromkeys(url for url in candidate_urls if _is_music_url(url))
            )
            if not music_urls:
                continue

            desc = ""
            meta = data.get("meta", {})
            if isinstance(meta, dict):
                for section in meta.values():
                    if not isinstance(section, dict):
                        continue
                    title = section.get("title") or section.get("songname")
                    singer = section.get("desc") or section.get("singer")
                    if title:
                        desc = f"分享歌曲:{title}"
                        if singer:
                            desc += f" 歌手:{singer}"
                        break
            return desc, music_urls, True
        return "", [], False

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def music_card(self, event: AstrMessageEvent):
        """Convert supported music links to native cards when possible.

        Args:
            event: Current AstrBot message event.
        """
        event.set_extra(
            _EVENT_STATE_KEY,
            {"card_sent": False, "card_in_flight": False, "search_count": 0},
        )

        card_desc, card_urls, is_card = self._card_info(event)
        text = event.message_str or ""

        # 有音乐 JSON 卡片:只把信息喂给 LLM,不重复发卡片
        if is_card:
            info = card_desc or "收到一张音乐分享卡片"
            if card_urls:
                info += f" 链接:{' '.join(card_urls)}"
            plain_parts = []
            for segment in event.get_messages():
                segment_type = getattr(segment, "type", "")
                segment_type = getattr(segment_type, "value", segment_type)
                if str(segment_type).lower() in {"plain", "text"}:
                    segment_text = str(getattr(segment, "text", "")).strip()
                    if segment_text:
                        plain_parts.append(segment_text)
            plain_text = " ".join(plain_parts)
            if plain_text and plain_text not in info:
                info += f" 文本:{plain_text}"
            event.message_str = info
            event.message_obj.message = []
            return

        urls = list(dict.fromkeys(_extract_urls(text)))
        netease_urls = [
            url for url in urls if _music_domain(url) in {"music.163.com", "163cn.tv"}
        ]
        for url in netease_urls:
            resolved_url = url
            if _music_domain(url) == "163cn.tv":
                try:
                    async with httpx.AsyncClient(
                        follow_redirects=True, timeout=10
                    ) as client:
                        response = await client.get(url)
                        response.raise_for_status()
                        resolved_url = str(response.url)
                except Exception as e:
                    logger.warning(f"网易云短链展开失败:{e}")
                    continue
                if _music_domain(resolved_url) != "music.163.com":
                    logger.warning(f"网易云短链跳转到非网易云地址:{resolved_url}")
                    continue
            song_id = _netease_song_id(resolved_url)
            if not song_id:
                continue
            ok, reason = await self._netease_card(event, song_id)
            if ok:
                event.stop_event()
                return
            logger.warning(f"网易云链接转卡失败:{reason},继续尝试其他链接")

        qq_urls = [url for url in urls if _music_domain(url) == "y.qq.com"]
        for url in qq_urls:
            try:
                info = await parse_qq_card(url)
            except Exception as e:
                logger.warning(f"QQ音乐链接解析失败:{e}")
                continue
            if not info or not info.get("title"):
                continue
            try:
                ne = await search_netease(info.get("title", ""), info.get("singer", ""))
            except Exception as e:
                logger.warning(f"QQ音乐网易云搜索失败:{e}")
                continue
            if not ne:
                logger.warning("QQ音乐未找到匹配的网易云歌曲,继续尝试其他链接")
                continue
            ok, reason = await self._netease_card(event, ne["id"])
            if ok:
                event.stop_event()
                return
            logger.warning(f"QQ音乐转卡失败:{reason},继续尝试其他链接")

        kugou_urls = [url for url in urls if _music_domain(url) == "kugou.com"]
        for url in kugou_urls:
            try:
                info = await parse_kugou_card(url)
            except Exception as e:
                logger.warning(f"酷狗链接解析失败:{e}")
                continue
            if not info or not info.get("title"):
                continue
            try:
                ne = await search_netease(info["title"], info.get("singer", ""))
            except Exception as e:
                logger.warning(f"酷狗网易云搜索失败:{e}")
                continue
            if not ne:
                logger.warning("酷狗未找到匹配的网易云歌曲,继续尝试其他链接")
                continue
            ok, reason = await self._netease_card(event, ne["id"])
            if ok:
                event.stop_event()
                return
            logger.warning(f"酷狗转卡失败:{reason},继续尝试其他链接")

    # ── LLM 工具 ──

    @filter.llm_tool(name="search_songs")
    async def search_songs(
        self, event: AstrMessageEvent, song_name: str, artist: str = ""
    ):
        """Search songs for a possible share or recommendation.

        Args:
            song_name(string): Song title or search phrase.
            artist(string): Optional artist name.

        Returns:
            Candidate songs with titles, artists, and IDs. The tool never sends.
        """
        state = self._event_state(event)
        state["search_count"] = int(state.get("search_count", 0)) + 1
        if state["search_count"] > 3:
            return "...好麻烦...璃月不想搜了"
        q = f"{song_name} {artist}".strip()
        results = await search_netease_multi(q, limit=3)
        if not results:
            return "...没找到"
        lines = [
            f"歌名:{song['name']} 歌手:{song['artist']} ID:{song['id']}"
            for song in results
        ]
        return "\n".join(lines) + "\n\n(中文歌名可能以日语显示,如'魔法'='まほう')"

    @filter.llm_tool(name="send_song_card")
    async def send_song_card(self, event: AstrMessageEvent, song_id: str):
        """把一首歌以网易云音乐卡片的形式发给对方听。

        只有你已经决定分享这首歌时才调用本工具;如果不想分享,不要调用本工具,
        直接用自己的回复表达拒绝。先使用 search_songs,只传入搜索结果中的实际 ID。
        本工具不会替你随机决定是否发送,调用后会直接尝试发送并返回实际结果。

        Args:
            song_id(string): 网易云歌曲 ID,必须来自 search_songs 的结果

        Returns:
            "已发送" on success, or a failure explanation when no card was sent.

        若歌曲不存在或平台发不出卡片,本工具会返回失败说明,不会谎报"已发送"。
        """
        state = self._event_state(event)
        if state.get("card_sent"):
            return "...刚发过了...这一轮不再发第二张"
        if state.get("card_in_flight"):
            return "...正在发...请不要重复调用"

        state["card_in_flight"] = True
        try:
            ok, reason = await self._netease_card(event, song_id)
        finally:
            state["card_in_flight"] = False
        if ok:
            state["card_sent"] = True
            return "已发送"
        return f"发送失败:{reason}"
