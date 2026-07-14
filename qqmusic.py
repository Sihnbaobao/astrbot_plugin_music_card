import re
import httpx


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


    # ======================
    # 直接提取 songmid
    # ======================

    mid = re.search(
        r"songmid=([A-Za-z0-9]+)",
        text
    )

    if mid:

        songmid = mid.group(1)



    # ======================
    # songid
    # ======================

    songid = None


    sid = re.search(
        r"songid=(\d+)",
        text
    )

    if sid:

        songid = sid.group(1)



    # ======================
    # songid 转网页解析
    # ======================

    if not songmid and songid:


        print(
            "尝试网页解析songid:",
            songid
        )


        url = (

            "https://i.y.qq.com/v8/playsong.html?"

            "songid="

            + songid

        )


        try:


            async with httpx.AsyncClient(

                timeout=10,

                follow_redirects=True,

                headers={

                    "User-Agent":
                    "Mozilla/5.0"

                }

            ) as client:


                r = await client.get(url)


                html = r.text



                mid = re.search(

                    r"songmid=([A-Za-z0-9]+)",

                    html

                )


                if mid:


                    songmid = mid.group(1)


        except Exception as e:


            print(
                "网页解析失败:",
                e
            )




    if not songmid:


        print(
            "没有songmid，退出"
        )


        return result



    # ======================
    # 获取歌曲详情
    # ======================


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



            title = info.get(

                "name",

                "QQ音乐歌曲"

            )



            singer = ",".join(

                [

                    x["name"]

                    for x in info.get(
                        "singer",
                        []
                    )

                ]

            )



            album = info.get(
                "album",
                {}
            )



            pic = ""


            if album.get("mid"):


                pic = (

                    "https://y.gtimg.cn/music/photo_new/T002R300x300M000/"

                    +

                    album["mid"]

                    +

                    ".jpg"

                )



            play_url = (

                "https://i.y.qq.com/v8/playsong.html?"

                "songmid="

                +

                songmid

            )



            result.update({

                "title":
                title,


                "singer":
                singer,


                "pic":
                pic,


                "url":
                play_url,


                "audio":
                play_url,


                "songmid":
                songmid

            })



            return result



    except Exception as e:


        print(

            "QQ详情获取失败:",

            e

        )


        return result
