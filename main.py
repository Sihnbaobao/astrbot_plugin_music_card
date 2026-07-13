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

        if "music.163.com" in msg:

            match = re.search(r"id=(\d+)", msg)

            if match:

                song_id = match.group(1)

                await event.bot.api.call_action(
                    "send_private_msg",
                    user_id=event.get_sender_id(),
                    message=[
                        {
                            "type": "music",
                            "data": {
                                "type": "163",
                                "id": song_id
                            }
                        }
                    ]
                )

                return
