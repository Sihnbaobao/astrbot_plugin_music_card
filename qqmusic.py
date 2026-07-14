import re
import httpx


async def parse_qq_music(text):

    songmid = None
    songid = None


    mid = re.search(
        r"songmid=([A-Za-z0-9]+)",
        text
    )

    if mid:
        songmid = mid.group(1)


    sid = re.search(
        r"songid=(\d+)",
        text
    )

    if sid:
        songid = sid.group(1)



    # 如果只有 songid
    # 转换成 songmid

    if not songmid and songid:

        print(
            "尝试songid转换:",
            songid
        )

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

                            "song_id":
                            songid

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


                songmid = info["mid"]


        except Exception as e:

            print(
                "songid转songmid失败:",
                e
            )

            return None



    if not songmid:

        return None



    # 获取歌曲信息

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


            title = info["name"]


            singer = ",".join(

                [
                    x["name"]

                    for x in info["singer"]

                ]

            )


            pic = (

                "https://y.gtimg.cn/music/photo_new/T002R300x300M000/"

                +

                info["album"]["mid"]

                +

                ".jpg"

            )



            url = (

                "https://i.y.qq.com/v8/playsong.html?"

                "songmid="

                +

                songmid

            )


            return {


                "title":
                title,


                "singer":
                singer,


                "pic":
                pic,


                "url":
                url,


                "audio":
                url,


                "songmid":
                songmid


            }


    except Exception as e:


        print(
            "QQ音乐解析失败:",
            e
        )


        return None
