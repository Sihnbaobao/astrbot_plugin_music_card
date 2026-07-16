# AstrBot Music Card Plugin

自动检测群聊/私聊里的 **QQ音乐** 和 **网易云音乐** 链接并发送 OneBot v11 音乐卡片。

## 功能

- 自动检测网易云音乐链接（`music.163.com` / `163cn.tv` 短链）→ 发送原生 `type:"163"` 音乐卡片，可点击播放
- 自动检测 QQ 音乐链接（`y.qq.com` / `c6.y.qq.com` / `i.y.qq.com` 含短链）→ 发送 QQ 音乐卡片
- QQ 音乐链接自动展开短链、解析 `songmid` / `songid`、调 QQ 音乐 API 拿歌曲信息
- 优先尝试原生 `type:"qq"` 卡片，NapCat 不支持时自动回退 `type:"custom"` 自定义卡片
- 支持配置 QQ 音乐登录 cookie，登录态下用 `musics.fcg` + `zzc_sign` 签名调用 vkey 接口拿可播放直链

## 环境

- AstrBot >= 4.26.5
- aiocqhttp 适配器
- NapCatQQ / LLOneBot 等 OneBot v11 协议端
- Python >= 3.10

## 安装

在 AstrBot WebUI 的「插件管理」页面，使用仓库地址安装：

```
https://github.com/Sihnbaobao/astrbot_plugin_music_card
```

或手动 clone 到 AstrBot 的 `data/plugins/` 目录：

```bash
cd AstrBot/data/plugins
git clone https://github.com/Sihnbaobao/astrbot_plugin_music_card
```

然后重启 AstrBot。

## 配置

插件支持以下配置项（在 WebUI「插件管理」→ 该插件下编辑）：

| 配置项 | 类型 | 说明 |
|---|---|---|
| `qqmusic_cookie` | text | QQ 音乐完整 Cookie。留空则匿名模式（QQ 音乐卡片会回退到 custom 显示为静态预览，不可直接点击播放）。 |

### 获取 QQ 音乐 Cookie

1. 浏览器打开 https://y.qq.com 并登录
2. 按 `F12` 打开开发者工具，切换到 `Network`（网络）面板
3. 刷新页面，在请求列表里任意找一个发往 `y.qq.com` / `u.y.qq.com` 的请求
4. 点开 → `Headers` 标签 → `Request Headers` 段里找到 `Cookie:` 这一行
5. **复制整行的值**（一长串 `xxx=yyy; zzz=www; ...`）粘到配置项 `qqmusic_cookie` 里
6. 保存配置并重启 AstrBot

Cookie 失效后（一般几天到几周）需要重新登录 y.qq.com 并更新配置。

## 使用

直接在 QQ 群聊或私聊里发送包含音乐链接的消息即可，无需任何命令前缀：

```
https://music.163.com/song?id=123456
https://y.qq.com/n/ryqq/songDetail/000abc...
https://i.y.qq.com/v8/playsong.html?songid=123456
https://c6.y.qq.com/base/fcgi-bin/u?__=xxxxx
```

插件会自动拦截消息，转换为音乐卡片发送，并阻止后续 AI 处理。

## 工作原理

### 网易云音乐

发送 OneBot v11 原生音乐卡片：

```json
[
  {
    "type": "music",
    "data": {
      "type": "163",
      "id": "<歌曲数字ID>"
    }
  }
]
```

QQNT 客户端内置了网易云分享卡片渲染，可直接点击播放。

### QQ 音乐

QQNT 客户端没有实现 `type:"qq"` 原生音乐卡片渲染（NapCat 会返回 `retcode=1200 消息体无法解析`），所以插件走以下策略：

1. **尝试** 发送 `type:"qq"` 原生卡片 → NapCat 拒收（1200）
2. **回退** 发送 `type:"custom"` 自定义卡片，需要填 `audio` 字段（可播放直链）

`audio` 直链的获取流程：

1. 跟随短链 redirect 得到真实 `songmid`
2. 调 `musicu.fcg` 的 `music.pf_song_detail_svr` 拿歌曲信息（标题、歌手、专辑封面 mid、数字 song_id）
3. 调 `musics.fcg` 的 `music.vkey.GetVkeyServer.GetVkey`，URL 带 `zzc_sign` 签名，登录态下带完整 cookie，拿可流式播放的 `purl`
4. 最终 audio = `sip[0] + purl`（带 vkey 的临时直链，有效期约数小时）

### zzc_sign 签名算法

QQ 音乐 web 端 `musics.fcg` 强制 URL 参数 `sign=zzcxxxxx` 校验，算法为：

1. body 字符串做 SHA1，得到 40 位 hex 大写
2. `part1` = 取索引 `[23,14,6,36,16,7,19]` 处的 7 个字符
3. `part2` = 取索引 `[16,1,32,12,19,27,8,5]` 处的 8 个字符
4. `part3` = 20 字节 SCR 数组与 SHA1 每两字符（一字节）异或
5. `b64` = `base64(part3)` 去掉 `/` `\` `+` `=`
6. 签名 = `zzc` + `part1` + `b64` + `part2`，整体小写

## 已知限制

- 「卡片上直接点击播放」在 NapCat + QQNT 环境下对 QQ 音乐是协议端限制，**网易云能而 QQ 音乐不能**（QQNT 内置了网易云分享卡片渲染，未实现 QQ 音乐原生分享）。本插件通过 vkey 拿真实播放直链填到 custom 卡片的 `audio` 字段，尽量让 QQ 客户端能在卡片上播放。
- QQ 音乐 cookie 失效后 vkey 会拿不到（响应 `req.code=500003`），需要重新登录 y.qq.com 取新 cookie。
- `type:"qq"` 原生卡片当前 100% 失败保留是为了未来 NapCat 一旦支持可自动生效。

## 致谢

- zzc_sign 算法参考：[L-1124/QQMusicApi](https://github.com/L-1124/QQMusicApi)、[AcheBreeze/qqmusic_qr_login](https://github.com/AcheBreeze/qqmusic_qr_login)
- 灵感与基础实现：AstrBot 社区