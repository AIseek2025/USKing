# realtime-signaling

负责 WebRTC 房间信令与媒体会话编排，不负责业务鉴权主数据。

## 输入
- 来自 `usking-api` 的用户身份/JWT
- 主播开播状态与房间元数据
- TURN 配置

## 输出
- 房间 join 信息
- viewer/host token
- ICE/TURN 信息
- 轨道能力声明

## 推荐实现
- LiveKit（推荐）
- 或 mediasoup + 自建信令

## 与现有仓库关系
- 现阶段由 `server/live_media.py` 先产出会话元数据
- 后续该目录可演化成独立服务仓或 monorepo 子服务

## 当前与 LiveKit 的衔接
- JWT 由 `server/live_media.py` 使用 `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` 签发。
- 浏览器使用 `static/js/livekit-usking.js` 动态加载 `livekit-client` UMD，连接 `LIVEKIT_WS_URL`。
- 业务鉴权仍在 FastAPI；SFU 为独立进程（官方 `livekit-server` 或云托管）。
