# 四维一体直播：目标定义与 Gstack 规范工作流拆解

本文档回答：

1. **总体规划是否包含摄像头与四路音视频** — 是；与 [LIVE_ARCHITECTURE_UPGRADE.md](LIVE_ARCHITECTURE_UPGRADE.md) 中「screen / camera / page audio / mic」一致，本仓库以 **业务契约 + 主播端合成 + 媒体平面轨** 分层落地。  
2. **如何用 Gstack 节奏（Think → Plan → Build → Review → Test → Ship → Reflect）拆解** — 见下文阶段表。

---

## 1. 最终产品目标（四维 + 布局）

| 维度 | 含义 | 主播侧 | 观众侧 |
|------|------|--------|--------|
| A | 目标网页/桌面画面 | `getDisplayMedia` 多窗口合成 | 主节目或 PiP/分屏中的一路 |
| B | 主播摄像头 | `getUserMedia` 视频 | 主节目或 PiP/分屏中的一路 |
| C | 目标网页/系统声音 | tab/system audio | 可关可开 / 独立音量（视实现） |
| D | 主播麦克风 | `getUserMedia` 音频 | 可关可开 / 独立音量 |

**布局目标（三种）：**

- `webMain_camPip`：网页（多窗口合成）为主画面，摄像头为小窗（典型 PiP）。  
- `camMain_webPip`：摄像头为主画面，网页合成小窗。  
- `split50`：左右约各 50%（左网页右摄像，或按产品定左右语义；实现上固定为「左：网页合成 / 右：摄像」可切换）。

**约束：** 任意一维在主播侧应可 **开/关**（画面黑场或静音轨，而非误推上一帧隐私）。

---

## 2. 与 Gstack 阶段对齐的拆解

### Wave A — Think / Plan（已部分完成）

- **产出**：本文件、`LIVE_ARCHITECTURE_UPGRADE.md`、媒体 API 契约。  
- **门禁**：不扩展 legacy JPEG 为主架构；多轨策略写在 `server/live_media.py` 的 `tracks` 描述中。

### Wave B — Build：主播端合成与开关（当前迭代）

- **产出**：`templates/index.html`、`app/live.html` 内合成器：节目布局三态、网页采集开关、摄像头开关、页音/麦音采集开关；单路节目视频输出给 `canvas.captureStream`（LiveKit/JPEG 共用）。  
- **门禁**：未开摄像头时行为与旧版多窗口布局一致；开摄像头后启用节目布局三态。

### Wave C — Build：媒体平面双音轨（可选下一 PR）

- **产出**：LiveKit 发布 **两条命名音频轨**（`page` / `mic`），`livekit-usking.js` 与观看端订阅两路并混音。  
- **门禁**：与 legacy `live-audio.js` 行为可并存开关；失败回退单混音轨。

### Wave D — Review / Test

- **Review**：安全（误开麦、误开屏）、布局切换是否闪烁、停止直播是否释放所有 `MediaStreamTrack`。  
- **Test**：Chrome/Edge/Safari 各一组；无摄像头仅网页；仅摄像头无网页（黑场+摄像）；弱网重连（LiveKit）。

### Wave E — Ship / Document

- **Ship**：`docs/DEPLOY.md`、`.env.example`、`LIVE_GSTACK_WORK_RECORD.md` 增补证据行。  
- **Reflect**：记录布局与双音轨的已知限制（浏览器系统音差异、Safari 约束）。

### Wave F — Phase 3（RTMP/HLS egress）

- **见** [services/media-egress/README.md](../services/media-egress/README.md)、[LIVE_PHASE3_EGRESS.md](LIVE_PHASE3_EGRESS.md)。  
- **门禁**：egress 输入为 **单路节目** 或与 SFU 订阅一致的多轨策略，避免与站内 WebRTC 混用同一套误配。

### Wave G — Phase 4（生产化）

- PostgreSQL / Redis / TURN / 监控；多实例下会话与在线态一致。

---

## 3. 文件与责任边界

| 区域 | 内容 |
|------|------|
| 主播 UI + 合成 | `templates/index.html`, `app/live.html` |
| 观看端 WebRTC | `templates/watch.html`, `static/js/livekit-usking.js` |
| 会话与轨声明 | `server/live_media.py`, `server/api.py` |
| Legacy 音频 | `static/js/live-audio.js`, `server/live_broadcast.py` |
| Egress / HLS | `services/media-egress/README.md`, `docs/LIVE_PHASE3_EGRESS.md` |

---

## 4. 禁止项（与执行手册一致）

- 不一次性在单 PR 内完成「四维 + 双音轨 + egress + DB」全栈。  
- 不在未调查根因时堆叠浏览器适配分支。  
- 不删除 `legacy_jpeg` 回退路径。
