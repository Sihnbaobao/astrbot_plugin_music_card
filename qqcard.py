import re
import json

from astrbot.core import logger



async def parse_qq_card(event):

    """
    解析QQ音乐分享消息

    返回:

    {
        title:"",
        singer:"",
        pic:"",
        url:"",
        audio:""
    }

    """



    result = None



    try:

        raw = event.message_obj.message


        logger.info(
            f"QQ原始消息:{raw}"
        )


    except Exception as e:

        logger.warning(
            f"读取QQ原始消息失败:{e}"
        )

        return None




    text = str(raw)



    # =========================
    # 尝试提取QQ音乐json
    # =========================


    json_match = re.search(
        r'\{.*?\}',
        text,
        re.S
    )


    if json_match:


        try:


            data = json.loads(
                json_match.group()
            )


            logger.info(
                f"QQ JSON:{data}"
            )


            # 后面根据实际格式补


        except Exception:


            pass




    # =========================
    # 备用：文本解析
    # =========================


    title = re.search(

        r"《(.+?)》",

        text

    )


    if title:


        result = {

            "title":
            title.group(1),

            "singer":
            "",

            "pic":
            "",

            "url":
            "",

            "audio":
            ""

        }





    logger.info(

        f"QQ卡片解析结果:{result}"

    )



    return result
