"""听歌流程：选歌 -> 歌词/热评 -> 模型听后感 -> 可选评论。

手动触发（插件页）和以后定时听歌都走这里；聊天里的 listen_song 工具只返回材料，
听后感由聊天模型自己说。
"""

import re
from datetime import datetime

from astrbot.core import logger

from .netease import (
    get_netease_song,
    get_song_comments,
    get_song_lyrics,
    post_song_comment,
    search_netease_artist_songs,
    search_netease_candidates,
)

_REACTION_PREFIX = re.compile(r"^(听后感|感想|评论)\s*[:：]\s*")


def _clean_reaction(text):
    """把模型输出收成一句干净的听后感。

    Args:
        text: 模型原始输出。

    Returns:
        去掉引号、前缀和多余空白后的短句。
    """
    text = str(text or "").strip()
    text = _REACTION_PREFIX.sub("", text)
    text = text.strip().strip("“”\"'「」")
    text = re.sub(r"\s+", " ", text)
    return text[:120]


def build_prompt(song, lyrics, comments):
    """拼听歌提示词。

    Args:
        song: get_netease_song 返回的歌曲信息。
        lyrics: 包含 lyric 和 translation 的字典。
        comments: 热评列表。

    Returns:
        发给模型的提示词。
    """
    lines = [
        "你刚刚在网易云听了一首歌。",
        f"歌名：{song.get('name', '')}",
        f"歌手：{song.get('artist', '')}",
    ]
    if lyrics.get("lyric"):
        lines.append("歌词（节选）：\n" + lyrics["lyric"])
    if lyrics.get("translation"):
        lines.append("歌词翻译（节选）：\n" + lyrics["translation"])
    if comments:
        lines.append("热评：")
        for item in comments[:5]:
            lines.append(f"- {item['user']}（{item['liked']} 赞）：{item['content']}")
    lines.append("")
    lines.append(
        "用你的人格写一句听后感，20-60 字，只写听后感本身，不要解释设定、不要列点。"
    )
    return "\n".join(lines)


def _persona_prompt(context, persona_id):
    """取人格提示词。

    Args:
        context: AstrBot Context。
        persona_id: 配置里的人格 ID，可为空。

    Returns:
        人格正文；取不到时返回空串。
    """
    manager = getattr(context, "persona_manager", None)
    if manager is None or not persona_id:
        return ""
    try:
        persona = manager.get_persona_v3_by_id(persona_id)
    except Exception as exc:
        logger.warning(f"读取人格 {persona_id} 失败：{exc}")
        return ""
    return str((persona or {}).get("prompt") or "").strip()


async def _current_provider(context):
    """取当前使用的聊天模型 ID。"""
    try:
        provider = await context.get_using_provider_async()
    except Exception:
        provider = None
    return str(provider.meta().id) if provider else ""


async def resolve_song(query="", song_id=""):
    """把歌曲 ID 或搜索词解析成一首歌。

    Args:
        query: 搜索词，可以是歌名或歌手名。
        song_id: 网易云歌曲 ID，优先使用。

    Returns:
        歌曲信息字典；没找到时返回 None。
    """
    song_id = str(song_id or "").strip()
    if song_id.isdigit():
        return await get_netease_song(song_id)
    query = str(query or "").strip()
    if not query:
        return None
    results = await search_netease_candidates(query, limit=1)
    if not results:
        results = await search_netease_artist_songs(query, limit=1)
    if not results:
        return None
    return await get_netease_song(results[0]["id"])


async def listen(
    context,
    store,
    *,
    query="",
    song_id="",
    persona_id="",
    provider_id="",
    auto_comment=False,
    daily_limit=3,
):
    """听一首歌并记录，必要时去评论区留言。

    Args:
        context: AstrBot Context。
        store: MusicStore。
        query: 搜索词。
        song_id: 直接指定歌曲 ID。
        persona_id: 用哪个人格写听后感。
        provider_id: 用哪个模型，空则用当前聊天模型。
        auto_comment: 听完是否自动评论。
        daily_limit: 每日评论上限。

    Returns:
        写入的听歌记录。

    Raises:
        ValueError: 没找到歌或没有可用模型。
    """
    song = await resolve_song(query, song_id)
    if not song:
        raise ValueError("没找到这首歌")
    lyrics = await get_song_lyrics(song["id"])
    comments = await get_song_comments(song["id"], 6)
    prompt = build_prompt(song, lyrics, comments)
    system_prompt = _persona_prompt(context, persona_id)
    provider = provider_id or await _current_provider(context)
    if not provider:
        raise ValueError("没有可用的聊天模型")
    response = await context.llm_generate(
        chat_provider_id=provider,
        prompt=prompt,
        system_prompt=system_prompt or None,
        max_tokens=200,
    )
    reaction = _clean_reaction(getattr(response, "completion_text", "") or "")
    entry = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "song_id": song["id"],
        "name": song["name"],
        "artist": song["artist"],
        "reaction": reaction,
        "commented": False,
        "source": "manual",
    }
    if auto_comment and daily_limit > 0 and store.comments_today() < daily_limit:
        content = reaction[:50]
        cookie = store.cookie
        if cookie and len(content) >= 2:
            ok, message = await post_song_comment(song["id"], content, cookie)
            store.add_comment(
                {
                    "at": entry["at"],
                    "song_id": song["id"],
                    "name": song["name"],
                    "content": content,
                    "ok": ok,
                    "message": message,
                }
            )
            entry["commented"] = ok
            entry["comment_message"] = message
    store.add_listened(entry)
    return entry
