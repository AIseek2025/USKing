# 直播最终生产清单

适用于本次已验证跑通的 `USKing + LiveKit + 独立 coturn` 方案。

## 1. 当前已验证的生产基线

- 站内实时主链路：`LiveKit(WebRTC)`
- TURN 方案：`独立 coturn`
- 当前稳定 ICE 组合：
  - `TURN_UDP_URL=turn:47.239.7.62:3478?transport=udp`
  - `TURN_TLS_URL=`
  - `TURN_STUN_URLS=stun:stun.l.google.com:19302`
- LiveKit 信令地址：`wss://livekit-47-239-7-62.nip.io`
- 结果：手机端、电脑端均已恢复声音，画面正常，跨网播放已跑通

## 2. 端口与网络清单

### 云防火墙 / 安全组

- `UDP 3478`
- `TCP 3478`
- `UDP 50000-54999`
- `TCP 50000-54999`
- `TCP 7881`
- `UDP 55000-60000`

### 服务职责分配

- coturn：
  - 控制端口 `3478`
  - 中继端口段 `50000-54999`
- LiveKit：
  - TCP ICE `7881`
  - 媒体端口段 `55000-60000`

## 3. coturn 最终配置原则

- 云主机 NAT 场景下，不要把 `listening-ip` 直接写成公网 IP
- 推荐写法：
  - `listening-ip=<机器内网IP>`
  - `relay-ip=<机器内网IP>`
  - `external-ip=<公网IP>/<机器内网IP>`
- 当前阶段只保留 `UDP TURN`
- 未启用独立 `TURNS(5349/443)` 时：
  - `TURN_TLS_URL` 留空
  - coturn 配置中启用 `no-tls`
  - 不必挂证书

## 4. 应用环境变量核对

以下变量应与生产一致：

```bash
LIVE_MEDIA_BACKEND=livekit
LIVE_PUBLISH_MODE=webrtc
LIVE_PLAYBACK_MODE=webrtc
LIVE_FALLBACK_ENABLED=true
LIVE_FALLBACK_MODE=legacy_jpeg

LIVEKIT_WS_URL=wss://livekit-47-239-7-62.nip.io

TURN_ENABLED=true
TURN_REALM=livekit-47-239-7-62.nip.io
TURN_UDP_URL=turn:47.239.7.62:3478?transport=udp
TURN_TLS_URL=
TURN_STUN_URLS=stun:stun.l.google.com:19302
```

说明：

- `TURN_SHARED_SECRET` 必须和 coturn 的 `static-auth-secret` 完全一致
- `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` 必须和 LiveKit 服务端配置一致
- `legacy_jpeg` 继续保留，只作为回退和直播列表缩略图预览链路

## 5. 页面与功能核对

### 主播页

- 默认勾选 `采集画面 / 系统声音`
- 默认勾选 `采集麦克风`
- 可正常发布视频轨
- 可正常发布混音音频轨

### 观众页

- 电脑端可直接出声
- 手机端可正常出声
- 直播画面正常播放
- 直播列表缩略图仍能刷新

## 6. 验收清单

- [ ] 主播开播后控制台出现 `signal connected`
- [ ] 控制台出现 `pc connection state connected`
- [ ] 控制台出现 `room connected`
- [ ] 控制台出现 `all tracks published`
- [ ] `[LK:rtc] local candidate` 中出现 `srflx` 或 `relay`
- [ ] coturn 日志出现 `ALLOCATE processed, success`
- [ ] 第三方手机端有声音
- [ ] 第三方电脑端有声音
- [ ] 直播列表缩略图持续刷新
- [ ] 延迟明显低于纯 JPEG 轮询模式

## 7. 快速排障信号

### 现象：只有 `host` 候选，没有 `srflx/relay`

优先检查：

- 安全组是否放通 `3478`、`50000-54999`
- `TURN_STUN_URLS` 是否为空或不可用
- coturn 是否启动成功

### 现象：`TURN allocate request timed out`

优先检查：

- 云防火墙 / 安全组
- coturn 控制端口是否监听
- coturn 中继端口段是否与安全组一致

### 现象：coturn 报 `Cannot assign requested address`

根因通常是：

- 把 `listening-ip` / `relay-ip` 误写成公网 IP

修正方式：

- 改回机器内网 IP
- 用 `external-ip=公网/内网` 对外宣告

### 现象：音频没声音但画面正常

优先检查：

- 主播页是否勾选系统声音/麦克风
- 是否成功发布 `audio` track
- 观众页是否被浏览器自动播放策略静音

## 8. 建议保留的运维命令

```bash
# 重启 USKing Web
cd /opt/usking && docker compose -f docker-compose.prod.yml restart web

# 查看 coturn 日志
cd /opt/coturn && docker compose logs --tail=100

# 查看关键监听端口
ss -lntu | awk 'NR==1 || /:3478|:7881|:50000|:55000|:60000/'
```

## 9. 当前不建议立即做的事

- 不要在当前稳定期内继续折腾 LiveKit 内置 TURN
- 不要在未准备好独立证书/公网 IP 前强推 `TURNS 443`
- 不要删掉 `legacy_jpeg` 预览链路

## 10. 后续升级路线

若后续要继续升级，可按这个顺序推进：

1. 给 coturn 单独域名和独立证书
2. 视企业网需求增加 `TURNS 443`
3. 补充一轮端到端延迟压测
4. 再评估是否需要独立媒体机或多机部署
