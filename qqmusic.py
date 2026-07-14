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


    # QQ短链展开
    if "c6.y.qq.com/base/fcgi-bin/u" in text:

        try:

            async with httpx.AsyncClient(
                timeout=10,
                follow_redirects=True
            ) as client:

                r = await client.get(text)

                text = str(r.url)

                print(
                    "QQ短链展开:",
                    text
                )

        except Exception as e:

            print(
                "QQ短链展开失败:",
                e
            )

            return None

    print(
        "进入 parse_qq_music:",
        text
    )


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
        "解析结果:",
        "songmid=",
        songmid,
        "songid=",
        songid
    )



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


                print(
                    "API状态:",
                    r.status_code
                )


                print(
                    "API返回:",
                    r.text[:500]
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
                        "没有track_info"
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
            "没有songmid，结束"
        )

        return None



    # 后续歌曲信息查询

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


            print(
                "详情API:",
                r.text[:300]
            )


            j = r.json()


            info = (
                j
                .get("songinfo", {})
                .get("data", {})
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
