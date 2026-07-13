import re
import json

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Star, register


@register(
    "astrbot_plugin_music_card",
    "Sihnbaobao",
    "QQ音乐网易云音乐链接转换音乐卡片",
    "0.1.3"
)
class MusicCardPlugin(Star):

    def __init__(self, context):
        super().__init__(context)


    # =========================
    # 发送消息
    # =========================

    async def send_music(
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



    # =========================
    # 网易云音乐
    # =========================

    async def send_163(
        self,
        event,
        song_id
    ):

        msg = [
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
            msg
        )



    # =========================
    # QQ音乐
    # =========================

    async def send_qq(
        self,
        event,
        song_mid
    ):


        jump_url = (
            "https://i.y.qq.com/v8/playsong.html"
            "?platform=11"
            "&appshare=android_qq"
            "&appversion=20040008"
            f"&songmid={song_mid}"
            "&type=0"
            "&appsongtype=1"
            "&_wv=1"
            "&source=qq"
            "&ADTAG=qfshare"
        )


        card = {

            "app": "com.tencent.music",

            "view": "news",

            "ver": "1.0.0.0",

            "prompt": "[分享]QQ音乐",

            "meta": {

                "news": {

                    "title": "QQ音乐",

                    "desc": "QQ音乐歌曲",

                    "jumpUrl": jump_url,

                    "preview": "",

                    "tag": "QQ音乐"

                }

            }

        }



        msg = [

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
            msg
        )



    # =========================
    # 消息监听
    # =========================


    @filter.event_message_type(
        filter.EventMessageType.ALL
    )
    async def music_card(
        self,
        event: AstrMessageEvent
    ):


        text = event.message_str



        # -----------------
        # 网易云
        # -----------------

        if "music.163.com" in text:


            result = re.search(
                r"id=(\d+)",
                text
            )


            if result:

                song_id = result.group(1)


                await self.send_163(
                    event,
                    song_id
                )


                event.stop_event()

                return



        # -----------------
        # QQ音乐
        # -----------------

        if "y.qq.com" in text:


            result = re.search(
                r"songDetail/([A-Za-z0-9]+)",
                text
            )


            if result:

                song_mid = result.group(1)


                await self.send_qq(
                    event,
                    song_mid
                )


                event.stop_event()

                return
