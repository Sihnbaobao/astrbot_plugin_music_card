"""网易云扫码登录。

流程：取 unikey -> 画二维码 -> 手机扫码 -> 轮询拿到 MUSIC_U / __csrf。
"""

import base64
import io

import httpx

_UNIKEY_URL = "https://music.163.com/api/login/qrcode/unikey"
_POLL_URL = "https://music.163.com/api/login/qrcode/client/login"
_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"}
_STATES = {800: "expired", 801: "waiting", 802: "scanned", 803: "confirmed"}


def _render_qr(text):
    """把文本画成二维码。

    Args:
        text: 二维码内容。

    Returns:
        PNG 的 data URL；没装 qrcode 库时返回空串。
    """
    try:
        import qrcode
    except ImportError:
        return ""
    image = qrcode.make(text)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _cookies_from_response(response):
    """从响应里收集 Cookie，httpx 的容器和 Set-Cookie 头都读一遍。

    Args:
        response: httpx 响应。

    Returns:
        Cookie 名值字典。
    """
    cookies = dict(response.cookies.items())
    for header in response.headers.get_list("set-cookie"):
        head = header.split(";", 1)[0]
        if "=" not in head:
            continue
        key, value = head.split("=", 1)
        cookies.setdefault(key.strip(), value.strip())
    return cookies


def _cookie_string(cookies):
    """把 Cookie 字典拼成请求头字符串。"""
    return "; ".join(
        f"{key}={value}" for key, value in cookies.items() if key and value
    )


async def _fetch_csrf(cookie):
    """访问首页补一个 __csrf，登录响应里偶尔没有它。

    Args:
        cookie: 当前 Cookie 字符串。

    Returns:
        __csrf 的值；拿不到时返回空串。
    """
    try:
        async with httpx.AsyncClient(
            timeout=10, headers={**_HEADERS, "Cookie": cookie}
        ) as client:
            response = await client.get("https://music.163.com/")
            return str(response.cookies.get("__csrf") or "")
    except Exception:
        return ""


class NeteaseLogin:
    """一次扫码登录会话。"""

    async def generate(self):
        """生成登录二维码。

        Returns:
            包含 key、url、image 的字典。

        Raises:
            RuntimeError: 网易云没有返回 unikey。
            httpx.HTTPError: 接口请求失败。
        """
        async with httpx.AsyncClient(timeout=10, headers=_HEADERS) as client:
            response = await client.post(_UNIKEY_URL, data={"type": "1"})
            response.raise_for_status()
            payload = response.json()
        key = str(payload.get("unikey") or "")
        if not key:
            raise RuntimeError("网易云没有返回二维码 key")
        url = f"https://music.163.com/login?codekey={key}"
        return {"key": key, "url": url, "image": _render_qr(url)}

    async def poll(self, key):
        """查询一次扫码状态。

        Args:
            key: generate 返回的 unikey。

        Returns:
            包含 state、message、cookies 的字典；确认登录时额外带 cookie。

        Raises:
            httpx.HTTPError: 接口请求失败。
        """
        async with httpx.AsyncClient(timeout=10, headers=_HEADERS) as client:
            response = await client.post(_POLL_URL, data={"key": key, "type": "1"})
            response.raise_for_status()
            payload = response.json()
            cookies = _cookies_from_response(response)
        code = int(payload.get("code") or 0)
        state = _STATES.get(code, "unknown")
        result = {
            "state": state,
            "message": str(payload.get("message") or ""),
            "cookies": cookies,
        }
        if state == "confirmed":
            if not cookies.get("__csrf"):
                csrf = await _fetch_csrf(_cookie_string(cookies))
                if csrf:
                    cookies["__csrf"] = csrf
            result["cookie"] = _cookie_string(cookies)
            result["cookies"] = cookies
        return result
