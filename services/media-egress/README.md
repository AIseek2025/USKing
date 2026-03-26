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

## 不建议继续沿用的链路
- `JPEG + polling`
- `PCM over business WebSocket`

这些链路只保留在业务仓里作为 fallback / 诊断，不再承担正式分发职责。
