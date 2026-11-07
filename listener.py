"""听歌流程：选歌 -> 歌词/热评 -> 模型听后感 -> 可选评论。

手动触发（插件页）和以后定时听歌都走这里；聊天里的 listen_song 工具只返回材料，
听后感由聊天模型自己说。
"""

import random
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


def persona_prompt(context, persona_id):
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


async def generate_reply(
    context,
    song_name,
    my_comment,
    reply_user,
    reply_content,
    *,
    persona_id="",
    persona_extra="",
    provider_id="",
):
    """为一条评论回复生成回应。

    Args:
        context: AstrBot Context。
        song_name: 歌曲名。
        my_comment: 自己之前发的评论。
        reply_user: 回复者昵称。
        reply_content: 回复内容。
        persona_id: 用哪个人格。
        persona_extra: 人格补充。
        provider_id: 用哪个模型。

    Returns:
        回复文本；没有可用模型时返回空串。
    """
    system_prompt = persona_prompt(context, persona_id)
    if persona_extra:
        system_prompt = f"{system_prompt}\n\n{persona_extra}".strip()
    provider = provider_id or await _current_provider(context)
    if not provider:
        return ""
    prompt = (
        "有人在网易云评论区回复了你的评论。\n"
        f"歌曲：{song_name}\n"
        f"你的评论：{my_comment}\n"
        f"对方（{reply_user}）：{reply_content}\n\n"
        "用你的人格写一句简短回复，5-50 字，只写回复本身，不要解释设定、不要列点。"
    )
    response = await context.llm_generate(
        chat_provider_id=provider,
        prompt=prompt,
        system_prompt=system_prompt or None,
        max_tokens=120,
    )
    return _clean_reaction(getattr(response, "completion_text", "") or "")


async def resolve_song(query="", song_id="", *, randomize=False, exclude_ids=()):
    """把歌曲 ID 或搜索词解析成一首歌。

    Args:
        query: 搜索词，可以是歌名或歌手名。
        song_id: 网易云歌曲 ID，优先使用。
        randomize: 按歌手搜到多首时是否随机挑一首。
        exclude_ids: 随机时尽量避开的歌曲 ID（最近听过的）。

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
    if results:
        return await get_netease_song(results[0]["id"])
    artist_songs = await search_netease_artist_songs(query, limit=10)
    if not artist_songs:
        return None
    excluded = {str(item) for item in exclude_ids}
    pool = [item for item in artist_songs if str(item.get("id")) not in excluded]
    if not pool:
        pool = artist_songs
    chosen = random.choice(pool) if randomize else pool[0]
    return await get_netease_song(chosen["id"])


async def listen(
    context,
    store,
    *,
    query="",
    song_id="",
    persona_id="",
    persona_extra="",
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
        persona_extra: 追加在人格后面的补充说明，用于评论前的口径调整。
        provider_id: 用哪个模型，空则用当前聊天模型。
        auto_comment: 听完是否自动评论。
        daily_limit: 每日评论上限。

    Returns:
        写入的听歌记录。

    Raises:
        ValueError: 没找到歌或没有可用模型。
    """
    recent_ids = [str(item.get("song_id") or "") for item in store.recent_listened(5)]
    song = await resolve_song(query, song_id, randomize=True, exclude_ids=recent_ids)
    if not song:
        raise ValueError("没找到这首歌")
    lyrics = await get_song_lyrics(song["id"])
    comments = await get_song_comments(song["id"], 6)
    prompt = build_prompt(song, lyrics, comments)
    system_prompt = persona_prompt(context, persona_id)
    if persona_extra:
        system_prompt = f"{system_prompt}\n\n{persona_extra}".strip()
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
        if store.has_commented(song["id"]):
            entry["comment_message"] = "已经评论过，跳过"
        else:
            content = reaction[:50]
            cookie = store.cookie
            if cookie and len(content) >= 2:
                result = await post_song_comment(song["id"], content, cookie)
                store.add_comment(
                    {
                        "at": entry["at"],
                        "song_id": song["id"],
                        "name": song["name"],
                        "content": content,
                        "ok": result["ok"],
                        "message": result["message"],
                        "comment_id": result.get("comment_id", ""),
                    }
                )
                entry["commented"] = result["ok"]
                entry["comment_message"] = result["message"]
    store.add_listened(entry)
    return entry
