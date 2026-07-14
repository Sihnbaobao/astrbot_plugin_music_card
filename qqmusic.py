import re
print("========== QQMUSIC新版加载 ==========")
import httpx


async def parse_qq_music(text):

    print(
        "进入parse_qq_music:",
        text
    )

    songmid = None
    songid = None


    # =========================
    # QQ短链解析
    # =========================

    if "c6.y.qq.com/base/fcgi-bin/u" in text:


        try:


            async with httpx.AsyncClient(
                timeout=10,
                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                }
            ) as client:


                r = await client.get(
                    text
                )


                html = r.text


                print(
                    "QQ短链返回:",
                    html[:300]
                )


                # 匹配真实歌曲链接

                m = re.search(
                    r"https://i\.y\.qq\.com/v8/playsong\.html\?[^\"']+",
                    html
                )


                if m:

                    text = m.group(0)

                    print(
                        "QQ短链解析:",
                        text
                    )


                else:

                    print(
                        "没有找到歌曲地址"
                    )

                    return None



        except Exception as e:


            print(
                "QQ短链解析失败:",
                e
            )

            return None



    # =========================
    # 提取 songmid
    # =========================

    mid = re.search(
        r"songmid=([A-Za-z0-9]+)",
        text
    )

    if mid:

        songmid = mid.group(1)



    # =========================
    # 提取 songid
    # =========================

    sid = re.search(
        r"songid=(\d+)",
        text
    )

    if sid:

        songid = sid.group(1)



    # =========================
    # songid 转 songmid
    # =========================

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
                    .get("songinfo", {})
                    .get("data", {})
                    .get("track_info")

                )



                if info:

                    songmid = info.get(
                        "mid"
                    )



        except Exception as e:


            print(
                "songid转songmid失败:",
                e
            )



    if not songmid:

        return None




    # =========================
    # 获取歌曲详情
    # =========================


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
                .get("songinfo", {})
                .get("data", {})
                .get("track_info")

            )



            if not info:

                print(
                    "没有获取歌曲详情"
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



            album_mid = (

                info
                .get("album", {})
                .get("mid")

            )



            pic = ""

            if album_mid:


                pic = (

                    "https://y.gtimg.cn/music/photo_new/T002R300x300M000/"

                    +

                    album_mid

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
            "QQ音乐解析失败:",
            e
        )


        return None
