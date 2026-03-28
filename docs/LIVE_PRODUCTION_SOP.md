# 直播生产运维 SOP

适用于当前已在生产跑通的 `USKing + LiveKit Egress + HLS Origin` 方案，用于日常巡检、发版验收与故障排查。

## 1. 目标

确保生产直播链路稳定满足以下结果：

- 主播可正常开播并发布真实画布流
- HLS 公播地址可在直播中访问
- 停播后录制状态回写为 `completed`
- MP4 录制文件可从公网地址正常下载

## 2. 当前生产基线

- 业务站点：`https://usking.vip`
- LiveKit 信令：`wss://livekit-47-239-7-62.nip.io`
- HLS 公播前缀：`https://usking.vip/live-hls`
- 业务容器：`usking-web`
- 业务依赖：`postgres`、`redis`
- 媒体平面：`livekit`、`egress`
- HLS/录制宿主机目录：`/data/live-hls`

当前链路语义：

- 直播进行中：HLS 应可访问、状态应为 `running`
- 停播完成后：录制任务应转为 `completed`，MP4 应返回 `200`

## 3. 每日巡检 SOP

每天至少执行一次：

1. 打开 `https://usking.vip`，确认业务站可访问。
2. 检查 `usking-web`、`postgres`、`redis` 是否正常运行。
3. 检查 `livekit`、`egress` 是否正常运行。
4. 检查宿主机 `/data/live-hls` 是否存在。
5. 抽查最近直播目录，确认存在以下产物：
   - `master.m3u8`
   - `segment_*.ts`
   - `recordings/*.mp4`
6. 检查日志中是否持续出现以下错误：
   - `invalid livekit webhook`
   - `permission denied`
   - `Local upload failed`
   - `room does not exist`

## 4. 发版后验收 SOP

每次涉及直播、配置、基础设施变更后，必须至少跑一轮完整验收：

1. 注册一个测试账号并登录。
2. 调用开播链路，确认主播已进入直播态。
3. 调用 `POST /api/live/media/host-session`，确认返回 `livekit.token`。
4. 真实发布一段测试画布流。
5. 轮询 `GET /api/live/egress/status/<username>`。
6. 确认 HLS 进入 `running`。
7. 访问 `https://usking.vip/live-hls/<username>/master.m3u8`，确认返回 `200` 且含 `#EXTM3U`。
8. 执行停播。
9. 再次轮询 `GET /api/live/egress/status/<username>` 与 `GET /api/live/recordings/<username>`。
10. 确认 recording 进入 `completed`。
11. 访问 `https://usking.vip/live-hls/<username>/recordings/stream-<id>.mp4`，确认返回 `200`。

通过标准：

- 开播后 HLS 可播
- 停播后 MP4 可下
- 状态链路完整经历 `planned -> running -> completed`

## 5. 标准运维命令

### 5.1 USKing Web

```bash
# 进入业务目录
cd /opt/usking

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 重建并重启 web
docker compose -f docker-compose.prod.yml up -d --build web

# 查看业务日志
docker compose -f docker-compose.prod.yml logs --tail=200 web
```

### 5.2 LiveKit / Egress

```bash
# 进入媒体目录
cd /opt/livekit

# 查看服务状态
docker compose ps

# 查看 LiveKit 日志
docker compose logs --tail=200 livekit

# 查看 Egress 日志
docker compose logs --tail=200 egress
```

### 5.3 HLS / 录制文件

```bash
# 查看 HLS 根目录
ls -la /data/live-hls

# 查看指定主播目录
ls -la /data/live-hls/<username>

# 查看录制目录
ls -la /data/live-hls/<username>/recordings
```

## 6. 关键配置检查项

每次排障优先核对以下环境变量未漂移：

```bash
LIVEKIT_WS_URL=
LIVEKIT_API_URL=
LIVE_HLS_BASE_URL=
LIVE_HLS_OUTPUT_DIR=/data/live-hls
LIVEKIT_EGRESS_ENABLED=true
LIVEKIT_EGRESS_CALLBACK_URL=
LIVE_EGRESS_WEBHOOK_SECRET=
```

同时确认以下基础条件仍成立：

- `docker-compose.prod.yml` 中 `usking-web` 挂载了 `/data/live-hls:/data/live-hls`
- `livekit` / `egress` 写入路径指向同一个宿主机 `/data/live-hls`
- `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` 与 LiveKit 服务端配置一致

## 7. 故障排查 SOP

### 7.1 现象：开播后一直没有 HLS

按顺序排查：

1. 查 `GET /api/live/egress/status/<username>`，确认状态是 `planned`、`running` 还是 `failed`。
2. 若卡在 `planned`：
   - 查业务日志是否有 webhook `403`
   - 查是否出现 `invalid livekit webhook`
3. 若为 `failed`：
   - 查 egress 日志
   - 重点搜索 `permission denied`、`Local upload failed`、`room does not exist`
4. 检查宿主机是否已写出 `/data/live-hls/<username>/master.m3u8`
5. 检查业务容器内是否能读取同一路径

### 7.2 现象：HLS 文件存在，但公网访问 404

按顺序排查：

1. 宿主机确认 `/data/live-hls/<username>/master.m3u8` 是否存在。
2. 容器内确认 `/data/live-hls/<username>/master.m3u8` 是否存在。
3. 核对 `docker-compose.prod.yml` 是否包含 `/data/live-hls:/data/live-hls`。
4. 核对 `LIVE_HLS_BASE_URL` 是否仍指向 `https://usking.vip/live-hls`。

### 7.3 现象：新直播一开播就失败

重点检查：

- `/data/live-hls/<username>/` 的目录权限
- egress 用户是否对新目录可写
- 是否出现 `open /data/live-hls/<username>/segment_00000.ts: permission denied`

### 7.4 现象：停播后 recording 已 completed，但 MP4 仍 404

按顺序排查：

1. 查 `GET /api/live/egress/status/<username>`。
2. 确认 `recording_url` 是否仍是公网地址：
   - 正确：`https://usking.vip/live-hls/<username>/recordings/stream-<id>.mp4`
   - 错误：`/data/live-hls/...`
3. 若回写成了本地路径，优先排查 webhook 结果归一逻辑。
4. 再检查宿主机文件是否真实存在。
5. 最后检查业务容器是否能读取该文件。

## 8. 故障分级

### P0

- 所有直播无法开播
- 所有 HLS 不可用
- 所有录制失败
- 业务站点无法访问

处理要求：

- 立即响应
- 优先恢复服务可用性
- 必要时回退到最近稳定版本

### P1

- 单个主播直播失败
- 单场直播停播后录制不可下载
- webhook 持续异常但未全站中断

处理要求：

- 2 小时内完成定位
- 当天完成修复或规避

### P2

- 状态展示不准
- 回放索引异常
- 告警存在但不影响主链路

处理要求：

- 纳入最近修复窗口

## 9. 变更门禁

凡涉及以下内容的变更，都必须重新跑完整验收：

- `server/api.py`
- `server/live_egress.py`
- `docker-compose.prod.yml`
- LiveKit / Egress 配置
- Nginx 转发
- `LIVE_HLS_*` 相关变量
- `LIVEKIT_*` 相关变量

## 10. 最终验收标准

只有同时满足以下 4 条，才算本次生产变更通过：

1. 主播可发布真实画布流
2. `master.m3u8` 返回 `200`
3. 停播后 recording 状态为 `completed`
4. MP4 返回 `200` 且可下载

## 11. 相关文档

- [`docs/DEPLOY.md`](./DEPLOY.md)
- [`docs/LIVE_PRODUCTION_FINAL_CHECKLIST.md`](./LIVE_PRODUCTION_FINAL_CHECKLIST.md)
- [`docs/LIVE_ARCHITECTURE_UPGRADE.md`](./LIVE_ARCHITECTURE_UPGRADE.md)
- [`infra/livekit/README.md`](../infra/livekit/README.md)
