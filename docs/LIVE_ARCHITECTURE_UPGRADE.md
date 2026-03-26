# USKing 直播架构升级落地说明

## 目标
- 站内实时观看：WebRTC
- 多平台分发：RTMP
- 公播/回放：HLS + CDN
- 当前 `legacy_jpeg`：仅保留为 fallback / 诊断链路

## 双平面架构
### 业务平面
- 继续由 FastAPI 承担用户、权限、直播间、公屏、回放索引、平台配置
- 对前端暴露统一媒体会话接口：
  - `GET /api/live/media/config`
  - `POST /api/live/media/host-session`
  - `GET /api/live/media/viewer-session/{username}`

### 媒体平面
- `realtime-signaling`：房间信令、媒体会话编排、TURN 协调
- `media-egress`：录制、RTMP fanout、HLS 打包、对象存储落盘
- `TURN/STUN`：NAT 穿透
- `Redis`：presence、房间在线态、幂等锁
- `PostgreSQL`：正式直播业务库

## 当前仓库中的实现位置
- 媒体平面配置：`server/config.py`
- 媒体会话生成：`server/live_media.py`
- 业务 API 接入：`server/api.py`
- 原型 fallback：`server/live_broadcast.py`
- WebRTC（LiveKit）浏览器侧：`static/js/livekit-usking.js`；观看页 `templates/watch.html`；主播 `templates/index.html`、`app/live.html`

## 媒体后端选择
### 默认推荐
- MVP：LiveKit
- 商业化增强：LiveKit + 自建 egress/FFmpeg

### 原因
- WebRTC 天然提供低延迟、A/V 同步和带宽自适应
- SFU 适合一主播多观众
- 支持多轨：
  - 视频：`screen`、`camera`
  - 音频：`page`、`mic`

## 播放模式
- `legacy_jpeg`：当前仓库已实现；仅用于 fallback
- `webrtc`：实时房间主模式
- `hls`：公开页、回放页、大规模观看

## 环境变量
- `LIVE_MEDIA_BACKEND`
- `LIVE_PUBLISH_MODE`
- `LIVE_PLAYBACK_MODE`
- `LIVE_FALLBACK_ENABLED`
- `LIVE_FALLBACK_MODE`
- `LIVE_SIGNALING_URL`
- `LIVE_HLS_BASE_URL`
- `LIVE_TURN_URLS`
- `LIVEKIT_WS_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

## 主播端采集约定
- 视频输入：
  - `screen`：`getDisplayMedia`
  - `camera`：`getUserMedia({ video: true })`
- 音频输入：
  - `page`：tab/system audio
  - `mic`：`getUserMedia({ audio: true })`
- 主节目输出：
  - `canvas.captureStream(30)` + mixed audio

## 兼容策略
- 当 `LIVE_MEDIA_BACKEND=legacy_jpeg` 时，前端仍可走：
  - `POST /api/live/push-frame`
  - `GET /api/live/last-frame/{username}`
  - `/api/ws/live/audio/*`
- 当切换到 `livekit` 时，业务层继续复用当前直播权限和房间元数据，只替换媒体链路。

## 执行手册
- 详细执行规则：[`docs/LIVE_GSTACK_COMPOSER2_EXECUTION.md`](./LIVE_GSTACK_COMPOSER2_EXECUTION.md)
- 执行摘要：[`docs/LIVE_GSTACK_COMPOSER2_QUICKSTART.md`](./LIVE_GSTACK_COMPOSER2_QUICKSTART.md)
- 工作记录与审计留底：[`docs/LIVE_GSTACK_WORK_RECORD.md`](./LIVE_GSTACK_WORK_RECORD.md)
