import re
import json

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


    async def send_music(self, event, message):

        try:

            group_id = getattr(
                event.message_obj,
                "group_id",
                None
            )


            if group_id:

                await event.bot.api.call_action(
                    "send_group_msg",
                    group_id=group_id,
                    message=message
                )

            else:

                await event.bot.api.call_action(
                    "send_private_msg",
                    user_id=event.get_sender_id(),
                    message=message
                )


        except Exception as e:

            self.log.error(
                f"发送音乐卡片失败: {e}"
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

                    "id": str(song_id)

                }

            }

        ]


        await self.send_music(
            event,
            message
        )



    # =====================
    # QQ音乐
    # =====================

    async def send_qq(
        self,
        event,
        songmid=None,
        songid=None
    ):


        if not songmid and not songid:

            return


        if songmid:

            url = (
                "https://y.qq.com/n/ryqq/songDetail/"
                f"{songmid}"
            )

        else:

            url = (
                "https://i.y.qq.com/v8/playsong.html?"
                f"songid={songid}"
            )



        card = {

            "app": "com.tencent.qqmusic",

            "view": "music",

            "ver": "0.0.0.0",

            "prompt": "分享音乐",

            "meta": {

                "music": {

                    "appid": "100497308",

                    "title": "QQ音乐歌曲",

                    "desc": "QQ音乐",

                    "jumpUrl": url,

                    "musicUrl": url,

                    "preview": url

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


        try:


            # 网易云

            if "music.163.com" in text:


                match = re.search(
                    r"(?:id=|song/)(\d+)",
                    text
                )


                if match:

                    await self.send_163(
                        event,
                        match.group(1)
                    )

                    event.stop_event()

                    return



            # QQ音乐

            if (
                "y.qq.com" in text
                or
                "c6.y.qq.com" in text
            ):


                qq = await parse_qq_music(
                    text
                )


                if not qq:

                    return


                await self.send_qq(
                    event,
                    songmid=qq.get(
                        "songmid"
                    ),
                    songid=qq.get(
                        "songid"
                    )
                )


                event.stop_event()


        except Exception as e:


            self.log.error(
                f"音乐卡片插件异常: {e}"
            )
