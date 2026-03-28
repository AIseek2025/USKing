# USKing 全球直播重构开发计划任务书

本文档可直接发给 `composer 2` 执行。

这是面向实施的总任务书，不是讨论稿。目标是把 USKing 当前已落地的“混合媒体控制面骨架”，继续推进到可长期运营的全球级直播系统。

不允许修改附带的计划文件本身。权威规划输入来自：

- `docs/LIVE_ARCHITECTURE_UPGRADE.md`
- `docs/LIVE_ROLLOUT_PHASES.md`
- `docs/LIVE_GSTACK_COMPOSER2_EXECUTION.md`
- `.cursor/plans/global-live-rebuild_fafe7544.plan.md`

---

## 1. 项目目标

把 USKing 直播系统升级为以下双平面结构：

- 站内互动直播：低延迟 RTC，目标端到端 `1-3s`
- 全球公播分发：HLS + CDN，目标端到端 `5-15s`

同时达成以下工程目标：

- 不再让 `legacy_jpeg + 站内音频 WS` 承担主链路
- 媒体能力与业务能力解耦
- 支持供应商切换、灰度发布、区域路由与回滚
- 具备录制、回放、QoE、SLO、异常定位与告警能力

---

## 2. 当前基线

以下基础已经在仓库中落地，`composer 2` 必须在此基础上继续推进，不允许推翻重做：

- `server/live_media.py`
  已具备媒体平面描述、区域感知、互动/公播/fallback 选择、会话下发
- `server/api.py`
  已提供 `host-session`、`viewer-session`、播放会话关闭、QoE 上报、观测汇总接口
- `server/live_state.py`
  已提供 `Redis -> Memory` 的 presence 降级封装
- `server/live_observability.py`
  已提供播放会话、录制任务、质量事件的持久化入口
- `templates/watch.html`
  已支持按会话选择 `WebRTC / HLS / fallback`
- `static/js/hls-usking.js`
  已接入 HLS 播放器薄封装
- `docker-compose.prod.yml`
  已接入 `Postgres`、`Redis` 容器，但默认仍兼容现网 `DATABASE_URL`

结论：

- 现在不是从零开始
- 当前阶段不是“设计新架构”，而是“把骨架补成可用的生产系统”

---

## 3. 总体技术路线

推荐默认供应商分工如下：

- 互动 RTC：`LiveKit Cloud` 或等价全球托管 RTC
- Egress / Recording：`Mux` 或 RTC 平台自带 egress
- 公播分发：`HLS + Global CDN`
- 状态层：`Redis + Postgres`
- 回退链路：`legacy_jpeg` 仅用于诊断、极低配预览、紧急回退

不建议 `composer 2` 在本任务中做以下事情：

- 自研 SFU
- 自研 TURN 调度系统
- 把所有厂商能力改成完全自托管
- 一次性删除全部 legacy 代码

---

## 4. 最高执行纪律

`composer 2` 必须严格遵守：

`Think -> Plan -> Build -> Review -> Test -> Ship -> Reflect`

每个阶段都必须先产出单阶段执行卡片，然后才能改代码。卡片格式如下：

```md
## Stage
<阶段名>

## Goal

## Scope

## OutOfScope

## FilesAllowed

## ArchitectureDecision

## Deliverables

## Tests

## Rollback

## DocsToUpdate

## DoneDefinition
```

没有这张卡片，不允许进入 Build。

---

## 5. 阶段划分

本任务按 6 个执行阶段推进。一次只允许做一个阶段。

### Phase A：Provider 抽象层正式化

#### Goal
把当前 `live_media.py` 中偏配置驱动的逻辑，升级为正式的 `MediaProvider` 适配层，支持后续对接真实托管媒体厂商。

#### Scope

- 抽出 `MediaProvider` 接口
- 提供至少两个 provider：
  - `ManagedLiveKitProvider`
  - `LegacyFallbackProvider`
- 把 token 签发、房间信息、区域端点、egress 描述从 `if/else` 拆到 provider 内
- 统一 host/viewer session 结构

#### OutOfScope

- 不做桌面端原生采集
- 不做完整后台管理页
- 不做数据库迁移到外部云托管

#### FilesAllowed

- `server/live_media.py`
- `server/api.py`
- `server/config.py`
- `server/`

#### Deliverables

- `MediaProvider` 抽象
- provider 注册与选择机制
- 标准化 session schema
- 至少一组 provider 级单元测试

#### Tests

- provider 选择逻辑测试
- 区域路由测试
- host/viewer session schema snapshot 测试

#### Rollback

- 保留当前环境变量路由开关
- provider 接入失败时必须回退 `legacy` 会话

#### DoneDefinition

- `server/live_media.py` 不再继续堆叠新的供应商判断分支
- 后续加新媒体厂商时，无需改观看页状态机

### Phase B：主播端统一发布 SDK

#### Goal
把 `app/live.html` 与 `templates/index.html` 里的主播推流逻辑统一为一套前端发布 SDK。

#### Scope

- 抽离共享发布器模块，统一：
  - 采集源管理
  - `screen/camera/page/mic` 轨处理
  - 分辨率与码率策略
  - RTC 发布
  - 预览帧推送
- 移除两处重复实现

#### OutOfScope

- 不重写 UI 风格
- 不改直播业务操作按钮语义

#### FilesAllowed

- `app/live.html`
- `templates/index.html`
- `static/js/`

#### Deliverables

- 新的前端发布 SDK 文件
- 主播页与站内后台共用同一发布器
- RTC 成功时不再启动站内音频 WS

#### Tests

- 手工验证：主播页开播
- 手工验证：站内后台开播
- 手工验证：切分辨率、切布局、切音源

#### Rollback

- 保留原入口页，但通过开关切回旧实现

#### DoneDefinition

- 主播链路只有一套核心发布代码
- 不再存在“修一处坏另一处”的重复逻辑

### Phase C：公播 HLS 与录制闭环

#### Goal
把现有 HLS 播放骨架接成真实闭环，形成“RTC 互动 + HLS 公播 + Recording”可运行体系。

#### Scope

- 接真实 egress / recording provider
- 输出 HLS manifest 与录制任务状态
- 增加多清晰度与播放页展示字段
- 增加基础回放索引页或接口

#### OutOfScope

- 不做完整视频中心产品
- 不做复杂推荐排序

#### FilesAllowed

- `server/api.py`
- `server/live_observability.py`
- `server/models.py`
- `templates/watch.html`
- `static/js/hls-usking.js`
- `templates/`

#### Deliverables

- HLS manifest 状态真实可追踪
- 录制任务状态可见
- 回放索引基础接口

#### Tests

- 互动主播开播后可生成 HLS
- 录制任务可落库
- 观看页在 broadcast plane 下稳定播放

#### Rollback

- HLS 不可用时自动回退 RTC 或 fallback，不能直接黑屏

#### DoneDefinition

- “公播页”不再只是概念字段，而是可实际播放

### Phase D：状态层与僵尸流彻底治理

#### Goal
把直播关键状态从当前混合内存态彻底迁到 `Redis + Postgres`，并清理主链路对 `server/live_broadcast.py` 的依赖。

#### Scope

- 直播在线态、心跳、播放会话、录制任务、质量事件全部正式入库或入 Redis
- `server/live_broadcast.py` 降级为 preview / emergency fallback
- 僵尸流、假在线、错误 viewer_count 做统一治理

#### OutOfScope

- 不删除 fallback 代码文件
- 不做消息总线大改

#### FilesAllowed

- `server/live_state.py`
- `server/live_observability.py`
- `server/live_broadcast.py`
- `server/api.py`
- `server/models.py`

#### Deliverables

- 关键状态迁移清单
- Redis key 设计
- 数据表字段审计与补齐

#### Tests

- 多实例部署下 active stream 不乱
- 主播断开后僵尸流自动回收
- 回退链路不影响主链路状态

#### Rollback

- 新状态层失败时可切回当前 Memory fallback

#### DoneDefinition

- `server/live_broadcast.py` 不再承担主观看路径状态职责

### Phase E：QoE、SLO、告警与运行手册

#### Goal
把“感觉慢、听不到、卡”变成可观测、可告警、可定位的问题。

#### Scope

- 统一 QoE 事件模型
- 增加关键指标：
  - 首帧时间
  - 首声时间
  - 播放失败率
  - 建连成功率
  - fallback 命中率
  - HLS 启动耗时
  - RTC 互动占比
- 输出运行手册与异常排查手册

#### FilesAllowed

- `server/live_observability.py`
- `server/api.py`
- `templates/watch.html`
- `docs/`

#### Deliverables

- 观测汇总接口增强
- 指标定义文档
- 告警阈值建议
- runbook

#### Tests

- 能人工触发一组 QoE 事件
- 能在接口中看到聚合结果

#### Rollback

- 观测失败不能阻断主链路播放

#### DoneDefinition

- 线上故障可从“用户反馈”升级为“指标报警 + 证据定位”

### Phase F：双栈迁移、灰度与正式切流

#### Goal
把新链路平滑切到生产默认，不中断现网。

#### Scope

- 完成灰度参数化：
  - 用户
  - 地域
  - 登录态
  - 主播 ID
  - 播放意图
- 写清切流策略、回滚策略、验收门槛
- 更新生产部署与发布手册

#### FilesAllowed

- `server/live_media.py`
- `server/config.py`
- `docker-compose.prod.yml`
- `docs/DEPLOY.md`
- `docs/`

#### Deliverables

- 灰度配置矩阵
- 发布检查单
- 回滚脚本或回滚步骤
- canary 观测清单

#### Tests

- 白名单灰度
- 国家灰度
- 一键回切 fallback

#### Rollback

- 任意阶段必须支持回退到：
  - broadcast 优先
  - interactive 优先
  - legacy only

#### DoneDefinition

- 新链路可以作为默认主路径上线
- 遇到异常时 10 分钟内可回退

---

## 6. `composer 2` 每阶段必须提交的产物

每完成一个阶段，必须交付以下内容：

- 代码实现
- 自动化测试
- 人工验收记录
- 变更摘要
- 风险清单
- 回滚说明
- 文档更新

每次汇报必须使用固定格式：

```md
## Stage

## What Changed

## Why

## Files Changed

## Tests Run

## Risks

## Rollback

## Next Recommended Stage
```

---

## 7. 统一验收标准

全项目最终验收必须满足：

- 登录用户观看互动直播时，默认能走 RTC
- 非互动用户或灰度策略指定用户，能稳定走 HLS
- fallback 仅在 RTC/HLS 失败时触发
- 主播端不再并行跑 RTC + 站内音频 WS
- 僵尸流、假在线、无声、黑屏问题有可定位证据
- 线上部署文档完整
- 回滚路径演练通过

---

## 8. 关键禁止事项

`composer 2` 不允许：

- 一次性把 6 个阶段混在一个 PR
- 修改计划文件 `.cursor/plans/global-live-rebuild_fafe7544.plan.md`
- 跳过阶段卡片直接开改
- 未经验证直接删除 fallback
- 在没有 runbook 的前提下切默认链路
- 因为“代码更优雅”而扩大范围重构无关模块

---

## 9. 推荐执行顺序

强制顺序如下：

1. `Phase A`
2. `Phase B`
3. `Phase C`
4. `Phase D`
5. `Phase E`
6. `Phase F`

任何阶段失败，都先修复本阶段或回滚，不允许跳到后续阶段赌运气。

---

## 10. 给 `composer 2` 的一句话指令

你不是在“继续修几个直播 bug”，你是在把 USKing 从试验性直播链路升级为“互动 RTC + 全球公播 + 可观测 + 可灰度 + 可回滚”的正式媒体平台。请严格按本任务书逐阶段执行，不得跨阶段扩张。
