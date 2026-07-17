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

- **1.0.5** 优化代码结构，限制重复调用
- **1.0.4** artist 参数改为可选
- **1.0.3** search_songs 拆为 song_name + artist 两个参数
- **1.0.2** 拆分为 search_songs + send_song_card 两个 LLM 工具
- **1.0.1** 新增 search_song 工具，LLM 可自主搜歌
- **1.0.0** QQ/酷狗/网易云链接转卡片
