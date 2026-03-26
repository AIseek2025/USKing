/**
 * Legacy 直播：从 MediaStream 拉取 mono Float32，主线程再编码为 int16 PCM 经 WebSocket 上传。
 */
class LiveAudioCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;
    const ch = input.length;
    const n = input[0].length;
    const out = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      let s = 0;
      for (let c = 0; c < ch; c++) s += input[c][i];
      out[i] = s / ch;
    }
    this.port.postMessage(out.buffer, [out.buffer]);
    return true;
  }
}

registerProcessor('live-audio-capture', LiveAudioCaptureProcessor);
