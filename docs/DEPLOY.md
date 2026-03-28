# USKing 生产部署清单

面向仓库：[AIseek2025/USKing](https://github.com/AIseek2025/USKing)。

## 1. 上线前必做

| 项 | 说明 |
|----|------|
| `SECRET_KEY` | 强随机字符串（≥32 字符），**禁止**使用代码中的默认值。 |
| `DEV_MODE` | 设为 `false`。未设置时开发默认 `true`，不适合生产。 |
| `MEIGUWANG_ADMIN_PASSWORD` | 首次启动创建 `admin` 时使用的密码；**仅在库中无 admin 时生效**。创建后请改密或依赖业务侧账号体系。 |
| 数据库 | 单机可用 SQLite（注意备份 `*.db`）；多实例请用 PostgreSQL 等，并设置 `DATABASE_URL`。PostgreSQL 需安装驱动：`pip install psycopg2-binary`。 |
| HTTPS | 生产务必由 **Nginx / Caddy / 云 LB** 终止 TLS；若使用仓库内 Docker Compose 示例，反代到 `127.0.0.1:8002`；若直接运行应用，可反代到 `127.0.0.1:8000`。 |
| 静态与上传 | 默认上传目录为项目下 `static/uploads`；Docker 示例通过 `UPLOAD_DIR=/data/uploads` 挂载卷持久化。访问 **`/static/uploads/*` 由独立路由从 `UPLOAD_DIR` 读盘**，避免被 `StaticFiles(/app/static)` 抢先匹配到镜像内空目录导致 **头像/图片 404**。 |

应用启动时若 `DEV_MODE=false` 且仍使用默认 `SECRET_KEY`，进程会**直接退出**（防止误部署）。

## 2. 环境变量模板

复制仓库根目录 `.env.example` 为 `.env`，按环境填写。

```bash
cp .env.example .env
# 编辑 .env 后启动
```

站内实时观看的标准组合建议固定为：

```bash
LIVE_MEDIA_BACKEND=livekit
LIVE_PUBLISH_MODE=webrtc
LIVE_PLAYBACK_MODE=webrtc
LIVE_FALLBACK_ENABLED=true
LIVE_FALLBACK_MODE=legacy_jpeg
LIVEKIT_WS_URL=wss://your-livekit-host
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
LIVEKIT_EGRESS_ENABLED=true
LIVEKIT_EGRESS_CALLBACK_URL=https://usking.vip/api/live/egress/livekit-webhook
LIVE_HLS_BASE_URL=https://usking.vip/live-hls
LIVE_HLS_OUTPUT_DIR=/data/live-hls
LIVE_EGRESS_WEBHOOK_SECRET=replace_with_random_shared_secret
```

含义：

- `WebRTC` 是站内实时主链路。
- `legacy_jpeg` 仅作为回退/诊断链路，不应继续作为默认观看体验。
- 直播列表缩略图仍依赖 `push-frame -> last-frame` 的低频 JPEG 预览缓存；即使已接通 LiveKit，也不要删除这条轻量预览路径。
- 若接入外部 egress / webhook，使用 `LIVE_EGRESS_WEBHOOK_SECRET` 保护 `POST /api/live/egress/event`，由媒体平面回写 HLS / recording job 状态。
- 若使用 LiveKit Egress 正式闭环，建议额外设置：
  - `LIVEKIT_EGRESS_ENABLED=true`
  - `LIVEKIT_EGRESS_CALLBACK_URL=https://你的域名/api/live/egress/livekit-webhook`
  - `LIVEKIT_API_URL=https://你的livekit域名`（若与 `LIVEKIT_WS_URL` 同域可省略）
- 若由业务应用自己承接 HLS origin，则 `LIVE_HLS_OUTPUT_DIR` 目录中的内容会通过 `GET /live-hls/*` 对外暴露；`LIVE_HLS_BASE_URL` 应与该公开路径一致，例如 `https://usking.vip/live-hls`。

### Phase C 公开播放与回放

- 公开页优先读取 `viewer-session` 中的 `broadcast plane` 与 `egress_status`；当 HLS 未 ready 或中途 fatal error 时，页面会重试并回退到 WebRTC / fallback，而不是直接黑屏。
- 主播 `host-session` 下发时，后端会在开启 `LIVEKIT_EGRESS_ENABLED` 后自动向 LiveKit 发起 `StartRoomCompositeEgress`；停播时调用 `StopEgress`。
- LiveKit 官方 webhook 入口为 `POST /api/live/egress/livekit-webhook`，使用 `Authorization: Bearer <jwt>` + `sha256` 校验请求体；旧的 `POST /api/live/egress/event` 仍保留给自定义回调或旁路脚本。
- 运营或排障可查询：
  - `GET /api/live/egress/status/{username}`
  - `GET /api/live/recordings/{username}`
  - `GET /api/live/observability/summary`

### LiveKit Egress 部署要点

- 参考 [`infra/livekit/README.md`](../infra/livekit/README.md) 与同目录的：
  - `docker-compose.yml`
  - `livekit.yaml.example`
  - `egress.yaml.example`
- 生产建议让 `redis + livekit + egress` 同机部署，三者通过 `127.0.0.1` 通信，减少跨机时序和防火墙复杂度。
- `egress` 需要挂载 `/data/live-hls:/data/live-hls`，这样 HLS 与 MP4 会直接写入业务侧对外暴露的 origin 目录。

### 独立 coturn（强烈推荐）

生产环境 WebRTC 跨网、手机、企业网通常 **必须 TURN**。推荐部署 **独立 coturn**，与 LiveKit 内置 TURN 解耦；USKing 通过 `POST /api/live/media/host-session` 与 `GET /api/live/media/viewer-session/{user}` 返回标准字段 **`ice_servers`**（`urls` + `username` + `credential`），前端 `livekit-usking.js` 将其传入 `Room.connect(..., { rtcConfig })`。

配置步骤与端口清单见仓库 [`infra/turn/README.md`](../infra/turn/README.md)。环境变量见根目录 `.env.example` 中 `TURN_*`。
当前实战验证后的最终交付清单见 [`docs/LIVE_PRODUCTION_FINAL_CHECKLIST.md`](./LIVE_PRODUCTION_FINAL_CHECKLIST.md)。

生产上已验证的一组稳定组合是：

```bash
TURN_ENABLED=true
TURN_UDP_URL=turn:turn.example.com:3478?transport=udp
TURN_TLS_URL=
TURN_STUN_URLS=stun:stun.l.google.com:19302
```

配套网络端口建议固定为：

- coturn：`3478` + `50000-54999`
- LiveKit：`7881` + `55000-60000`

**回滚**：将 `TURN_ENABLED=false` 并重启应用；前端不再注入 `rtcConfig`，回退为 LiveKit 客户端默认 ICE。

## 3. 直接运行（无 Docker）

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DEV_MODE=false
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export MEIGUWANG_ADMIN_PASSWORD='你的强密码'
uvicorn server.main:app --host 0.0.0.0 --port 8000 --proxy-headers
```

## 4. Docker Compose（示例）

```bash
cp .env.example .env
# 在 .env 中填写 SECRET_KEY、MEIGUWANG_ADMIN_PASSWORD，并设 DEV_MODE=false

docker compose -f docker-compose.prod.yml up -d --build
```

数据卷 `usking-data` 内包含：`/data/meiguwang.db`、`/data/uploads`。

## 4.1 可选：使用仓库内 `deploy/` 辅助脚本

若你希望把重复性部署动作收敛成固定脚本，而不是保留本地时间戳快照，可使用：

- [`deploy/README.md`](../deploy/README.md)
- [`deploy/server-setup.sh`](../deploy/server-setup.sh)
- [`deploy/start.sh`](../deploy/start.sh)
- [`deploy/nginx/usking.conf.example`](../deploy/nginx/usking.conf.example)

这些文件是**辅助层**，不是第二套权威文档。权威来源仍然是：

- 本文 [`docs/DEPLOY.md`](./DEPLOY.md)
- [`docker-compose.prod.yml`](../docker-compose.prod.yml)

推荐顺序：

```bash
# 1) 初始化服务器依赖与目录
sudo APP_DIR=/opt/usking DATA_DIR=/data/usking bash deploy/server-setup.sh

# 2) 同步仓库代码到 APP_DIR，并在服务器上创建 .env
cp .env.example .env

# 3) 启动服务
APP_DIR=/opt/usking bash deploy/start.sh
```

## 5. 反向代理要点

- 转发 `Host`、`X-Forwarded-For`、`X-Forwarded-Proto`，以便生成正确链接与日志。
- Uvicorn 已使用 `--proxy-headers`；请将受信任代理 IP 收窄到内网（当前示例为 `*` 便于先跑通，**生产建议改为具体 CIDR**）。
- **站内直播（默认 HTTP，推荐）**：观众轮询 **`GET /api/live/last-frame/{username}`**（单张 JPEG，最耐代理缓冲）；主播推 **`POST /api/live/push-frame`**。与普通 API 一样反代即可，**不要求** WebSocket。若仍使用 MJPEG 长连接 **`GET /api/live/mjpeg/{username}`**，须关闭缓冲并拉长读超时，否则可能一直卡在「连接中」：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8002;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400s;
    proxy_buffering off;
    proxy_request_buffering off;
}
```

- **可选 WebSocket**（若仍使用 `/api/ws/live/*`）：需 `Upgrade` 头，示例：

```nginx
location /api/ws/ {
    proxy_pass http://127.0.0.1:8002;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400s;
    proxy_buffering off;
}
```

  - 修改后执行 `sudo nginx -t && sudo systemctl reload nginx`。
  - WS 自测应返回 **`101 Switching Protocols`**：`curl -sI -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' 'https://你的域名/api/ws/live/watch/testuser'`
  - **`curl -I` / `curl -sI` 发的是 HEAD**；`/api/live/last-frame/` 已支持 HEAD。要拉一整张图自检请用：`curl -sS -o /tmp/f.jpg 'https://你的域名/api/live/last-frame/用户名'`（GET）。

- 直播状态仅在 **单进程** 内存中广播；`uvicorn --workers` 大于 1 时各 worker 互不共享。**站内直播建议 `--workers 1`**，或后续改为 Redis 等跨进程方案。
- 当前 `last-frame` 还承担直播列表实时缩略图职责，因此如果仍使用单机 fallback/preview 缓存，部署时同样要满足上面的 **单 worker 或共享缓存** 约束。

## 6. 可选能力

- **媒体平面架构升级**：
  - 业务层仍可使用当前 FastAPI 服务；
  - 正式直播建议引入独立媒体平面（WebRTC/RTMP/HLS），详见 [docs/LIVE_ARCHITECTURE_UPGRADE.md](LIVE_ARCHITECTURE_UPGRADE.md)；
  - 建议新增环境变量：`LIVE_MEDIA_BACKEND`、`LIVE_PLAYBACK_MODE`、`LIVE_SIGNALING_URL`、`LIVE_TURN_URLS`、`LIVE_HLS_BASE_URL`、`LIVEKIT_*`。
- **Redis / PostgreSQL**：正式直播推荐使用 PostgreSQL 作为主业务库，Redis 承担在线态、presence、幂等与实时元数据。
- **TURN/STUN**：若启用 WebRTC，生产必须部署 TURN（例如 coturn），并将地址通过 `LIVE_TURN_URLS` 暴露给客户端。
- **LiveKit WebRTC**：设置 `LIVE_MEDIA_BACKEND=livekit`、`LIVE_PUBLISH_MODE=webrtc`、`LIVE_PLAYBACK_MODE=webrtc`，并填写 `LIVEKIT_WS_URL`（一般为 `wss://…`，与 LiveKit Server 可达），以及 `LIVEKIT_API_KEY`、`LIVEKIT_API_SECRET`（与服务器 `keys` 一致）。浏览器通过 `livekit-client` 连接；未配置或连接失败时仍可回退 `legacy_jpeg`（见 `LIVE_FALLBACK_ENABLED`）。
- **Stripe**：会员支付需配置 `STRIPE_*` 与 Webhook。
- **SMTP**：邮件验证码需配置 `SMTP_*`。
- **OpenAI**：AI 客服需 `OPENAI_API_KEY`。
- **美股数据面板**：`FRED_API_KEY` 可选（不填则使用 FRED 官网公开 CSV 降级）；`NEWSAPI_KEY`、`NEWS_RSS_URLS` 可选；未配置 NewsAPI 与自定义 RSS 时，默认拉取 **SEC 新闻稿官方 RSS**（可用 `NEWS_RSS_DISABLE_BUILTIN=1` 关闭）。访问 SEC 时请设置 `SEC_HTTP_USER_AGENT` 为含**真实联系邮箱**的字符串（**勿**在 UA 中写 `https://`，否则易被 SEC 返回 403）。
- **公司投研频道**：`FINNHUB_API_KEY`、`ALPHA_VANTAGE_API_KEY` 均为各平台**免费注册**所得（有调用频率/日限额）；不配置时页面仅展示注册说明与 SEC 披露列表。

## 7. 合规与安全

- 不要将 `.env`、数据库文件、用户上传内容提交到 Git（见 `.gitignore`）。
- 定期备份数据库与 `UPLOAD_DIR`。
- 关注依赖漏洞：`pip audit` 或 GitHub Dependabot。

## 8. 协作：Git 推送失败（大仓库）

向远端 **`git push`** 若提示增大 **`http.postBuffer`** 或出现 **HTTP/2 framing** 类错误，可在仓库根目录执行：

```bash
git config http.postBuffer 524288000
git config http.version HTTP/1.1
```

然后重试 `git push`。更完整的说明与全局配置方式见仓库根目录 [README.md](../README.md) 中的 **「Git 推送（大仓库 / 推送失败）」**。
