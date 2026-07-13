import re

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



    # =====================
    # 网易云
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
    # QQ音乐
    # =====================

    async def send_qq(
        self,
        event,
        songid=None,
        songmid=None
    ):


        if not songid:
            return



        # QQ音乐XML卡片

        jump_url = (
            "https://i.y.qq.com/v8/playsong.html?"
            "songid="
            + songid
            + "&songtype=0"
        )



        xml = f"""
<msg serviceID="2"
     templateID="1"
     action="web"
     actionData=""
     brief="[分享]QQ音乐"
     sourceMsgId="0"
     url="{jump_url}"
     flag="3">

    <item layout="0">

        <title>QQ音乐</title>

        <summary>点击播放歌曲</summary>

    </item>


    <item>

        <title>QQ音乐歌曲</title>

        <summary>来自QQ音乐分享</summary>

    </item>


    <source
        name="QQ音乐"
        icon="https://y.qq.com/favicon.ico"/>

</msg>
"""


        message = [

            {

                "type": "xml",

                "data": {

                    "data": xml

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



        # -----------------
        # 网易云
        # -----------------

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




        # -----------------
        # QQ音乐
        # -----------------

        if (

            "y.qq.com" in text

            or

            "c6.y.qq.com" in text

            or

            "i.y.qq.com" in text

        ):


            qq = await parse_qq_music(text)



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
