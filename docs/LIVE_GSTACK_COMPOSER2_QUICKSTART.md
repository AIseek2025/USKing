# Composer 2 Quickstart

给 `composer 2` 的最短执行摘要：

1. 把 gstack 当成 **开发治理流程**，不要当成运行时依赖。
2. 严格按 `Think -> Plan -> Build -> Review -> Test -> Ship -> Reflect` 推进。
3. 一次只做一个 Phase，不允许跨阶段重写直播栈。
4. 以 [`docs/LIVE_ARCHITECTURE_UPGRADE.md`](/Users/surferboy/.openclaw/workspace/USKing/docs/LIVE_ARCHITECTURE_UPGRADE.md) 为架构基线。
5. 以 [`docs/LIVE_ROLLOUT_PHASES.md`](/Users/surferboy/.openclaw/workspace/USKing/docs/LIVE_ROLLOUT_PHASES.md) 为阶段权威来源。
6. 旧链路 [`server/live_broadcast.py`](/Users/surferboy/.openclaw/workspace/USKing/server/live_broadcast.py) 仅是 `fallback`，不要继续往里面堆主功能。
7. 本阶段进入 Build 之前，必须先写清：
   - `Goal`
   - `Scope`
   - `FilesAllowed`
   - `ArchitectureDecision`
   - `Risks`
   - `Tests`
   - `Rollback`
   - `DocsToUpdate`
   - `DoneDefinition`
8. 复杂直播故障先调查根因，再修复；不要连续试错。
9. 每个阶段完成后必须同步文档、部署说明、回滚说明。
10. 上线顺序固定为：`staging -> review -> qa -> ship -> deploy -> canary`。

详细版请看：
- [`docs/LIVE_GSTACK_COMPOSER2_EXECUTION.md`](/Users/surferboy/.openclaw/workspace/USKing/docs/LIVE_GSTACK_COMPOSER2_EXECUTION.md)
