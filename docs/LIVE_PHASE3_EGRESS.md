# Phase 3：RTMP / HLS Egress（实施纲要）

本阶段在 **站内 WebRTC（LiveKit）** 已跑通的前提下，把 **同一房间或同一节目流** 接到 **转码与分发**，用于多平台 RTMP 与公网 HLS。

## 目标

- **RTMP**：向 YouTube / Bilibili / Twitch 等推送（每平台一路或多路 fanout）。  
- **HLS**：生成 `master.m3u8`，供 CDN 大规模播放与回放索引。  
- **与站内关系**：浏览器仍优先 WebRTC；HLS 为延迟较高、可扩展播放路径。

## 推荐组件（择一）

- LiveKit **Egress**（Room Composite 或 Track Composite）+ FFmpeg 输出 RTMP/HLS。  
- 或 SRS / 自建 FFmpeg 拉 WebRTC/SRT 再转封装。

## 与 USKing API 的衔接

- 房间名：`server/live_media.py` 中 `room_name_for_username`。  
- 业务层仅保存 **回放元数据、封面、HLS URL**（`LIVE_HLS_BASE_URL` + 用户名路径）；**不**在 FastAPI 内做重转码。

## 环境变量（已有）

- `LIVE_HLS_BASE_URL`：对外 manifest 基址。  
- 后续可增加：`EGRESS_WEBHOOK_SECRET`、`LIVEKIT_EGRESS_*` 等（按所选方案补全）。

## 验收清单

- [ ] 开播后 egress 任务可观测（状态、失败重试）。  
- [ ] RTMP 断开后自动重连或告警。  
- [ ] HLS 延迟与分片时长符合产品预期。  
- [ ] 不影响站内 WebRTC 房间稳定性。

## Gstack 门禁

单 PR 只接 **一种** egress 路径（例如仅 LiveKit Egress RTMP），合并后 staging 验证再扩展 HLS。
