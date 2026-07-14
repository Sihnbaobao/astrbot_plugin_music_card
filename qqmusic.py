import re
import httpx
import json


async def parse_qq_music(text):

    result = {

        "songid": None,
        "songmid": None,

        "title": "",
        "singer": "",
        "cover": "",
        "url": ""

    }


    # =====================
    # 提取 songid
    # =====================

    sid = re.search(
        r"songid=(\d+)",
        text
    )

    if sid:
        result["songid"] = sid.group(1)



    # =====================
    # 提取 songmid
    # =====================

    mid = re.search(
        r"(?:songDetail/|songmid=)([A-Za-z0-9]+)",
        text
    )

    if mid:
        result["songmid"] = mid.group(1)



    # =====================
    # 短链接解析
    # =====================

    if "c6.y.qq.com" in text:

        try:

            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=10,
                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                }
            ) as client:


                r = await client.get(text)

                url = str(r.url)


                sid = re.search(
                    r"songid=(\d+)",
                    url
                )

                if sid:
                    result["songid"] = sid.group(1)



                mid = re.search(
                    r"songmid=([A-Za-z0-9]+)",
                    url
                )

                if mid:
                    result["songmid"] = mid.group(1)



        except Exception:
            pass



    # =====================
    # i.y.qq.com解析
    # =====================


    if "i.y.qq.com" in text:


        try:

            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=10,
                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                }
            ) as client:


                r = await client.get(text)

                url = str(r.url)



                sid = re.search(
                    r"songid=(\d+)",
                    url
                )

                if sid:
                    result["songid"] = sid.group(1)



                mid = re.search(
                    r"songmid=([A-Za-z0-9]+)",
                    url
                )

                if mid:
                    result["songmid"] = mid.group(1)


        except Exception:

            pass



    # =====================
    # 获取歌曲信息
    # =====================


    if result["songmid"]:


        try:


            api = (
                "https://u.y.qq.com/cgi-bin/musicu.fcg"
            )


            payload = {

                "req_0": {

                    "module":
                    "music.pf_song_detail_svr",

                    "method":
                    "get_song_detail_yqq",

                    "param":
                    {
                        "song_mid":
                        result["songmid"]
                    }

                }

            }



            async with httpx.AsyncClient(
                timeout=10,
                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                }
            ) as client:


                r = await client.post(

                    api,

                    json=payload

                )


                data = r.json()



                track = (
                    data
                    .get("req_0", {})
                    .get("data", {})
                    .get("track", {})
                )


                if track:


                    result["title"] = (
                        track.get("name","")
                    )


                    singers = track.get(
                        "singer",
                        []
                    )


                    result["singer"] = (
                        " / ".join(
                            [
                                x.get("name","")
                                for x in singers
                            ]
                        )
                    )


                    album = track.get(
                        "album",
                        {}
                    )


                    mid = album.get(
                        "mid",
                        ""
                    )


                    if mid:

                        result["cover"] = (
                            "https://y.gtimg.cn/music/photo_new/T002R300x300M000"
                            + mid
                            + ".jpg"
                        )



        except Exception as e:

            print(
                "QQ音乐信息获取失败:",
                e
            )



    return result
