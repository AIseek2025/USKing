/**
 * USKing 主播端统一发布 SDK（Phase B）。
 * 依赖：先加载 livekit-usking.js（USKingLiveKit）。
 */
(function (global) {
  'use strict';

  function wantManagedLiveKit(cfg) {
    return !!(
      cfg &&
      cfg.planes &&
      cfg.planes.interactive &&
      cfg.planes.interactive.enabled &&
      cfg.livekit &&
      cfg.livekit.ready &&
      (cfg.publish_mode === 'webrtc' || cfg.publish_mode === 'livekit')
    );
  }

  /**
   * @param {object} opts
   * @param {HTMLCanvasElement} opts.canvasEl
   * @param {function(): Promise<object>} opts.loadConfig
   * @param {function(): Promise<object>} opts.loadHostSession
   * @param {MediaStreamTrack|null} [opts.audioPageTrack]
   * @param {MediaStreamTrack|null} [opts.audioMicTrack]
   * @param {number} [opts.captureFps]
   * @param {number} [opts.peerConnectionTimeout]
   * @param {boolean} [opts.skipCanvasSizeCheck]
   * @param {boolean} [opts.allowMissingVideoTrack] 独立页可在无画轨时静默跳过
   * @param {boolean} [opts.requireLiveVideoTrack]
   * @param {string} [opts.noVideoMessage]
   * @param {boolean} [opts.showError]
   * @param {HTMLElement|null} [opts.errorEl]
   * @param {string} [opts.errorPrefix]
   * @param {function} [opts.onConnected] (room, session, rawHs)
   * @param {function} [opts.onError]
   */
  async function connectHostRealtime(opts) {
    opts = opts || {};
    var cv = opts.canvasEl;
    if (!cv || (!opts.skipCanvasSizeCheck && !cv.width)) {
      return { room: null, used: false };
    }
    if (typeof USKingLiveKit === 'undefined') {
      return { room: null, used: false };
    }
    try {
      var cfg = await opts.loadConfig();
      if (!wantManagedLiveKit(cfg)) {
        return { room: null, used: false };
      }
      var hs = await opts.loadHostSession();
      var session = hs && hs.session ? hs.session : hs;
      var lk = session && session.livekit;
      if (!lk || !lk.token) {
        return { room: null, used: false };
      }
      await USKingLiveKit.loadScript();
      var fps = opts.captureFps || 30;
      var cap = cv.captureStream(fps);
      var vtrack = cap.getVideoTracks && cap.getVideoTracks()[0];
      if (!vtrack) {
        if (opts.allowMissingVideoTrack) {
          return { room: null, used: false };
        }
        throw new Error(opts.noVideoMessage || '当前页还没有可发布的视频轨');
      }
      var needLive = opts.requireLiveVideoTrack !== false;
      if (needLive && vtrack.readyState !== 'live') {
        throw new Error(opts.noVideoMessage || '当前页还没有可发布的视频轨');
      }
      var ice =
        (session && session.ice_servers) ||
        (session && session.livekit && session.livekit.ice_servers) ||
        [];
      var room = await USKingLiveKit.hostConnect({
        url: lk.ws_url,
        token: lk.token,
        videoTrack: vtrack,
        audioPageTrack: opts.audioPageTrack || null,
        audioMicTrack: opts.audioMicTrack || null,
        iceServers: ice,
        peerConnectionTimeout: opts.peerConnectionTimeout || 25000,
      });
      if (typeof opts.onConnected === 'function') {
        opts.onConnected(room, session, hs);
      }
      return { room: room, used: true, session: session, raw: hs };
    } catch (e) {
      if (opts.showError !== false && opts.errorEl) {
        opts.errorEl.textContent =
          (opts.errorPrefix || 'WebRTC: ') + (e && e.message ? e.message : '连接失败，暂时回退');
        opts.errorEl.style.display = 'block';
      }
      if (typeof opts.onError === 'function') {
        opts.onError(e);
      }
      console.error('[USKingLiveHost] connectHostRealtime', e);
      return { room: null, used: false, error: e };
    }
  }

  global.USKingLiveHost = {
    wantManagedLiveKit: wantManagedLiveKit,
    connectHostRealtime: connectHostRealtime,
  };
})(typeof window !== 'undefined' ? window : this);
