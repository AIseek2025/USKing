# Redis

Redis 用于承接“实时但非主媒体流”的共享状态。

## 建议职责
- 房间在线态 / presence
- 观众在线数缓存
- 幂等锁
- rate limit
- 聊天 fanout 元数据
- egress 任务状态

## 不承载
- 正式音视频主媒体流

主媒体流应留在 WebRTC SFU / RTMP / HLS 平面，不经 Redis。
