import re
import json

from astrbot.core import logger

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

        jump_url = (
            "https://i.y.qq.com/v8/playsong.html?"
            "songid="
            + songid
            + "&songtype=0"
        )

        card = {
            "app": "com.tencent.music",
            "desc": "QQ音乐",
            "view": "music",
            "ver": "0.0.0.0",
            "prompt": "[分享] QQ音乐",
            "meta": {
                "music": {
                    "title": "QQ音乐歌曲",
                    "desc": "QQ音乐",
                    "jumpUrl": jump_url,
                    "musicUrl": jump_url,
                    "preview": jump_url
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

        # =====================
        # 调试：打印收到的消息组件
        # =====================

        logger.info("========== 收到消息组件 ==========")

        try:

            logger.info(f"message_str: {text}")

            for comp in event.message_obj.message:

                logger.info(f"组件类型: {type(comp)}")

                logger.info(f"repr: {repr(comp)}")

                if hasattr(comp, "__dict__"):

                    logger.info(
                        json.dumps(
                            comp.__dict__,
                            ensure_ascii=False,
                            indent=4,
                            default=str
                        )
                    )

        except Exception:

            logger.exception("打印消息组件失败")

        logger.info("========== 结束 ==========")

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

            logger.info(
                f"QQ解析结果: {json.dumps(qq, ensure_ascii=False)}"
            )

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
