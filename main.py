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

from .qqmusic import parse_qq_music
from .netease import search_netease



@register(
    "astrbot_plugin_music_card",
    "Sihnbaobao",
    "QQ音乐网易云音乐链接转换音乐卡片",
    "0.1.7"
)
class MusicCardPlugin(Star):


    def __init__(self, context):

        super().__init__(context)



    async def send_music(
        self,
        event,
        message
    ):


        try:


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


        except Exception as e:


            logger.exception(
                f"音乐卡片发送失败: {e}"
            )

            raise e




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



        if "music.163.com" in text:


            result = re.search(
                r"id=(\d+)",
                text
            )


            if result:


                await self.send_163(
                    event,
                    result.group(1)
                )


                event.stop_event()

                return





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



            if not qq:


                logger.warning(
                    "QQ解析失败"
                )


                event.stop_event()

                return




            # ==========================
            # 优先QQ音乐卡片
            # ==========================


            try:


                await self.send_qq(
                    event,
                    qq
                )


                logger.info(
                    "QQ音乐卡片发送成功"
                )


                event.stop_event()

                return



            except Exception:


                logger.warning(
                    "QQ音乐卡片失败，尝试网易云"
                )





                # ==========================
                # QQ失败备用网易云
                # ==========================


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


                if ne:


                    await self.send_163(

                        event,

                        ne["id"]

                    )


                    event.stop_event()

                    return


                else:


                    logger.warning(
                        "网易云也没有找到歌曲"
                    )



        if (

            "music.163.com" in text

            or

            "y.qq.com" in text

            or

            "c6.y.qq.com" in text

            or

            "i.y.qq.com" in text

        ):


            event.stop_event()

            return
