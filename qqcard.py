import re
import httpx

from astrbot.core import logger



async def parse_qq_card(text):

    logger.info(
        f"QQ卡片解析输入:{text}"
    )


    # =========================
    # 提取URL
    # =========================

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



    # =========================
    # 展开QQ短链
    # =========================

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
            f"QQ短链展开失败:{e}"
        )

        return None



    logger.info(
        f"QQ真实地址:{real_url}"
    )



    # =========================
    # 获取songmid
    # =========================


    songmid = None


    m = re.search(

        r"songmid=([A-Za-z0-9]+)",

        real_url

    )


    if m:

        songmid = m.group(1)



    # 部分QQ分享是songid

    if not songmid:


        m = re.search(

            r"songid=(\d+)",

            real_url

        )


        if m:

            songmid = m.group(1)



    if not songmid:


        logger.warning(
            "没有找到songmid"
        )

        return None



    logger.info(
        f"QQ歌曲ID:{songmid}"
    )



    # =========================
    # 请求QQ音乐歌曲信息
    # =========================


    api = (
        "https://u.y.qq.com/cgi-bin/musicu.fcg"
    )


    payload = {

        "comm":{

            "ct":24,

            "cv":0

        },

        "songinfo":{

            "method":
            "get_song_detail_yqq",

            "param":{

                "song_mid":
                songmid

            },

            "module":
            "music.pf_song_detail_svr"

        }

    }



    try:


        async with httpx.AsyncClient(

            timeout=10

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


        song = (
            data
            ["songinfo"]
            ["data"]
            ["track_info"]
        )


    except Exception:


        logger.warning(
            "QQ歌曲数据结构异常"
        )

        return None




    title = song.get(
        "name",
        ""
    )


    singer = ""


    singers = song.get(
        "singer",
        []
    )


    if singers:


        singer = singers[0].get(
            "name",
            ""
        )



    album = song.get(
        "album",
        {}
    )


    mid = song.get(
        "mid",
        ""
    )



    pic = ""

    if album.get("mid"):


        pic = (
            "https://y.gtimg.cn/music/photo_new/"
            "T002R300x300M000/"
            f"{album['mid']}.jpg"
        )




    result = {


        "title":
        title,


        "singer":
        singer,


        "pic":
        pic,


        "url":
        real_url,


        "audio":
        real_url


    }



    logger.info(
        f"QQ卡片结果:{result}"
    )


    return result
