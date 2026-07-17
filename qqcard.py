import re
import httpx

from astrbot.core import logger


QQ_API = "https://u.y.qq.com/cgi-bin/musicu.fcg"


async def convert_songid_to_mid(songid):
    payload = {
        "comm": {"ct": 24, "cv": 0},
        "music.pf_song_detail_svr": {
            "method": "get_song_detail_yqq",
            "module": "music.pf_song_detail_svr",
            "param": {"song_id": int(songid)}
        }
    }
    try:
        async with httpx.AsyncClient(
            timeout=10, headers={"User-Agent": "Mozilla/5.0"}
        ) as c:
            r = await c.post(QQ_API, json=payload)
            mid = (
                r.json()
                ["music.pf_song_detail_svr"]
                ["data"]["track_info"]["mid"]
            )
            logger.info(f"songid->mid:{songid}->{mid}")
            return mid
    except Exception as e:
        logger.warning(f"songid转换失败:{e}")
    return None


async def get_qq_song(song_mid):
    payload = {
        "comm": {"ct": 24, "cv": 0},
        "songinfo": {
            "method": "get_song_detail_yqq",
            "module": "music.pf_song_detail_svr",
            "param": {"song_mid": song_mid}
        }
    }
    try:
        async with httpx.AsyncClient(
            timeout=10, headers={"User-Agent": "Mozilla/5.0"}
        ) as c:
            r = await c.post(QQ_API, json=payload)
            track = r.json()["songinfo"]["data"]["track_info"]
    except Exception as e:
        logger.warning(f"歌曲请求失败:{e}")
        return None

    title = track.get("name", "")
    singer = ""
    if track.get("singer"):
        singer = track["singer"][0].get("name", "")
    pic = ""
    album_mid = track.get("album", {}).get("mid", "")
    if album_mid:
        pic = (
            "https://y.gtimg.cn/music/photo_new/"
            f"T002R500x500M000/{album_mid}.jpg"
        )

    return {
        "title": title,
        "singer": singer,
        "pic": pic,
        "url": f"https://y.qq.com/n/ryqq/songDetail/{song_mid}",
        "audio": (
            f"https://isure.stream.qqmusic.qq.com/"
            f"C400{song_mid}.m4a?guid=10000&uin=0&fromtag=66"
        ),
        "songmid": song_mid,
        "song_id": track.get("id", 0)
    }


async def parse_qq_card(text):
    m = re.search(r"https?://[^\s]+", text)
    if not m:
        return None

    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        ) as c:
            real_url = str((await c.get(m.group(0))).url)
    except Exception as e:
        logger.warning(f"链接展开失败:{e}")
        return None

    logger.info(f"QQ真实地址:{real_url}")

    song_mid = None
    m2 = re.search(r"songDetail/([0-9A-Za-z]+)", real_url)
    if m2:
        val = m2.group(1)
        song_mid = await convert_songid_to_mid(val) if val.isdigit() else val
    if not song_mid:
        m2 = re.search(r"songmid=([0-9A-Za-z]+)", real_url)
        if m2:
            song_mid = m2.group(1)
    if not song_mid:
        m2 = re.search(r"songid=(\d+)", real_url)
        if m2:
            song_mid = await convert_songid_to_mid(m2.group(1))

    if not song_mid:
        return None

    logger.info(f"最终songmid:{song_mid}")
    return await get_qq_song(song_mid)
