import re
import httpx
from urllib.parse import urlparse, parse_qs


async def expand_qq_url(url):

    print(
        "开始展开QQ短链:",
        url
    )


    try:

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=10,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        ) as client:


            r = await client.get(
                url
            )


            print(
                "QQ短链状态:",
                r.status_code
            )


            print(
                "QQ最终地址:",
                r.url
            )


            return str(r.url), r.text



    except Exception as e:


        print(
            "QQ短链展开失败:",
            repr(e)
        )


        return None, None





async def parse_qq_share(text):


    print(
        "进入QQ分享解析:",
        text
    )


    result = {}



    # ======================
    # 提取QQ链接
    # ======================


    url = re.search(

        r"https?://[^\s]+",

        text

    )


    if not url:


        print(
            "没有QQ链接"
        )


        return None



    qq_url = url.group(0)



    # 去掉QQ后缀

    qq_url = qq_url.replace(
        "@QQ音乐",
        ""
    )



    print(
        "提取QQ链接:",
        qq_url
    )



    # ======================
    # 展开短链
    # ======================


    if "c6.y.qq.com" in qq_url:


        final_url, html = await expand_qq_url(
            qq_url
        )


        if final_url:

            qq_url = final_url



    print(
        "最终QQ地址:",
        qq_url
    )





    # ======================
    # 解析songid
    # ======================


    songid = re.search(

        r"songid=(\d+)",

        qq_url

    )


    if songid:


        result["songid"] = songid.group(1)



    # ======================
    # 解析songmid
    # ======================


    songmid = re.search(

        r"songmid=([A-Za-z0-9]+)",

        qq_url

    )


    if songmid:


        result["songmid"] = songmid.group(1)



    # ======================
    # 解析文字标题
    # ======================


    title = re.search(

        r"《(.+?)》",

        text

    )


    if title:


        result["title"] = title.group(1)



    # ======================
    # 解析歌手
    # ======================


    singer = re.search(

        r"分享(.+?)/",

        text

    )


    if singer:


        result["singer"] = singer.group(1)



    else:


        singer2 = re.search(

            r"^(.*?)《",

            text

        )


        if singer2:


            result["singer"] = (
                singer2.group(1)
                .strip()
            )




    print(
        "QQ分享最终结果:",
        result
    )



    if (
        result.get("title")
        or
        result.get("songid")
        or
        result.get("songmid")
    ):


        return result



    return None
