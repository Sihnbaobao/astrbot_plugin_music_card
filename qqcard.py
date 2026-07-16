import re
import httpx
import json as _json
import time as _time

from base64 import b64encode
from hashlib import sha1

from astrbot.core import logger


QQ_API = "https://u.y.qq.com/cgi-bin/musicu.fcg"
QQ_API_V2 = "https://u6.y.qq.com/cgi-bin/musics.fcg"


PART_1 = [23, 14, 6, 36, 16, 7, 19]
PART_2 = [16, 1, 32, 12, 19, 27, 8, 5]
SCRAMBLE = [89, 39, 179, 150, 218, 82, 58, 252, 177, 52,
            186, 123, 120, 64, 242, 133, 143, 161, 121, 179]


def zzc_sign(text):

    if isinstance(text, str):
        text = text.encode()
    h = sha1(text).hexdigest().upper()
    p1 = "".join(h[i] for i in PART_1)
    p2 = "".join(h[i] for i in PART_2)
    p3 = bytearray(20)
    for i, v in enumerate(SCRAMBLE):
        p3[i] = v ^ int(h[i * 2:i * 2 + 2], 16)
    b64 = re.sub(rb"[\\/+=]", b"", b64encode(p3)).decode()
    return f"zzc{p1}{b64}{p2}".lower()


async def get_playable_url(song_mid, uin=0, cookie=""):

    logger.info(f"获取播放URL:{song_mid}")

    body = {
        "comm": {
            "ct": 23,
            "cv": 0,
            "uin": uin,
            "format": "json",
            "inCharset": "utf-8",
            "outCharset": "utf-8",
            "notice": 0,
            "platform": "h5",
            "needNewCode": 1
        },
        "req_0": {
            "module": "music.vkey.GetVkeyServer",
            "method": "GetVkey",
            "param": {
                "guid": "10000",
                "songmid": [song_mid],
                "songtype": [0],
                "filename": [f"C400{song_mid}.m4a"],
                "uin": str(uin),
                "loginflag": 1 if uin else 0,
                "platform": "20"
            }
        }
    }

    body_str = _json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    sign = zzc_sign(body_str)
    url = f"{QQ_API_V2}?_webcgikey=GetVkey&sign={sign}&_={int(_time.time() * 1000)}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://y.qq.com/",
        "Origin": "https://y.qq.com",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    if cookie:
        headers["Cookie"] = cookie
        logger.info("vkey请求带Cookie")

    try:
        async with httpx.AsyncClient(timeout=10, headers=headers) as c:
            r = await c.post(url, data=body_str)
            data = r.json()
    except Exception as e:
        logger.warning(f"vkey请求失败:{e}")
        return None

    try:
        inner = data.get("req_0", {})
        code = inner.get("code", -1)
        logger.info(f"vkey响应:code={code}, keys={list(inner.keys())[:5]}")

        if code == 0:
            d = inner.get("data", {})
            sip = d.get("sip", [])
            midurlinfo = d.get("midurlinfo", [])
            if midurlinfo and sip:
                purl = midurlinfo[0].get("purl", "")
                if purl:
                    audio = sip[0] + purl
                    logger.info(f"vkey成功:{audio[:80]}...")
                    return audio
                logger.warning("vkey purl为空")
            else:
                logger.warning(f"vkey无数据:sip={sip},info={midurlinfo}")
        else:
            logger.warning(f"vkey code={code}, subcode={inner.get('subcode')}")
    except Exception as e:
        logger.warning(f"vkey解析失败:{e}")

    return None


async def convert_songid_to_mid(songid):

    logger.info(f"转换QQ songid:{songid}")

    payload = {
        "comm": {"ct": 24, "cv": 0},
        "music.pf_song_detail_svr": {
            "method": "get_song_detail_yqq",
            "module": "music.pf_song_detail_svr",
            "param": {"song_id": int(songid)}
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.post(QQ_API, json=payload)
            data = r.json()
    except Exception as e:
        logger.warning(f"songid请求失败:{e}")
        return None

    try:
        mid = data["music.pf_song_detail_svr"]["data"]["track_info"].get("mid")
        if mid:
            logger.info(f"songid转换成功:{mid}")
            return mid
    except Exception as e:
        logger.warning(f"songid转换失败:{e}")

    return None


async def get_qq_song(song_mid):

    logger.info(f"获取QQ歌曲:{song_mid}")

    payload = {
        "comm": {"ct": 24, "cv": 0},
        "songinfo": {
            "method": "get_song_detail_yqq",
            "module": "music.pf_song_detail_svr",
            "param": {"song_mid": song_mid}
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.post(QQ_API, json=payload)
            data = r.json()
    except Exception as e:
        logger.warning(f"QQ歌曲请求失败:{e}")
        return None

    try:
        track = data["songinfo"]["data"]["track_info"]
    except Exception as e:
        logger.warning(f"歌曲结构错误:{e}")
        return None

    title = track.get("name", "")
    singer = (track.get("singer", [{}])[0].get("name", "") if track.get("singer") else "")
    album_mid = (track.get("album", {}).get("mid", ""))

    pic = ""
    if album_mid:
        pic = f"https://y.gtimg.cn/music/photo_new/T002R500x500M000/{album_mid}.jpg"

    audio = f"https://isure.stream.qqmusic.qq.com/C400{song_mid}.m4a?guid=10000&uin=0&fromtag=66"

    playable = await get_playable_url(song_mid)
    if playable:
        audio = playable

    result = {
        "title": title,
        "singer": singer,
        "pic": pic,
        "url": f"https://y.qq.com/n/ryqq/songDetail/{song_mid}",
        "audio": audio,
        "songmid": song_mid,
        "song_id": track.get("id", 0)
    }

    logger.info(f"QQ歌曲信息:{result}")
    return result


async def parse_qq_card(text):

    logger.info(f"QQ卡片解析输入:{text}")

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
        logger.warning(f"QQ链接展开失败:{e}")
        return None

    logger.info(f"QQ真实地址:{real_url}")

    song_mid = None

    m = re.search(r"songDetail/([0-9A-Za-z]+)", real_url)
    if m:
        value = m.group(1)
        if value.isdigit():
            song_mid = await convert_songid_to_mid(value)
        else:
            song_mid = value

    if not song_mid:
        m = re.search(r"songmid=([0-9A-Za-z]+)", real_url)
        if m:
            song_mid = m.group(1)

    if not song_mid:
        m = re.search(r"songid=(\d+)", real_url)
        if m:
            song_mid = await convert_songid_to_mid(m.group(1))

    if not song_mid:
        logger.warning("无法获得songmid")
        return None

    logger.info(f"最终songmid:{song_mid}")
    return await get_qq_song(song_mid)
