"""网易云扫码登录。

流程：取 unikey -> 画二维码 -> 手机扫码 -> 轮询拿到 MUSIC_U / __csrf。
接口走 weapi，并且整段流程共用一个 cookie 会话（NMTID 要跟着走）。
"""

import base64
import io
import json
import random
import string

import httpx
from Crypto.Cipher import AES

_UNIKEY_URL = "https://music.163.com/weapi/login/qrcode/unikey"
_POLL_URL = "https://music.163.com/weapi/login/qrcode/client/login"
_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"}
_STATES = {800: "expired", 801: "waiting", 802: "scanned", 803: "confirmed"}

_MODULUS = (
    "00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e"
    "417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee25593257"
    "5cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7"
)
_PUBKEY = "010001"
_NONCE = b"0CoJUm6Qyw8W8jud"
_IV = b"0102030405060708"


def _pad(data):
    """PKCS7 补齐到 16 字节。"""
    count = 16 - len(data) % 16
    return data + bytes([count]) * count


def _aes(text, key):
    """AES-CBC 加密并转成 base64 文本。"""
    cipher = AES.new(key, AES.MODE_CBC, _IV)
    return base64.b64encode(cipher.encrypt(_pad(text))).decode("ascii")


def _rsa(secret):
    """把随机密钥倒序后做 RSA，得到 encSecKey。"""
    raw = int(secret[::-1].encode().hex(), 16)
    return format(pow(raw, int(_PUBKEY, 16), int(_MODULUS, 16)), "x").zfill(256)


def _weapi(payload):
    """把参数加密成 weapi 需要的 params / encSecKey。

    Args:
        payload: 要发送的明文字典。

    Returns:
        包含 params、encSecKey、csrf_token 的表单字典。
    """
    text = json.dumps(payload, separators=(",", ":"))
    secret = "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(16)
    )
    params = _aes(_aes(text.encode(), _NONCE).encode(), secret.encode())
    return {"params": params, "encSecKey": _rsa(secret), "csrf_token": ""}


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


def _cookie_string(cookies):
    """把 Cookie 字典拼成请求头字符串。"""
    return "; ".join(
        f"{key}={value}" for key, value in cookies.items() if key and value
    )


class NeteaseLogin:
    """一次扫码登录会话，内部保持同一个 httpx 客户端以保留 cookie。"""

    def __init__(self):
        self._client = None

    async def _get_client(self):
        """懒加载一个带 cookie jar 的客户端。"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10, headers=_HEADERS)
        return self._client

    async def close(self):
        """关闭客户端，丢弃这次登录会话。"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def generate(self):
        """生成登录二维码。

        Returns:
            包含 key、url、image 的字典。

        Raises:
            RuntimeError: 网易云没有返回 unikey。
            httpx.HTTPError: 接口请求失败。
        """
        client = await self._get_client()
        response = await client.post(_UNIKEY_URL, data=_weapi({"type": 1}))
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
        client = await self._get_client()
        response = await client.post(_POLL_URL, data=_weapi({"key": key, "type": 1}))
        response.raise_for_status()
        payload = response.json()
        code = int(payload.get("code") or 0)
        state = _STATES.get(code, "unknown")
        cookies = dict(client.cookies.items())
        result = {
            "state": state,
            "message": str(payload.get("message") or ""),
            "cookies": cookies,
        }
        if state == "confirmed":
            if not cookies.get("__csrf"):
                try:
                    home = await client.get("https://music.163.com/")
                    csrf = str(home.cookies.get("__csrf") or "")
                except Exception:
                    csrf = ""
                if csrf:
                    cookies["__csrf"] = csrf
            result["cookie"] = _cookie_string(cookies)
            result["cookies"] = cookies
        return result
