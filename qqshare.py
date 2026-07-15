import re


async def parse_qq_share(text):


    print(
        "进入 QQ分享解析:",
        text
    )


    result = {}


    # ======================
    # 提取歌名
    # ======================

    title = re.search(
        r"《(.+?)》",
        text
    )


    if title:

        result["title"] = title.group(1)



    # ======================
    # 提取歌手
    # ======================

    singer = re.search(
        r"分享(.+?)/",
        text
    )


    if singer:

        result["singer"] = singer.group(1)


    else:


        # 兼容:
        # 歌手《歌曲》

        singer2 = re.search(
            r"^(.*?)《",
            text
        )


        if singer2:

            result["singer"] = singer2.group(1).strip()



    print(
        "QQ分享解析结果:",
        result
    )


    if result.get("title"):

        return result



    return None
