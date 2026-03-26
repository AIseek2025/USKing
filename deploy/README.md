# USKing 部署辅助脚本

本目录提供**可入库的通用部署辅助资产**，用于补充正式入口：

- [`docs/DEPLOY.md`](../docs/DEPLOY.md)
- [`docker-compose.prod.yml`](../docker-compose.prod.yml)

这两者仍然是**权威来源**；`deploy/` 仅负责把重复性运维动作收敛为可复用脚本与模板。

## 目录结构

```text
deploy/
├── README.md
├── server-setup.sh
├── start.sh
└── nginx/
    └── usking.conf.example
```

## 设计原则

- 不复制真实 `.env`
- 不生成 `deploy-YYYYMMDD-*` 时间戳快照目录
- 不写死某台机器的公网 IP
- 不制造第二份长期 `docker-compose.prod.yml`
- 使用占位符或环境变量，而不是把单机假设写成唯一真相

## 推荐使用顺序

1. 先阅读 [`docs/DEPLOY.md`](../docs/DEPLOY.md)，准备 `.env`、反向代理与数据目录。
2. 在服务器上运行：

```bash
sudo APP_DIR=/opt/usking DATA_DIR=/data/usking bash deploy/server-setup.sh
```

3. 把仓库代码同步到服务器的 `APP_DIR`（例如 `git clone`、`git pull`、`rsync`）。
4. 在服务器的 `APP_DIR` 下创建并填写 `.env`：

```bash
cp .env.example .env
```

5. 参考 [`deploy/nginx/usking.conf.example`](./nginx/usking.conf.example) 配置反向代理。
6. 启动或重启服务：

```bash
APP_DIR=/opt/usking bash deploy/start.sh
```

## 注意事项

- 当前生产 compose 端口映射为 `8002:8000`，Nginx 反代必须对齐 `127.0.0.1:8002`。
- 若服务器未安装 `docker compose` 插件，`start.sh` 会回退到 `docker-compose`。
- 根目录旧 `deploy.sh` 仍视为**本地历史脚本**，不再作为正式部署入口。
