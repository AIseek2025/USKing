/**
 * 站内直播音频：主播 WebSocket 上传双声道 PCM（0=画面系统音 1=麦克风），观众可独立开关两路。
 * 优先使用 AudioWorklet；不支持时回退 ScriptProcessorNode。
 */
(function (global) {
  'use strict';
  var CH_PAGE = 0;
  var CH_MIC = 1;
  var MAX_QUEUES = 80;

  var CAPTURE_WORKLET_URL = '/static/js/audio-worklets/live-audio-capture-processor.js';
  var PLAYBACK_WORKLET_URL = '/static/js/audio-worklets/live-audio-playback-processor.js';

  function wsBase() {
    var p = location.protocol === 'https:' ? 'wss:' : 'ws:';
    return p + '//' + location.host;
  }

  function floatToInt16(f32) {
    var n = f32.length;
    var out = new Int16Array(n);
    for (var i = 0; i < n; i++) {
      var s = f32[i];
      if (s > 1) s = 1;
      if (s < -1) s = -1;
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out;
  }

  function downmixMono(inputBuffer) {
    var n = inputBuffer.length;
    var ch = inputBuffer.numberOfChannels;
    var out = new Float32Array(n);
    for (var i = 0; i < n; i++) {
      var s = 0;
      for (var c = 0; c < ch; c++) s += inputBuffer.getChannelData(c)[i];
      out[i] = s / ch;
    }
    return out;
  }

  function LiveAudioPublisher(token) {
    this.token = token;
    this.ws = null;
    this.ctx = null;
    this.procNodes = [];
    this.workletNodes = [];
  }

  LiveAudioPublisher.prototype.start = function (pageStream, micStream) {
    this.stop();
    var tok = this.token;
    var hasPage = pageStream && pageStream.getAudioTracks && pageStream.getAudioTracks().length;
    var hasMic = micStream && micStream.getAudioTracks && micStream.getAudioTracks().length;
    if (!hasPage && !hasMic) return;

    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    var self = this;
    var wsUrl = wsBase() + '/api/ws/live/audio/publish';
    if (tok) wsUrl += '?token=' + encodeURIComponent(tok);
    this.ws = new WebSocket(wsUrl);
    this.ws.binaryType = 'arraybuffer';

    this.ws.onopen = function () {
      try {
        self.ws.send(
          JSON.stringify({ type: 'audio_cfg', sample_rate: self.ctx.sampleRate })
        );
      } catch (e) {}
    };

    function sendPcm(chId, f32) {
      var pcm = floatToInt16(f32);
      var buf = new Uint8Array(1 + pcm.byteLength);
      buf[0] = chId;
      buf.set(new Uint8Array(pcm.buffer), 1);
      if (self.ws && self.ws.readyState === WebSocket.OPEN) {
        try {
          self.ws.send(buf.buffer);
        } catch (err) {}
      }
    }

    function wireStreamScript(stream, chId) {
      if (!stream || !stream.getAudioTracks().length) return;
      var src = self.ctx.createMediaStreamSource(stream);
      var inch = Math.min(2, Math.max(1, src.channelCount || 1));
      var proc = self.ctx.createScriptProcessor(4096, inch, 1);
      var gain = self.ctx.createGain();
      gain.gain.value = 0;
      src.connect(proc);
      proc.connect(gain);
      gain.connect(self.ctx.destination);
      proc.onaudioprocess = function (e) {
        var mono = downmixMono(e.inputBuffer);
        sendPcm(chId, mono);
      };
      self.procNodes.push({ proc: proc, src: src, gain: gain });
    }

    function wireStreamWorklet(stream, chId) {
      if (!stream || !stream.getAudioTracks().length) return;
      var src = self.ctx.createMediaStreamSource(stream);
      var node = new AudioWorkletNode(self.ctx, 'live-audio-capture');
      var gain = self.ctx.createGain();
      gain.gain.value = 0;
      src.connect(node);
      node.connect(gain);
      gain.connect(self.ctx.destination);
      node.port.onmessage = function (ev) {
        var ab = ev.data;
        if (!ab) return;
        sendPcm(chId, new Float32Array(ab));
      };
      self.workletNodes.push({ node: node, src: src, gain: gain });
    }

    function startScriptFallback() {
      wireStreamScript(pageStream, CH_PAGE);
      wireStreamScript(micStream, CH_MIC);
    }

    if (this.ctx.audioWorklet && typeof AudioWorkletNode !== 'undefined') {
      this.ctx.audioWorklet
        .addModule(CAPTURE_WORKLET_URL)
        .then(function () {
          wireStreamWorklet(pageStream, CH_PAGE);
          wireStreamWorklet(micStream, CH_MIC);
        })
        .catch(function () {
          startScriptFallback();
        });
    } else {
      startScriptFallback();
    }
  };

  LiveAudioPublisher.prototype.stop = function () {
    this.workletNodes.forEach(function (n) {
      try {
        n.node.disconnect();
        n.src.disconnect();
        n.gain.disconnect();
      } catch (e) {}
    });
    this.workletNodes = [];
    this.procNodes.forEach(function (n) {
      try {
        n.proc.disconnect();
        n.src.disconnect();
        n.gain.disconnect();
      } catch (e) {}
    });
    this.procNodes = [];
    if (this.ws) {
      try {
        this.ws.close();
      } catch (e) {}
      this.ws = null;
    }
    if (this.ctx) {
      var c = this.ctx;
      this.ctx = null;
      c.close().catch(function () {});
    }
  };

  function LiveAudioViewer(username) {
    this.username = username;
    this.ws = null;
    this.ctx = null;
    this.proc = null;
    this.playbackNode = null;
    this.gainPage = 1;
    this.gainMic = 1;
    this.qPage = [];
    this.qMic = [];
    this.offPage = 0;
    this.offMic = 0;
  }

  LiveAudioViewer.prototype._trim = function (q) {
    while (q.length > MAX_QUEUES) q.shift();
  };

  LiveAudioViewer.prototype._pullSample = function (which) {
    var q = which === 0 ? this.qPage : this.qMic;
    var off = which === 0 ? this.offPage : this.offMic;
    while (q.length && off >= q[0].length) {
      q.shift();
      off = 0;
    }
    if (which === 0) this.offPage = off;
    else this.offMic = off;
    if (!q.length) return 0;
    var arr = q[0];
    var v = arr[off] / 32768;
    if (which === 0) this.offPage++;
    else this.offMic++;
    return v;
  };

  LiveAudioViewer.prototype.setGains = function (playPage, playMic) {
    this.gainPage = playPage ? 1 : 0;
    this.gainMic = playMic ? 1 : 0;
    if (this.playbackNode && this.playbackNode.port) {
      try {
        this.playbackNode.port.postMessage({ type: 'gains', page: playPage, mic: playMic });
      } catch (e) {}
    }
  };

  LiveAudioViewer.prototype.start = function () {
    this.stop();
    var self = this;
    var un = this.username;
    if (!un) return;
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this._silentOsc = null;
    var pending = [];

    this._pushFallbackQueue = function (ch, copy) {
      if (ch === CH_PAGE) {
        self.qPage.push(copy);
        self._trim(self.qPage);
      } else if (ch === CH_MIC) {
        self.qMic.push(copy);
        self._trim(self.qMic);
      }
    };

    function postToWorklet(ch, copy) {
      var ab = copy.buffer.slice(copy.byteOffset, copy.byteOffset + copy.byteLength);
      self.playbackNode.port.postMessage({ type: 'push', ch: ch, buffer: ab }, [ab]);
    }

    function routeChunk(ch, copy) {
      if (self.playbackNode && self.playbackNode.port) {
        try {
          postToWorklet(ch, copy);
        } catch (e) {
          self._pushFallbackQueue(ch, copy);
        }
      } else if (self.proc) {
        self._pushFallbackQueue(ch, copy);
      } else {
        pending.push({ ch: ch, copy: copy });
      }
    }

    function flushPending() {
      var i;
      for (i = 0; i < pending.length; i++) {
        var item = pending[i];
        if (self.playbackNode && self.playbackNode.port) {
          try {
            postToWorklet(item.ch, item.copy);
          } catch (e) {
            self._pushFallbackQueue(item.ch, item.copy);
          }
        } else if (self.proc) {
          self._pushFallbackQueue(item.ch, item.copy);
        }
      }
      pending = [];
    }

    this.ws = new WebSocket(wsBase() + '/api/ws/live/audio/watch/' + encodeURIComponent(un));
    this.ws.binaryType = 'arraybuffer';
    this.ws.onmessage = function (ev) {
      if (typeof ev.data === 'string') {
        try {
          JSON.parse(ev.data);
        } catch (e) {}
        return;
      }
      var u8 = new Uint8Array(ev.data);
      if (u8.length < 3) return;
      var ch = u8[0];
      var samples = (u8.length - 1) >> 1;
      if (samples <= 0) return;
      var pcm = new Int16Array(u8.buffer, u8.byteOffset + 1, samples);
      var copy = new Int16Array(pcm.length);
      copy.set(pcm);
      routeChunk(ch, copy);
    };

    function startScriptPlayback() {
      var proc;
      try {
        proc = self.ctx.createScriptProcessor(2048, 0, 1);
      } catch (e1) {
        proc = null;
      }
      if (!proc) {
        try {
          proc = self.ctx.createScriptProcessor(2048, 1, 1);
        } catch (e2) {
          return;
        }
      }
      self.proc = proc;
      if (proc.numberOfInputs > 0) {
        var sg = self.ctx.createGain();
        sg.gain.value = 0;
        var osc = self.ctx.createOscillator();
        osc.frequency.value = 20;
        osc.connect(sg);
        sg.connect(proc);
        osc.start();
        self._silentOsc = osc;
      }
      proc.onaudioprocess = function (e) {
        var out = e.outputBuffer.getChannelData(0);
        var n = out.length;
        var j;
        for (j = 0; j < n; j++) {
          var sum =
            self._pullSample(0) * self.gainPage + self._pullSample(1) * self.gainMic;
          if (sum > 1) sum = 1;
          if (sum < -1) sum = -1;
          out[j] = sum;
        }
      };
      proc.connect(self.ctx.destination);
      flushPending();
    }

    if (this.ctx.audioWorklet && typeof AudioWorkletNode !== 'undefined') {
      this.ctx.audioWorklet
        .addModule(PLAYBACK_WORKLET_URL)
        .then(function () {
          var node = new AudioWorkletNode(self.ctx, 'live-audio-playback');
          node.port.postMessage({
            type: 'gains',
            page: self.gainPage === 1,
            mic: self.gainMic === 1,
          });
          node.connect(self.ctx.destination);
          self.playbackNode = node;
          flushPending();
        })
        .catch(function () {
          startScriptPlayback();
        });
    } else {
      startScriptPlayback();
    }
  };

  LiveAudioViewer.prototype.stop = function () {
    if (this._silentOsc) {
      try {
        this._silentOsc.stop();
        this._silentOsc.disconnect();
      } catch (e) {}
      this._silentOsc = null;
    }
    if (this.ws) {
      try {
        this.ws.close();
      } catch (e) {}
      this.ws = null;
    }
    if (this.playbackNode) {
      try {
        this.playbackNode.disconnect();
      } catch (e) {}
      this.playbackNode = null;
    }
    if (this.proc) {
      try {
        this.proc.disconnect();
      } catch (e) {}
      this.proc = null;
    }
    if (this.ctx) {
      var c = this.ctx;
      this.ctx = null;
      c.close().catch(function () {});
    }
    this.qPage = [];
    this.qMic = [];
    this.offPage = 0;
    this.offMic = 0;
  };

  LiveAudioViewer.prototype.unlock = function () {
    if (this.ctx && this.ctx.state === 'suspended') return this.ctx.resume();
    return Promise.resolve();
  };

  global.USKingLiveAudio = {
    CH_PAGE: CH_PAGE,
    CH_MIC: CH_MIC,
    wsBase: wsBase,
    Publisher: LiveAudioPublisher,
    Viewer: LiveAudioViewer,
  };
})(typeof window !== 'undefined' ? window : globalThis);
