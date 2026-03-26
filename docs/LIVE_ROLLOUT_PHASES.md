# USKing 直播升级实施阶段

## Phase 0：原型降级为 fallback
- 保留 `server/live_broadcast.py`
- 明确其职责：诊断、开发回退、极低配环境预览
- 不再将其视为正式生产主链路

## Phase 1：业务层与媒体层解耦
- 落地 `server/live_media.py`
- 通过 API 返回 host/viewer 媒体会话
- 引入媒体平面环境变量与部署文档

## Phase 2：WebRTC 实时观看
- 接入 LiveKit 或等价 SFU
- 主播端改为发布 `screen/camera/page/mic` 媒体轨
- 观看端改为消费 `viewer-session`

### 已落地（LiveKit 路径）
- 环境变量：`LIVE_MEDIA_BACKEND=livekit`、`LIVE_PUBLISH_MODE=webrtc`、`LIVE_PLAYBACK_MODE=webrtc` 且配置 `LIVEKIT_*` 时，主播端用 `canvas.captureStream` + 麦克风/页音轨发布；观众端用 `livekit-client`（`static/js/livekit-usking.js`）订阅。
- 未配置 LiveKit 或失败时：`LIVE_FALLBACK_ENABLED` 仍为 true 则回退 JPEG 轮询 +  legacy 音频 WS。
- 匿名观众 `viewer-session` 使用唯一 identity，避免 SFU 内互踢。

## Phase 3：RTMP + HLS
- egress 输出多平台 RTMP
- 生成 HLS manifest
- 公开直播页与回放页走 HLS

## Phase 4：生产化
- PostgreSQL 替换 SQLite
- Redis 承担 presence / 幂等 / 实时 fanout 元数据
- TURN 独立部署
- 监控、录制、对象存储、告警

## Phase 5：桌面端增强
- Windows：Graphics Capture + WASAPI
- macOS：ScreenCaptureKit + AVFoundation
- 补齐系统音频、窗口管理、后台稳定性
