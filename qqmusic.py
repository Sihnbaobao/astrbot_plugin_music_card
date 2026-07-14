import re
import httpx



async def parse_qq_music(text):


    songmid = None


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


    if not songmid and sid:

        songid = sid.group(1)

    else:

        songid = None



    if not songmid:

        return None



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



    try:


        async with httpx.AsyncClient(

            timeout=10

        ) as client:


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



            audio = url



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
                audio

            }



    except Exception as e:


        print(
            "QQ解析失败",
            e
        )


        return None
