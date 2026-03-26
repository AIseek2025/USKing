/**
 * Legacy 直播观众：双声道队列混音输出（与旧 ScriptProcessor 行为一致）。
 */
const MAX_QUEUES = 80;
const CH_PAGE = 0;
const CH_MIC = 1;

class LiveAudioPlaybackProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._qPage = [];
    this._qMic = [];
    this._offPage = 0;
    this._offMic = 0;
    this._gainPage = 1;
    this._gainMic = 1;
    this.port.onmessage = (e) => {
      const d = e.data;
      if (!d || typeof d !== 'object') return;
      if (d.type === 'push') {
        const copy = new Int16Array(d.buffer);
        if (d.ch === CH_PAGE) {
          this._qPage.push(copy);
          this._trim(this._qPage);
        } else if (d.ch === CH_MIC) {
          this._qMic.push(copy);
          this._trim(this._qMic);
        }
      } else if (d.type === 'gains') {
        this._gainPage = d.page ? 1 : 0;
        this._gainMic = d.mic ? 1 : 0;
      }
    };
  }

  _trim(q) {
    while (q.length > MAX_QUEUES) q.shift();
  }

  _pull(which) {
    const q = which === 0 ? this._qPage : this._qMic;
    let off = which === 0 ? this._offPage : this._offMic;
    while (q.length && off >= q[0].length) {
      q.shift();
      off = 0;
    }
    if (which === 0) this._offPage = off;
    else this._offMic = off;
    if (!q.length) return 0;
    const v = q[0][off] / 32768;
    if (which === 0) this._offPage++;
    else this._offMic++;
    return v;
  }

  process(outputs) {
    const out = outputs[0][0];
    const n = out.length;
    for (let i = 0; i < n; i++) {
      let sum = this._pull(0) * this._gainPage + this._pull(1) * this._gainMic;
      if (sum > 1) sum = 1;
      if (sum < -1) sum = -1;
      out[i] = sum;
    }
    return true;
  }
}

registerProcessor('live-audio-playback', LiveAudioPlaybackProcessor);
