import re
import json

from astrbot.core import logger

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Star, register

from .qqmusic import parse_qq_music


@register(
    "astrbot_plugin_music_card",
    "Sihnbaobao",
    "QQ音乐网易云音乐链接转换音乐卡片",
    "0.1.5"
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
                    group_id=event.message_obj.group_id,
                    message=message
                )

            else:

                await event.bot.api.call_action(
                    "send_private_msg",
                    user_id=event.get_sender_id(),
                    message=message
                )


        except Exception as e:

            logger.error(
                f"音乐卡片发送失败: {e}"
            )



    # =====================
    # 网易云音乐
    # =====================


    async def send_163(
        self,
        event,
        song_id
    ):


        message = [

            {

                "type": "music",

                "data": {

                    "type": "163",

                    "id": song_id

                }

            }

        ]


        await self.send_music(
            event,
            message
        )



    # =====================
    # QQ音乐 Ark卡片
    # =====================


    async def send_qq(
        self,
        event,
        songid=None,
        songmid=None
    ):


        if songmid:


            jump_url = (

                "https://i.y.qq.com/v8/playsong.html?"

                "songmid="

                + songmid

                + "&type=0"

            )


        elif songid:


            jump_url = (

                "https://i.y.qq.com/v8/playsong.html?"

                "songid="

                + songid

            )


        else:

            return
        card = {


            "app": "com.tencent.tuwen.lua",


            "bizsrc": "qqconnect.sdkshare",



            "config": {


                "ctime": 0,


                "forward": 1,


                "type": "normal"


            },



            "extra": {


                "app_type": 1,


                "appid": 100497308


            },



            "meta": {


                "news": {


                    "app_type": 1,


                    "appid": 100497308,


                    "desc": "QQ音乐",


                    "jumpUrl": jump_url,


                    "preview": "",


                    "tag": "QQ音乐",


                    "title": "QQ音乐歌曲"


                }


            },



            "prompt": "[分享]QQ音乐",



            "ver": "0.0.0.1",



            "view": "news"


        }



        message = [


            {


                "type": "json",


                "data": {


                    "data": json.dumps(

                        card,

                        ensure_ascii=False

                    )


                }


            }


        ]



        await self.send_music(

            event,

            message

        )





    # =====================
    # 消息监听
    # =====================



    @filter.event_message_type(

        filter.EventMessageType.ALL

    )

    async def music_card(

        self,

        event: AstrMessageEvent

    ):


        text = event.message_str



        # =====================
        # 调试日志
        # =====================


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


        except Exception as e:


            logger.error(

                f"消息组件读取失败: {e}"

            )



        logger.info(

            "========== 结束 =========="

        )



        if not text:


            return



        # =====================
        # 网易云
        # =====================


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
        # =====================
        # QQ音乐
        # =====================


        if (

            "y.qq.com" in text

            or

            "c6.y.qq.com" in text

            or

            "i.y.qq.com" in text

        ):


            try:


                qq = await parse_qq_music(text)



                logger.info(

                    "QQ解析结果: "

                    + json.dumps(

                        qq,

                        ensure_ascii=False

                    )

                )



                if (

                    qq.get("songid")

                    or

                    qq.get("songmid")

                ):



                    await self.send_qq(

                        event,

                        songid=qq.get("songid"),

                        songmid=qq.get("songmid")

                    )



                    event.stop_event()



                    return



            except Exception as e:


                logger.exception(

                    f"QQ音乐处理失败: {e}"

                )



        return
