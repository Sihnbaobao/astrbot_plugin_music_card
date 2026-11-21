import re
from urllib.parse import parse_qs, urlparse

import httpx

from astrbot.core import logger

QQ_API = "https://u.y.qq.com/cgi-bin/musicu.fcg"
_URL_TRAILING_CHARS = ".,!?;:)]}，。！？；：）》”’"


def _clean_url(url):
    """Remove punctuation attached to a QQ music URL.

    Args:
        url: URL text extracted from a message.

    Returns:
        Cleaned URL text.
    """
    return url.rstrip(_URL_TRAILING_CHARS)


def _is_qq_music_host(url):
    """Check whether a URL host belongs to QQ Music.

    Args:
        url: URL to inspect.

    Returns:
        True for y.qq.com subdomains, otherwise False.
    """
    try:
        hostname = (urlparse(url).hostname or "").lower()
    except (TypeError, ValueError):
        return False
    return hostname == "y.qq.com" or hostname.endswith(".y.qq.com")


def _extract_qq_url(text):
    """Find the first URL hosted by QQ Music.

    Args:
        text: Message text containing candidate URLs.

    Returns:
        A cleaned QQ Music URL, or None when no supported URL exists.
    """
    for raw_url in re.findall(r"https?://[^\s<>]+", text or "", re.IGNORECASE):
        url = _clean_url(raw_url)
        if _is_qq_music_host(url):
            return url
    return None


def _url_params(url):
    """Parse query parameters from a URL and its hash fragment.

    Args:
        url: URL to parse.

    Returns:
        URL path and merged query parameters.
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    fragment_path, separator, fragment_query = parsed.fragment.partition("?")
    path = parsed.path
    if separator:
        if fragment_path:
            path = fragment_path
        for key, values in parse_qs(fragment_query).items():
            params.setdefault(key, values)
    return path, params


async def convert_songid_to_mid(songid):
    """Convert a numeric QQ Music song ID to a song mid.

    Args:
        songid: Numeric QQ Music song ID.

    Returns:
        QQ Music song mid, or None when conversion fails.
    """
    songid = str(songid).strip()
    if not songid.isdigit():
        return None
    payload = {
        "comm": {"ct": 24, "cv": 0},
        "music.pf_song_detail_svr": {
            "method": "get_song_detail_yqq",
            "module": "music.pf_song_detail_svr",
            "param": {"song_id": int(songid)},
        },
    }
    try:
        async with httpx.AsyncClient(
            timeout=10, headers={"User-Agent": "Mozilla/5.0"}
        ) as client:
            response = await client.post(QQ_API, json=payload)
            response.raise_for_status()
            mid = response.json()["music.pf_song_detail_svr"]["data"]["track_info"][
                "mid"
            ]
            logger.info(f"songid->mid:{songid}->{mid}")
            return str(mid) if mid else None
    except Exception as e:
        logger.warning(f"songid转换失败:{e}")
        return None


async def get_qq_song(song_mid):
    """Fetch QQ Music metadata for a song mid.

    Args:
        song_mid: QQ Music song mid.

    Returns:
        Song metadata dictionary, or None when the request fails.
    """
    payload = {
        "comm": {"ct": 24, "cv": 0},
        "songinfo": {
            "method": "get_song_detail_yqq",
            "module": "music.pf_song_detail_svr",
            "param": {"song_mid": song_mid},
        },
    }
    try:
        async with httpx.AsyncClient(
            timeout=10, headers={"User-Agent": "Mozilla/5.0"}
        ) as client:
            response = await client.post(QQ_API, json=payload)
            response.raise_for_status()
            track = response.json()["songinfo"]["data"]["track_info"]
    except Exception as e:
        logger.warning(f"歌曲请求失败:{e}")
        return None

    if not isinstance(track, dict):
        logger.warning("QQ歌曲响应缺少有效的 track_info")
        return None
    title_value = track.get("name")
    title = str(title_value).strip() if title_value else ""
    singers = track.get("singer") or []
    if not isinstance(singers, list):
        singers = []
    singer = " / ".join(
        str(item.get("name", "")).strip()
        for item in singers
        if isinstance(item, dict) and item.get("name")
    )
    album = track.get("album") or {}
    if not isinstance(album, dict):
        album = {}
    album_mid = str(album.get("mid", "")).strip()
    pic = (
        f"https://y.gtimg.cn/music/photo_new/T002R500x500M000/{album_mid}.jpg"
        if album_mid
        else ""
    )
    return {
        "title": title,
        "singer": singer,
        "pic": pic,
        "url": f"https://y.qq.com/n/ryqq/songDetail/{song_mid}",
        "audio": f"https://isure.stream.qqmusic.qq.com/C400{song_mid}.m4a?guid=10000&uin=0&fromtag=66",
        "songmid": song_mid,
        "song_id": track.get("id", 0),
    }


async def parse_qq_card(text):
    """Resolve a QQ Music URL and return its metadata.

    Args:
        text: Message text containing a QQ Music URL.

    Returns:
        QQ song metadata, or None when the URL cannot be resolved.
    """
    url = _extract_qq_url(text)
    if not url:
        return None

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            real_url = str(response.url)
    except Exception as e:
        logger.warning(f"链接展开失败:{e}")
        return None

    logger.info(f"QQ真实地址:{real_url}")
    if not _is_qq_music_host(real_url):
        logger.warning(f"QQ链接跳转到非QQ音乐地址:{real_url}")
        return None
    path, params = _url_params(real_url)
    song_mid = None
    match = re.search(r"songDetail/([0-9A-Za-z]+)", path, re.IGNORECASE)
    if match:
        value = match.group(1)
        song_mid = await convert_songid_to_mid(value) if value.isdigit() else value
    if not song_mid:
        song_mid = params.get("songmid", [None])[0]
    if not song_mid:
        song_id = params.get("songid", [None])[0]
        if song_id:
            song_mid = await convert_songid_to_mid(song_id)
    if not song_mid:
        return None

    logger.info(f"最终songmid:{song_mid}")
    return await get_qq_song(song_mid)
