# USKing（美股王）项目手册

> **文档性质**：本文件为**增量补充型**详尽说明，与仓库根目录 `README.md`、`docs/REQUIREMENTS.md` 等既有文档**并列存在**。  
> **不替代**历史文档；新结论、新流程、新验收标准优先以**新文件**沉淀（见下文「文档与 README 工作规范」）。

---

## 1. 文档与 README 工作规范（团队与协作者必读）

### 1.1 核心原则：新增用新文件，保留历史可追溯

| 做法 | 说明 |
|------|------|
| **新增详尽说明、阶段总结、验收清单** | 在 `docs/` 下**新建**独立 Markdown 文件，使用清晰文件名（见 1.2）。 |
| **不默认覆盖** | 未经明确要求，**不**把新内容整块合并进已有 `README.md`、已有需求/架构文档，避免冲淡历史版本与审计线索。 |
| **根目录 README** | 保持简短入口角色；若需「更全」内容，**新增**如本手册或专题文档，并在**新文件**内互相引用。 |
| **修正明显错误** | 错别字、失效链接、与安全相关的硬错误，可在原文件**最小范围**修正；结构性重写仍建议**新开文档**并注明替代关系。 |

### 1.2 新文档命名建议

- **手册类**：`README-<主题>-HANDBOOK.md` 或 `README-<主题>.md`（与本文件同类）。  
- **阶段/迭代**：`<主题>-PHASE<n>-<简述>.md` 或带日期 `<主题>-YYYY-MM-DD-<简述>.md`。  
- **流程/规范**：`<流程名>-WORKFLOW.md`、`<流程名>-RUNBOOK.md`。  
- **工作留底**：`LIVE_GSTACK_WORK_RECORD.md` 一类**可追加**的记录文件，与「版本快照」类文档区分：后者仍优先**新文件**留版本。

### 1.3 交叉引用方式

- 在新文档中**显式链接**到既有文档路径，例如：「详见 [LIVE_ARCHITECTURE_UPGRADE.md](./LIVE_ARCHITECTURE_UPGRADE.md)」。  
- 仓库内链接统一使用 **仓库相对路径**，**不要**写本机绝对路径（如 `/Users/...`），以保证远端可点击与可协作。  
- 若某专题已有多份文档，在新文档开头写 **「文档地图」** 小节，列出阅读顺序。

### 1.4 与本手册的关系

- **本手册**（`docs/README-USKING-HANDBOOK.md`）遵循上述规范：作为**独立手册**存在；后续若需更新「详尽说明」，可再新建 `README-USKING-HANDBOOK-v2.md` 或按日期增量，**不强制**回头改写本文件全文，除非团队决定合并版本。

---

## 2. 项目定位与读者对象

### 2.1 一句话

**USKing** 是面向美股王会员的**交易界面直播** Web 平台：主播在本地采集看盘软件、交易终端等画面（及可选摄像头/麦克风），经合成与推流，观众在站内或外站观看。

### 2.2 读者对象

| 角色 | 建议阅读 |
|------|----------|
| 新开发者 | 根目录 `README.md` → 本手册 `§3`～`§5` → `docs/DEPLOY.md`（生产） |
| 媒体/直播架构 | `docs/LIVE_ARCHITECTURE_UPGRADE.md`、`docs/LIVE_ROLLOUT_PHASES.md`、`docs/LIVE_PHASE3_EGRESS.md` |
| Gstack / Composer 节奏 | `docs/LIVE_GSTACK_COMPOSER2_QUICKSTART.md`、`docs/LIVE_GSTACK_COMPOSER2_EXECUTION.md`、`docs/LIVE_FOUR_DIM_GSTACK_WORKFLOW.md` |
| 产品术语与范围 | `docs/REQUIREMENTS.md` |

---

## 3. 仓库导航（高层）

```
USKing/
├── server/              # FastAPI：业务 API、鉴权、直播会话、媒体配置等
├── templates/           # Jinja2，含站内 SPA（dashboard 等）
├── static/              # JS/CSS/上传目录（上传内容勿提交 Git）
├── app/                 # 独立页面入口（如 live 采集页）
├── services/            # 媒体/信令等子服务说明与占位
├── infra/               # PostgreSQL、Redis、TURN 等说明
├── capture/ composer/ stream/   # 边界说明（规划）
├── requirements.txt Dockerfile docker-compose*.yml .env.example
└── docs/                # 需求、架构、部署、直播升级与流程文档
```

更细的目录与命令以根目录 `README.md` 为准。

---

## 4. 开发与运行（摘要）

以下仅为手册摘要；**环境变量与生产检查清单**以 `docs/DEPLOY.md` 为准。

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

- 开发模式可启用 `DEV_MODE=true`（见 `.env.example`）。  
- **生产**必须：`DEV_MODE=false`、强随机 `SECRET_KEY`、管理员密码与 HTTPS 等（见 `docs/DEPLOY.md`）。

---

## 5. 直播技术路线（摘要）

| 层级 | 说明 |
|------|------|
| **业务平面** | FastAPI：开播/停播、JWT、LiveKit token、媒体配置等 |
| **浏览器侧** | `getDisplayMedia` 采集窗口、`getUserMedia` 摄像头/麦克风、Canvas 合成、`canvas.captureStream` + LiveKit 或 JPEG 推帧 fallback |
| **媒体平面（推荐）** | LiveKit（WebRTC SFU）、后续 egress（RTMP/HLS 等）见 `docs/LIVE_PHASE3_EGRESS.md` |

**Fallback**：JPEG 轮询 + 站内展示，用于无 WebRTC 或诊断；**正式能力**以 WebRTC + 可选 egress 为目标。

---

## 6. 四维一体与节目布局（主播侧能力摘要）

目标能力（与 `docs/LIVE_FOUR_DIM_GSTACK_WORKFLOW.md` 一致）：

| 维度 | 说明 |
|------|------|
| 目标网页/桌面画面 | 窗口采集，可多源布局 |
| 主播摄像头 | 可开关 |
| 画面/系统音 | 与采集选项一致（含 `getDisplayMedia` 音频） |
| 麦克风 | 与采集选项一致 |

**节目布局（与多窗口「布局」并列）**：

- 网页主 + 摄像小窗（PiP）  
- 摄像主 + 网页小窗（PiP，离屏绘制网页小窗）  
- 左右约各一半（左网页合成、右摄像头）

**实现落点（代码层，便于排查）**：

- 站内 SPA：`templates/index.html`（Dashboard 侧栏与 `dash*` 合成逻辑）  
- 独立页：`app/live.html`（同源逻辑，变量名与根 `README` 中「前端」描述一致）  
- LiveKit 双音轨：`static/js/livekit-usking.js`（`audioPageTrack` / `audioMicTrack` 命名）  
- 文案：`static/js/i18n.js` 中 `dash.prog_*`、`dash.cam_*` 等键  

---

## 7. 文档地图（docs/ 推荐阅读顺序）

| 文件 | 用途 |
|------|------|
| [REQUIREMENTS.md](./REQUIREMENTS.md) | 业务需求与术语 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 架构设想与模块 |
| [DEPLOY.md](./DEPLOY.md) | 生产部署清单 |
| [DEPLOY_ASSETS_REVIEW.md](./DEPLOY_ASSETS_REVIEW.md) | 本地部署脚本/快照是否值得入库的审计结论 |
| [LIVE_ARCHITECTURE_UPGRADE.md](./LIVE_ARCHITECTURE_UPGRADE.md) | 直播升级总览 |
| [LIVE_ROLLOUT_PHASES.md](./LIVE_ROLLOUT_PHASES.md) | 分阶段上线 |
| [LIVE_PHASE3_EGRESS.md](./LIVE_PHASE3_EGRESS.md) | Phase 3 egress 纲要 |
| [LIVE_FOUR_DIM_GSTACK_WORKFLOW.md](./LIVE_FOUR_DIM_GSTACK_WORKFLOW.md) | 四维 + Gstack 波次 |
| [LIVE_GSTACK_COMPOSER2_QUICKSTART.md](./LIVE_GSTACK_COMPOSER2_QUICKSTART.md) | Composer2 快速上手 |
| [LIVE_GSTACK_COMPOSER2_EXECUTION.md](./LIVE_GSTACK_COMPOSER2_EXECUTION.md) | Composer2 执行细则 |
| [LIVE_GSTACK_WORK_RECORD.md](./LIVE_GSTACK_WORK_RECORD.md) | 可审计工作记录 |
| [COMPOSER_PUSH_BOUNDARY.md](./COMPOSER_PUSH_BOUNDARY.md) | 哪些产物应该推送的边界清单 |
| [REFERENCES.md](./REFERENCES.md) | 外部参考 |

---

## 8. 协作与提交约定（摘要）

- **Python**：遵循项目现有风格；依赖锁定在 `requirements.txt`。  
- **前端**：大段内联脚本在 `templates/` / `app/` 中已与现有模式一致，改动时保持与 `live.html` / Dashboard 行为对齐。  
- **安全**：勿提交真实密钥、`.env` 副本；生产变量见 `docs/DEPLOY.md`。  
- **Git**：大仓库推送问题见根目录 `README.md` 中 `http.postBuffer` 说明。
- **推送边界**：提交前先对照 [`docs/COMPOSER_PUSH_BOUNDARY.md`](./COMPOSER_PUSH_BOUNDARY.md) 判断哪些文件该推、哪些应留本地。

---

## 9. 本手册变更记录

| 日期 | 说明 |
|------|------|
| 2026-03-26 | 初版：项目手册 + 文档/ README 工作规范（新增文档用新文件、不默认覆盖历史 md）。 |

---

**维护**：后续重大更新请**新增** `README-USKING-HANDBOOK-YYYY-MM-DD.md` 或本文件附录小节，或按团队约定另起版本文件；**不强制**修改本文件首版日期行以外的历史表述。
