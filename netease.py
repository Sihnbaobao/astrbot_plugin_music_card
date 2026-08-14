import httpx

from astrbot.core import logger


async def get_netease_song(song_id):
    """按歌曲 ID 查询网易云歌曲,返回 {id,name,artist,url,pic,audio}。

    pic 为封面图,audio 为官方外链播放地址,用于自建分享卡片;
    歌曲不存在(或不是歌曲,如歌单/用户 ID)时返回 None;
    网络/接口异常时抛出异常,由调用方决定是否降级发送。
    """
    async with httpx.AsyncClient(
        timeout=6, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"}
    ) as c:
        r = await c.get(
            "https://music.163.com/api/song/detail/",
            params={"id": song_id, "ids": f"[{song_id}]"},
        )
        songs = r.json().get("songs", [])
    if not songs:
        return None
    s = songs[0]
    artists = s.get("artists") or []
    album = s.get("album") or {}
    pic = album.get("picUrl") or (artists[0].get("img1v1Url") if artists else "") or ""
    return {
        "id": str(s.get("id") or song_id),
        "name": s.get("name", ""),
        "artist": artists[0].get("name", "") if artists else "",
        "url": f"https://y.music.163.com/m/song?id={song_id}",
        "pic": pic,
        "audio": f"https://music.163.com/song/media/outer/url?id={song_id}&sc=wm&tn=",
    }


async def search_netease(title, singer=""):
    """搜索单首,返回第一条结果"""
    results = await search_netease_multi(f"{title} {singer}", limit=1)
    return results[0] if results else None


async def search_netease_multi(query, limit=5):
    """搜索多首,返回列表含歌名/歌手/ID"""
    try:
        async with httpx.AsyncClient(
            timeout=10, headers={"User-Agent": "Mozilla/5.0"}
        ) as c:
            r = await c.get(
                "https://music.163.com/api/search/get/web",
                params={
                    "s": query, "type": 1,
                    "offset": 0, "limit": limit, "csrf_token": "",
                }
            )
            songs = r.json().get("result", {}).get("songs", [])
        return [
            {
                "id": str(s["id"]), "name": s["name"],
                "artist": s.get("artists", [{}])[0].get("name", "")
            }
            for s in songs
        ]
    except Exception as e:
        logger.warning(f"搜索失败:{e}")
        return []