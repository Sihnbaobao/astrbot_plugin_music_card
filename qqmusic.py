import re
import httpx


def extract_url(text):
    """
    从消息里提取URL
    """
    urls = re.findall(
        r"https?://[^\s]+",
        text
    )

    if urls:
        return urls[0]

    return None



async def expand_url(url):

    try:

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=10,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        ) as client:

            r = await client.get(url)

            return str(r.url)


    except Exception:

        return url




async def parse_qq_music(text):

    result = {
        "songid": None,
        "songmid": None
    }


    # 提取链接

    url = extract_url(text)


    if not url:
        return result



    # 短链展开

    if "c6.y.qq.com" in url:

        url = await expand_url(url)



    # songmid

    mid = re.search(
        r"(?:songDetail/|songmid=)([A-Za-z0-9]+)",
        url
    )


    if mid:

        result["songmid"] = mid.group(1)



    # songid

    sid = re.search(
        r"songid=(\d+)",
        url
    )


    if sid:

        result["songid"] = sid.group(1)



    return result
