import re
import asyncio
import requests



def expand_qq_url_sync(url):

    if "c6.y.qq.com" not in url:
        return url


    try:

        headers={
            "User-Agent":
            "Mozilla/5.0"
        }


        r=requests.get(
            url,
            headers=headers,
            allow_redirects=False,
            timeout=5
        )


        location=r.headers.get(
            "Location"
        )


        if location:

            print(
                "QQ短链展开:",
                location
            )

            return location


    except Exception as e:

        print(
            "短链展开失败:",
            e
        )


    return url




def get_song_info_sync(songmid):


    try:

        api="https://u.y.qq.com/cgi-bin/musicu.fcg"


        payload={

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


        r=requests.post(
            api,
            json=payload,
            timeout=5
        )


        j=r.json()


        track=j["songinfo"]["data"]["track_info"]


        singers=[]


        for s in track["singer"]:

            singers.append(
                s["name"]
            )


        album_mid=track["album"]["mid"]


        pic=(
            "https://y.gtimg.cn/music/photo_new/"
            "T002R300x300M000/"
            +
            album_mid
            +
            ".jpg"
        )


        return {

            "title":
            track["title"],


            "singer":
            "/".join(singers),


            "pic":
            pic,


            "cover":
            pic

        }


    except Exception as e:

        print(
            "歌曲信息错误:",
            e
        )

        return None





async def parse_qq_music(url):


    # 展开短链
    url = await asyncio.to_thread(
        expand_qq_url_sync,
        url
    )


    print(
        "最终QQ地址:",
        url
    )



    songmid=None



    m=re.search(
        r"songmid=([A-Za-z0-9]+)",
        url
    )


    if m:

        songmid=m.group(1)



    if not songmid:


        m=re.search(
            r"songid=(\d+)",
            url
        )


        if m:


            songid=m.group(1)


            print(
                "发现songid:",
                songid
            )


            # QQ分享页songid需要搜索转换

            try:


                api="https://u.y.qq.com/cgi-bin/musicu.fcg"


                payload={

                    "req_0":{

                        "module":
                        "music.musicsearch.SearchCgiService",


                        "method":
                        "DoSearchForQQMusicDesktop",


                        "param":{

                            "query":
                            songid,

                            "search_type":
                            100,

                            "num_per_page":
                            1,

                            "page_num":
                            1
                        }

                    }

                }



                r=await asyncio.to_thread(
                    requests.post,
                    api,
                    json=payload,
                    timeout=5
                )


                j=r.json()


                song=(

                    j["req_0"]
                    ["data"]
                    ["body"]
                    ["song"]
                    ["list"][0]

                )


                songmid=song["mid"]


            except Exception as e:

                print(
                    "songid转换失败:",
                    e
                )





    if not songmid:

        return None




    info=await asyncio.to_thread(
        get_song_info_sync,
        songmid
    )


    if not info:

        return None




    return {


        "title":
        info["title"],


        "singer":
        info["singer"],


        "pic":
        info["pic"],


        "cover":
        info["cover"],


        "songmid":
        songmid,


        "url":
        "https://i.y.qq.com/v8/playsong.html?songmid="
        +
        songmid,


        "audio":
        "https://i.y.qq.com/v8/playsong.html?songmid="
        +
        songmid

    }
