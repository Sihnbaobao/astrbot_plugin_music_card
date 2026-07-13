import re
import httpx



async def parse_qq_music(text):


    result = {

        "songid": None,

        "songmid": None

    }



    # =====================
    # songid
    # =====================


    sid = re.search(

        r"songid=(\d+)",

        text

    )


    if sid:

        result["songid"] = sid.group(1)



    # =====================
    # songmid
    # =====================


    mid = re.search(

        r"(?:songDetail/|songmid=)([A-Za-z0-9]+)",

        text

    )


    if mid:

        result["songmid"] = mid.group(1)



    # =====================
    # QQ短链接
    # =====================


    if (

        "c6.y.qq.com" in text

    ):


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
    # i.y.qq.com 网页分享
    # =====================


    if (

        "i.y.qq.com" in text

        and not result["songid"]

    ):


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



        except Exception:


            pass



    return result
