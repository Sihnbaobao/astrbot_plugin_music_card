import re
from urllib.parse import parse_qs, urlparse

import httpx

from astrbot.core import logger

_HASH_LENGTH = 32
_URL_TRAILING_CHARS = ".,!?;:)]}，。！？；：）》”’"


def _clean_url(url):
    """Remove punctuation attached to a Kugou URL.

    Args:
        url: URL text extracted from a message.

    Returns:
        Cleaned URL text.
    """
    return url.rstrip(_URL_TRAILING_CHARS)


def _valid_hash(value):
    """Validate a 32-character Kugou song hash.

    Args:
        value: Candidate hash value.

    Returns:
        The candidate hash, or None when it is invalid.
    """
    return value if value and re.fullmatch(r"[0-9A-Fa-f]{32}", value) else None


def _is_kugou_host(url):
    """Check whether a URL host belongs to Kugou.

    Args:
        url: URL to inspect.

    Returns:
        True for kugou.com subdomains, otherwise False.
    """
    try:
        hostname = (urlparse(url).hostname or "").lower()
    except (TypeError, ValueError):
        return False
    return hostname == "kugou.com" or hostname.endswith(".kugou.com")


_HASH_PATTERNS = (
    r"(?i)(?:^|[?&#])(?:hash|filehash|songhash)=([0-9a-f]{32})(?:[&#]|$)",
    r"(?i)song/(?:#|%23)?([0-9a-f]{32})",
    r"(?i)(?:^|[?&#])chain=([0-9a-f]{32})(?:[&#]|$)",
    r"(?i)[\"\'](?:hash|filehash|songhash)[\"\']\s*[:=]\s*[\"\']([0-9a-f]{32})",
    r"(?i)data-(?:hash|filehash)=[\x27\x22]([0-9a-f]{32})",
    r"(?i)(?:hash|filehash)\s*=\s*([0-9a-f]{32})",
)


def _hash_from_value(value):
    """Extract a valid Kugou hash from one text value.

    Args:
        value: URL, message text, or resolved HTML.

    Returns:
        Uppercase 32-character hash, or None when absent.
    """
    value = str(value or "")
    try:
        query = parse_qs(urlparse(value).query)
    except (TypeError, ValueError):
        query = {}
    for key, values in query.items():
        if key.lower() not in {"hash", "filehash", "songhash"}:
            continue
        candidate = _valid_hash(values[0] if values else None)
        if candidate:
            return candidate.upper()
    for pattern in _HASH_PATTERNS:
        match = re.search(pattern, value)
        if match:
            return match.group(1).upper()
    return None


async def _extract_hash(text, url):
    """Extract a Kugou song hash from text, URL, or resolved HTML.

    Args:
        text: Original message text.
        url: Candidate Kugou URL.

    Returns:
        Uppercase 32-character song hash, or None when unavailable.
    """
    for candidate in (text, url):
        song_hash = _hash_from_value(candidate)
        if song_hash:
            return song_hash

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            response = await client.get(_clean_url(url))
            response.raise_for_status()
            html = response.text
            real_url = str(response.url)
        logger.info(f"酷狗真实地址:{real_url}")
        if not _is_kugou_host(real_url):
            logger.warning(f"酷狗链接跳转到非酷狗地址:{real_url}")
            return None
        for candidate in (real_url, html):
            song_hash = _hash_from_value(candidate)
            if song_hash:
                return song_hash
    except Exception as e:
        logger.warning(f"酷狗请求失败:{e}")
    return None


async def parse_kugou_card(text):
    """Resolve a Kugou URL and return its song metadata.

    Args:
        text: Message text containing a Kugou URL.

    Returns:
        Kugou song metadata, or None when the URL cannot be resolved.
    """
    match = re.search(r"https?://[^\s<>]+", text or "", re.IGNORECASE)
    if not match:
        return None
    url = _clean_url(match.group(0))
    if not _is_kugou_host(url):
        return None
    song_hash = await _extract_hash(text, url)
    if not song_hash or len(song_hash) != _HASH_LENGTH:
        logger.warning("未提取到酷狗hash")
        return None

    logger.info(f"酷狗hash:{song_hash}")
    try:
        async with httpx.AsyncClient(
            timeout=10, headers={"User-Agent": "Mozilla/5.0"}
        ) as client:
            response = await client.get(
                "https://m.kugou.com/app/i/getSongInfo.php",
                params={"cmd": "playInfo", "hash": song_hash},
            )
            response.raise_for_status()
            data = response.json()
        if isinstance(data.get("data"), dict):
            data = {**data, **data["data"]}
        title = (
            data.get("songName") or data.get("songname") or data.get("song_name") or ""
        )
        singer = (
            data.get("singerName") or data.get("singername") or data.get("singer") or ""
        )
    except Exception as e:
        logger.warning(f"酷狗歌曲信息请求失败:{e}")
        return None

    if not title:
        logger.warning("酷狗歌曲信息缺少歌名")
        return None
    logger.info(f"酷狗歌曲:{title} - {singer}")
    return {"title": str(title), "singer": str(singer)}
