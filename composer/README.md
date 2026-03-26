# composer — 多路画面合成与布局

将多路采集源（美股王多窗口 + 盈透 + 摄像头）合成为单路主节目，支持：

- 多屏行情布局（网格、分栏等）
- 盈透界面作为主画面或画中画
- 摄像头 PiP 或分栏
- 可选叠加层（Logo、文字等）

## 推荐布局预设
- `screenOnly`
- `screenPlusPipCam`
- `screenAndCamSideBySide`

## 输出
- MVP：浏览器 `canvas.captureStream()`
- 正式生产：作为媒体平面的主节目输入，供 WebRTC/RTMP/HLS 后续处理
