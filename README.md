# 音乐链接转网易云卡片

将 QQ音乐 / 酷狗 / 网易云 链接自动转为网易云原生音乐卡片（`type:"163"`），支持点击播放 + 专辑封面。

## 效果

- **网易云** → 原生卡片（可点播 + 封面）
- **QQ音乐** → 提取歌名歌手 → 搜网易云 → 发网易云卡片
- **酷狗** → 同上（share/chain 格式）
- **`/song 歌名`** → 直接搜歌发卡片
- **LLM 工具** → bot 可在聊天中自主搜歌发卡片

## 安装

AstrBot WebUI → 插件管理 → 仓库地址：
```
https://github.com/Sihnbaobao/astrbot_plugin_music_card
```

## 使用

直接发链接即可，无需命令：

| 平台 | 示例链接 |
|---|---|
| 网易云 | `https://music.163.com/song?id=123456` |
| QQ音乐 | `https://y.qq.com/n/ryqq/songDetail/xxx` |
| QQ音乐 | `https://i.y.qq.com/v8/playsong.html?songid=xxx` |
| 酷狗 | `https://m.kugou.com/share/song.html?chain=xxx` |

## 更新日志

**v1.0.x** — `search_songs` + `send_song_card` LLM 工具；优化代码结构；修复幻觉处理

**v1.0.0** — QQ音乐/酷狗/网易云链接转 type:163 卡片；`/song` 命令

## 环境

- AstrBot >= 4.26 · aiocqhttp + NapCatQQ / LLOneBot
- Python >= 3.10 · httpx
