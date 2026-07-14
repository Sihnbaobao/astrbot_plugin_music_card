import re
import httpx
import os


print(
    "========== qqmusic.py 已加载 =========="
)

print(
    "qqmusic实际文件:",
    os.path.abspath(__file__)
)

print(
    "======================================"
)



async def parse_qq_music(text):


    print(
        "进入 parse_qq_music:",
        text
    )



    # ======================
    # QQ短链接处理
    # ======================


    if "c6.y.qq.com" in text:


        print(
            "检测到QQ短链接"
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



                r = await client.get(
                    text
                )


                print(
                    "短链状态:",
                    r.status_code
                )


                print(
                    "最终地址:",
                    str(r.url)
                )



                # 优先使用最终URL

                text = str(r.url)



                # 如果最终URL没有参数

                # 再从返回内容找

                if (

                    "songid=" not in text

                    and

                    "songmid=" not in text

                ):


                    print(
                        "尝试解析返回内容"
                    )


                    m = re.search(

                        r"(https?://[^\s\"']+)",

                        r.text

                    )


                    if m:


                        text = m.group(1)


                        print(
                            "内容提取地址:",
                            text
                        )



                    else:


                        print(
                            "短链没有找到真实地址"
                        )


                        return None



        except Exception as e:


            print(
                "QQ短链异常:",
                repr(e)
            )


            return None





    songmid = None

    songid = None



    # songmid

    mid = re.search(

        r"songmid=([A-Za-z0-9]+)",

        text

    )


    if mid:

        songmid = mid.group(1)



    # songid

    sid = re.search(

        r"songid=(\d+)",

        text

    )


    if sid:

        songid = sid.group(1)



    print(

        "解析结果:",

        "songmid=",

        songmid,

        "songid=",

        songid

    )





    # ======================
    # songid转换songmid
    # ======================


    if not songmid and songid:


        print(

            "进入 songid 转换:",

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

                            int(songid)

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

                    .get("songinfo",{})

                    .get("data",{})

                    .get("track_info")

                )



                if not info:


                    print(
                        "songid转换失败"
                    )


                    return None



                songmid = info.get(
                    "mid"
                )



                print(

                    "转换得到songmid:",

                    songmid

                )



        except Exception as e:


            print(

                "songid转换异常:",

                repr(e)

            )


            return None





    if not songmid:


        print(
            "没有songmid"
        )


        return None





    # ======================
    # 查询歌曲详情
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

                .get("songinfo",{})

                .get("data",{})

                .get("track_info")

            )



            if not info:


                return None




            title = info.get(
                "name"
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



            pic = (

                "https://y.gtimg.cn/music/photo_new/T002R300x300M000/"

                +

                album.get(
                    "mid",
                    ""
                )

                +

                ".jpg"

            )



            url = (

                "https://i.y.qq.com/v8/playsong.html?songmid="

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


                "cover":

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

            "歌曲详情失败:",

            repr(e)

        )


        return None
