import re
from difflib import SequenceMatcher

import httpx

from astrbot.core import logger

_ARTIST_SPLIT_RE = re.compile(
    r"\s*(?:/|、|,|，|&|\b(?:feat|ft|featuring)\.?\s+)\s*",
    re.IGNORECASE,
)


def _normalize(value):
    """Normalize titles and artist names for comparison.

    Args:
        value: Text to normalize.

    Returns:
        Case-folded text with punctuation and whitespace removed.
    """
    return re.sub(r"[\W_]+", "", str(value or "").casefold())


def _similarity(left, right):
    """Calculate a normalized similarity score for two text values.

    Args:
        left: First text value.
        right: Second text value.

    Returns:
        Similarity score from 0.0 to 1.0.
    """
    left = _normalize(left)
    right = _normalize(right)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    return SequenceMatcher(None, left, right).ratio()


def _split_artists(value):
    """Split a singer value into comparable artist names.

    Args:
        value: Artist text, list, or artist dictionaries.

    Returns:
        Non-empty artist names with collaboration separators removed.
    """
    values = value if isinstance(value, (list, tuple, set)) else [value]
    names = []
    for item in values:
        if isinstance(item, dict):
            item = item.get("name", "")
        names.extend(_ARTIST_SPLIT_RE.split(str(item or "")))
    return [name.strip() for name in names if name.strip()]


def _artist_similarity(result, singer):
    """Score all requested singers against a search result's artists.

    Args:
        result: Search result containing artist fields.
        singer: Requested singer name or collaboration.

    Returns:
        Similarity score from 0.0 to 1.0, requiring every requested artist.
    """
    requested = _split_artists(singer)
    artists = _split_artists(result.get("artists") or result.get("artist", ""))
    if not requested or not artists:
        return 0.0
    scores = [
        max((_similarity(name, artist) for artist in artists), default=0.0)
        for name in requested
    ]
    return min(scores, default=0.0)


def _select_best_result(results, title, singer):
    """Select a result only when its title and singer are credible.

    Args:
        results: Candidate search results.
        title: Requested song title.
        singer: Requested singer name.

    Returns:
        Best matching result, or None when matching confidence is too low.
    """
    if not results or not str(title or "").strip():
        return None
    candidates = [
        result for result in results if isinstance(result, dict) and result.get("name")
    ]
    if not candidates:
        return None
    title_key = _normalize(title)
    exact_title = [
        result for result in candidates if _normalize(result.get("name")) == title_key
    ]
    if not singer:
        if exact_title:
            return exact_title[0]
        logger.info(f"网易云未找到标题完全匹配结果:{title}")
        return None

    best = None
    best_score = -1.0
    best_artist_score = 0.0
    for result in candidates:
        title_score = _similarity(title, result.get("name", ""))
        artist_score = _artist_similarity(result, singer)
        score = title_score * 0.65 + artist_score * 0.35
        if score > best_score:
            best = result
            best_score = score
            best_artist_score = artist_score
    if best_artist_score < 0.6:
        logger.info(f"未找到歌手匹配的网易云结果:{title} - {singer}")
        return None
    if best_score < 0.8:
        logger.info(f"网易云搜索匹配度不足:{title} - {singer}")
        return None
    return best


async def get_netease_song(song_id):
    """按歌曲 ID 查询网易云歌曲。

    Args:
        song_id: 网易云歌曲 ID。

    Returns:
        歌曲信息字典;如果歌曲不存在则返回 None。

    Raises:
        httpx.HTTPError: 网易云接口返回 HTTP 错误时抛出。
        ValueError: 网易云接口返回非 JSON 内容时抛出。
    """
    song_id = str(song_id).strip()
    if not song_id.isdigit():
        return None
    async with httpx.AsyncClient(
        timeout=6,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
    ) as client:
        response = await client.get(
            "https://music.163.com/api/song/detail/",
            params={"id": song_id, "ids": f"[{song_id}]"},
        )
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        return None
    songs = payload.get("songs")
    if not isinstance(songs, list) or not songs:
        return None
    song = songs[0]
    if not isinstance(song, dict):
        return None
    song_name = song.get("name")
    if not song_name:
        return None
    artists = song.get("artists") or song.get("ar") or []
    if not isinstance(artists, list) or not artists:
        return None
    first_artist = artists[0]
    if not isinstance(first_artist, dict) or not first_artist.get("name"):
        return None
    artist_names = [
        str(artist.get("name", "")).strip()
        for artist in artists
        if isinstance(artist, dict) and artist.get("name")
    ]
    album = song.get("album") or song.get("al") or {}
    if not isinstance(album, dict):
        album = {}
    pic = album.get("picUrl") or first_artist.get("img1v1Url") or ""
    actual_id = str(song.get("id") or song_id)
    return {
        "id": actual_id,
        "name": str(song_name),
        "artist": " / ".join(artist_names),
        "url": f"https://y.music.163.com/m/song?id={actual_id}",
        "pic": pic,
        "audio": f"https://music.163.com/song/media/outer/url?id={actual_id}&sc=wm&tn=",
    }


async def search_netease(title, singer=""):
    """搜索歌曲并选择标题、歌手都匹配的最佳结果。

    Args:
        title: 歌曲标题。
        singer: 歌手名称,可选。

    Returns:
        最匹配的歌曲信息;没有达到匹配阈值时返回 None。
    """
    title = str(title or "").strip()
    singer = str(singer or "").strip()
    if not title:
        return None
    results = await search_netease_multi(f"{title} {singer}".strip(), limit=5)
    return _select_best_result(results, title, singer)


async def search_netease_multi(query, limit=5):
    """搜索多首歌曲。

    Args:
        query: 网易云搜索关键词。
        limit: 返回结果数量,限制在 1 到 20 之间。

    Returns:
        歌曲结果列表;接口失败时返回空列表。
    """
    query = str(query or "").strip()
    if not query:
        return []
    try:
        limit = max(1, min(int(limit), 20))
        async with httpx.AsyncClient(
            timeout=10, headers={"User-Agent": "Mozilla/5.0"}
        ) as client:
            response = await client.get(
                "https://music.163.com/api/search/get/web",
                params={
                    "s": query,
                    "type": 1,
                    "offset": 0,
                    "limit": limit,
                    "csrf_token": "",
                },
            )
            response.raise_for_status()
            songs = response.json().get("result", {}).get("songs", [])
        results = []
        for song in songs:
            if not isinstance(song, dict):
                continue
            song_id = song.get("id")
            name = song.get("name")
            if song_id is None or not name:
                continue
            artists = song.get("artists") or song.get("ar") or []
            artist_names = [
                str(artist.get("name", "")).strip()
                for artist in artists
                if isinstance(artist, dict) and artist.get("name")
            ]
            results.append(
                {
                    "id": str(song_id),
                    "name": name,
                    "artist": " / ".join(artist_names),
                    "artists": artist_names,
                }
            )
        return results
    except Exception as e:
        logger.warning(f"搜索失败:{e}")
        return []
