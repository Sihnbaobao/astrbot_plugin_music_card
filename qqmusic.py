import re
import httpx



async def parse_qq_music(text):


    songmid = None


    songid = None



    # =====================
    # 提取参数
    # =====================


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
        "解析参数:",
        songid,
        songmid
    )



    async with httpx.AsyncClient(

        timeout=10,

        headers={

            "User-Agent":
            "Mozilla/5.0"

        }

    ) as client:



        # =====================
        # 没有songmid
        # 用songid搜索
        # =====================


        if not songmid and songid:


            try:


                api = (
                    "https://c.y.qq.com/soso/fcgi-bin/"
                    "client_search_cp"
                )



                params={

                    "ct":24,

                    "qqmusic_ver":1298,

                    "new_json":1,

                    "remoteplace":"txt.yqq.song",

                    "t":0,

                    "aggr":1,

                    "cr":1,

                    "catZhida":1,

                    "lossless":0,

                    "flag_qc":0,

                    "p":1,

                    "n":10,

                    "w":songid

                }



                r = await client.get(

                    api,

                    params=params

                )


                j=r.json()



                songs=(

                    j

                    ["data"]

                    ["song"]

                    ["list"]

                )



                if songs:


                    songmid=songs[0]["mid"]


                    print(

                        "搜索得到songmid:",

                        songmid

                    )



            except Exception as e:


                print(

                    "songid搜索失败:",

                    e

                )





        if not songmid:


            return None





        # =====================
        # 获取歌曲详情
        # =====================



        try:


            api=(

                "https://u.y.qq.com/cgi-bin/musicu.fcg"

            )



            data={


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



            r=await client.post(

                api,

                json=data

            )


            j=r.json()



            info=(

                j

                ["songinfo"]

                ["data"]

                ["track_info"]

            )



            title=info["name"]



            singer=",".join(

                [

                    x["name"]

                    for x in info["singer"]

                ]

            )



            pic=(

                "https://y.gtimg.cn/music/photo_new/"
                "T002R300x300M000/"

                +

                info["album"]["mid"]

                +

                ".jpg"

            )



            url=(

                "https://i.y.qq.com/v8/playsong.html?"

                "songmid="

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

                e

            )


            return None
