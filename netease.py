import httpx

from astrbot.core import logger


async def search_netease(title, singer=""):
    """搜索单首,返回第一条结果"""
    results = await search_netease_multi(f"{title} {singer}", limit=1)
    return results[0] if results else None


async def search_netease_multi(query, limit=5):
    """搜索多首,返回列表含歌名/歌手/ID"""
    try:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.get("https://music.163.com/api/search/get/web", params={
                "s": query, "type": 1, "offset": 0, "limit": limit, "csrf_token": ""
            })
            songs = r.json().get("result", {}).get("songs", [])
        return [
            {"id": str(s["id"]), "name": s["name"],
             "artist": s.get("artists", [{}])[0].get("name", "")}
            for s in songs
        ]
    except Exception as e:
        logger.warning(f"搜索失败:{e}")
        return []
