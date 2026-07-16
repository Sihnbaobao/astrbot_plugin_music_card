import httpx

from astrbot.core import logger


async def search_netease(title, singer=""):

    try:

        keyword = f"{title} {singer}"


        async with httpx.AsyncClient(
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        ) as client:


            r = await client.get(
                "https://music.163.com/api/search/get/web",
                params={
                    "s": keyword,
                    "type": 1,
                    "offset": 0,
                    "limit": 5,
                    "csrf_token": ""
                }
            )


            songs = (
                r.json()
                .get("result", {})
                .get("songs", [])
            )


            if not songs:
                return None


            song = songs[0]


            return {
                "id": str(song["id"]),
                "name": song["name"]
            }



    except Exception as e:

        logger.warning(f"网易云搜索失败:{e}")
        return None
