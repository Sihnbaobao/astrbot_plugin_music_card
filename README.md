# 音乐卡片插件 (AstrBot)

自动将 QQ音乐 / 网易云音乐 链接转为 OneBot 音乐卡片。

## 效果

- **网易云链接** → 原生 `type:"163"` 卡片，可点击播放 + 专辑封面
- **QQ音乐链接** → 自动搜网易云同款歌曲，找到即发 `type:"163"` 卡片，没找到发 custom 卡片

## 安装

WebUI 插件管理 → 仓库安装：
```
https://github.com/Sihnbaobao/astrbot_plugin_music_card
```

## 使用

群聊/私聊直接发音乐链接即可:

```
https://music.163.com/song?id=123456
https://y.qq.com/n/ryqq/songDetail/xxx
https://i.y.qq.com/v8/playsong.html?songid=123456
```

## 环境

- AstrBot >= 4.26
- aiocqhttp + NapCatQQ (OneBot v11)
