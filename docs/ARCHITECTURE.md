# 美股王直播平台 — 架构设想（草案）

## 整体数据流

```
[美股王窗口1] ─┐                                          ┌─→ [自建平台/CDN]
[美股王窗口2] ─┼─→ [采集层] ─→ [合成/布局] ─→ [编码] ─→ [多平台推流] ─┼─→ [YouTube Live]
[美股王窗口N] ─┤                                          ├─→ [TikTok Live]
[盈透证券窗口] ─┘                                          ├─→ [Twitch]
                                                          └─→ [其他 RTMP 平台...]
```

## 当前实现与目标实现

- **当前实现**：业务仓内的 `JPEG + polling + 进程内存 fanout`
- **目标实现**：业务平面 + 媒体平面分离
- **说明**：当前仓库中的 `server/live_broadcast.py` 应视为 fallback / 诊断链路，不再作为正式主链路长期扩展

## 模块职责（规划）

| 模块 | 职责 | 备注 |
|------|------|------|
| **capture** | 按窗口/屏幕采集美股王、盈透、摄像头、系统音频、麦克风 | 浏览器做 MVP，桌面端补齐系统能力 |
| **composer** | 多路画面布局（网格、画中画等）、叠加层 | 输出主节目 `MediaStream` |
| **realtime-signaling** | 房间信令、TURN 协调、媒体会话下发 | 推荐与业务平面分离 |
| **stream / media-egress** | 编码、录制、**多平台同步推流**、HLS 打包 | 同一路主节目导出到 RTMP/HLS |
| **app** | 主播端 UI：选窗口、预览、开播/停播、**多平台管理** | 浏览器版先行，后续桌面端增强 |

## 多平台同步推流（Simulcast）

编码后的单路流同时推送到多个直播平台，主播只需开播一次即可覆盖所有渠道。

### 支持平台（规划）

| 平台 | 协议 | 推流地址格式 |
|------|------|-------------|
| **YouTube Live** | RTMP | `rtmp://a.rtmp.youtube.com/live2/{stream_key}` |
| **TikTok Live** | RTMP | TikTok 提供的推流地址 + stream key |
| **Twitch** | RTMP | `rtmp://live.twitch.tv/app/{stream_key}` |
| **Bilibili** | RTMP | `rtmp://live-push.bilivideo.com/live-bvc/{stream_key}` |
| **自建平台** | RTMP/SRT/WebRTC | 可自定义 |
| **自定义** | RTMP | 用户手动填入任意 RTMP 地址 |

### 实现方式

1. **FFmpeg tee muxer**：一次编码、多路输出，CPU 开销最低。
   ```
   ffmpeg -i input ... -f tee "[f=flv]rtmp://youtube/key|[f=flv]rtmp://tiktok/key|..."
   ```
2. **多进程/多线程分发**：编码后的包通过内部队列复制到 N 个独立推流线程。
3. **中继服务**：本地推一路到自建 Nginx-RTMP / SRS，由服务端 relay 到各平台（适合带宽受限或需要录制回放的场景）。

### 主播端管理

- 在 app 中添加/删除/启停各平台推流目标。
- 每个目标只需填：平台类型 + Stream Key（或完整 RTMP URL）。
- 实时显示各平台推流状态（连接中/推流中/断开/错误）。

## 技术选型（建议）

- **站内实时**：WebRTC SFU（优先 LiveKit）
- **采集**：Windows（Graphics Capture / WASAPI）、macOS（ScreenCaptureKit / AVFoundation）；浏览器版用 `getDisplayMedia` / `getUserMedia`
- **合成与编码**：浏览器 `canvas.captureStream()` 做 MVP；正式 egress 由 FFmpeg / LiveKit Egress 承担
- **推流**：RTMP 为主（YouTube/TikTok/Twitch/Bilibili 等均支持）；自建平台回放与公播走 HLS
- **多平台分发**：FFmpeg tee muxer / 独立 egress / 云直播服务
- **主播端**：浏览器先行，长期建议 Electron/Tauri

## 多屏布局示例

- 左侧：美股王多个行情窗口（网格或标签切换）。
- 右侧或画中画：盈透证券交易界面。
- 具体布局可在 app 中可配置，并保存为预设。

---

*具体技术方案在实现阶段再细化。*
