# 部署资产审计与 canonical 入口建议

> 背景：仓库根目录存在 `deploy.sh`，本地还存在一份时间戳部署快照目录 `deploy-20260325-172328/`。  
> 本文的目标不是把这些文件原样入库，而是回答：**哪些值得整理保留，哪些应继续留在本地，当前唯一可信的部署入口是什么。**

---

## 1. 审计结论

当前阶段，USKing 的**唯一正式部署入口**应定义为：

1. [`docs/DEPLOY.md`](./DEPLOY.md)
2. 仓库根目录 [`docker-compose.prod.yml`](../docker-compose.prod.yml)

这两者已经足以表达：

- 生产环境变量要求
- 反向代理要求
- Docker Compose 启动方式
- 端口、数据卷、健康检查等正式约束

因此，**现阶段不建议**把 `deploy.sh` 或 `deploy-20260325-172328/` 整包直接纳入正式推送产物。

---

## 2. 各部署资产的判断

### 2.1 `deploy.sh`

当前特征：

- 是本地执行的部署辅助脚本
- 会生成 `deploy-YYYYMMDD-HHMMSS/` 时间戳目录
- 会复制本地 `.env`
- 内嵌域名 `usking.vip` 与部署假设
- 与 `docs/DEPLOY.md`、`docker-compose.prod.yml` 部分职责重叠

结论：

- **暂不作为正式仓库入口推送**
- 可以保留在本地作为个人运维辅助脚本
- 若未来要入库，必须先重构为：
  - 不复制真实 `.env`
  - 不依赖个人机器工作流
  - 不生成时间戳快照作为主产物
  - 与 `docs/DEPLOY.md` 保持单一事实来源关系

### 2.2 `deploy-20260325-172328/`

当前特征：

- 是一次性部署快照
- 内含 `setup.sh`、`docker-compose.prod.yml`、`DEPLOY_GUIDE.md`
- `docker-compose.prod.yml` 与仓库根目录版本存在差异
  - 快照目录端口映射是 `8000:8000`
  - 根目录正式版本映射是 `8002:8000`

结论：

- **不应原样入库**
- 原因：
  - 时间戳目录不适合作为长期结构
  - 与正式 compose 长期并存会制造“到底哪份是对的”问题
  - 目录内部署说明与 `docs/DEPLOY.md` 重复

### 2.3 `DEPLOY_GUIDE.md`（快照内）

结论：

- 内容可作为一次性部署记录参考
- 但不宜作为长期权威文档
- 正式信息应继续收敛到 [`docs/DEPLOY.md`](./DEPLOY.md)

---

## 3. 为什么当前 canonical 入口必须收敛

如果同时存在多份长期部署入口，团队会遇到以下问题：

| 风险 | 说明 |
|---|---|
| 端口漂移 | 一份写 `8000`，一份写 `8002`，Nginx 代理很容易配错。 |
| 文档分叉 | 一处更新、另一处遗漏，导致部署步骤互相打架。 |
| 调试成本上升 | 出问题时先花时间判断“按哪份部署的”。 |
| AI 协作者误判 | Composer 容易把本地快照当正式入口继续扩写。 |

所以，部署入口必须保持**单一事实来源**。

---

## 4. 当前建议的仓库策略

### 4.1 现在保留为正式入口的

- [`docs/DEPLOY.md`](./DEPLOY.md)
- [`docker-compose.prod.yml`](../docker-compose.prod.yml)

### 4.2 现在继续留本地、不推送的

- `deploy-20260325-172328/`
- `usking-deploy.tar.gz`
- `.env`
- 含登录凭据或上传操作的临时辅助脚本

### 4.3 未来若确实需要“正式部署脚本”，建议这样入库

建议采用固定目录，而不是时间戳快照：

```text
deploy/
├── README.md
├── server-setup.sh
├── start.sh
└── nginx/
    └── usking.vip.conf.example
```

入库前必须满足：

1. 不含真实密码、密钥、`.env` 实值
2. 使用占位符，而不是把单台服务器信息写死为唯一真相
3. 与 [`docs/DEPLOY.md`](./DEPLOY.md) 相互引用，不重复维护两套完整说明
4. 只保留**一份**生产 compose 入口

---

## 5. 给 Composer 的执行规则

当仓库里同时出现 `deploy.sh`、`deploy-时间戳目录/`、`docker-compose.prod.yml`、`docs/DEPLOY.md` 时，优先级必须是：

1. `docs/DEPLOY.md`
2. `docker-compose.prod.yml`
3. 其余脚本仅视为候选本地辅助资产

除非人类明确要求，否则：

- 不把时间戳快照目录加入 Git
- 不把复制 `.env` 的脚本当正式产物提交
- 不新增第二份长期生产 compose

---

## 6. 与其他文档的关系

- 推送边界总则见 [`docs/COMPOSER_PUSH_BOUNDARY.md`](./COMPOSER_PUSH_BOUNDARY.md)
- 项目手册见 [`docs/README-USKING-HANDBOOK.md`](./README-USKING-HANDBOOK.md)

---

## 7. 变更记录

| 日期 | 说明 |
|---|---|
| 2026-03-26 | 初版：审计本地部署资产，明确当前 canonical 部署入口与未来入库方向。 |
