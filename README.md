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
- **直播**：浏览器采集 + Canvas 合成（见站内「直播后台」）

更多采集/推流规划见历史文档 `docs/REQUIREMENTS.md`（若存在）。
