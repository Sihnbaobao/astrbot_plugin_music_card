import re
import aiohttp
from urllib.parse import urlparse, parse_qs


async def expand_url(url):

    """
    QQ短链接展开
    """

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
            "短链展开失败:",
            e
        )


    return url





async def get_song_info(songid):


    api = "https://u.y.qq.com/cgi-bin/musicu.fcg"


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



    try:

        async with aiohttp.ClientSession() as session:


            async with session.post(

                api,

                json=data,

                timeout=10

            ) as r:


                js = await r.json()



        info = (
            js
            .get("songinfo",{})
            .get("data",{})
            .get("track_info")
        )


        if not info:

            print(
                "QQ接口没有返回歌曲信息"
            )

            return None



        return {


            "title":
            info.get(
                "name",
                "未知歌曲"
            ),


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

            f"https://y.gtimg.cn/music/photo_new/T002R300x300M000/{info['album']['mid']}.jpg",



            "cover":

            f"https://y.gtimg.cn/music/photo_new/T002R300x300M000/{info['album']['mid']}.jpg",



            "url":

            f"https://i.y.qq.com/v8/playsong.html?songmid={info['mid']}",



            "audio":

            f"https://i.y.qq.com/v8/playsong.html?songmid={info['mid']}",



            "songmid":

            info["mid"]

        }



    except Exception as e:


        print(
            "QQ歌曲查询失败:",
            e
        )


        return None





async def parse_qq_music(url):


    try:


        print(
            "原始QQ链接:",
            url
        )


        url = await expand_url(url)


        print(
            "展开后:",
            url
        )



        # songid

        m = re.search(

            r"songid[=/](\d+)",

            url

        )


        if m:


            print(
                "发现songid:",
                m.group(1)
            )


            return await get_song_info(
                m.group(1)
            )



        # songmid


        m = re.search(

            r"songmid[=/]([A-Za-z0-9]+)",

            url

        )


        if m:


            mid = m.group(1)


            return {


                "title":
                "QQ音乐歌曲",


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
                mid

            }



        print(
            "没有匹配songid/songmid"
        )


    except Exception as e:


        print(
            "QQ解析异常:",
            e
        )


    return None
