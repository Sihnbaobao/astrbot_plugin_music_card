import re
import httpx

from astrbot.core import logger


QQ_API = "https://u.y.qq.com/cgi-bin/musicu.fcg"


# =========================
# songid 转 songmid
# =========================

async def convert_songid_to_mid(songid):

    logger.info(f"转换QQ songid:{songid}")

    payload = {
        "comm": {
            "ct": 24,
            "cv": 0
        },
        "music.search.SearchCgiService": {
            "method": "DoSearchForQQMusicDesktop",
            "module": "music.search.SearchCgiService",
            "param": {
                "query": songid,
                "num_per_page": 1,
                "page_num": 1
            }
        }
    }

    try:
        async with httpx.AsyncClient(
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        ) as client:

            r = await client.post(
                QQ_API,
                json=payload
            )

            data = r.json()

    except Exception as e:

        logger.warning(
            f"songid转换失败:{e}"
        )

        return None


    try:

        song = (
            data
            ["music.search.SearchCgiService"]
            ["data"]
            ["body"]
            ["song"]
            ["list"][0]
        )

        mid = song.get("mid")

        logger.info(
            f"songid转换mid成功:{mid}"
        )

        return mid

    except Exception as e:

        logger.warning(
            f"解析mid失败:{e}"
        )

        return None



# =========================
# 获取歌曲信息
# =========================

async def get_qq_song(song_mid):

    logger.info(
        f"获取QQ歌曲信息:{song_mid}"
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

    except Exception:

        logger.warning(
            "QQ歌曲数据为空"
        )

        return None



    title = track.get(
        "name",
        ""
    )


    singer = ""


    if track.get("singer"):

        singer = (
            track["singer"][0]
            .get(
                "name",
                ""
            )
        )


    album = track.get(
        "album",
        {}
    )


    pic = ""


    if album.get("mid"):

        pic = (
            "https://y.gtimg.cn/music/photo_new/"
            "T002R300x300M000/"
            + album["mid"]
            + ".jpg"
        )



    if not title:

        logger.warning(
            "歌曲标题为空"
        )

        return None



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
        f"https://isure.stream.qqmusic.qq.com/C400{song_mid}.m4a",


        "songmid":
        song_mid

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
        f"QQ解析输入:{text}"
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
            f"展开失败:{e}"
        )

        return None



    logger.info(
        f"QQ真实地址:{real_url}"
    )


    song_mid = None



    # mid

    m = re.search(
        r"songDetail/([0-9A-Za-z]+)",
        real_url
    )


    if m:

        value = m.group(1)

        # 数字不是mid
        if not value.isdigit():

            song_mid = value

        else:

            song_mid = await convert_songid_to_mid(
                value
            )



    # songmid参数

    if not song_mid:

        m = re.search(
            r"songmid=([0-9A-Za-z]+)",
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



    # songid

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
            "无法获取songmid"
        )

        return None



    logger.info(
        f"最终songmid:{song_mid}"
    )



    return await get_qq_song(
        song_mid
    )
