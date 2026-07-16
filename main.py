import re
import os
import httpx

from astrbot.core import logger

from astrbot.api.event import (
    filter,
    AstrMessageEvent
)

from astrbot.api.star import (
    Star,
    register
)

from .qqcard import (
    parse_qq_card,
    set_qq_credential,
    has_qq_credential,
    sign_qq_music_card,
    set_sign_url
)


print("========== music_card 加载检查 ==========")
print("main.py路径:", os.path.abspath(__file__))
print("========================================")


@register(
    "astrbot_plugin_music_card",
    "Sihnbaobao",
    "QQ音乐网易云音乐链接转换音乐卡片",
    "0.5.4"
)
class MusicCardPlugin(Star):

    def __init__(
        self,
        context,
        config=None
    ):

        super().__init__(context)


        if config is None:

            config = {}


        cookie = (

            config.get(
                "qqmusic_cookie",
                ""
            )

            or

            ""

        ).strip()


        if cookie:

            set_qq_credential(
                cookie
            )

            logger.info(
                "已加载QQ音乐登录凭据"
            )


        else:

            logger.info(
                "未配置QQ音乐登录凭据,匿名模式"
            )


        sign_url = (

            config.get(
                "qqmusic_sign_url",
                ""
            )

            or

            ""

        ).strip()


        set_sign_url(sign_url)


    async def expand_netease_url(
        self,
        url
    ):

        if "163cn.tv" not in url:
            return url


        try:

            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=10
            ) as client:

                r = await client.get(url)

                return str(r.url)


        except Exception as e:

            logger.warning(
                f"网易云短链展开失败:{e}"
            )

            return url



    async def send_music(
        self,
        event,
        message
    ):

        try:

            if event.message_obj.group_id:


                await event.bot.api.call_action(

                    "send_group_msg",

                    group_id=
                    event.message_obj.group_id,

                    message=
                    message

                )


            else:


                await event.bot.api.call_action(

                    "send_private_msg",

                    user_id=
                    event.get_sender_id(),

                    message=
                    message

                )


        except Exception as e:


            logger.error(
                f"发送消息失败:{e}"
            )

            raise




    # =========================
    # 网易云音乐
    # =========================

    async def send_163(
        self,
        event,
        song_id
    ):


        message = [

            {

                "type":
                "music",


                "data":
                {

                    "type":
                    "163",


                    "id":
                    song_id

                }

            }

        ]


        logger.info(
            f"发送网易云音乐:{message}"
        )


        await self.send_music(

            event,

            message

        )




    # =========================
    # QQ音乐
    # =========================

    async def send_qq_card(
        self,
        event,
        qq
    ):


        songmid = qq.get(
            "songmid",
            ""
        )


        if songmid:

            sign_body = {
                "type": "custom",
                "url": qq.get("url", ""),
                "title": qq.get("title", "QQ音乐"),
                "image": qq.get("pic", ""),
                "singer": qq.get("singer", "")
            }

            card_json = await sign_qq_music_card(
                sign_body
            )


            if card_json and len(card_json) > 50:

                message = [
                    {
                        "type": "json",
                        "data": {
                            "data": card_json
                        }
                    }
                ]


                logger.info(
                    f"发送QQ音乐Ark卡片,长度={len(card_json)}"
                )


                try:

                    await self.send_music(
                        event,
                        message
                    )

                    return

                except Exception as e:

                    logger.warning(
                        f"Ark卡片发送失败回退:{e}"
                    )



        message = [

            {

                "type":
                "music",


                "data":
                {

                    "type":
                    "custom",


                    "url":
                    qq.get(
                        "url",
                        ""
                    ),


                    "audio":
                    qq.get(
                        "audio",
                        ""
                    ),


                    "image":
                    qq.get(
                        "pic",
                        ""
                    ),


                    "title":
                    qq.get(
                        "title",
                        "QQ音乐"
                    ),


                    "content":
                    qq.get(
                        "singer",
                        ""
                    ),


                    "app":
                    "QQ音乐"

                }

            }

        ]


        logger.info(
            f"发送QQ custom卡片:{message}"
        )


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
        event:AstrMessageEvent
    ):


        text = event.message_str or ""


        logger.info(
            "========== 收到消息 =========="
        )


        logger.info(
            f"message_str:{text}"
        )




        # =====================
        # 网易云
        # =====================


        if (

            "music.163.com" in text

            or

            "163cn.tv" in text

        ):


            m = re.search(

                r"https?://[^\s]+",

                text

            )


            url = (

                m.group(0)

                if m

                else text

            )


            url = await self.expand_netease_url(

                url

            )


            logger.info(
                f"网易云真实地址:{url}"
            )


            m = re.search(

                r"id=(\d+)",

                url

            )


            if m:


                await self.send_163(

                    event,

                    m.group(1)

                )


                event.stop_event()

                return





        # =====================
        # QQ音乐
        # =====================


        if (

            "y.qq.com" in text

            or

            "c6.y.qq.com" in text

            or

            "i.y.qq.com" in text

        ):


            logger.info(
                "检测到QQ音乐"
            )


            qq = await parse_qq_card(

                text

            )


            logger.info(
                f"QQ解析结果:{qq}"
            )



            if qq:


                await self.send_qq_card(

                    event,

                    qq

                )


            else:


                logger.warning(
                    "QQ音乐解析失败"
                )


            event.stop_event()

            return





        # 防止AI处理音乐链接

        if (

            "music.163.com" in text

            or

            "163cn.tv" in text

            or

            "y.qq.com" in text

            or

            "c6.y.qq.com" in text

            or

            "i.y.qq.com" in text

        ):

            event.stop_event()

            return
