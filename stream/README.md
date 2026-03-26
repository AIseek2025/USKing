# stream — 编码、导出与多平台分发

- 接收主节目（视频 + 混音后音频）
- 编码（H.264 / AAC 等）
- **多平台同步推流（Simulcast）**
- HLS 打包
- 录制与对象存储

## 支持平台
- YouTube Live (`rtmp://a.rtmp.youtube.com/live2/`)
- TikTok Live
- Twitch (`rtmp://live.twitch.tv/app/`)
- Bilibili (`rtmp://live-push.bilivideo.com/live-bvc/`)
- 自建平台（RTMP / HLS / WebRTC）
- 任意自定义 RTMP 地址

## 推荐实现
1. **LiveKit Egress + FFmpeg**
2. **FFmpeg tee muxer**：一次编码、多路输出
3. **中继服务**：SRS / 云直播 / relay

## 约束
- 当前仓库中的 `server/live_broadcast.py` 不是正式 stream 模块，只是 fallback 链路
- 正式编码与导出应在独立媒体平面完成，不放在 FastAPI 业务进程中
