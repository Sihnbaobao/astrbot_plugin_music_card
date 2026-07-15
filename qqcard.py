import re
import httpx
import json

from astrbot.core import logger



# =========================
# 获取QQ歌曲信息
# =========================


async def get_qq_song(song_id):


    logger.info(
        f"尝试获取QQ歌曲信息:{song_id}"
    )


    api = (
        "https://u.y.qq.com/cgi-bin/musicu.fcg"
    )


    # QQ接口同时支持songid和mid
    payload = {


        "comm":{

            "ct":24,

            "cv":0

        },


        "songinfo":{

            "method":
            "get_song_detail_yqq",


            "module":
            "music.pf_song_detail_svr",


            "param":{

                "song_mid":
                song_id

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

                api,

                json=payload

            )


            data = r.json()



    except Exception as e:


        logger.warning(

            f"QQ接口请求失败:{e}"

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

            "QQ接口返回结构异常"

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


    if album.get("mid"):


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

        f"https://y.qq.com/n/ryqq/songDetail/{song_id}",


        "audio":

        f"https://i.y.qq.com/v8/playsong.html?songmid={song_id}"


    }



    logger.info(

        f"QQ歌曲信息:{result}"

    )


    return result






# =========================
# QQ卡片解析入口
# =========================


async def parse_qq_card(text):


    logger.info(

        f"QQ卡片解析输入:{text}"

    )



    # 找链接

    m = re.search(

        r"https?://[^\s]+",

        text

    )


    if not m:


        logger.warning(

            "没有发现QQ链接"

        )


        return None



    url = m.group(0)





    # ======================
    # 展开短链
    # ======================


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





    song_id = None




    # ======================
    # 新版songDetail
    # ======================


    m = re.search(

        r"songDetail/([0-9A-Za-z]+)",

        real_url

    )


    if m:


        song_id = m.group(1)





    # ======================
    # 老版songid
    # ======================


    if not song_id:


        m = re.search(

            r"songid=(\d+)",

            real_url

        )


        if m:


            song_id = m.group(1)





    # ======================
    # songmid
    # ======================


    if not song_id:


        m = re.search(

            r"songmid=([0-9A-Za-z]+)",

            real_url

        )


        if m:


            song_id = m.group(1)




    if not song_id:


        logger.warning(

            "无法提取QQ歌曲ID"

        )

        return None





    logger.info(

        f"QQ歌曲ID:{song_id}"

    )





    # 请求歌曲资料


    result = await get_qq_song(

        song_id

    )



    if result:


        return result



    return None
