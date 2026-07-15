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
    # 提取消息里的QQ链接
    # ======================

    url_match = re.search(
        r"https?://[^\s]+",
        text
    )


    if url_match:

        text = url_match.group(0)

        print(
            "提取QQ链接:",
            text
        )



    # ======================
    # QQ短链解析
    # ======================


    if "c6.y.qq.com" in text:


        print(
            "检测到QQ短链"
        )


        try:


            async with httpx.AsyncClient(

                timeout=15,

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
                    "QQ短链状态:",
                    r.status_code
                )


                print(
                    "QQ短链最终:",
                    r.url
                )


                html = r.text


                print(
                    "QQ短链内容:",
                    html[:500]
                )



                # 找 playsong

                m = re.search(

                    r"https?://i\.y\.qq\.com/v8/playsong\.html\?[^\"']+",

                    html

                )


                if m:


                    text = m.group(0)


                    print(
                        "找到playsong:",
                        text
                    )


                else:


                    # 找 songmid

                    m = re.search(

                        r"songmid=([A-Za-z0-9]+)",

                        html

                    )


                    if m:


                        songmid = m.group(1)


                        text = (

                            "https://i.y.qq.com/v8/playsong.html?songmid="

                            +

                            songmid

                        )


                        print(
                            "找到songmid:",
                            text
                        )


                    else:


                        # 找 songid

                        m = re.search(

                            r"songid=(\d+)",

                            html

                        )


                        if m:


                            songid = m.group(1)


                            text = (

                                "https://i.y.qq.com/v8/playsong.html?songid="

                                +

                                songid

                            )


                            print(
                                "找到songid:",
                                text
                            )


                        else:


                            print(
                                "QQ短链没有找到歌曲信息"
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



    # ======================
    # 提取songmid
    # ======================


    mid = re.search(

        r"songmid=([A-Za-z0-9]+)",

        text

    )


    if mid:

        songmid = mid.group(1)





    # ======================
    # 提取songid
    # ======================


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
            "songid转换songmid:",
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


                print(
                    "没有歌曲详情"
                )


                return None





            title = info.get(
                "name",
                ""
            )



            singer = ",".join(

                [

                    x.get(
                        "name",
                        ""
                    )

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



            result = {


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



            print(
                "QQ解析成功:",
                result
            )



            return result





    except Exception as e:


        print(
            "歌曲详情失败:",
            repr(e)
        )


        return None
