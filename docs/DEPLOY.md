# USKing 生产部署清单

面向仓库：[AIseek2025/USKing](https://github.com/AIseek2025/USKing)。

## 1. 上线前必做

| 项 | 说明 |
|----|------|
| `SECRET_KEY` | 强随机字符串（≥32 字符），**禁止**使用代码中的默认值。 |
| `DEV_MODE` | 设为 `false`。未设置时开发默认 `true`，不适合生产。 |
| `MEIGUWANG_ADMIN_PASSWORD` | 首次启动创建 `admin` 时使用的密码；**仅在库中无 admin 时生效**。创建后请改密或依赖业务侧账号体系。 |
| 数据库 | 单机可用 SQLite（注意备份 `*.db`）；多实例请用 PostgreSQL 等，并设置 `DATABASE_URL`。PostgreSQL 需安装驱动：`pip install psycopg2-binary`。 |
| HTTPS | 生产务必由 **Nginx / Caddy / 云 LB** 终止 TLS，反代到本服务（如 `127.0.0.1:8000`）。 |
| 静态与上传 | 默认上传目录为项目下 `static/uploads`；Docker 示例通过 `UPLOAD_DIR=/data/uploads` 挂载卷持久化。 |

应用启动时若 `DEV_MODE=false` 且仍使用默认 `SECRET_KEY`，进程会**直接退出**（防止误部署）。

## 2. 环境变量模板

复制仓库根目录 `.env.example` 为 `.env`，按环境填写。

```bash
cp .env.example .env
# 编辑 .env 后启动
```

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

## 5. 反向代理要点

- 转发 `Host`、`X-Forwarded-For`、`X-Forwarded-Proto`，以便生成正确链接与日志。
- Uvicorn 已使用 `--proxy-headers`；请将受信任代理 IP 收窄到内网（当前示例为 `*` 便于先跑通，**生产建议改为具体 CIDR**）。

## 6. 可选能力

- **Stripe**：会员支付需配置 `STRIPE_*` 与 Webhook。
- **SMTP**：邮件验证码需配置 `SMTP_*`。
- **OpenAI**：AI 客服需 `OPENAI_API_KEY`。

## 7. 合规与安全

- 不要将 `.env`、数据库文件、用户上传内容提交到 Git（见 `.gitignore`）。
- 定期备份数据库与 `UPLOAD_DIR`。
- 关注依赖漏洞：`pip audit` 或 GitHub Dependabot。
