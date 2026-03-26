# 独立 coturn 上线与验收（简版）

## 根因摘要

- 信令（WSS）可通时，若仍出现 `could not establish pc connection`，问题在 **ICE / RTP 路径**，不是 HTTP API。
- 内置 TURN 与站点 443、证书、端口模型易冲突；应使用 **独立 coturn** 与标准 **`ice_servers`**。
- 前端不得把 `turns:` 伪造成 `stuns:`，不得从 TURN URL「反推」STUN；必须由 **后端签发** `username` / `credential`。

## 上线前检查

- [ ] DNS：`turn.example.com` → 公网 IP  
- [ ] 若启用 TURNS：`turn.example.com` 的 PEM 路径与 `TURN_TLS_URL` 一致  
- [ ] 防火墙：3478 TCP/UDP、50000-54999 TCP/UDP、7881 TCP、55000-60000 UDP  
- [ ] coturn：`static-auth-secret` = `TURN_SHARED_SECRET`  
- [ ] USKing：`TURN_ENABLED=true`，`TURN_UDP_URL` 正确；若未启用 TURNS，则 `TURN_TLS_URL` 留空  
- [ ] LiveKit：`livekit.yaml` 建议关闭内置 `turn`（见 `infra/livekit/livekit.yaml.example`）

## 验收

- [ ] `GET /api/live/media/config` 中 `turn_mode` 为 `rest`，`turn_enabled` 为 true  
- [ ] 主播 `POST /api/live/media/host-session` 返回非空 `ice_servers`，含 `credential`  
- [ ] 观众 `GET /api/live/media/viewer-session/...` 同上  
- [ ] 浏览器 Console：`[LK:rtc] rtcConfig from API` 且 `hasAuth: true`  
- [ ] Console：`[LK:rtc] local candidate` 中出现 `typ relay` 或 `typ srflx`  
- [ ] coturn 日志出现 `ALLOCATE processed, success`  
- [ ] 第三方电脑与手机能听到混音后的节目音频  
- [ ] 延迟明显优于纯 JPEG 轮询  
- [ ] 直播列表缩略图仍刷新（push-frame 预览）  

## 回滚

1. 设置 `TURN_ENABLED=false`，重启 USKing Web。  
2. 可选：恢复 LiveKit 内置 TURN（不推荐长期）。  
3. 验证：`ice_servers` 为空时，Console 出现 `no ice_servers from API; using LiveKit default ICE`。

## 本次实战收口

- 最终跑通方案：`UDP TURN(3478)` + `Google STUN` + 独立 coturn + LiveKit `55000-60000`
- 阿里云侧必须显式放通：
  - `UDP/TCP 3478`
  - `UDP/TCP 50000-54999`
  - `TCP 7881`
  - `UDP 55000-60000`
- 在云主机 NAT 场景下，coturn 必须用 `external-ip=公网/内网`，不要把 `listening-ip` 直接写成公网 IP
