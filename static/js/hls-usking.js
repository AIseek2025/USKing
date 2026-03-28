(function (global) {
  'use strict';

  var SCRIPT_URL = 'https://cdn.jsdelivr.net/npm/hls.js@1.5.18/dist/hls.min.js';

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
    if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = url;
      return Promise.resolve({
        destroy: function () {
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
      hls.loadSource(url);
      hls.attachMedia(video);
      return {
        destroy: function () {
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
