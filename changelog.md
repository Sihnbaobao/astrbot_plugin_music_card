## v0.6.0

- 放弃外部签名服务，自建 `com.tencent.structmsg` 格式 Ark JSON 卡片
- 封面图直接嵌入 `preview` 和 `source_icon` 字段（500x500）
- 移除音频直链，卡片不再报"服务器异常"
- 点击卡片跳转 QQ 音乐网页播放

## v0.5.x

- 新增 QQ 音乐登录凭据配置（WebUI 填 Cookie）
- QQ 音乐卡片改为三层策略：Arkk卡片 → 签名服务 → custom 回退
- 签名服务支持 type:qq 和 type:custom（思思默认服务）
- zzc_sign 签名算法实现（QQ 音乐 musics.fcg 接口）

## v0.3.x

- 重构 send_qq_card：优先尝试原生 type:qq 卡片，失败回退 custom
- QQ 音乐凭据支持手填完整 Cookie（WebUI textarea 配置）
- song_id → songmid 转换、歌曲详情 API 调用

## v0.2.1

- 修复 vkey 调用函数内重复 import

## v0.2.0

- QQ 音乐歌曲信息 API 调用（标题/歌手/封面/songmid）
- vkey 接口调用获取可播放音频直链
- songid → songmid 转换

## v0.1.0

- 初始版本：网易云音乐链接转卡片（type:163）
- QQ 音乐链接检测基础支持
