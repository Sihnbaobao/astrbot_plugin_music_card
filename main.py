from astrbot.api.star import Star
from astrbot.api import register
from astrbot.api.event import filter, AstrMessageEvent

from .utils.parser import parse_music_url


@register(
    "music_card",
    "your_name",
    "音乐链接转卡片",
    "0.1.0"
)
class MusicCardPlugin(Star):

    def __init__(self, context):
        super().__init__(context)


    @filter.on_message()
    async def handle_music_link(
        self,
        event: AstrMessageEvent
    ):

        msg = event.message_str

        music = parse_music_url(msg)

        if not music:
            return


        try:

            await event.bot.call_action(
                "send_music",
                **{
                    "user_id":
                    event.get_sender_id(),

                    "type":
                    music["type"],

                    "id":
                    music["id"]
                }
            )


        except Exception as e:

            self.context.logger.error(
                f"音乐卡片发送失败:{e}"
            )