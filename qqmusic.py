import re
import httpx
import os


print("========== qqmusic.py 已加载 ==========")
print("qqmusic实际文件:", os.path.abspath(__file__))
print("======================================")



async def parse_qq_music(text):

    print("进入 parse_qq_music:", text)


    # ==================================
    # 1. 从混合文本提取QQ链接
    # ==================================

    url_match = re.search(
        r"https?://[^\s]+",
        text
    )


    if url_match:

        text = url_match.group(0)

        print(
            "提取QQ真实链接:",
            text
        )



    # ==================================
    # 2. QQ短链展开
    # ==================================

    if "c6.y.qq.com" in text:


        print(
            "检测到QQ短链"
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
                    "QQ短链状态:",
                    r.status_code
                )


                print(
                    "QQ最终地址:",
                    str(r.url)
                )



                # 优先最终跳转地址

                text = str(r.url)



                # 如果没有参数

                if (
                    "songid=" not in text
                    and
                    "songmid=" not in text
                ):


                    print(
                        "尝试从页面寻找歌曲链接"
                    )


                    m = re.search(

                        r"https?://[^\"']*(?:playsong|songDetail)[^\"']*",

                        r.text

                    )


                    if m:


                        text = m.group(0)


                        print(
                            "页面提取:",
                            text
                        )


                    else:


                        print(
                            "QQ短链没有找到歌曲地址"
                        )

                        return None



        except Exception as e:


            print(
                "QQ短链异常:",
                repr(e)
            )


            return None





    # ==================================
    # 3. 提取songmid / songid
    # ==================================


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



    print(

        "解析:",
        songmid,
        songid

    )




    # ==================================
    # 4. songid转换songmid
    # ==================================


    if not songmid and songid:


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



                if info:


                    songmid = info.get(
                        "mid"
                    )


                    print(
                        "songmid:",
                        songmid
                    )


        except Exception as e:


            print(
                "songid转换失败:",
                repr(e)
            )



    if not songmid:


        print(
            "没有songmid"
        )

        return None






    # ==================================
    # 5. 获取歌曲详情
    # ==================================


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

            "QQ详情失败:",

            repr(e)

        )


        return None
