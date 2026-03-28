# USKing（美股王）交易直播平台

[![GitHub](https://img.shields.io/badge/GitHub-AIseek2025%2FUSKing-181717?logo=github)](https://github.com/AIseek2025/USKing)

专为美股王会员打造的**实时交易界面直播**站点：主播打开看盘软件与交易界面并开播，观众可同步观看多屏行情与交易画面。

---

## 快速开始（开发）

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # 按需编辑
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

开发环境可保持 `DEV_MODE=true`（默认）；未设置 `MEIGUWANG_ADMIN_PASSWORD` 时，开发模式可使用默认管理员（见启动日志，**切勿用于生产**）。

站内 **公司投研** 频道（侧栏）默认使用 **SEC 官方披露**；若需按代码聚合公开新闻，请在 `.env` 中配置免费注册的 **`FINNHUB_API_KEY`** 和/或 **`ALPHA_VANTAGE_API_KEY`**（见 `.env.example` 注释与 [docs/DEPLOY.md](docs/DEPLOY.md)）。

---

## 生产上线

**必读：** [docs/DEPLOY.md](docs/DEPLOY.md)

核心条件：

1. `DEV_MODE=false`
2. 设置强随机 `SECRET_KEY`（否则进程拒绝启动）
3. 配置 `MEIGUWANG_ADMIN_PASSWORD`（首次创建管理员）
4. HTTPS + 反向代理；数据库与上传目录持久化与备份

Docker 示例：

```bash
cp .env.example .env   # 填写生产变量
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Git 推送（大仓库 / 推送失败）

向 GitHub 首次推送或对象较大时，若出现 **`unable to rewind rpc post data — try increasing http.postBuffer`**、**`RPC failed; curl 16 Error in the HTTP2 framing layer`** 或远端意外断开，可在**本仓库**执行（仅作用于当前仓库，不写进代码）：

```bash
git config http.postBuffer 524288000
git config http.version HTTP/1.1
git push -u origin main
```

- **`http.postBuffer`**：增大 HTTP 推送缓冲，避免大包体需要重绕失败。  
- **`http.version HTTP/1.1`**：部分网络/代理下 Git 走 HTTP/2 会不稳定，强制 HTTP/1.1 常可恢复。

若仅需全局默认（所有仓库），可把上述两条里的 `git config` 换成 `git config --global`。

---

## 直播架构（当前与升级方向）

- **当前 fallback**：浏览器采集 + Canvas 合成 + JPEG 推帧 + 站内轮询
- **推荐主链路**：业务平面（FastAPI）+ 媒体平面（WebRTC/RTMP/HLS）
- **媒体平面推荐**：LiveKit / 等价 SFU + egress

详细方案见：
- [docs/LIVE_ARCHITECTURE_UPGRADE.md](docs/LIVE_ARCHITECTURE_UPGRADE.md)
- [docs/LIVE_PRODUCTION_SOP.md](docs/LIVE_PRODUCTION_SOP.md)
- [docs/LIVE_ROLLOUT_PHASES.md](docs/LIVE_ROLLOUT_PHASES.md)
- [docs/LIVE_GSTACK_COMPOSER2_EXECUTION.md](docs/LIVE_GSTACK_COMPOSER2_EXECUTION.md)
- [docs/LIVE_GSTACK_COMPOSER2_QUICKSTART.md](docs/LIVE_GSTACK_COMPOSER2_QUICKSTART.md)
- [docs/LIVE_GSTACK_WORK_RECORD.md](docs/LIVE_GSTACK_WORK_RECORD.md)（gstack 嵌入与迭代工作记录，可审计留底）
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 直播形式与内容

| 来源 | 说明 |
|------|------|
| **美股王交易软件** | 会员专用看盘软件，多前端行情窗口。 |
| **盈透证券 (IB)** | 交易执行界面，与看盘软件同屏直播。 |

---

## 项目结构（概览）

```
├── server/           # FastAPI 后端（API、鉴权、直播业务）
├── templates/        # Jinja2 页面与 SPA 片段
├── static/           # 静态资源与上传目录（上传勿提交 Git）
├── app/              # 采集页等静态入口
├── services/         # 规划中的媒体平面子服务说明
├── infra/            # PostgreSQL / Redis / TURN 等基础设施说明
├── capture/          # 采集模块边界说明
├── composer/         # 合成模块边界说明
├── stream/           # 编码与 egress 模块边界说明
├── requirements.txt
├── Dockerfile
├── docker-compose.prod.yml
├── .env.example
└── docs/DEPLOY.md    # 生产部署清单
```

---

## 参考文档（产品与业务）

- 《美股王-20260315140157》
- 《美股王交易技术分析大全2.0》
- 《美股王智能交易分析软件操作手册-20260315140132》
- 《美股王波段交易大赢家V2.0》

---

## 技术栈

- **后端**：FastAPI、SQLAlchemy、JWT
- **前端**：Jinja2 + 站内 SPA（`templates/index.html`）
- **直播 fallback**：浏览器采集 + Canvas 合成 + JPEG/PCM 原型链路
- **直播升级**：WebRTC（站内实时）、RTMP（平台分发）、HLS（大规模播放/回放）

更多采集/推流规划见历史文档 `docs/REQUIREMENTS.md`（若存在）。
