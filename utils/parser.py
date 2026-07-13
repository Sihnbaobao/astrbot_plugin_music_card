import re



def parse_music_url(text):


    # 网易云

    if "music.163.com" in text:

        result = re.search(
            r"id=(\d+)",
            text
        )


        if result:

            return {

                "type": 1,

                "id":
                result.group(1)

            }



    # QQ音乐

    if "qq.com" in text:

        result = re.search(
            r"songDetail/([A-Za-z0-9]+)",
            text
        )


        if result:

            return {

                "type": 1,

                "id":
                result.group(1)

            }


    return None