"""网易云 weapi 参数加密。

登录、发评论这类写接口都要把参数加密成 params / encSecKey。
"""

import base64
import json
import random
import string

from Crypto.Cipher import AES

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


def weapi(payload):
    """把参数加密成 weapi 需要的表单。

    Args:
        payload: 要发送的明文字典。

    Returns:
        包含 params 和 encSecKey 的表单字典。
    """
    text = json.dumps(payload, separators=(",", ":"))
    secret = "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(16)
    )
    params = _aes(_aes(text.encode(), _NONCE).encode(), secret.encode())
    return {"params": params, "encSecKey": _rsa(secret)}
