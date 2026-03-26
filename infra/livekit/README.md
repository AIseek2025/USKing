# LiveKit 与 USKing 同机部署（最小可用）

USKing 站内实时观看需要 **独立的 LiveKit Server**（SFU）。业务鉴权仍在 FastAPI；浏览器通过 `LIVEKIT_WS_URL` 连接 SFU。

## 你需要准备什么

1. 一台可公网访问的 VPS，且 **安全组/防火墙** 放行（阿里云等控制台）：
   - TCP `80`、`443`（HTTPS 与证书签发）
   - TCP `7881`（ICE/TCP 回退）
   - UDP `50000-60000`（WebRTC 媒体）
2. 一个可用于 **Let's Encrypt** 的域名解析到该机器公网 IP。  
   若暂时不能改 DNS，可使用 **`*.nip.io`** 动态域名（例如 `livekit.<公网IP>.nip.io`），本仓库的 `nginx-livekit-nip.conf.example` 即按此方式命名。

## 目录约定（服务器）

推荐在服务器使用固定目录（与仓库内文件一致）：

- `/opt/livekit/docker-compose.yml`（从本目录复制）
- `/opt/livekit/livekit.yaml`（**由 `livekit.yaml.example` 复制后填写真实 keys**，不要提交到 Git）

## 密钥与 USKing 对齐

1. 在 `livekit.yaml` 的 `keys:` 下配置一对 `api_key: api_secret`。
2. 在 USKing 的 `.env` 中设置 **完全相同** 的：
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`
3. 设置 WebSocket 地址（浏览器可访问的 **wss**）：
   - `LIVEKIT_WS_URL=wss://你的LiveKit域名`
4. 启用站内 WebRTC 主链路：
   - `LIVE_MEDIA_BACKEND=livekit`
   - `LIVE_PUBLISH_MODE=webrtc`
   - `LIVE_PLAYBACK_MODE=webrtc`
   - 建议保留 `LIVE_FALLBACK_ENABLED=true`，便于回退诊断。

重启 USKing：`docker compose -f docker-compose.prod.yml up -d --build`（或你的部署脚本）。

## Nginx 与证书

- LiveKit 信令 HTTP 默认监听本机 `7880`（见 `livekit.yaml`）。
- 对外应通过 **Nginx 终止 TLS**，再反代到 `http://127.0.0.1:7880`，并携带 WebSocket 头（见 `nginx-livekit-nip.conf.example`）。
- 证书：`certbot --nginx -d <你的LiveKit域名>`。

## 验收

- `curl -sS https://<你的USKing域名>/api/live/media/config` 中 `livekit.ready` 应为 `true`（在 `LIVEKIT_*` 配置正确时）。
- 主播端开播后观众端应走 WebRTC；若仍高延迟，优先检查是否仍落在 `legacy_jpeg`（环境变量未生效或未重启容器）。
