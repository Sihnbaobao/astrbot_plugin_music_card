import re
import json

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Star, register


@register(
    "astrbot_plugin_music_card",
    "Sihnbaobao",
    "QQ音乐网易云音乐链接转音乐卡片",
    "0.1.1"
)
class MusicCardPlugin(Star):

    def __init__(self, context):
        super().__init__(context)


    # ==========================
    # 网易云音乐 OneBot music
    # ==========================

    async def send_163_music(
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

        await self.send_message(
            event,
            message
        )


    # ==========================
    # QQ音乐 JSON卡片
    # ==========================

    async def send_qq_music(
        self,
        event,
        song_id
    ):

        card = {
            "app": "com.tencent.qqmusic",
            "view": "RichInfoView",
            "ver": "0.0.0.1",
            "prompt": "[QQ音乐]",
            "meta": {
                "music": {
                    "appid": 100497308,
                    "title": "QQ音乐",
                    "desc": "",
                    "jumpUrl": f"https://y.qq.com/n/ryqq/songDetail/{song_id}",
                    "musicUrl": "",
                    "preview": "",
                    "tag": "QQ音乐"
                }
            }
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


        await self.send_message(
            event,
            message
        )


    # ==========================
    # 根据来源发送
    # ==========================

    async def send_message(
        self,
        event,
        message
    ):

        # 群聊
        if event.message_obj.group_id:

            await event.bot.api.call_action(
                "send_group_msg",
                group_id=event.message_obj.group_id,
                message=message
            )


        # 私聊

        else:

            await event.bot.api.call_action(
                "send_private_msg",
                user_id=event.get_sender_id(),
                message=message
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


        msg = event.message_str



        # --------------------------
        # 网易云
        # --------------------------

        if "music.163.com" in msg:

            match = re.search(
                r"id=(\d+)",
                msg
            )


            if match:

                song_id = match.group(1)


                await self.send_163_music(
                    event,
                    song_id
                )


                event.stop_event()

                return



        # --------------------------
        # QQ音乐
        # --------------------------

        if "y.qq.com" in msg:

            match = re.search(
                r"songDetail/([A-Za-z0-9]+)",
                msg
            )


            if match:

                song_id = match.group(1)


                await self.send_qq_music(
                    event,
                    song_id
                )


                event.stop_event()

                return
