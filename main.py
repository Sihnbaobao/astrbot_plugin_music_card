import re
import json
import os
import importlib

from astrbot.core import logger


print("========== music_card 加载检查 ==========")

print(
    "main.py路径:",
    os.path.abspath(__file__)
)


try:

    qqmusic_module = importlib.import_module(
        ".qqmusic",
        __package__
    )

    print(
        "qqmusic.py路径:",
        os.path.abspath(
            qqmusic_module.__file__
        )
    )

except Exception as e:

    print(
        "qqmusic路径检测失败:",
        e
    )


print("========================================")


from astrbot.api.event import (
    filter,
    AstrMessageEvent
)

from astrbot.api.star import (
    Star,
    register
)


# 注意：
# 删除 qqshare 导入
# 不再使用 parse_qq_share

from .qqmusic import parse_qq_music
from .netease import search_netease

import httpx



async def expand_netease_url(url):


    if "163cn.tv" not in url:

        return url


    try:


        async with httpx.AsyncClient(

            follow_redirects=True,

            timeout=10

        ) as client:


            r = await client.get(
                url
            )


            return str(
                r.url
            )


    except Exception as e:


        logger.warning(
            f"网易云短链展开失败:{e}"
        )


        return url





@register(
    "astrbot_plugin_music_card",
    "Sihnbaobao",
    "QQ音乐网易云音乐链接转换音乐卡片",
    "0.1.8"
)
class MusicCardPlugin(Star):


    def __init__(self, context):

        super().__init__(context)




    async def send_music(
        self,
        event,
        message
    ):


        if event.message_obj.group_id:


            await event.bot.api.call_action(

                "send_group_msg",

                group_id=
                event.message_obj.group_id,

                message=
                message

            )


        else:


            await event.bot.api.call_action(

                "send_private_msg",

                user_id=
                event.get_sender_id(),

                message=
                message

            )





    async def send_163(
        self,
        event,
        song_id
    ):


        message = [

            {

                "type":
                "music",


                "data":
                {

                    "type":
                    "163",


                    "id":
                    song_id

                }

            }

        ]


        await self.send_music(
            event,
            message
        )





    async def send_qq(
        self,
        event,
        qq
    ):


        message = [

            {

                "type":
                "music",


                "data":
                {

                    "type":
                    "custom",


                    "url":
                    qq.get(
                        "url",
                        ""
                    ),


                    "audio":
                    qq.get(
                        "audio",
                        ""
                    ),


                    "image":
                    qq.get(
                        "pic",
                        ""
                    ),


                    "title":
                    qq.get(
                        "title",
                        "QQ音乐歌曲"
                    ),


                    "content":
                    qq.get(
                        "singer",
                        ""
                    )

                }

            }

        ]


        await self.send_music(
            event,
            message
        )
    @filter.event_message_type(
        filter.EventMessageType.ALL
    )
    async def music_card(

        self,

        event: AstrMessageEvent

    ):


        text = event.message_str or ""


        logger.info(
            "========== 收到消息 =========="
        )


        logger.info(
            f"message_str: {text}"
        )



        # ==========================
        # 网易云链接处理
        # ==========================


        if (
            "music.163.com" in text
            or
            "163cn.tv" in text
        ):


            # 提取真正URL

            url_match = re.search(
                r"https?://[^\s]+",
                text
            )


            if url_match:

                netease_url = url_match.group(0)

            else:

                netease_url = text



            logger.info(
                f"网易云真实链接:{netease_url}"
            )



            netease_url = await expand_netease_url(
                netease_url
            )


            logger.info(
                f"网易云展开:{netease_url}"
            )



            m = re.search(
                r"id=(\d+)",
                netease_url
            )


            if m:


                await self.send_163(

                    event,

                    m.group(1)

                )


                event.stop_event()

                return






        # ==========================
        # QQ音乐处理
        # ==========================


        if (

            "y.qq.com" in text

            or

            "c6.y.qq.com" in text

            or

            "i.y.qq.com" in text

        ):



            qq = await parse_qq_music(

                text

            )



            logger.info(

                "QQ解析结果: "

                +

                json.dumps(

                    qq,

                    ensure_ascii=False

                )

                if qq

                else "null"

            )




            # QQ解析失败

            if not qq:


                logger.warning(
                    "QQ音乐解析失败"
                )


                event.stop_event()

                return






            # ==========================
            # 搜索网易云
            # ==========================


            try:


                ne = await search_netease(

                    qq.get(
                        "title",
                        ""
                    ),

                    qq.get(
                        "singer",
                        ""
                    )

                )


            except Exception as e:


                logger.exception(

                    f"网易云搜索异常:{e}"

                )


                ne = None






            if ne:


                logger.info(

                    f"网易云匹配成功:{ne}"

                )



                await self.send_163(

                    event,

                    ne["id"]

                )


                event.stop_event()

                return






            # ==========================
            # 网易云失败
            # 发送QQ卡片
            # ==========================


            logger.info(

                "网易云没有匹配，发送QQ音乐卡片"

            )



            await self.send_qq(

                event,

                qq

            )


            event.stop_event()

            return






        # ==========================
        # 防止AI继续处理链接
        # ==========================


        if (

            "music.163.com" in text

            or

            "163cn.tv" in text

            or

            "y.qq.com" in text

            or

            "c6.y.qq.com" in text

            or

            "i.y.qq.com" in text

        ):


            event.stop_event()

            return
