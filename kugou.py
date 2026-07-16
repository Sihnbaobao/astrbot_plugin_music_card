import re
import httpx

from astrbot.core import logger


async def parse_kugou_card(text):
    m = re.search(r"https?://[^\s]+", text)
    if not m:
        return None

    url = m.group(0)

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10,
                                     headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.get(url)
            real_url = str(r.url)
    except Exception as e:
        logger.warning(f"酷狗链接展开失败:{e}")
        return None

    logger.info(f"酷狗真实地址:{real_url}")

    song_hash = None

    m2 = re.search(r"hash=([0-9A-Fa-f]+)", real_url)
    if m2:
        song_hash = m2.group(1).upper()

    if not song_hash:
        m2 = re.search(r"/([0-9A-Fa-f]{32})(?:\.html|\?|$)", real_url)
        if m2:
            song_hash = m2.group(1).upper()

    if not song_hash:
        return None

    logger.info(f"酷狗hash:{song_hash}")

    info_url = (
        "https://m.kugou.com/app/i/getSongInfo.php"
        f"?cmd=playInfo&hash={song_hash}"
    )

    try:
        async with httpx.AsyncClient(timeout=10,
                                     headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.get(info_url)
            data = r.json()
    except Exception as e:
        logger.warning(f"酷狗歌曲信息请求失败:{e}")
        return None

    try:
        title = data.get("songName", "")
        singer = data.get("singerName", "")
    except Exception:
        return None

    if not title:
        return None

    logger.info(f"酷狗歌曲:{title} - {singer}")
    return {"title": title, "singer": singer}
