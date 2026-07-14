import re
import requests


def expand_qq_url(url):
    """
    QQ音乐短链接展开
    c6.y.qq.com/base/fcgi-bin/u?__=xxxx
    """

    if "c6.y.qq.com" not in url:
        return url

    try:

        headers = {
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }


        r = requests.get(
            url,
            headers=headers,
            allow_redirects=False,
            timeout=5
        )


        location = r.headers.get("Location")


        if location:
            print(
                "QQ短链展开:",
                location
            )

            return location


    except Exception as e:

        print(
            "QQ短链展开失败:",
            e
        )


    return url



def get_song_info(songmid):

    """
    获取QQ歌曲详细信息
    """

    try:

        api = (
            "https://u.y.qq.com/cgi-bin/musicu.fcg"
        )


        payload = {

            "comm": {
                "ct":24,
                "cv":0
            },


            "songinfo": {

                "module":
                "music.pf_song_detail_svr",


                "method":
                "get_song_detail_yqq",


                "param": {

                    "song_mid":
                    songmid

                }

            }

        }



        r = requests.post(
            api,
            json=payload,
            timeout=5
        )


        data = r.json()


        song = (
            data
            ["songinfo"]
            ["data"]
            ["track_info"]
        )


        title = song.get(
            "title"
        )


        singers=[]


        for s in song.get(
            "singer",
            []
        ):

            singers.append(
                s["name"]
            )


        singer = " / ".join(
            singers
        )


        album_mid = (
            song
            .get("album", {})
            .get("mid")
        )


        pic = None


        if album_mid:

            pic = (
                "https://y.gtimg.cn/music/photo_new/"
                "T002R300x300M000/"
                +
                album_mid
                +
                ".jpg"
            )



        return {

            "title":
            title,


            "singer":
            singer,


            "pic":
            pic,


            "cover":
            pic

        }


    except Exception as e:

        print(
            "获取歌曲信息失败:",
            e
        )

        return None




def parse_qq_music(url):

    """
    QQ音乐解析入口
    """


    # ==========================
    # 第一步 展开短链接
    # ==========================

    url = expand_qq_url(
        url
    )


    print(
        "最终解析地址:",
        url
    )



    songmid = None



    # ==========================
    # 解析 songmid
    # ==========================


    m = re.search(
        r"songmid=([A-Za-z0-9]+)",
        url
    )


    if m:

        songmid = m.group(1)



    # ==========================
    # songid数字
    # ==========================

    if not songmid:


        m = re.search(
            r"songid=(\d+)",
            url
        )


        if m:

            songid=m.group(1)


            print(
                "发现songid:",
                songid
            )


            try:


                api = (
                    "https://u.y.qq.com/cgi-bin/musicu.fcg"
                )


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



                r=requests.post(
                    api,
                    json=payload,
                    timeout=5
                )


                j=r.json()



                song=(

                    j
                    ["req_0"]
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




    info=get_song_info(
        songmid
    )



    if not info:

        return None




    result={

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
        (
            "https://i.y.qq.com/v8/playsong.html?songmid="
            +
            songmid
        ),


        "audio":
        (
            "https://i.y.qq.com/v8/playsong.html?songmid="
            +
            songmid
        )

    }



    return result
