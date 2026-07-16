import re
import httpx

from astrbot.core import logger


async def parse_kugou_card(text):
    m = re.search(r"https?://[^\s]+", text)
    if not m:
        return None

    url = m.group(0)

    # 直接从原始文本提取 hash(片段不经过HTTP)
    song_hash = None
    m2 = re.search(r"[#&]hash=([0-9A-Fa-f]+)", text)
    if m2:
        song_hash = m2.group(1).upper()

    # share页面的chain参数
    if not song_hash:
        m2 = re.search(r"chain=([0-9A-Za-z]+)", text)
        if m2:
            chain = m2.group(1)
            # 先试试chain本身就是hash
            if re.match(r"^[0-9A-Fa-f]{32}$", chain):
                song_hash = chain.upper()

    if not song_hash:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10,
                                         headers={"User-Agent": "Mozilla/5.0"}) as c:
                r = await c.get(url)
                real_url = str(r.url)
                logger.info(f"酷狗真实地址:{real_url}")

                # 从真实地址提取
                m2 = re.search(r"hash=([0-9A-Fa-f]+)", real_url)
                if m2:
                    song_hash = m2.group(1).upper()

                # 从页面HTML提取
                if not song_hash:
                    html = r.text
                    m2 = re.search(r'"hash"\s*:\s*"([0-9A-Fa-f]{32})"', html)
                    if m2:
                        song_hash = m2.group(1).upper()
                    if not song_hash:
                        m2 = re.search(r"data-hash=['\"]([0-9A-Fa-f]{32})", html)
                        if m2:
                            song_hash = m2.group(1).upper()
                    if not song_hash:
                        m2 = re.search(r'hash=([0-9A-Fa-f]{32})', html)
                        if m2:
                            song_hash = m2.group(1).upper()
        except Exception as e:
            logger.warning(f"酷狗请求失败:{e}")
            return None

    if not song_hash:
        logger.warning("未提取到酷狗hash")
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
