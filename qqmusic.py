import re
import aiohttp


async def expand_url(url):

    if "c6.y.qq.com" not in url:
        return url


    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                url,
                allow_redirects=True,
                timeout=10
            ) as resp:

                return str(resp.url)


    except Exception as e:

        print(
            "QQ短链接展开失败:",
            e
        )


    return url



async def parse_qq_music(url):


    try:

        # 展开短链接

        url = await expand_url(url)


        print(
            "QQ最终URL:",
            url
        )


        songid = None
        songmid = None



        m = re.search(
            r"songid=(\d+)",
            url
        )


        if m:

            songid = m.group(1)



        m = re.search(
            r"songmid=([A-Za-z0-9]+)",
            url
        )


        if m:

            songmid = m.group(1)



        # songid获取信息

        if songid:


            api = (
                "https://u.y.qq.com/cgi-bin/musicu.fcg"
            )


            data = {

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

                        "song_id":
                        int(songid)

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
                .get("songinfo", {})
                .get("data", {})
                .get("track_info")
            )



            if info:


                album_mid = (
                    info
                    .get("album", {})
                    .get("mid","")
                )


                return {


                    "title":
                    info.get("name"),


                    "singer":
                    ",".join(
                        [
                            x.get("name","")
                            for x in info.get(
                                "singer",
                                []
                            )
                        ]
                    ),


                    "pic":
                    f"https://y.gtimg.cn/music/photo_new/T002R300x300M000/{album_mid}.jpg",


                    "cover":
                    f"https://y.gtimg.cn/music/photo_new/T002R300x300M000/{album_mid}.jpg",


                    "url":
                    url,


                    "audio":
                    url,


                    "songmid":
                    info.get("mid")

                }



        # songmid至少生成卡片

        if songmid:


            return {

                "title":
                "QQ音乐",


                "singer":
                "",


                "pic":
                "",


                "cover":
                "",


                "url":
                url,


                "audio":
                url,


                "songmid":
                songmid

            }



    except Exception as e:

        print(
            "QQ解析异常:",
            e
        )



    return None
