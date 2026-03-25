# stream — 编码与多平台推流

- 接收合成后的视频（及可选音频）
- 编码（如 H.264）
- **多平台同步推流（Simulcast）**：同一路编码流同时推送到多个 RTMP 端点

## 支持平台

- YouTube Live (`rtmp://a.rtmp.youtube.com/live2/`)
- TikTok Live
- Twitch (`rtmp://live.twitch.tv/app/`)
- Bilibili (`rtmp://live-push.bilivideo.com/live-bvc/`)
- 自建平台（RTMP/SRT/WebRTC）
- 任意自定义 RTMP 地址

## 实现思路

1. **FFmpeg tee muxer**：一次编码、多路输出，开销最低
2. **多线程分发**：编码包通过内部队列复制到 N 个推流线程
3. **中继服务**：本地推一路到 Nginx-RTMP / SRS，由服务端 relay 到各平台

主播端通过 app 模块配置各平台 Stream Key 并按需启停。
