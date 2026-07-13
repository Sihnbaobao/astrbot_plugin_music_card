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


    async def send_music_card(
        self,
        event: AstrMessageEvent,
        music_type: str,
        song_id: str
    ):

        message = [
            {
                "type": "music",
                "data": {
                    "type": music_type,
                    "id": song_id
                }
            }
        ]

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


    @filter.event_message_type(filter.EventMessageType.ALL)
    async def music_card(self, event: AstrMessageEvent):

        msg = event.message_str


        # =====================
        # 网易云音乐
        # =====================

        if "music.163.com" in msg:

            match = re.search(
                r"id=(\d+)",
                msg
            )

            if match:

                song_id = match.group(1)

                await self.send_music_card(
                    event,
                    "163",
                    song_id
                )

                # 阻止 AI 继续回复
                event.stop_event()

                return


        # =====================
        # QQ音乐
        # =====================

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
