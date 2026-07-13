import re

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Star, register


@register(
    "astrbot_plugin_music_card",
    "Sihnbaobao",
    "QQ音乐网易云音乐链接转音乐卡片",
    "0.1.0"
)
class MusicCardPlugin(Star):

    def __init__(self, context):
        super().__init__(context)


    @filter.event_message_type(filter.EventMessageType.ALL)
    async def music_card(self, event: AstrMessageEvent):

        msg = event.message_str

        # 网易云音乐
        if "music.163.com" in msg:

            match = re.search(r"id=(\d+)", msg)

            if match:
                song_id = match.group(1)

                await event.send(
                    {
                        "type": "music",
                        "data": {
                            "type": "163",
                            "id": song_id
                        }
                    }
                )

                return


        # QQ音乐
        if "y.qq.com" in msg:

            match = re.search(
                r"songDetail/([A-Za-z0-9]+)",
                msg
            )

            if match:
                song_id = match.group(1)

                await event.send(
                    {
                        "type": "music",
                        "data": {
                            "type": "qq",
                            "id": song_id
                        }
                    }
                )

                return
