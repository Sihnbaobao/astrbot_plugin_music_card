import re
import os
import asyncio
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
    create_qr_login,
    check_qr_login,
    exchange_code
)


print("========== music_card 加载检查 ==========")
print("main.py路径:", os.path.abspath(__file__))
print("========================================")


@register(
    "astrbot_plugin_music_card",
    "Sihnbaobao",
    "QQ音乐网易云音乐链接转换音乐卡片",
    "1.3.0"
)
class MusicCardPlugin(Star):

    def __init__(
        self,
        context,
        config=None
    ):

        super().__init__(context)


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


        message = [
            {
                "type":
                "music",

                "data":
                {
                    "type":
                    "custom",

                    "url":
                    qq.get("url", ""),

                    "audio":
                    qq.get("audio", ""),

                    "image":
                    qq.get("pic", ""),

                    "title":
                    qq.get("title", "QQ音乐"),

                    "content":
                    qq.get("singer", ""),

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
        # QQ音乐登录命令
        # =====================

        if text.strip().startswith("/qqmusic\u767b\u5f55"):

            event.stop_event()


            await self.send_music(
                event,
                [{"type": "text", "data": {"text": "\u6b63\u5728\u751f\u6210\u767b\u5f55\u4e8c\u7ef4\u7801..."}}]
            )

            qrcookie, qrsig, qr_png = await create_qr_login()

            if not qrsig:
                await self.send_music(
                    event,
                    [{"type": "text", "data": {"text": "\u751f\u6210\u4e8c\u7ef4\u7801\u5931\u8d25,\u8bf7\u7a0d\u540e\u91cd\u8bd5"}}]
                )
                return


            from base64 import b64encode

            b64_img = b64encode(qr_png).decode()

            await self.send_music(
                event,
                [{"type": "image", "data": {"file": f"base64://{b64_img}", "type": "base64"}}]
            )

            await self.send_music(
                event,
                [{"type": "text", "data": {"text": "\u8bf7\u7528\u624b\u673aQQ\u626b\u63cf\u4e0a\u65b9\u4e8c\u7ef4\u7801\u767b\u5f55\uff0c\u6709\u6548\u671f120\u79d2\u3002"}}]
            )


            for i in range(60):

                await asyncio.sleep(2)

                status, info = await check_qr_login(qrsig)

                if status == "ok":
                    cookie_str, uin = await exchange_code(info)

                    if cookie_str:
                        await self.send_music(
                            event,
                            [{"type": "text", "data": {"text": f"\u767b\u5f55\u6210\u529f! uin={uin}"}}]
                        )
                    else:
                        await self.send_music(
                            event,
                            [{"type": "text", "data": {"text": "\u767b\u5f55\u6210\u529f\u4f46cookie\u83b7\u53d6\u5931\u8d25,\u8bf7\u8bd5\u8bd5\u624b\u52a8\u7c98\u8d34cookie\u5230\u914d\u7f6e\u9879"}}]
                        )
                    return

                elif status == "confirm":
                    await self.send_music(
                        event,
                        [{"type": "text", "data": {"text": "\u5df2\u626b\u7801,\u8bf7\u5728\u624b\u673a\u4e0a\u786e\u8ba4\u767b\u5f55..."}}]
                    )

                elif status == "expired":
                    await self.send_music(
                        event,
                        [{"type": "text", "data": {"text": "\u4e8c\u7ef4\u7801\u5df2\u8fc7\u671f,\u8bf7\u91cd\u65b0\u53d1\u9001 /qqmusic\u767b\u5f55"}}]
                    )
                    return

                elif status == "scan":
                    if i == 0:
                        await self.send_music(
                            event,
                            [{"type": "text", "data": {"text": "\u68c0\u6d4b\u5230\u626b\u7801,\u8bf7\u5728\u624b\u673a\u4e0a\u786e\u8ba4..."}}]
                        )

            await self.send_music(
                event,
                [{"type": "text", "data": {"text": "\u767b\u5f55\u8d85\u65f6,\u8bf7\u91cd\u65b0\u53d1\u9001 /qqmusic\u767b\u5f55"}}]
            )
            return




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
