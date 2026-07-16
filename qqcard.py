import re
import os
import json as _json
import time as _time
import httpx

from base64 import b64encode
from hashlib import sha1

from astrbot.core import logger


QQ_API = "https://u.y.qq.com/cgi-bin/musicu.fcg"
QQ_API_V2 = "https://u6.y.qq.com/cgi-bin/musics.fcg"

COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qqmusic_cookie.json")

_qq_cookie = ""
_qq_uin = 0

PART_1 = [23, 14, 6, 36, 16, 7, 19]
PART_2 = [16, 1, 32, 12, 19, 27, 8, 5]
SCRAMBLE = [89, 39, 179, 150, 218, 82, 58, 252, 177, 52,
            186, 123, 120, 64, 242, 133, 143, 161, 121, 179]


def zzc_sign(text):
    if isinstance(text, str):
        text = text.encode()
    h = sha1(text).hexdigest().upper()
    p1 = "".join(h[i] for i in PART_1)
    p2 = "".join(h[i] for i in PART_2)
    p3 = bytearray(20)
    for i, v in enumerate(SCRAMBLE):
        p3[i] = v ^ int(h[i * 2:i * 2 + 2], 16)
    b64 = re.sub(rb"[\\/+=]", b"", b64encode(p3)).decode()
    return f"zzc{p1}{b64}{p2}".lower()


def _hash33(s):
    v = 0
    for c in s:
        v += (v << 5) + ord(c)
    return v & 0x7fffffff


def load_cookie():
    global _qq_cookie, _qq_uin
    try:
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE, "r") as f:
                data = _json.load(f)
            _qq_cookie = data.get("cookie", "")
            _qq_uin = data.get("uin", 0)
            logger.info(f"已加载缓存cookie,uin={_qq_uin}")
    except Exception as e:
        logger.warning(f"加载cookie失败:{e}")


def save_cookie(cookie, uin):
    global _qq_cookie, _qq_uin
    _qq_cookie = cookie
    _qq_uin = uin
    try:
        with open(COOKIE_FILE, "w") as f:
            _json.dump({"cookie": cookie, "uin": uin}, f)
        logger.info(f"cookie已保存,uin={uin}")
    except Exception as e:
        logger.warning(f"保存cookie失败:{e}")


async def create_qr_login():
    cookie = ""
    qrsig = ""
    try:
        import random
        url = (
            "https://ssl.ptlogin2.qq.com/ptqrshow"
            "?appid=716027609"
            "&e=2&l=M&s=3&d=72&v=4"
            f"&t={random.random()}"
            "&daid=383"
            "&pt_3rd_aid=100497308"
        )
        async with httpx.AsyncClient(
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://xui.ptlogin2.qq.com/"}
        ) as c:
            r = await c.get(url)
            for h in r.headers.get_list("set-cookie"):
                if "qrsig" in h:
                    qrsig = h.split(";")[0].split("=", 1)[1]
                    break
            else:
                for h in r.headers.get_list("Set-Cookie"):
                    if "qrsig" in h:
                        qrsig = h.split(";")[0].split("=", 1)[1]
                        break
            if qrsig:
                cookie = f"qrsig={qrsig}"
                logger.info(f"qrsig获取成功")
                return cookie, qrsig, r.content
    except Exception as e:
        logger.warning(f"生成二维码失败:{e}")
    return None, None, None


async def check_qr_login(qrsig):
    try:
        ptqrtoken = _hash33(qrsig)
        url = (
            "https://ssl.ptlogin2.qq.com/ptqrlogin"
            f"?ptqrtoken={ptqrtoken}"
            "&u1=https://y.qq.com/portal/wx_redirect.html?login_type=2&surl=https://y.qq.com/"
            "&ptredirect=0&h=1&t=1&g=1&from_ui=1&ptlang=2052"
            "&action=0-0-0&js_ver=20102616&js_type=1"
            "&pt_uistyle=40&aid=716027609&daid=383&pt_3rd_aid=100497308"
        )
        async with httpx.AsyncClient(
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://xui.ptlogin2.qq.com/"},
            cookies={"qrsig": qrsig}
        ) as c:
            r = await c.get(url)
            text = r.text

            m = re.search(r"'(\d+)'", text)
            code = m.group(1) if m else ""

            if code == "0":
                m2 = re.search(r"'([^']*https?://[^']*)'", text)
                if m2:
                    redirect = m2.group(1)
                    logger.info(f"扫码成功redirect:{redirect[:80]}")
                    return "ok", redirect
                return "ok", text
            elif code == "66":
                return "scan", text
            elif code == "65":
                return "expired", text
            elif code == "67":
                return "confirm", text
            else:
                return str(code), text
    except Exception as e:
        logger.warning(f"检查扫码失败:{e}")
    return "error", ""


async def exchange_code(redirect_url):
    try:
        import uuid
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        m = re.search(r"ptsigx=([^&\s'\"#]+)", redirect_url)
        uin_match = re.search(r"uin=(\d+)", redirect_url)
        uin = int(uin_match.group(1)) if uin_match else 0
        ptsigx = m.group(1) if m else ""

        if not ptsigx or not uin:
            logger.warning("未提取到ptsigx")
            return None, 0

        logger.info(f"exchange:uin={uin}")

        # Step 1: check_sig → p_skey
        cs_url = redirect_url.replace("ptlogin2.qq.com", "ssl.ptlogin2.graph.qq.com")
        async with httpx.AsyncClient(timeout=15, follow_redirects=False, headers=headers) as c:
            r = await c.get(cs_url)
            p_skey = ""
            for h in r.headers.get_list("set-cookie") or r.headers.get_list("Set-Cookie") or []:
                if "p_skey=" in h:
                    p_skey = h.split(";")[0].split("=", 1)[1]
                    break
            if not p_skey:
                logger.warning("未获取p_skey")
                return None, 0
            cs_cookies = "; ".join(f"{k}={v}" for k, v in dict(r.cookies).items())
            logger.info(f"p_skey获取成功,长度={len(p_skey)}")

        # Step 2: graph.qq.com OAuth → code
        g_tk = _hash33(p_skey)
        auth_url = (
            "https://graph.qq.com/oauth2.0/authorize"
            "?response_type=code"
            "&client_id=100497308"
            "&redirect_uri=https://y.qq.com/portal/wx_redirect.html?login_type=2&surl=https://y.qq.com/"
            "&scope=get_user_info,get_app_friends"
            "&state=state"
            f"&g_tk={g_tk}"
            f"&auth_time={int(_time.time())}"
            f"&ui={uuid.uuid4().hex[:16]}"
        )
        async with httpx.AsyncClient(timeout=15, follow_redirects=False, headers={
            **headers, "Cookie": f"p_skey={p_skey}; {cs_cookies}",
            "Referer": "https://xui.ptlogin2.qq.com/"
        }) as c:
            r2 = await c.get(auth_url)
            loc = r2.headers.get("location") or r2.headers.get("Location") or ""
            code = ""
            cm = re.search(r"code=([^&\s'\"#]+)", loc)
            if cm:
                code = cm.group(1)
            if not code:
                logger.warning(f"OAuth未获取code,location={loc[:100]}")
                return None, 0
            logger.info(f"OAuth code获取成功:{code[:20]}...")

        # Step 3: musicu.fcg → musickey/qm_keyst
        mbody = {
            "comm": {
                "g_tk": 0, "uin": uin, "format": "json",
                "inCharset": "utf-8", "outCharset": "utf-8",
                "notice": 0, "platform": "h5", "needNewCode": 1,
                "tmeLoginType": 2
            },
            "req_0": {
                "module": "QQConnectLogin.LoginServer",
                "method": "QQLogin",
                "param": {"code": code}
            }
        }
        async with httpx.AsyncClient(timeout=15, headers={
            **headers, "Referer": "https://y.qq.com/", "Origin": "https://y.qq.com"
        }) as c:
            r3 = await c.post(QQ_API, json=mbody)
            d = r3.json()
            mdata = d.get("req_0", {}).get("data", {})
            musickey = mdata.get("musickey", "") or mdata.get("qqmusic_key", "")
            musicid = mdata.get("musicid", uin)
            logger.info(f"musickey长度={len(musickey)}, musicid={musicid}")

            if musickey:
                cookie_str = (
                    f"uin=o{musicid}; qm_keyst={musickey}; "
                    f"qqmusic_key={musickey}; tmeLoginType=2; "
                    f"login_type=2; tmeLoginMethod=3"
                )
                save_cookie(cookie_str, int(musicid))
                return cookie_str, int(musicid)
            logger.warning("musickey为空")

    except Exception as e:
        logger.warning(f"exchange_code失败:{e}")
    return None, 0


async def get_playable_url(song_mid):
    uin = _qq_uin
    cookie = _qq_cookie

    body = {
        "comm": {
            "ct": 23, "cv": 0, "uin": uin,
            "format": "json", "platform": "h5",
            "inCharset": "utf-8", "outCharset": "utf-8",
            "notice": 0, "needNewCode": 1
        },
        "req_0": {
            "module": "music.vkey.GetVkeyServer",
            "method": "GetVkey",
            "param": {
                "guid": "10000", "songmid": [song_mid], "songtype": [0],
                "filename": [f"C400{song_mid}.m4a"],
                "uin": str(uin) if uin else "0",
                "loginflag": 1 if uin else 0,
                "platform": "20"
            }
        }
    }

    body_str = _json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    sign = zzc_sign(body_str)
    url = f"{QQ_API_V2}?_webcgikey=GetVkey&sign={sign}&_={int(_time.time() * 1000)}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://y.qq.com/", "Origin": "https://y.qq.com",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    if cookie:
        headers["Cookie"] = cookie

    try:
        async with httpx.AsyncClient(timeout=10, headers=headers) as c:
            r = await c.post(url, data=body_str)
            data = r.json()
    except Exception as e:
        logger.warning(f"vkey请求失败:{e}")
        return None

    try:
        inner = data.get("req_0", {})
        code = inner.get("code", -1)
        if code == 0:
            d = inner.get("data", {})
            sip = d.get("sip", [])
            infos = d.get("midurlinfo", [])
            if infos and sip:
                purl = infos[0].get("purl", "")
                if purl:
                    audio = sip[0] + purl
                    logger.info(f"vkey成功:{audio[:80]}...")
                    return audio
        else:
            logger.warning(f"vkey code={code}, subcode={inner.get('subcode')}")
    except Exception as e:
        logger.warning(f"vkey解析:{e}")
    return None


async def convert_songid_to_mid(songid):
    payload = {
        "comm": {"ct": 24, "cv": 0},
        "music.pf_song_detail_svr": {
            "method": "get_song_detail_yqq",
            "module": "music.pf_song_detail_svr",
            "param": {"song_id": int(songid)}
        }
    }
    try:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.post(QQ_API, json=payload)
            mid = r.json()["music.pf_song_detail_svr"]["data"]["track_info"]["mid"]
            return mid
    except:
        return None


async def get_qq_song(song_mid):
    payload = {
        "comm": {"ct": 24, "cv": 0},
        "songinfo": {
            "method": "get_song_detail_yqq",
            "module": "music.pf_song_detail_svr",
            "param": {"song_mid": song_mid}
        }
    }
    try:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.post(QQ_API, json=payload)
            track = r.json()["songinfo"]["data"]["track_info"]
    except:
        return None

    title = track.get("name", "")
    singer = (track.get("singer", [{}])[0].get("name", "") if track.get("singer") else "")
    pic = ""
    album_mid = track.get("album", {}).get("mid", "")
    if album_mid:
        pic = f"https://y.gtimg.cn/music/photo_new/T002R500x500M000/{album_mid}.jpg"

    audio = f"https://isure.stream.qqmusic.qq.com/C400{song_mid}.m4a?guid=10000&uin=0&fromtag=66"
    playable = await get_playable_url(song_mid)
    if playable:
        audio = playable

    return {
        "title": title, "singer": singer, "pic": pic,
        "url": f"https://y.qq.com/n/ryqq/songDetail/{song_mid}",
        "audio": audio, "songmid": song_mid,
        "song_id": track.get("id", 0)
    }


async def parse_qq_card(text):
    m = re.search(r"https?://[^\s]+", text)
    if not m:
        return None

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10,
                                     headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.get(m.group(0))
            real_url = str(r.url)
    except:
        return None

    logger.info(f"QQ真实地址:{real_url}")

    song_mid = None
    m2 = re.search(r"songDetail/([0-9A-Za-z]+)", real_url)
    if m2:
        val = m2.group(1)
        song_mid = await convert_songid_to_mid(val) if val.isdigit() else val

    if not song_mid:
        m2 = re.search(r"songmid=([0-9A-Za-z]+)", real_url)
        if m2:
            song_mid = m2.group(1)
    if not song_mid:
        m2 = re.search(r"songid=(\d+)", real_url)
        if m2:
            song_mid = await convert_songid_to_mid(m2.group(1))

    if not song_mid:
        return None

    logger.info(f"最终songmid:{song_mid}")
    return await get_qq_song(song_mid)


load_cookie()
