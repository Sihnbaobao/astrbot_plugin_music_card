import re
import aiohttp
from urllib.parse import urlparse, parse_qs


async def expand_url(url):
    """
    展开QQ音乐短链接
    """

    if "c6.y.qq.com" not in url:
        return url

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                allow_redirects=False,
                timeout=10
            ) as resp:

                location = resp.headers.get("Location")

                if location:
                    return location

    except Exception as e:
        print("短链接解析失败:", e)

    return url



async def parse_qq_music(url):

    try:

        # 处理QQ短链接
        url = await expand_url(url)


        songmid = None


        # songid形式
        m = re.search(
            r"songid[=/](\d+)",
            url
        )

        if m:
            songid = m.group(1)

        else:
            songid = None


        # songmid形式
        m2 = re.search(
            r"songmid=([A-Za-z0-9]+)",
            url
        )

        if m2:
            songmid = m2.group(1)


        # 如果只有songid，去QQ接口获取信息

        if songid:

            api = (
                "https://u.y.qq.com/cgi-bin/musicu.fcg"
            )


            data = {
                "comm": {
                    "ct":24,
                    "cv":0
                },
                "songinfo":{
                    "method":"get_song_detail_yqq",
                    "module":"music.pf_song_detail_svr",
                    "param":{
                        "song_id":int(songid)
                    }
                }
            }


            async with aiohttp.ClientSession() as session:

                async with session.post(
                    api,
                    json=data,
                    timeout=10
                ) as r:

                    js = await r.json()


            info = (
                js
                .get("songinfo")
                .get("data")
                .get("track_info")
            )


            if info:

                return {
                    "title":
                        info["name"],

                    "singer":
                        ",".join(
                            [
                                x["name"]
                                for x in info["singer"]
                            ]
                        ),

                    "pic":
                        f"https://y.gtimg.cn/music/photo_new/T002R300x300M000/{info['album']['mid']}.jpg",

                    "cover":
                        f"https://y.gtimg.cn/music/photo_new/T002R300x300M000/{info['album']['mid']}.jpg",

                    "url":
                        url,

                    "audio":
                        url,

                    "songmid":
                        info["mid"]
                }



        # 已经有songmid

        if songmid:

            return {
                "title":None,
                "singer":None,
                "pic":None,
                "cover":None,
                "url":url,
                "audio":url,
                "songmid":songmid
            }


    except Exception as e:

        print(
            "QQ音乐解析异常:",
            e
        )


    return None
