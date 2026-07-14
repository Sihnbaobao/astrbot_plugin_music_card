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



    # ======================
    # 短链接展开
    # ======================

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


                url = str(r.url)


                print(
                    "QQ短链展开:",
                    url
                )


                mid = re.search(

                    r"songmid=([A-Za-z0-9]+)",

                    url

                )


                if mid:

                    songmid = mid.group(1)



                sid = re.search(

                    r"songid=(\d+)",

                    url

                )


                if sid:

                    songid = sid.group(1)



        except Exception as e:


            print(

                "短链解析失败:",

                e

            )




    # ======================
    # songid 转 songmid
    # ======================

    if not songmid and songid:


        print(

            "尝试songid查询:",

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



                params = {


                    "songid":

                    songid

                }



                r = await client.get(

                    api,

                    params=params

                )



                j = r.json()



                print(

                    "songid接口返回:",

                    j

                )



                if (

                    "data"

                    in j

                    and

                    len(j["data"]) > 0

                ):



                    songmid = (

                        j["data"][0]

                        .get("mid")

                    )



        except Exception as e:


            print(

                "songid转换失败:",

                e

            )




    if not songmid:


        print(

            "没有获取songmid"

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
