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
    songid = None



    print(
        "========== QQ解析开始 =========="
    )

    print(
        "原始文本:",
        text
    )



    # ======================
    # 提取 songmid
    # ======================

    mid = re.search(

        r"songmid=([A-Za-z0-9]+)",

        text

    )


    if mid:

        songmid = mid.group(1)



    # ======================
    # 提取 songid
    # ======================

    sid = re.search(

        r"songid=(\d+)",

        text

    )


    if sid:

        songid = sid.group(1)



    print(

        "提取结果:",

        "songid=",

        songid,

        "songmid=",

        songmid

    )



    # ======================
    # songid 转 songmid
    # ======================


    if not songmid and songid:


        print(

            "进入songid转换:",

            songid

        )



        try:


            async with httpx.AsyncClient(

                timeout=10,

                headers={

                    "User-Agent":

                    "Mozilla/5.0"

                }

            ) as client:



                api = (

                    "https://c.y.qq.com/v8/fcg-bin/"

                    "fcg_play_single_song.fcg"

                )



                r = await client.get(

                    api,

                    params={

                        "songid":

                        songid

                    }

                )



                print(

                    "接口状态:",

                    r.status_code

                )


                print(

                    "接口文本:",

                    r.text[:500]

                )



                try:

                    data = r.json()


                except Exception as e:


                    print(

                        "JSON解析失败:",

                        e

                    )


                    data = {}



                print(

                    "接口JSON:",

                    data

                )



                if (

                    "data"

                    in data

                ):


                    songs = data["data"]


                    if isinstance(

                        songs,

                        list

                    ) and len(songs) > 0:



                        songmid = songs[0].get(

                            "mid"

                        )



        except Exception as e:


            print(

                "songid转换异常:",

                e

            )



    print(

        "转换后songmid:",

        songmid

    )



    if not songmid:


        print(

            "没有songmid，结束"

        )


        print(

            "========== QQ解析结束 =========="

        )


        return result





    # ======================
    # 获取歌曲详情
    # ======================


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



            print(

                "详情接口返回:",

                j

            )



            info = (

                j

                .get("songinfo", {})

                .get("data", {})

                .get("track_info")

            )



            if not info:


                print(

                    "没有track_info"

                )


                return result



            title = info.get(

                "name",

                "QQ音乐歌曲"

            )



            singer = ",".join(

                [

                    x.get("name","")

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

                    "https://y.gtimg.cn/music/photo_new/"

                    "T002R300x300M000/"

                    +

                    album["mid"]

                    +

                    ".jpg"

                )



            url = (

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

                url,


                "audio":

                url,


                "songmid":

                songmid

            })



            print(

                "最终结果:",

                result

            )



            print(

                "========== QQ解析结束 =========="

            )


            return result



    except Exception as e:


        print(

            "详情获取失败:",

            e

        )


        print(

            "========== QQ解析结束 =========="

        )


        return result
