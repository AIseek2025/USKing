(function (global) {
  'use strict';

  var SCRIPT_URL = 'https://cdn.jsdelivr.net/npm/hls.js@1.5.18/dist/hls.min.js';
  var MEDIA_ERROR_RECOVERY_LIMIT = 1;

  function loadScript() {
    if (global.Hls) return Promise.resolve(global.Hls);
    return new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = SCRIPT_URL;
      s.async = true;
      s.onload = function () {
        if (global.Hls) resolve(global.Hls);
        else reject(new Error('Hls.js loaded but unavailable'));
      };
      s.onerror = function () {
        reject(new Error('Failed to load hls.js'));
      };
      document.head.appendChild(s);
    });
  }

  function attach(opts) {
    var video = opts && opts.videoEl;
    var url = opts && opts.url;
    if (!video || !url) return Promise.reject(new Error('missing video/url'));
    video.playsInline = true;
    video.setAttribute('playsinline', 'true');
    function notifyLoaded() {
      if (typeof opts.onLoaded === 'function') opts.onLoaded();
    }
    function notifyError(payload) {
      if (typeof opts.onError === 'function') opts.onError(payload);
    }
    if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = url;
      var onNativeLoaded = function () {
        notifyLoaded();
      };
      var onNativeError = function () {
        notifyError({ fatal: true, message: 'native_hls_error' });
      };
      video.addEventListener('loadeddata', onNativeLoaded);
      video.addEventListener('error', onNativeError);
      return Promise.resolve({
        destroy: function () {
          video.removeEventListener('loadeddata', onNativeLoaded);
          video.removeEventListener('error', onNativeError);
          try {
            video.pause();
          } catch (e) {}
          try {
            video.removeAttribute('src');
            video.load();
          } catch (e) {}
        },
      });
    }
    return loadScript().then(function (Hls) {
      if (!Hls || !Hls.isSupported || !Hls.isSupported()) {
        throw new Error('HLS unsupported');
      }
      var hls = new Hls({
        lowLatencyMode: true,
        backBufferLength: 30,
        enableWorker: true,
      });
      var mediaRecoveries = 0;
      var onLoadedData = function () {
        notifyLoaded();
      };
      video.addEventListener('loadeddata', onLoadedData);
      hls.on(Hls.Events.ERROR, function (_event, data) {
        var payload = {
          fatal: !!(data && data.fatal),
          type: data && data.type,
          details: data && data.details,
          message: data && (data.details || data.type) || 'hls_error',
        };
        notifyError(payload);
        if (!data || !data.fatal) return;
        if (data.type === Hls.ErrorTypes.MEDIA_ERROR && mediaRecoveries < MEDIA_ERROR_RECOVERY_LIMIT) {
          mediaRecoveries += 1;
          try {
            hls.recoverMediaError();
            return;
          } catch (e) {}
        }
        try {
          hls.destroy();
        } catch (e) {}
      });
      hls.loadSource(url);
      hls.attachMedia(video);
      return {
        destroy: function () {
          video.removeEventListener('loadeddata', onLoadedData);
          try {
            hls.destroy();
          } catch (e) {}
          try {
            video.pause();
          } catch (e) {}
        },
      };
    });
  }

  global.USKingHls = {
    attach: attach,
  };
})(typeof window !== 'undefined' ? window : this);
