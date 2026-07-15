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

            "method":
            "GetTrackInfo",

            "module":
            "music.trackInfo.UniformRuleCtrl",

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
            f"songid转换请求失败:{e}"
        )

        return None



    try:

        track = (
            data
            ["music.trackInfo.UniformRuleCtrl"]
            ["data"]
            ["tracks"]
            [0]
        )


        mid = track.get(
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
# 获取真实播放地址
# =========================

async def get_play_url(song_mid):


    logger.info(
        f"获取QQ播放地址:{song_mid}"
    )


    payload = {

        "comm": {

            "ct":24,
            "cv":0

        },


        "music.vkey.GetVkeyServer": {

            "method":
            "CgiGetVkey",


            "module":
            "music.vkey.GetVkeyServer",


            "param": {

                "guid":
                "10000",


                "songmid": [

                    song_mid

                ],


                "songtype": [

                    0

                ],


                "uin":
                "0",


                "loginflag":
                1,


                "platform":
                "20"

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
            f"获取播放地址失败:{e}"
        )

        return ""




    try:


        info = (

            data

            ["music.vkey.GetVkeyServer"]

            ["data"]

        )


        sip = info.get(

            "sip",

            []

        )


        midurlinfo = info.get(

            "midurlinfo",

            []

        )


        if sip and midurlinfo:


            purl = midurlinfo[0].get(

                "purl",

                ""

            )


            if purl:


                url = sip[0] + purl


                logger.info(

                    f"真实播放地址:{url}"

                )


                return url




    except Exception as e:


        logger.warning(

            f"播放地址解析失败:{e}"

        )



    return ""





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


    except Exception:


        logger.warning(

            "QQ歌曲结构错误"

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





    audio = await get_play_url(

        song_mid

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



        "audio":

        audio,



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



    # songDetail

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





    # songmid

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

            "无法获得songmid"

        )

        return None





    logger.info(

        f"最终songmid:{song_mid}"

    )



    return await get_qq_song(

        song_mid

    )
