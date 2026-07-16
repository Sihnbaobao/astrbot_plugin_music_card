import re
import httpx

from base64 import b64encode
from hashlib import sha1
import json as _json
import time as _time

from astrbot.core import logger


QQ_API = "https://u.y.qq.com/cgi-bin/musicu.fcg"


QQ_API_NEW = "https://u6.y.qq.com/cgi-bin/musics.fcg"


PART_1_INDEXES = [23, 14, 6, 36, 16, 7, 19]

PART_2_INDEXES = [16, 1, 32, 12, 19, 27, 8, 5]

SCRAMBLE_VALUES = [
    89, 39, 179, 150, 218, 82, 58, 252, 177, 52,
    186, 123, 120, 64, 242, 133, 143, 161, 121, 179,
]


def zzc_sign(payload):

    if isinstance(payload, str):

        payload_bytes = payload.encode("utf-8")

    else:

        payload_bytes = bytes(payload)

    hash_hex = sha1(payload_bytes).hexdigest().upper()

    part1 = "".join(hash_hex[i] for i in PART_1_INDEXES)

    part2 = "".join(hash_hex[i] for i in PART_2_INDEXES)

    part3 = bytearray(20)

    for i, v in enumerate(SCRAMBLE_VALUES):

        part3[i] = v ^ int(hash_hex[i * 2 : i * 2 + 2], 16)

    b64_part = re.sub(
        rb"[\\/+=]",
        b"",
        b64encode(part3)
    ).decode("utf-8")

    return f"zzc{part1}{b64_part}{part2}".lower()


_qq_cookie = ""

_qq_uin = 0


def set_qq_credential(cookie):

    global _qq_cookie, _qq_uin

    _qq_cookie = (cookie or "").strip()

    _qq_uin = _parse_cookie_uin(_qq_cookie)

    logger.info(
        f"已设置QQ凭据:cookie长度={len(_qq_cookie)}, uin={_qq_uin}"
    )


def has_qq_credential():

    return bool(_qq_cookie and "qm_keyst=" in _qq_cookie)


def _parse_cookie_uin(cookie):

    if not cookie:

        return 0

    m = re.search(
        r"(?:^|;|\s)uin=o?(\d+)",
        cookie
    )

    if m:

        try:

            return int(m.group(1))

        except ValueError:

            return 0

    m = re.search(
        r"(?:^|;|\s)wxuin=o?(\d+)",
        cookie
    )

    if m:

        try:

            return int(m.group(1))

        except ValueError:

            return 0

    return 0


# =========================
# songid 转 songmid
# =========================

async def convert_songid_to_mid(songid):

    logger.info(
        f"转换QQ songid:{songid}"
    )


    payload = {

        "comm": {
            "ct": 24,
            "cv": 0
        },


        "music.pf_song_detail_svr": {

            "method":
            "get_song_detail_yqq",


            "module":
            "music.pf_song_detail_svr",


            "param": {

                "song_id":
                int(songid)

            }

        }

    }


    try:

        async with httpx.AsyncClient(
            timeout=10,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        ) as client:


            r = await client.post(
                QQ_API,
                json=payload
            )


            data = r.json()



    except Exception as e:


        logger.warning(
            f"songid请求失败:{e}"
        )

        return None





    try:


        track = (

            data

            ["music.pf_song_detail_svr"]

            ["data"]

            ["track_info"]

        )


        mid = track.get(
            "mid"
        )


        if mid:


            logger.info(
                f"songid转换成功:{mid}"
            )


            return mid



    except Exception as e:


        logger.warning(
            f"songid转换失败:{e}"
        )



    return None





# =========================
# 获取可播放音频URL(vkey)
# =========================

async def get_playable_audio(song_mid):

    logger.info(
        f"获取vkey:{song_mid}"
    )


    filename = f"C400{song_mid}.m4a"


    logged_in = has_qq_credential()


    comm_uin = (

        _qq_uin

        if logged_in

        else 0

    )


    param_uin = (

        str(_qq_uin)

        if logged_in

        else "0"

    )


    loginflag = (

        1

        if logged_in

        else 0

    )


    platform = "h5" if logged_in else "20"


    payload = {

        "comm": {
            "ct": 24,
            "cv": 0,
            "uin": comm_uin,
            "format": "json",
            "platform": platform
        },

        "req": {
            "module":
            "music.vkey.GetVkeyServer",

            "method":
            "GetVkey",

            "param": {
                "filename": [filename],
                "guid": "10000",
                "songmid": [song_mid],
                "songtype": [0],
                "uin": param_uin,
                "loginflag": loginflag,
                "platform": platform
            }
        }

    }


    headers = {

        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",

        "Referer":
        "https://y.qq.com/",

        "Origin":
        "https://y.qq.com",

        "Content-Type":
        "application/x-www-form-urlencoded"
    }


    if logged_in:

        headers["Cookie"] = _qq_cookie

        logger.info(
            f"vkey请求以登录态发起, uin={_qq_uin}"
        )


    body_str = _json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":")
    )

    sign = zzc_sign(body_str)

    url = (
        f"{QQ_API_NEW}"
        f"?_webcgikey=GetVkey"
        f"&sign={sign}"
        f"&_={int(_time.time() * 1000)}"
    )

    logger.info(
        f"vkey请求URL:{url}"
    )


    try:

        async with httpx.AsyncClient(
            timeout=10,
            headers=headers
        ) as client:

            r = await client.post(
                url,
                data=body_str
            )

            data = r.json()

    except Exception as e:

        logger.warning(
            f"vkey请求失败:{e}"
        )

        return None


    try:

        import json as _json

        logger.info(
            f"vkey原始响应:{_json.dumps(data, ensure_ascii=False)[:1000]}"
        )


        found = None

        for k, v in data.items():

            if k == "comm":

                continue

            if isinstance(v, dict):

                inner = v.get("data")

                if isinstance(inner, dict) and "midurlinfo" in inner:

                    found = inner

                    logger.info(
                        f"vkey命中key:{k}"
                    )

                    break


        if found:

            sip = found.get("sip", [])

            infos = found.get("midurlinfo", [])

            if infos and sip:

                purl = infos[0].get("purl", "")

                if purl:

                    audio = sip[0] + purl

                    logger.info(
                        f"vkey获取成功:{audio}"
                    )

                    return audio

                logger.warning(
                    "vkey返回purl为空,可能歌曲无版权或需要登录"
                )

            else:

                logger.warning(
                    f"vkey无sip或midurlinfo:sip={sip} infos={infos}"
                )

        else:

            logger.warning(
                "vkey响应中未找到midurlinfo"
            )

    except Exception as e:

        logger.warning(
            f"vkey解析失败:{e}"
        )


    return None




# =========================
# 获取歌曲信息
# =========================


async def get_qq_song(song_mid):


    logger.info(
        f"获取QQ歌曲:{song_mid}"
    )


    payload = {


        "comm": {

            "ct":24,
            "cv":0

        },


        "songinfo": {


            "method":
            "get_song_detail_yqq",


            "module":
            "music.pf_song_detail_svr",


            "param": {

                "song_mid":
                song_mid

            }

        }

    }



    try:


        async with httpx.AsyncClient(

            timeout=10,

            headers={

                "User-Agent":
                "Mozilla/5.0"

            }

        ) as client:


            r = await client.post(

                QQ_API,

                json=payload

            )


            data = r.json()



    except Exception as e:


        logger.warning(
            f"QQ歌曲请求失败:{e}"
        )


        return None





    try:


        track = (

            data

            ["songinfo"]

            ["data"]

            ["track_info"]

        )


    except Exception as e:


        logger.warning(
            f"歌曲结构错误:{e}"
        )


        return None





    title = track.get(
        "name",
        ""
    )



    singer = ""


    singers = track.get(
        "singer",
        []
    )


    if singers:


        singer = singers[0].get(
            "name",
            ""
        )



    album = track.get(
        "album",
        {}
    )


    pic = ""


    if album.get(
        "mid"
    ):


        pic = (

            "https://y.gtimg.cn/music/photo_new/"
            "T002R300x300M000/"
            +
            album["mid"]
            +
            ".jpg"

        )





    audio = await get_playable_audio(song_mid)


    if not audio:

        audio = f"https://isure.stream.qqmusic.qq.com/C400{song_mid}.m4a?guid=10000&uin=0&fromtag=66"


    result = {


        "title":
        title,


        "singer":
        singer,


        "pic":
        pic,


        "url":
        f"https://y.qq.com/n/ryqq/songDetail/{song_mid}",


        "audio":
        audio,


        "songmid":
        song_mid,


        "song_id":
        track.get("id", 0)


    }



    logger.info(
        f"QQ歌曲信息:{result}"
    )


    return result







# =========================
# QQ链接解析
# =========================


async def parse_qq_card(text):


    logger.info(
        f"QQ卡片解析输入:{text}"
    )



    m = re.search(
        r"https?://[^\s]+",
        text
    )


    if not m:

        return None



    url = m.group(0)



    try:


        async with httpx.AsyncClient(

            follow_redirects=True,

            timeout=10,

            headers={

                "User-Agent":
                "Mozilla/5.0"

            }

        ) as client:


            r = await client.get(
                url
            )


            real_url = str(
                r.url
            )


    except Exception as e:


        logger.warning(
            f"QQ链接展开失败:{e}"
        )


        return None





    logger.info(
        f"QQ真实地址:{real_url}"
    )



    song_mid = None




    # =========================
    # songDetail
    # =========================


    m = re.search(
        r"songDetail/([0-9A-Za-z]+)",
        real_url
    )


    if m:


        value = m.group(1)



        if value.isdigit():


            song_mid = await convert_songid_to_mid(
                value
            )


        else:


            song_mid = value





    # =========================
    # songmid
    # =========================


    if not song_mid:


        m = re.search(
            r"songmid=([0-9A-Za-z]+)",
            real_url
        )


        if m:


            song_mid = m.group(1)





    # =========================
    # songid
    # =========================


    if not song_mid:


        m = re.search(
            r"songid=(\d+)",
            real_url
        )


        if m:


            song_mid = await convert_songid_to_mid(
                m.group(1)
            )




    if not song_mid:


        logger.warning(
            "无法获得songmid"
        )


        return None





    logger.info(
        f"最终songmid:{song_mid}"
    )



    return await get_qq_song(
        song_mid
    )
