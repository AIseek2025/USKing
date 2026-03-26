# Gstack 相关工作过程报告（USKing 直播升级）

> **文档性质**：本报告为**独立增量文档**，说明在 USKing 仓库语境下，协作者（含 AI 助手）如何**对照** [gstack](https://github.com/garrytan/gstack) 思想开展工作，以及**未**采取的做法与原因。  
> **不修改**既有 `README.md` 或其他历史 md；与 [`README-USKING-HANDBOOK.md`](./README-USKING-HANDBOOK.md) 中的文档工作规范一致。

---

## 1. 报告目的与范围

| 问题 | 本报告中的结论摘要 |
|------|-------------------|
| Gstack 的 md 是否被拷贝进 USKing？ | **否**。仓库内**没有** `gstack/` 上游仓库或整包文档的 vendoring。 |
| 那 Gstack 如何体现？ | 通过 **USKing 自撰** 的专题文档，把阶段节奏、门禁、分工思想**映射**到本项目（见 §2）。 |
| 是否创建了多 Agent 团队分工开发？ | **本次连续实施会话中未创建**。原因见 §4。 |

---

## 2. Gstack 在 USKing 中的实际用法：治理框架，非代码依赖

### 2.1 与上游 gstack 的关系（事实陈述）

- **上游来源**：公开仓库 [garrytan/gstack](https://github.com/garrytan/gstack)（虚拟工程团队工作流、技能链、ETHOS 等概念）。  
- **USKing 仓库内检索结果**：  
  - **不存在** `gstack/` 子目录或从上游 **整库拷贝** 的 Markdown 树。  
  - **存在**的是以 `LIVE_GSTACK_*`、`LIVE_FOUR_DIM_GSTACK_*` 等命名的 **本项目文档**，内容由项目需求驱动撰写，并**引用**上游链接与阶段名（Think → Plan → Build → Review → Test → Ship → Reflect）。

### 2.2 「拷贝」还是「阅读理解后转写」？

| 方式 | 是否采用 | 说明 |
|------|----------|------|
| 将 gstack 仓库内 md **原样复制**到 `docs/third-party/gstack/` 等路径 | **否** | 未在 USKing 中做上游文档镜像；避免许可证/同步负担与双源维护。 |
| 阅读公开说明与社区共识后，**按 USKing 场景转写** | **是** | 例如 [`LIVE_GSTACK_COMPOSER2_EXECUTION.md`](./LIVE_GSTACK_COMPOSER2_EXECUTION.md)、[`LIVE_GSTACK_WORK_RECORD.md`](./LIVE_GSTACK_WORK_RECORD.md)、[`LIVE_FOUR_DIM_GSTACK_WORKFLOW.md`](./LIVE_FOUR_DIM_GSTACK_WORKFLOW.md) 等，明确写的是 **USKing 的**门禁、文件边界、波次与证据索引。 |

因此：**不是**「把 Gstack 的 md 文件拷进工作文件夹」，而是 **理解其思想与阶段模型后，在 USKing 内新建专用文档** 完成对齐与落地说明。

### 2.3 使用 Gstack「框架」时具体做了什么

在工程含义上，「使用 Gstack」在本项目中等价于：

1. **阶段化**：用与 gstack 一致的 sprint 顺序拆解直播升级（需求冻结、实现、评审、测试、发布、反思）。  
2. **产物化**：把门禁与边界写进 `docs/LIVE_*`，使执行者不依赖单次聊天上下文也能按同一套纪律推进。  
3. **显式非目标**：不把 gstack 当 FastAPI/前端的 **运行时依赖**；不把上游 CLI/技能二进制塞进 USKing 业务进程（[`LIVE_GSTACK_WORK_RECORD.md`](./LIVE_GSTACK_WORK_RECORD.md) 中已有说明）。

可选增强（对人类开发者）：在个人 IDE 中安装上游 gstack 技能，在**对话内**使用 `/plan-eng-review` 等——这与 USKing **仓库产物**独立，本报告不将其记为「仓库内拷贝」。

---

## 3. 与仓库文档的对应关系（便于审计）

| USKing 文档 | 与 Gstack 的关系 |
|-------------|------------------|
| [`LIVE_GSTACK_COMPOSER2_QUICKSTART.md`](./LIVE_GSTACK_COMPOSER2_QUICKSTART.md) | 快速约定：gstack 作治理流程、非运行时依赖 |
| [`LIVE_GSTACK_COMPOSER2_EXECUTION.md`](./LIVE_GSTACK_COMPOSER2_EXECUTION.md) | 执行手册：映射表、Composer 2 约束 |
| [`LIVE_FOUR_DIM_GSTACK_WORKFLOW.md`](./LIVE_FOUR_DIM_GSTACK_WORKFLOW.md) | 四维直播目标 + 波次拆解 |
| [`LIVE_GSTACK_WORK_RECORD.md`](./LIVE_GSTACK_WORK_RECORD.md) | 嵌入方式、证据索引、可审计留底 |
| [`LIVE_PHASE3_EGRESS.md`](./LIVE_PHASE3_EGRESS.md) | Phase 3 与门禁段落 |

以上均为 **USKing 原创撰写**的 Markdown，**不是**上游仓库文件的逐文件拷贝。

---

## 4. 多 Agent 团队：本次是否创建？若未创建，原因是什么？

### 4.1 结论

在 **本轮由同一助手连续完成的直播相关实现与文档补充**（例如：Dashboard/`app/live.html` 合成与开关、LiveKit 双音轨、`i18n`、项目手册等）中，**没有**通过「创建多个子 Agent / 虚拟团队」的方式并行分工。

### 4.2 未创建多 Agent 团队的典型原因（诚实说明）

| 原因类别 | 说明 |
|----------|------|
| **任务耦合度高** | 合成逻辑、`live.html` 与 `index.html`、`livekit-usking.js` 需 **同一套语义与变量约定**，单上下文连续修改可减少不一致与重复劳动。 |
| **变更面集中** | 修改集中在少数文件，并行拆给多个 Agent 易带来 **合并冲突** 与 **接口约定漂移**（例如 `hostConnect` 参数形状、停播时是否释放摄像头）。 |
| **未收到显式编排要求** | 用户未要求「必须按 gstack 多角色拆成多个 Agent 并行」，则默认采用 **单会话串行** 完成，成本更低。 |
| **gstack 的「团队」在仓库中的落点** | 文档中强调的是 **流程与角色视角**（需求、工程、评审、QA）；**不等于**必须在 Cursor/Composer 里实例化多个 Agent 进程。 |

### 4.3 何时「值得」用多 Agent（供后续迭代参考）

- 大范围 **探索**：多路径调研（如 egress 选型 SRS vs LiveKit Egress）可并行 Task/explore。  
- **独立子树**：无共享状态的脚本、独立服务的 README、与主站无关的基准测试。  
- **显式要求**：当用户或流程要求「评审与实现隔离」时，可用只读子任务做 review，与实现会话分离。

---

## 5. 局限与声明

- 本报告描述的是 **当前仓库状态** 与 **本助手可陈述的工作方式**；若历史上曾有其他会话或人类开发者向仓库提交内容，以 **git 记录** 为准。  
- 未在 USKing 内保存与 gstack 上游 **逐字镜像** 的文档树；若未来需要合规审计「上游原文」，应在 CI 或 `docs/third-party/` 中 **单独** 引入并标明版本与许可证，**仍建议**保持 USKing 自有映射文档为 **主读路径**（与 [`README-USKING-HANDBOOK.md`](./README-USKING-HANDBOOK.md) §1 一致）。

---

## 6. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-03-26 | 初版：Gstack 使用方式事实说明、未拷贝上游 md、未使用多 Agent 团队的原因与后续建议。 |
