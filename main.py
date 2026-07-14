import re
import json

from astrbot.core import logger

from astrbot.api.event import (
    filter,
    AstrMessageEvent
)

from astrbot.api.star import (
    Star,
    register
)

from .qqmusic import parse_qq_music



@register(
    "astrbot_plugin_music_card",
    "Sihnbaobao",
    "QQ音乐网易云音乐链接转换音乐卡片",
    "0.1.6"
)
class MusicCardPlugin(Star):


    def __init__(self, context):

        super().__init__(context)



    # ==========================
    # 发送消息
    # ==========================

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



    # ==========================
    # 网易云音乐
    # ==========================

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



    # ==========================
    # QQ音乐 custom卡片
    # ==========================

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
                        "url",
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



    # ==========================
    # 消息监听
    # ==========================

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


        try:


            for comp in event.message_obj.message:


                logger.info(

                    f"组件类型: {type(comp)}"

                )


                logger.info(

                    f"组件内容: {repr(comp)}"

                )


        except Exception:


            logger.exception(
                "组件打印失败"
            )



        logger.info(

            "========== 结束 =========="

        )



        # ======================
        # 网易云
        # ======================


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


        # ======================
        # QQ音乐
        # ======================


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

            )


            if not qq:

                logger.warning(
                    "QQ音乐解析失败，返回为空"
                )

                event.stop_event()

                return


            # 有歌曲信息才发送

            if (

                qq.get("title")

                or

                qq.get("songmid")

                or

                qq.get("songid")

            ):


                await self.send_qq(

                    event,

                    qq

                )


                event.stop_event()

                return



            else:


                logger.warning(

                    "QQ音乐解析失败，没有歌曲信息"

                )



        # ======================
        # 防止链接被AI继续处理
        # ======================


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
