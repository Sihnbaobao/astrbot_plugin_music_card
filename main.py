import asyncio
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

from astrbot.api import AstrBotConfig
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.message_components import Music, Plain
from astrbot.api.star import Context, Star, register
from astrbot.core import logger
from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path

from .kugou import parse_kugou_card
from .listener import generate_reply, listen
from .netease import (
    add_song_to_playlist,
    find_or_create_playlist,
    get_comment_replies,
    get_netease_account,
    get_netease_csrf,
    get_netease_song,
    get_song_comments,
    get_song_lyrics,
    like_song,
    post_song_comment,
    reply_to_comment,
    search_netease,
    search_netease_artist_songs,
    search_netease_candidates,
)
from .qqcard import parse_qq_card
from .store import MusicStore

MUSIC_DOMAINS = (
    "music.163.com",
    "163cn.tv",
    "y.qq.com",
    "kugou.com",
)
_EVENT_STATE_KEY = "astrbot_plugin_music_card.state"
_URL_TRAILING_CHARS = ".,!?;:)]}，。！？；：）》”’"
_SEARCH_RESULT_LIMIT = 5


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


@register("astrbot_plugin_music_card", "Sihnbaobao", "音乐链接转网易云卡片", "1.15.6")
class MusicCardPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config
        self.data_dir = (
            Path(get_astrbot_plugin_data_path()) / "astrbot_plugin_music_card"
        )
        self.store = MusicStore(self.data_dir)
        self._account = {}
        self._account_at = 0.0
        self._reply_task = None
        self._register_web_apis()

    async def initialize(self) -> None:
        """插件激活时启动回复检查。"""
        if self._reply_task is None:
            self._reply_task = asyncio.create_task(self._reply_loop())
            logger.info("[music-card] 回复检查已启动")

    async def terminate(self) -> None:
        """插件停用时取消后台任务。"""
        if self._reply_task is not None:
            self._reply_task.cancel()
            try:
                await self._reply_task
            except asyncio.CancelledError:
                pass
            self._reply_task = None

    @filter.on_llm_request()
    async def on_llm_request(self, event, req):
        """Nudge recommendation requests to verify song names first.

        Args:
            event: Current AstrBot message event.
            req: Provider request being built.
        """
        text = str(getattr(event, "message_str", "") or "")
        hints = []
        if re.search(r"(推荐|歌单|好听的歌|听什么歌|有什么歌|找.*歌|想听)", text):
            hints.append(
                "聊到推荐或找歌时，先 search_songs 确认一下；"
                "只提真的搜到的歌，没搜到就说没找到，别凭印象编歌名。"
            )
        if re.search(r"(听歌|听会儿歌|去听|听听歌|放首歌|听一首)", text):
            hints.append(
                "想听歌的时候，直接 listen_music 去听；"
                "留空就按自己的喜好挑，听完会有听后感。"
            )
        if not hints:
            return
        hint = "\n\n[音乐] " + " ".join(hints)
        req.system_prompt = str(getattr(req, "system_prompt", "") or "") + hint

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

    # ── 配置与插件页 ──

    def _cfg(self, key, default=None):
        """读取插件配置，空值回退到默认值。

        Args:
            key: 配置项名。
            default: 缺省值。

        Returns:
            配置值或默认值。
        """
        try:
            value = (self.config or {}).get(key, default)
        except AttributeError:
            value = default
        if value is None or value == "":
            return default
        return value

    def _register_web_apis(self):
        """注册插件页用的接口。"""
        routes = [
            ("page/status", self._api_status, ["GET"], "听歌：状态与记录"),
            ("page/personas", self._api_personas, ["GET"], "听歌：人格列表"),
            ("page/settings", self._api_settings, ["POST"], "听歌：保存人格设置"),
            (
                "page/login/cookie",
                self._api_login_cookie,
                ["POST"],
                "听歌：Cookie 登录",
            ),
            ("page/listen", self._api_listen, ["POST"], "听歌：手动听一首"),
            ("page/logout", self._api_logout, ["POST"], "听歌：退出登录"),
        ]
        for endpoint, handler, methods, desc in routes:
            self.context.register_web_api(
                f"/astrbot_plugin_music_card/{endpoint}", handler, methods, desc
            )
        logger.info("[music-card] 插件页接口已注册")

    async def _api_status(self):
        """插件页顶部的全部状态。"""
        from astrbot.api.web import json_response

        auth = self.store.load_auth()
        account = self._account
        if auth.get("cookie") and (not account or time.time() - self._account_at > 600):
            fetched = await get_netease_account(auth["cookie"])
            if fetched:
                account = fetched
                self._account = fetched
                self._account_at = time.time()
        if not account and auth:
            account = {
                "name": auth.get("name", ""),
                "avatar": auth.get("avatar", ""),
                "userId": auth.get("userId", ""),
            }
        return json_response(
            {
                "logged_in": bool(auth.get("cookie")),
                "account": account,
                "listened": self.store.recent_listened(30),
                "comments": self.store.recent_comments(30),
                "listened_total": len(self.store.recent_listened(500)),
                "comments_total": len(self.store.recent_comments(500)),
                "comments_today": self.store.comments_today(),
                "daily_limit": int(self._cfg("COMMENT_DAILY_LIMIT", 3)),
                "auto_comment": bool(self._cfg("AUTO_COMMENT", False)),
                "listen_query": str(self._cfg("LISTEN_QUERY", "花谱")),
                "persona_id": str(self._cfg("PERSONA_ID", "")),
                "persona_extra": str(self._cfg("PERSONA_EXTRA", "")),
                "replies": self.store.recent_replies(30),
                "auto_reply": bool(self._cfg("AUTO_REPLY", False)),
                "reply_watch": bool(self._cfg("REPLY_WATCH", True)),
                "reply_interval": int(self._cfg("REPLY_INTERVAL_MINUTES", 30)),
            }
        )

    async def _api_login_cookie(self):
        """用浏览器复制的 Cookie 登录。"""
        from astrbot.api.web import error_response, json_response, request

        try:
            payload = await request.json(default={})
        except Exception:
            payload = {}
        cookie = str((payload or {}).get("cookie") or "").strip()
        if not cookie:
            return error_response("请粘贴 Cookie")
        if "MUSIC_U=" not in cookie:
            cookie = f"MUSIC_U={cookie}"
        if "__csrf" not in cookie:
            csrf = await get_netease_csrf(cookie)
            if csrf:
                cookie = f"{cookie}; __csrf={csrf}"
        account = await get_netease_account(cookie)
        if not account:
            return error_response("Cookie 无效或已过期，请重新复制")
        self.store.save_auth(
            {
                "cookie": cookie,
                "name": account.get("name", ""),
                "avatar": account.get("avatar", ""),
                "userId": account.get("userId", ""),
                "at": time.time(),
            }
        )
        self._account = account
        self._account_at = time.time()
        return json_response({"ok": True, "account": account})

    async def _api_listen(self):
        """手动听一首歌。"""
        from astrbot.api.web import error_response, json_response, request

        try:
            payload = await request.json(default={})
        except Exception:
            payload = {}
        query = str((payload or {}).get("query") or "").strip()
        song_id = str((payload or {}).get("song_id") or "")
        auto = bool(
            (payload or {}).get("auto_comment", self._cfg("AUTO_COMMENT", False))
        )
        raw_categories = str(self._cfg("PLAYLIST_CATEGORIES", "深夜,通勤,元气,emo"))
        categories = [
            item.strip()
            for item in raw_categories.replace("，", ",").split(",")
            if item.strip()
        ]
        try:
            entry = await listen(
                self.context,
                self.store,
                query=query,
                song_id=song_id,
                persona_id=str(self._cfg("PERSONA_ID", "")),
                persona_extra=str(self._cfg("PERSONA_EXTRA", "")),
                provider_id=str(self._cfg("PROVIDER_ID", "")),
                persona_pick=not query and not song_id,
                fallback_query=str(self._cfg("LISTEN_QUERY", "花谱")),
                auto_comment=auto,
                daily_limit=int(self._cfg("COMMENT_DAILY_LIMIT", 3)),
                auto_save=bool(self._cfg("AUTO_SAVE", False)),
                min_score=int(self._cfg("LIKE_MIN_SCORE", 9)),
                playlist_prefix=str(self._cfg("PLAYLIST_PREFIX", "璃月")),
                categories=categories,
            )
        except Exception as exc:
            logger.warning(f"[music-card] 听歌失败：{exc}")
            return error_response(str(exc))
        return json_response({"entry": entry})

    async def _api_personas(self):
        """可选的人格列表。"""
        from astrbot.api.web import json_response

        personas = []
        manager = getattr(self.context, "persona_manager", None)
        if manager is not None:
            try:
                items = await manager.get_all_personas()
            except Exception as exc:
                logger.warning(f"[music-card] 读取人格列表失败：{exc}")
                items = []
            for item in items:
                persona_id = str(getattr(item, "persona_id", "") or "").strip()
                if persona_id:
                    personas.append({"id": persona_id, "name": persona_id})
        return json_response({"personas": personas})

    async def _api_settings(self):
        """保存听歌人格设置。"""
        from astrbot.api.web import error_response, json_response, request

        try:
            payload = await request.json(default={})
        except Exception:
            payload = {}
        data = payload or {}
        updates = {}
        if "persona_id" in data:
            updates["PERSONA_ID"] = str(data.get("persona_id") or "").strip()
        if "persona_extra" in data:
            extra = str(data.get("persona_extra") or "").strip()
            if len(extra) > 2000:
                return error_response("人格补充太长了，控制在 2000 字以内")
            updates["PERSONA_EXTRA"] = extra
        if "auto_reply" in data:
            updates["AUTO_REPLY"] = bool(data.get("auto_reply"))
        if not updates:
            return error_response("没有要保存的内容")
        if self.config is None:
            return error_response("插件配置不可用")
        for key, value in updates.items():
            self.config[key] = value
        try:
            await self.config.save_config_async()
        except Exception as exc:
            logger.warning(f"[music-card] 保存设置失败：{exc}")
            return error_response(f"保存失败：{exc}")
        return json_response(
            {"saved": True, **{k.lower(): v for k, v in updates.items()}}
        )

    async def _api_logout(self):
        """退出登录。"""
        from astrbot.api.web import json_response

        self.store.clear_auth()
        self._account = {}
        self._account_at = 0.0
        return json_response({"ok": True})

    # ── 回复检查 ──

    async def _reply_loop(self) -> None:
        """定时检查自己评论下有没有新回复。"""
        while True:
            try:
                await self._check_replies()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(f"[music-card] 检查回复失败：{exc}")
            interval = max(5, int(self._cfg("REPLY_INTERVAL_MINUTES", 30)))
            await asyncio.sleep(interval * 60)

    async def _check_replies(self) -> None:
        """检查最近评论下的新回复，必要时自动回复。"""
        if not self._cfg("REPLY_WATCH", True):
            return
        auth = self.store.load_auth()
        cookie = str(auth.get("cookie") or "")
        if not cookie:
            return
        my_id = str(auth.get("userId") or "")
        seen = self.store.seen_reply_ids()
        auto_reply = bool(self._cfg("AUTO_REPLY", False))
        daily_limit = int(self._cfg("REPLY_DAILY_LIMIT", 5))
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        comments = [
            item
            for item in self.store.recent_comments(20)
            if item.get("ok")
            and item.get("comment_id")
            and str(item.get("at", "")) >= cutoff
        ][:5]
        for comment in comments:
            replies = await get_comment_replies(
                comment.get("song_id", ""), comment.get("comment_id", ""), cookie
            )
            for reply in replies:
                reply_id = str(reply.get("reply_id") or "")
                if not reply_id or reply_id in seen:
                    continue
                if my_id and str(reply.get("user_id") or "") == my_id:
                    continue
                seen.add(reply_id)
                entry = {
                    "at": datetime.now().isoformat(timespec="seconds"),
                    "song_id": comment.get("song_id", ""),
                    "name": comment.get("name", ""),
                    "parent_comment_id": comment.get("comment_id", ""),
                    "reply_id": reply_id,
                    "user": reply.get("user", ""),
                    "content": reply.get("content", ""),
                    "my_reply": "",
                }
                if (
                    auto_reply
                    and daily_limit > 0
                    and self.store.replies_today() < daily_limit
                ):
                    text = await generate_reply(
                        self.context,
                        comment.get("name", ""),
                        comment.get("content", ""),
                        reply.get("user", ""),
                        reply.get("content", ""),
                        persona_id=str(self._cfg("PERSONA_ID", "")),
                        persona_extra=str(self._cfg("PERSONA_EXTRA", "")),
                        provider_id=str(self._cfg("PROVIDER_ID", "")),
                    )
                    if text:
                        ok, message = await reply_to_comment(
                            comment.get("song_id", ""),
                            comment.get("comment_id", ""),
                            text,
                            cookie,
                        )
                        entry["my_reply"] = text
                        entry["my_reply_ok"] = ok
                        entry["my_reply_message"] = message
                        if ok:
                            logger.info(
                                f"[music-card] 已回复 {reply.get('user', '')} 的评论"
                            )
                self.store.add_reply(entry)

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

    async def _listen_shared(self, event, song_id):
        """Listen to a song shared in chat and reply with a short reaction.

        Args:
            event: Current message event.
            song_id: Numeric NetEase song ID.
        """
        if not bool(self._cfg("LISTEN_SHARED", True)):
            return
        raw_categories = str(self._cfg("PLAYLIST_CATEGORIES", "深夜,通勤,元气,emo"))
        categories = [
            item.strip()
            for item in raw_categories.replace("，", ",").split(",")
            if item.strip()
        ]
        try:
            entry = await listen(
                self.context,
                self.store,
                song_id=song_id,
                persona_id=str(self._cfg("PERSONA_ID", "")),
                persona_extra=str(self._cfg("PERSONA_EXTRA", "")),
                provider_id=str(self._cfg("PROVIDER_ID", "")),
                persona_text=await self._session_persona_text(event),
                source="shared",
                auto_save=bool(self._cfg("AUTO_SAVE", False)),
                min_score=int(self._cfg("LIKE_MIN_SCORE", 9)),
                playlist_prefix=str(self._cfg("PLAYLIST_PREFIX", "璃月")),
                categories=categories,
            )
        except Exception as exc:
            logger.warning(f"[music-card] 分享歌曲听歌失败：{exc}")
            return
        if not entry.get("like"):
            return
        text = str(entry.get("reaction") or "").strip()
        if not text:
            return
        try:
            await event.send(MessageChain([Plain(text)]))
        except Exception as exc:
            logger.warning(f"[music-card] 听后感发送失败：{exc}")

    async def _session_persona_text(self, event):
        """Resolve the persona prompt used in the current chat session.

        Args:
            event: Current message event.

        Returns:
            Persona prompt text, or an empty string.
        """
        try:
            persona = await self.context.persona_manager.get_default_persona_v3(
                event.unified_msg_origin
            )
            return str((persona or {}).get("prompt") or "")
        except Exception:
            return ""

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
            info += (
                " （别人分享的歌；想听的话先用 search_songs 找到网易云 ID，"
                "再 listen_song 听，然后说点什么。）"
            )
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
                await self._listen_shared(event, song_id)
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
                await self._listen_shared(event, ne["id"])
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
                await self._listen_shared(event, ne["id"])
                event.stop_event()
                return
            logger.warning(f"酷狗转卡失败:{reason},继续尝试其他链接")

    # ── LLM 工具 ──

    @filter.llm_tool(name="search_songs")
    async def search_songs(
        self, event: AstrMessageEvent, song_name: str, artist: str = ""
    ):
        """想找歌、确认歌名或歌手时查一下；对不上会按歌手搜。

        Args:
            song_name(string): 歌名，或歌手名。
            artist(string): 歌手名，可留空。

        Returns:
            候选歌名、歌手和 ID；没有就直说没找到。
        """
        state = self._event_state(event)
        state["search_count"] = int(state.get("search_count", 0)) + 1
        if state["search_count"] > 3:
            return "本轮搜索次数已用完。"
        results = await search_netease_candidates(
            song_name, artist, limit=_SEARCH_RESULT_LIMIT
        )
        by_artist = False
        if not results:
            # 模型常把歌手名填进 song_name，歌名没匹配上时按歌手再搜一次。
            results = await search_netease_artist_songs(
                artist or song_name, limit=_SEARCH_RESULT_LIMIT
            )
            by_artist = bool(results)
        if not results:
            return "没有找到匹配的歌曲。"
        lines = [
            f"歌名:{song['name']} 歌手:{song['artist']} ID:{song['id']}"
            for song in results
        ]
        suffix = "\n\n(中文歌名可能以日语显示,如'魔法'='まほう')"
        if by_artist:
            suffix = "\n\n(按歌手搜索,以上是该歌手的歌)" + suffix
        return "\n".join(lines) + suffix

    @filter.llm_tool(name="send_song_card")
    async def send_song_card(self, event: AstrMessageEvent, song_id: str):
        """把一首歌做成网易云卡片发到聊天里。

        Args:
            song_id(string): 从 search_songs 拿到的歌曲 ID。

        Returns:
            发出去了就说一声；发不出去就照实说。
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

    # ── 听歌与评论 ──

    @filter.llm_tool(name="listen_song")
    async def listen_song(self, event: AstrMessageEvent, song_id: str):
        """翻歌词、翻译和热评，了解一首歌在唱什么；不写听后感。

        Args:
            song_id(string): 歌曲 ID，从 search_songs 来。

        Returns:
            歌名、歌手、歌词节选和热评；没找到就直说。
        """
        song_id = str(song_id or "").strip()
        if not song_id.isdigit():
            return "歌曲 ID 无效。"
        song = await get_netease_song(song_id)
        if not song:
            return "没有找到这首歌。"
        lyrics = await get_song_lyrics(song_id)
        comments = await get_song_comments(song_id, 6)
        self.store.add_listened(
            {
                "at": datetime.now().isoformat(timespec="seconds"),
                "song_id": song["id"],
                "name": song["name"],
                "artist": song["artist"],
                "reaction": "",
                "commented": False,
                "source": "chat",
            }
        )
        lines = [f"歌名:{song['name']} 歌手:{song['artist']}"]
        if lyrics.get("lyric"):
            lines.append("歌词(节选):\n" + lyrics["lyric"][:600])
        if lyrics.get("translation"):
            lines.append("翻译(节选):\n" + lyrics["translation"][:400])
        if comments:
            lines.append("热评:")
            for item in comments[:4]:
                lines.append(
                    f"- {item['user']}({item['liked']}赞): {item['content'][:60]}"
                )
        if not lyrics.get("lyric") and not comments:
            lines.append("(没拿到歌词或评论)")
        return "\n".join(lines)

    @filter.llm_tool(name="listen_music")
    async def listen_music(self, event: AstrMessageEvent, query: str = ""):
        """真的去听一首：挑歌、写听后感。你自己突然想听的时候就可以去听。
        留空按喜好挑，填歌名或歌手就听指定的。

        Args:
            query(string): 歌名或歌手；留空按喜好挑。

        Returns:
            听了什么、听后感；没听成就直说。
        """
        query = str(query or "").strip()
        raw_categories = str(self._cfg("PLAYLIST_CATEGORIES", "深夜,通勤,元气,emo"))
        categories = [
            item.strip()
            for item in raw_categories.replace("，", ",").split(",")
            if item.strip()
        ]
        try:
            entry = await listen(
                self.context,
                self.store,
                query=query,
                persona_id=str(self._cfg("PERSONA_ID", "")),
                persona_extra=str(self._cfg("PERSONA_EXTRA", "")),
                provider_id=str(self._cfg("PROVIDER_ID", "")),
                persona_text=await self._session_persona_text(event),
                persona_pick=not query,
                fallback_query=str(self._cfg("LISTEN_QUERY", "花谱")),
                source="chat",
                auto_save=bool(self._cfg("AUTO_SAVE", False)),
                min_score=int(self._cfg("LIKE_MIN_SCORE", 9)),
                playlist_prefix=str(self._cfg("PLAYLIST_PREFIX", "璃月")),
                categories=categories,
            )
        except Exception as exc:
            logger.warning(f"[music-card] 聊天听歌失败：{exc}")
            return f"没听成：{exc}"
        lines = [
            f"刚听了《{entry['name']}》（{entry['artist']}）：{entry['reaction']}",
        ]
        if entry.get("saved"):
            lines.append(f"已收藏并加入歌单「{entry.get('playlist', '')}」。")
        return "\n".join(lines)

    @filter.llm_tool(name="comment_song")
    async def comment_song(self, event: AstrMessageEvent, song_id: str, content: str):
        """在网易云评论区留一句话；先听过再去，每天有次数上限。

        Args:
            song_id(string): 网易云歌曲 ID。
            content(string): 想留的话，2-50 字。

        Returns:
            发出去了就说一声；发不出去就照实说。
        """
        song_id = str(song_id or "").strip()
        content = str(content or "").strip()
        if not song_id.isdigit():
            return "歌曲 ID 无效。"
        if not 2 <= len(content) <= 50:
            return "评论内容要 2-50 字。"
        limit = int(self._cfg("COMMENT_DAILY_LIMIT", 3))
        if limit <= 0:
            return "现在不允许发评论。"
        if self.store.comments_today() >= limit:
            return "今天的评论次数用完了。"
        listened = any(
            str(item.get("song_id")) == song_id
            for item in self.store.recent_listened(200)
        )
        if not listened:
            return "先听一遍这首歌再评论。"
        if self.store.has_commented(song_id):
            return "这首歌已经评论过了。"
        cookie = self.store.cookie
        if not cookie:
            return "还没有登录网易云，发不了评论。"
        result = await post_song_comment(song_id, content, cookie)
        self.store.add_comment(
            {
                "at": datetime.now().isoformat(timespec="seconds"),
                "song_id": song_id,
                "name": "",
                "content": content,
                "ok": result["ok"],
                "message": result["message"],
                "comment_id": result.get("comment_id", ""),
            }
        )
        return "已评论" if result["ok"] else f"评论失败:{result['message']}"

    @filter.llm_tool(name="like_song")
    async def like_song_tool(self, event: AstrMessageEvent, song_id: str):
        """把一首歌收进「我喜欢的音乐」。

        Args:
            song_id(string): 网易云歌曲 ID。

        Returns:
            收好了就说一声；没成就照实说。
        """
        cookie = self.store.cookie
        if not cookie:
            return "还没有登录网易云，先登录再收藏。"
        ok, message = await like_song(song_id, cookie)
        return "已收藏" if ok else f"收藏失败:{message}"

    @filter.llm_tool(name="save_to_playlist")
    async def save_to_playlist_tool(
        self, event: AstrMessageEvent, song_id: str, category: str = ""
    ):
        """把一首歌放进歌单；没有就建一个。

        Args:
            song_id(string): 网易云歌曲 ID。
            category(string): 分类，比如 深夜、通勤；留空就归到「收藏」。

        Returns:
            放进去了就说一声；没成就照实说。
        """
        cookie = self.store.cookie
        auth = self.store.load_auth()
        if not cookie:
            return "还没有登录网易云，先登录再加入歌单。"
        prefix = str(self._cfg("PLAYLIST_PREFIX", "璃月"))
        name = f"{prefix}·{category.strip()}" if category.strip() else f"{prefix}·收藏"
        playlist_id = await find_or_create_playlist(name, cookie, auth.get("userId"))
        if not playlist_id:
            return "创建或查找歌单失败。"
        ok, message = await add_song_to_playlist(playlist_id, song_id, cookie)
        return f"已加入歌单「{name}」" if ok else f"加入歌单失败:{message}"
