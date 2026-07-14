import re
import httpx
from urllib.parse import unquote


async def parse_qq_music(text):

    result = {
        "title": None,
        "singer": None,
        "pic": None,
        "url": None,
        "audio": None,
        "songmid": None
    }


    songmid = None


    # 直接songmid

    mid = re.search(
        r"songmid=([A-Za-z0-9]+)",
        text
    )

    if mid:

        songmid = mid.group(1)



    # =====================
    # songid分享页解析
    # =====================

    if not songmid and "songid=" in text:

        try:

            async with httpx.AsyncClient(
                timeout=10,
                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                },
                follow_redirects=True

            ) as client:


                r = await client.get(text)


                html = r.text



                print(
                    "QQ网页长度:",
                    len(html)
                )


                # 找songmid

                mid = re.search(
                    r'"songmid":"([A-Za-z0-9]+)"',
                    html
                )


                if mid:

                    songmid = mid.group(1)


                    print(
                        "网页找到songmid:",
                        songmid
                    )



        except Exception as e:

            print(
                "网页解析失败:",
                e
            )



    if not songmid:

        print(
            "没有找到songmid"
        )

        return result



    # =====================
    # 获取详情
    # =====================


    try:


        async with httpx.AsyncClient(
            timeout=10
        ) as client:


            api = (
                "https://u.y.qq.com/cgi-bin/musicu.fcg"
            )


            data = {

                "comm":{
                    "ct":24,
                    "cv":0
                },


                "songinfo":{

                    "module":
                    "music.pf_song_detail_svr",

                    "method":
                    "get_song_detail_yqq",

                    "param":{

                        "song_mid":
                        songmid

                    }

                }

            }


            r = await client.post(
                api,
                json=data
            )


            j=r.json()


            info=(
                j
                ["songinfo"]
                ["data"]
                ["track_info"]
            )


            result["title"]=info["name"]


            result["singer"]=",".join(
                [
                    x["name"]
                    for x in info["singer"]
                ]
            )


            result["pic"]=(
                "https://y.gtimg.cn/music/photo_new/"
                "T002R300x300M000/"
                +
                info["album"]["mid"]
                +
                ".jpg"
            )


            result["url"]=(
                "https://i.y.qq.com/v8/playsong.html?"
                "songmid="
                +
                songmid
            )


            result["audio"]=result["url"]


            result["songmid"]=songmid



            return result



    except Exception as e:

        print(
            "详情获取失败:",
            e
        )

        return result
