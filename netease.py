import httpx
import urllib.parse


async def search_netease(
    title,
    singer=""
):

    try:

        keyword = (
            title
            +
            " "
            +
            singer
        )


        url = (
            "https://music.163.com/api/search/get/web"
            "?csrf_token="
        )


        params = {

            "s": keyword,

            "type": 1,

            "offset": 0,

            "limit": 5

        }


        headers = {

            "User-Agent":
            "Mozilla/5.0"

        }


        async with httpx.AsyncClient(
            timeout=10
        ) as client:


            r = await client.get(
                url,
                params=params,
                headers=headers
            )


            data = r.json()



        songs = (
            data
            .get("result", {})
            .get("songs", [])
        )


        if not songs:

            return None



        song = songs[0]


        return {

            "id":
            str(song["id"]),


            "name":
            song["name"]

        }



    except Exception as e:


        print(
            "网易云搜索失败:",
            repr(e)
        )


        return None
