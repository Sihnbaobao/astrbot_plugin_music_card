## v2.0.0

- QQ音乐链接改为搜网易云,找到即发 type:163 原生卡片(可点播+封面)
- 删除所有无效代码: zzc_sign / vkey / QR登录 / OAuth / cookie
- 代码精简: main.py ~140行 qqcard.py ~90行

## v1.x

- 尝试多种方案(vkey/cookie/签名服务/QR登录),均因QQ音乐接口限制未能实现可点播
- 改为网易云卡片搜索方案

## v0.x

- 初始版本: 网易云链接转卡片, QQ音乐基础支持
