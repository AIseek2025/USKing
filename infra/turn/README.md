# TURN / STUN

站内 WebRTC 实时观看上线后，TURN 是生产必需件，不是可选件。

## 作用
- NAT 穿透
- 企业/校园网回落中继
- 保证弱网与复杂网络环境的可连通性

## 推荐
- coturn

## 配置来源
- 由 `LIVE_TURN_URLS` 暴露给业务层
- 由 `realtime-signaling` 下发给客户端
