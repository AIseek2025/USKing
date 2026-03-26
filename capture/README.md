# capture — 窗口/屏幕/音频采集

负责采集以下信源：

- **美股王交易软件**：一个或多个前端行情窗口
- **盈透证券 (IB)**：交易界面窗口
- **摄像头**
- **目标网页 / 桌面音频**
- **主播麦克风**

## MVP
- 浏览器：
  - `getDisplayMedia()` 采集主屏幕/目标网页
  - `getUserMedia({ video: true })` 采集摄像头
  - `getUserMedia({ audio: true })` 采集麦克风

## 长期
- Windows：Graphics Capture + WASAPI
- macOS：ScreenCaptureKit + AVFoundation

## 输出契约
- 视频轨：`screen`、`camera`
- 音频轨：`page`、`mic`
- 提供给 composer 的统一输出应是 `MediaStream` / 轨道对象，而不是 JPEG 快照
