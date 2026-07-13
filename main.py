import re
import json
import httpx

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



    # =========================
    # 发送消息
    # =========================

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



    # =========================
    # 网易云
    # =========================

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



    # =========================
    # songid 转 songmid
    # =========================

    async def get_songmid(
        self,
        songid
    ):

        try:

            url = (
                "https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg"
                f"?songid={songid}"
            )


            async with httpx.AsyncClient(
                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                },
                timeout=10
            ) as client:


                r = await client.get(url)


                data = r.json()


                mid = data["data"][0]["mid"]


                return mid


        except Exception:

            return None



    # =========================
    # QQ音乐卡片
    # =========================

    async def send_qq(
        self,
        event,
        songid=None,
        songmid=None
    ):


        # 没有songmid，用songid查询

        if not songmid and songid:

            songmid = await self.get_songmid(
                songid
            )


        if not songmid:

            return



        jump_url = (
            "https://y.qq.com/n/ryqq/songDetail/"
            f"{songmid}"
        )


        card = {


            "app": "com.tencent.qqmusic",


            "view": "song",


            "ver": "0.0.0.1",


            "prompt": "[分享]QQ音乐",


            "meta": {


                "music": {


                    "appid": "100497308",


                    "songmid": songmid,


                    "jumpUrl": jump_url,


                    "preview": "",


                    "title": "QQ音乐歌曲"


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



        # 网易云

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



        # QQ音乐


        if (

            "y.qq.com" in text

            or "c6.y.qq.com" in text

        ):


            qq = await parse_qq_music(
                text
            )


            if (

                qq["songid"]

                or qq["songmid"]

            ):


                await self.send_qq(

                    event,

                    songid=qq["songid"],

                    songmid=qq["songmid"]

                )


                event.stop_event()

                return
