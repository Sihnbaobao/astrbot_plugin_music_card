import re
import httpx

from astrbot.core import logger


async def _extract_hash(text, url):
    """从文本/URL/HTML中提取酷狗32位hash"""
    m = re.search(r"[#&]hash=([0-9A-Fa-f]+)", text)
    if m:
        return m.group(1).upper()
    m = re.search(r"song/#([0-9A-Za-z]+)", text)
    if m:
        return m.group(1).upper()
    m = re.search(r"chain=([0-9A-Za-z]+)", text)
    if m and re.match(r"^[0-9A-Fa-f]{32}$", m.group(1)):
        return m.group(1).upper()

    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        ) as c:
            r = await c.get(url)
            html, real_url = r.text, str(r.url)
            logger.info(f"酷狗真实地址:{real_url}")

            m = re.search(r"hash=([0-9A-Fa-f]+)", real_url)
            if m:
                return m.group(1).upper()
            for p in (
                r'"hash"\s*:\s*"([0-9A-Fa-f]{32})"',
                r"data-hash=['\"]([0-9A-Fa-f]{32})",
                r'hash=([0-9A-Fa-f]{32})',
            ):
                m = re.search(p, html)
                if m:
                    return m.group(1).upper()
    except Exception as e:
        logger.warning(f"酷狗请求失败:{e}")
    return None


async def parse_kugou_card(text):
    m = re.search(r"https?://[^\s]+", text)
    if not m:
        return None

    song_hash = await _extract_hash(text, m.group(0))
    if not song_hash or len(song_hash) < 32:
        logger.warning("未提取到酷狗hash(SPA页面暂不支持)")
        return None

    logger.info(f"酷狗hash:{song_hash}")

    try:
        async with httpx.AsyncClient(
            timeout=10, headers={"User-Agent": "Mozilla/5.0"}
        ) as c:
            data = (await c.get(
                "https://m.kugou.com/app/i/getSongInfo.php"
                f"?cmd=playInfo&hash={song_hash}"
            )).json()
            title = data.get("songName", "")
            singer = data.get("singerName", "")
    except Exception as e:
        logger.warning(f"酷狗歌曲信息请求失败:{e}")
        return None

    if not title:
        return None
    logger.info(f"酷狗歌曲:{title} - {singer}")
    return {"title": title, "singer": singer}
