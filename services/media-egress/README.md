# media-egress

负责把实时主节目从媒体平面导出为平台分发与存储可消费的格式。

## 职责
- RTMP fanout（YouTube / TikTok / Bilibili / Twitch）
- HLS 打包
- 录制 MP4 / TS
- 封面帧生成
- 对象存储上传

## 推荐组合
- LiveKit Egress + FFmpeg
- 或 SRS / Ant Media / 云直播服务

## 业务侧对接约定
- 业务仓不直接做转码；仅接收 egress 状态并写入 `LiveRecordingJob`
- 推荐由媒体平面调用：`POST /api/live/egress/event`
- 建议使用 `X-USKing-Egress-Secret` 对应 `LIVE_EGRESS_WEBHOOK_SECRET`
- 业务侧可查询：
  - `GET /api/live/egress/status/{username}`
  - `GET /api/live/recordings/{username}`

## 不建议继续沿用的链路
- `JPEG + polling`
- `PCM over business WebSocket`

这些链路只保留在业务仓里作为 fallback / 诊断，不再承担正式分发职责。
