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

        if (
            "music.163.com" in msg
            or "y.qq.com" in msg
        ):
            yield event.plain_result(
                "检测到音乐链接：" + msg
            )
