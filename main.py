import re
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

from .qqcard import parse_qq_card
from .netease import search_netease
from .kugou import parse_kugou_card


@register(
    "astrbot_plugin_music_card",
    "Sihnbaobao",
    "音乐链接转网易云卡片",
    "2.3.0"
)
class MusicCardPlugin(Star):

    def __init__(self, context, config=None):
        super().__init__(context)


    async def send_music(self, event, message):
        try:
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
        except Exception as e:
            logger.error(f"发送消息失败:{e}")
            raise


    async def send_netease_card(self, event, song_id):
        message = [
            {
                "type": "music",
                "data": {
                    "type": "163",
                    "id": song_id
                }
            }
        ]
        logger.info(f"发送网易云卡片:id={song_id}")
        await self.send_music(event, message)


async def send_custom_card(self, event, qq):
        message = [
            {
                "type": "music",
                "data": {
                    "type": "custom",
                    "url": qq.get("url", ""),
                    "audio": qq.get("audio", ""),
                    "image": qq.get("pic", ""),
                    "title": qq.get("title", "QQ\u97f3\u4e50"),
                    "content": qq.get("singer", ""),
                    "app": "QQ\u97f3\u4e50"
                }
            }
        ]
        logger.info("\u53d1\u9001custom\u5361\u7247")
        await self.send_music(event, message)


    @filter.llm_tool(name="search_song")
    async def search_song(self, event: AstrMessageEvent, query: str):
        """\u641c\u7d22\u4e00\u9996\u6b4c\u5e76\u53d1\u9001\u97f3\u4e50\u5361\u7247\u3002\u5f53\u4f60\u6216\u5bf9\u65b9\u5728\u804a\u5929\u4e2d\u63d0\u5230\u67d0\u9996\u6b4c\u65f6\uff0c\u53ef\u4ee5\u8c03\u7528\u6b64\u5de5\u5177\u53d1\u9001\u8be5\u6b4c\u66f2\u7684\u97f3\u4e50\u5361\u7247\u3002

        Args:
            query(string): \u8981\u641c\u7d22\u7684\u6b4c\u66f2\u540d\u79f0\uff0c\u6700\u597d\u5305\u542b\u6b4c\u624b\u540d\u4ee5\u63d0\u9ad8\u5339\u914d\u7cbe\u5ea6\uff0c\u4f8b\u5982\"\u6674\u5929 \u5468\u6770\u4f26\"
        """
        ne = await search_netease(query)
        if ne:
            await self.send_netease_card(event, str(ne["id"]))
            yield event.plain_result(f"\u5df2\u53d1\u9001\u6b4c\u66f2\u5361\u7247\uff1a{ne['name']}")
        else:
            yield event.plain_result(f"\u672a\u627e\u5230\u6b4c\u66f2\uff1a{query}")


    @filter.event_message_type(filter.EventMessageType.ALL)
    async def music_card(self, event: AstrMessageEvent):

        text = event.message_str or ""

        # ---- 点歌命令 ----
        if text.strip().startswith("/song ") or text.strip().startswith("/\u70b9\u6b4c "):

            query = text.strip().split(" ", 1)[1] if " " in text else ""

            if query:

                ne = await search_netease(query)

                if ne:

                    logger.info(f"\u70b9\u6b4c:{query} -> id={ne['id']}")
                    await self.send_netease_card(event, ne["id"])

                else:

                    await self.send_music(event, [{

                        "type": "text",

                        "data": {

                            "text": f"\u6ca1\u627e\u5230: {query}"

                        }

                    }])

            event.stop_event()
            return

        # ---- 网易云 ----
        if "music.163.com" in text or "163cn.tv" in text:
            m = re.search(r"https?://[^\s]+", text)
            if not m:
                return
            url = m.group(0)

            if "163cn.tv" in url:
                try:
                    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as c:
                        url = str((await c.get(url)).url)
                except Exception:
                    pass

            m = re.search(r"id=(\d+)", url)
            if m:
                await self.send_netease_card(event, m.group(1))
                event.stop_event()
                return

        # ---- QQ音乐 ----
        if "y.qq.com" in text or "c6.y.qq.com" in text or "i.y.qq.com" in text:
            qq = await parse_qq_card(text)

            if qq:
                title = qq.get("title", "")
                singer = qq.get("singer", "")

                ne = await search_netease(title, singer)

                if ne:
                    logger.info(f"QQ->网易云:{title}-{singer} -> id={ne['id']}")
                    await self.send_netease_card(event, ne["id"])
                    event.stop_event()
                    return

                logger.info(f"网易云未找到,fallback custom:{title}")
                await self.send_custom_card(event, qq)

            event.stop_event()
            return

        # ---- 酷狗音乐 ----
        if "kugou.com" in text:

            kg = await parse_kugou_card(text)

            if kg:
                ne = await search_netease(kg["title"], kg["singer"])

                if ne:
                    logger.info(f"酷狗->网易云:{kg['title']}-{kg['singer']} -> id={ne['id']}")
                    await self.send_netease_card(event, ne["id"])
                    event.stop_event()
                    return

            event.stop_event()
            return

        # 防止AI处理音乐链接
        if any(k in text for k in ["music.163.com","163cn.tv","y.qq.com","c6.y.qq.com","i.y.qq.com","kugou.com"]):
            event.stop_event()
