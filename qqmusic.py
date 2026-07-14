import re
import httpx


async def parse_qq_music(text):

    print("================")
    print("进入QQ解析")
    print(text)
    print("================")


    result = {

        "title": None,
        "singer": None,
        "pic": None,
        "url": None,
        "audio": None,
        "songmid": None

    }



    # =====================
    # 处理QQ短链
    # =====================


    if "c6.y.qq.com" in text:


        try:


            async with httpx.AsyncClient(

                timeout=10,

                follow_redirects=True,

                headers={

                    "User-Agent":
                    "Mozilla/5.0"

                }

            ) as client:


                r = await client.get(text)


                text = str(r.url)


                print(
                    "短链展开:",
                    text
                )


        except Exception as e:


            print(
                "短链展开失败:",
                e
            )



    songmid = None



    # =====================
    # 提取songmid
    # =====================


    mid = re.search(

        r"songmid=([A-Za-z0-9]+)",

        text

    )


    if mid:

        songmid = mid.group(1)



    print(
        "发现songmid:",
        songmid
    )



    if not songmid:


        print(
            "没有songmid，无法继续"
        )

        return result



    # =====================
    # QQ详情API
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


            j = r.json()



            info = (

                j

                ["songinfo"]

                ["data"]

                ["track_info"]

            )



            result["title"] = info["name"]



            result["singer"] = ",".join(

                [

                    x["name"]

                    for x in info["singer"]

                ]

            )



            result["pic"] = (

                "https://y.gtimg.cn/music/photo_new/"

                "T002R300x300M000/"

                +

                info["album"]["mid"]

                +

                ".jpg"

            )



            result["url"] = (

                "https://i.y.qq.com/v8/playsong.html?"

                "songmid="

                +

                songmid

            )


            result["audio"] = result["url"]


            result["songmid"] = songmid



            return result



    except Exception as e:


        print(

            "QQ详情失败:",

            e

        )


        return result
