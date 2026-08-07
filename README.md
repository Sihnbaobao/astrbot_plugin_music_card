# 音乐链接转网易云卡片

将 QQ音乐 / 酷狗 / 网易云 链接自动转为网易云原生卡片（`type:"163"`）。

## 功能

- 网易云、QQ音乐、酷狗链接自动转卡片
- LLM 工具 `search_songs` + `send_song_card`：bot 聊天中自主搜歌发卡片

## 安装

```
https://github.com/Sihnbaobao/astrbot_plugin_music_card
```

## 环境

AstrBot >= 4.26 · aiocqhttp + NapCatQQ · Python >= 3.10 · httpx

## 更新日志

- **1.1.2** `send_song_card` 加纯随缘意愿判定，30% 概率拒绝发卡，不再是"有求必应"
- **1.1.1** 优化 LLM 工具描述，支持 bot 在聊天中主动搜歌/分享歌曲，发卡片前由 LLM 自行判断
- **1.1.0** 添加 LLM 工具 `search_songs` + `send_song_card`，bot 可自主搜歌发卡片
- **1.0.0** QQ/酷狗/网易云链接转卡片
