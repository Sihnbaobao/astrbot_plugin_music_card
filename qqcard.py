import re
import httpx

from astrbot.core import logger


QQ_API = "https://u.y.qq.com/cgi-bin/musicu.fcg"


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

        "music.trackInfo.UniformRuleCtrl": {

            "method": "GetTrackInfo",

            "module": "music.trackInfo.UniformRuleCtrl",

            "param": {

                "ids": [
                    int(songid)
                ]

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
            f"songid转换请求失败:{e}"
        )

        return None



    try:

        tracks = (
            data
            ["music.trackInfo.UniformRuleCtrl"]
            ["data"]
            ["tracks"]
        )


        if not tracks:

            return None


        mid = tracks[0].get(
            "mid"
        )


        logger.info(
            f"songid转换成功:{mid}"
        )


        return mid


    except Exception as e:

        logger.warning(
            f"songid转换解析失败:{e}"
        )

        return None




# =========================
# 获取QQ歌曲信息
# =========================

async def get_qq_song(song_mid):


    logger.info(
        f"获取QQ歌曲:{song_mid}"
    )


    payload = {

        "comm": {

            "ct": 24,
            "cv": 0

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
            f"QQ歌曲结构错误:{e}"
        )

        return None



    title = track.get(
        "name",
        ""
    )


    singers = track.get(
        "singer",
        []
    )


    singer = ""


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



    result = {

        "title":
        title,

        "singer":
        singer,

        "pic":
        pic,

        "url":
        f"https://y.qq.com/n/ryqq/songDetail/{song_mid}",

        # 后续vkey获取播放地址
        "audio":
        "",

        "songmid":
        song_mid

    }


    logger.info(
        f"QQ歌曲信息:{result}"
    )


    return result
# =========================
# QQ解析入口
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

        logger.warning(
            "没有找到QQ链接"
        )

        return None



    url = m.group(0)



    # 展开QQ短链

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


        # 重点：
        # QQ新版数字songDetail不是songid
        # 直接作为mid尝试

        song_mid = value




    # =========================
    # songmid参数
    # =========================

    if not song_mid:


        m = re.search(

            r"songmid=([0-9A-Za-z]+)",

            real_url

        )


        if m:


            value = m.group(1)


            song_mid = value





    # =========================
    # 老版songid参数
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
            "无法获取songmid"
        )

        return None





    logger.info(

        f"最终songmid:{song_mid}"

    )




    result = await get_qq_song(

        song_mid

    )



    return result
