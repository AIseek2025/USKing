/**
 * USKing — LiveKit WebRTC helper (CDN-loaded livekit-client UMD).
 * Token issued by FastAPI; this file handles Room connect / track pub-sub.
 */
(function (global) {
  'use strict';

  var SCRIPT_URL =
    'https://cdn.jsdelivr.net/npm/livekit-client@2.18.0/dist/livekit-client.umd.min.js';

  var _log = function (tag, msg, extra) {
    var prefix = '[LK:' + tag + ']';
    if (extra !== undefined) {
      console.log(prefix, msg, extra);
    } else {
      console.log(prefix, msg);
    }
  };

  function _isIPv4(host) {
    if (!/^\d{1,3}(?:\.\d{1,3}){3}$/.test(host)) return false;
    var parts = host.split('.');
    for (var i = 0; i < parts.length; i++) {
      var n = Number(parts[i]);
      if (n < 0 || n > 255) return false;
    }
    return true;
  }

  function _isValidHostname(host) {
    if (!host) return false;
    if (_isIPv4(host)) return true;
    if (host.indexOf('[') === 0 && host.lastIndexOf(']') === host.length - 1) return true;
    var labels = host.split('.');
    if (!labels.length) return false;
    for (var i = 0; i < labels.length; i++) {
      var label = labels[i];
      if (!label) return false;
      if (!/^[a-z0-9-]+$/i.test(label)) return false;
      if (label.charAt(0) === '-' || label.charAt(label.length - 1) === '-') return false;
    }
    return true;
  }

  function _extractIceHost(url) {
    var m = String(url || '').match(/^(stun|stuns|turn|turns):(.+)$/i);
    if (!m) return '';
    var rest = m[2].split('?')[0];
    if (!rest) return '';
    if (rest.charAt(0) === '[') {
      var end = rest.indexOf(']');
      return end === -1 ? '' : rest.slice(0, end + 1);
    }
    var idx = rest.lastIndexOf(':');
    return idx === -1 ? rest : rest.slice(0, idx);
  }

  function _normalizeIceUrl(url) {
    var raw = String(url || '');
    var m = raw.match(/^(stun|stuns|turn|turns):(.+)$/i);
    if (!m) return raw;
    var scheme = m[1];
    var restWithQuery = m[2];
    var parts = restWithQuery.split('?');
    var hostPort = parts[0];
    var query = parts.length > 1 ? '?' + parts.slice(1).join('?') : '';
    if (!hostPort) return raw;
    if (hostPort.charAt(0) === '[') return raw;
    var idx = hostPort.lastIndexOf(':');
    var host = idx === -1 ? hostPort : hostPort.slice(0, idx);
    var port = idx === -1 ? '' : hostPort.slice(idx);
    var normalizedHost = host.replace(/[{}\s]/g, '');
    if (normalizedHost !== host) {
      return scheme + ':' + normalizedHost + port + query;
    }
    return raw;
  }

  function _parseIceCandidate(candidate) {
    var text = String(candidate || '');
    var out = { raw: text };
    var m = text.match(/^candidate:\S+\s+\d+\s+(\w+)\s+\d+\s+(\S+)\s+(\d+)\s+typ\s+(\w+)/);
    if (m) {
      out.protocol = m[1];
      out.address = m[2];
      out.port = m[3];
      out.type = m[4];
    }
    return out;
  }

  /**
   * 仅使用后端下发的标准 ice_servers（含 turn/turns + username/credential + 可选 stun）。
   * 未配置时不覆盖 rtcConfig，交给 LiveKit 客户端默认 ICE。
   */
  function _buildRtcConfig(opts) {
    if (opts && opts.rtcConfig) return opts.rtcConfig;
    var raw = opts && Array.isArray(opts.iceServers) ? opts.iceServers : [];
    if (!raw.length) {
      _log('rtc', 'no ice_servers from API; using LiveKit default ICE (no rtcConfig override)');
      return undefined;
    }
    var iceServers = raw
      .map(function (s) {
        if (!s || s.urls == null) return null;
        var urls = Array.isArray(s.urls) ? s.urls.slice() : [s.urls];
        var out = { urls: urls };
        if (s.username != null && s.username !== '') out.username = s.username;
        if (s.credential != null && s.credential !== '') out.credential = s.credential;
        return out;
      })
      .filter(Boolean);
    if (!iceServers.length) return undefined;
    _log(
      'rtc',
      'rtcConfig from API',
      iceServers.map(function (x) {
        return { urls: x.urls, hasAuth: !!(x.username && x.credential) };
      })
    );
    return {
      iceTransportPolicy: 'all',
      iceServers: iceServers,
    };
  }

  function _sanitizeRtcConfig(config) {
    if (!config || !config.iceServers || !config.iceServers.length) return config;
    var copy = {};
    for (var k in config) copy[k] = config[k];
    copy.iceServers = config.iceServers
      .map(function (server) {
        var urls = Array.isArray(server.urls) ? server.urls.slice() : [server.urls];
        var clean = urls
          .map(function (url) {
            var normalized = _normalizeIceUrl(url);
            if (normalized !== url) {
              _log('rtc', 'rewrote ICE url', { before: url, after: normalized });
            }
            return normalized;
          })
          .filter(function (url) {
          var host = _extractIceHost(url);
          var ok = _isValidHostname(host);
          if (!ok) _log('rtc', 'dropping invalid ICE url', { url: url, host: host });
          return ok;
        });
        if (!clean.length) return null;
        var out = {};
        for (var k in server) out[k] = server[k];
        out.urls = clean;
        return out;
      })
      .filter(Boolean);
    _log(
      'rtc',
      'sanitized ice servers',
      copy.iceServers.map(function (s) { return s.urls; })
    );
    return copy;
  }

  function _installRtcDebugShim() {
    if (global.__USKING_RTC_SHIM_INSTALLED) return;
    var NativePC = global.RTCPeerConnection || global.webkitRTCPeerConnection;
    if (!NativePC) return;
    function WrappedRTCPeerConnection(config, constraints) {
      var sanitized = config;
      try {
        sanitized = _sanitizeRtcConfig(config);
      } catch (e) {
        _log('rtc', 'sanitize rtc config failed', e && e.message ? e.message : e);
      }
      try {
        var pc = new NativePC(sanitized, constraints);
        try {
          pc.addEventListener('icecandidate', function (ev) {
            if (!ev || !ev.candidate || !ev.candidate.candidate) return;
            _log('rtc', 'local candidate', _parseIceCandidate(ev.candidate.candidate));
          });
          pc.addEventListener('icecandidateerror', function (ev) {
            _log('rtc', 'ice candidate error', {
              url: ev && ev.url,
              errorCode: ev && ev.errorCode,
              errorText: ev && ev.errorText,
            });
          });
          pc.addEventListener('iceconnectionstatechange', function () {
            _log('rtc', 'ice connection state', pc.iceConnectionState);
          });
          pc.addEventListener('icegatheringstatechange', function () {
            _log('rtc', 'ice gathering state', pc.iceGatheringState);
          });
          pc.addEventListener('connectionstatechange', function () {
            _log('rtc', 'pc connection state', pc.connectionState);
          });
        } catch (e) {}
        return pc;
      } catch (e) {
        _log('rtc', 'RTCPeerConnection construct failed', {
          error: e && e.message ? e.message : String(e),
          iceServers: sanitized && sanitized.iceServers ? sanitized.iceServers.map(function (s) { return s.urls; }) : [],
        });
        throw e;
      }
    }
    WrappedRTCPeerConnection.prototype = NativePC.prototype;
    try {
      Object.setPrototypeOf(WrappedRTCPeerConnection, NativePC);
    } catch (e) {}
    global.RTCPeerConnection = WrappedRTCPeerConnection;
    global.__USKING_RTC_SHIM_INSTALLED = true;
  }

  function getLib() {
    var L = global.LivekitClient || global.livekit;
    if (!L || !L.Room) {
      throw new Error('livekit-client not loaded');
    }
    return L;
  }

  function loadScript() {
    _installRtcDebugShim();
    if (global.LivekitClient || global.livekit) {
      return Promise.resolve();
    }
    return new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = SCRIPT_URL;
      s.async = true;
      s.onload = function () {
        _log('load', 'livekit-client loaded', (global.LivekitClient || global.livekit).version || 'unknown');
        resolve();
      };
      s.onerror = function () {
        reject(new Error('Failed to load livekit-client from CDN'));
      };
      document.head.appendChild(s);
    });
  }

  function _closeHostResources(room) {
    if (room && room.__uskingCleanup) {
      try {
        room.__uskingCleanup();
      } catch (e) {}
      room.__uskingCleanup = null;
    }
  }

  function _buildMixedAudio(opts, Track) {
    var pageTrack = opts.audioPageTrack;
    var micTrack = opts.audioMicTrack;
    var singleTrack = opts.audioTrack;
    var liveTracks = [];
    if (pageTrack && pageTrack.readyState === 'live') {
      liveTracks.push({ track: pageTrack, kind: 'page' });
    }
    if (micTrack && micTrack.readyState === 'live') {
      liveTracks.push({ track: micTrack, kind: 'mic' });
    }
    if (!liveTracks.length && singleTrack && singleTrack.readyState === 'live') {
      return Promise.resolve({
        track: singleTrack,
        name: 'audio',
        source: Track && Track.Source ? Track.Source.Microphone : undefined,
        cleanup: function () {},
      });
    }
    if (!liveTracks.length) {
      return Promise.resolve(null);
    }
    var Ctx = global.AudioContext || global.webkitAudioContext;
    if (!Ctx) {
      _log('host', 'AudioContext unavailable, fallback to raw audio track');
      return Promise.resolve({
        track: liveTracks[0].track,
        name: liveTracks.length > 1 ? 'audio' : liveTracks[0].kind,
        source: Track && Track.Source ? Track.Source.Microphone : undefined,
        cleanup: function () {},
      });
    }
    var ctx = new Ctx();
    var dest = ctx.createMediaStreamDestination();
    var compressor = ctx.createDynamicsCompressor();
    compressor.threshold.setValueAtTime(-24, ctx.currentTime);
    compressor.knee.setValueAtTime(12, ctx.currentTime);
    compressor.ratio.setValueAtTime(8, ctx.currentTime);
    compressor.attack.setValueAtTime(0.003, ctx.currentTime);
    compressor.release.setValueAtTime(0.15, ctx.currentTime);
    compressor.connect(dest);
    var nodes = [];
    var multi = liveTracks.length > 1;
    liveTracks.forEach(function (item) {
      var src = ctx.createMediaStreamSource(new MediaStream([item.track]));
      var gain = ctx.createGain();
      gain.gain.value = multi ? 0.7 : 0.9;
      var lastNode = src;
      if (item.kind === 'mic') {
        var hp = ctx.createBiquadFilter();
        hp.type = 'highpass';
        hp.frequency.value = 80;
        hp.Q.value = 0.7;
        lastNode.connect(hp);
        lastNode = hp;
      }
      lastNode.connect(gain);
      gain.connect(compressor);
      nodes.push({ src: src, gain: gain });
    });
    var mixedTrack = dest.stream.getAudioTracks()[0];
    if (!mixedTrack) {
      nodes.forEach(function (item) {
        try {
          item.src.disconnect();
          item.gain.disconnect();
        } catch (e) {}
      });
      try { compressor.disconnect(); } catch (e) {}
      ctx.close().catch(function () {});
      return Promise.resolve({
        track: liveTracks[0].track,
        name: liveTracks.length > 1 ? 'audio' : liveTracks[0].kind,
        source: Track && Track.Source ? Track.Source.Microphone : undefined,
        cleanup: function () {},
      });
    }
    return Promise.resolve({
      track: mixedTrack,
      name: liveTracks.length > 1 ? 'audio' : liveTracks[0].kind,
      source:
        liveTracks.length > 1
          ? Track && Track.Source
            ? Track.Source.Microphone
            : undefined
          : liveTracks[0].kind === 'page'
            ? Track && Track.Source && Track.Source.ScreenShareAudio !== undefined
              ? Track.Source.ScreenShareAudio
              : Track && Track.Source
                ? Track.Source.ScreenShare
                : undefined
            : Track && Track.Source
              ? Track.Source.Microphone
              : undefined,
      cleanup: function () {
        try {
          mixedTrack.stop();
        } catch (e) {}
        nodes.forEach(function (item) {
          try {
            item.src.disconnect();
            item.gain.disconnect();
          } catch (e) {}
        });
        try { compressor.disconnect(); } catch (e) {}
        ctx.close().catch(function () {});
      },
    });
  }

  function _wireRoomDebug(room, tag) {
    var L = getLib();
    var RE = L.RoomEvent;
    room.on(RE.SignalConnected, function () { _log(tag, 'signal connected'); });
    room.on(RE.Connected, function () { _log(tag, 'room connected'); });
    room.on(RE.Disconnected, function (reason) { _log(tag, 'room disconnected', reason); });
    room.on(RE.Reconnecting, function () { _log(tag, 'reconnecting…'); });
    room.on(RE.Reconnected, function () { _log(tag, 'reconnected'); });
    room.on(RE.SignalReconnecting, function () { _log(tag, 'signal reconnecting…'); });
    room.on(RE.MediaDevicesError, function (e) { _log(tag, 'media device error', e); });
    room.on(RE.ConnectionQualityChanged, function (q, p) {
      if (p && p.isLocal) _log(tag, 'local quality', q);
    });
  }

  function viewerConnect(opts) {
    return loadScript().then(function () {
      var L = getLib();
      var Room = L.Room;
      var RoomEvent = L.RoomEvent;
      var room = new Room({
        adaptiveStream: true,
        dynacast: true,
        disconnectOnPageLeave: true,
      });
      _wireRoomDebug(room, 'viewer');
      var videoEl = opts.videoEl;
      var url = opts.url;
      var token = opts.token;
      var connectOpts = {};
      var rtcConfig = _buildRtcConfig(opts);
      if (rtcConfig) connectOpts.rtcConfig = rtcConfig;
      if (opts.peerConnectionTimeout) connectOpts.peerConnectionTimeout = opts.peerConnectionTimeout;
      var firstVideo = false;

      function attachIfRemote(track, participant, publication) {
        if (!participant || participant.isLocal) return;
        if (opts.onTrackSubscribed) {
          try { opts.onTrackSubscribed(track, publication, participant); } catch (e) {}
        }
        if (track.kind === 'video' && videoEl) {
          track.attach(videoEl);
          videoEl.style.display = '';
          if (!firstVideo && opts.onFirstFrame) {
            firstVideo = true;
            try { opts.onFirstFrame(); } catch (e) {}
          }
        }
        if (track.kind === 'audio') {
          var a = track.attach();
          a.style.position = 'absolute';
          a.style.width = '1px';
          a.style.height = '1px';
          a.style.opacity = '0';
          a.style.pointerEvents = 'none';
          a.autoplay = true;
          a.playsInline = true;
          a.setAttribute('playsinline', 'true');
          a.muted = true;
          a.dataset.lkTrackKind = 'audio';
          a.dataset.lkTrackName =
            (publication && (publication.trackName || publication.name)) || '';
          (videoEl && videoEl.parentNode ? videoEl.parentNode : document.body).appendChild(a);
          if (opts.onAudioTrack) {
            try { opts.onAudioTrack(track, publication, participant, a); } catch (e) {}
          }
          a.play().catch(function (err) {
            if (opts.onAudioPlaybackBlocked) {
              try { opts.onAudioPlaybackBlocked(err, track, publication, participant, a); } catch (e) {}
            }
          });
        }
      }

      room.on(RoomEvent.TrackSubscribed, function (track, publication, participant) {
        _log('viewer', 'track subscribed', { kind: track.kind, name: publication && publication.trackName });
        attachIfRemote(track, participant, publication);
      });

      room.on(RoomEvent.Disconnected, function (reason) {
        _log('viewer', 'disconnected callback', reason);
        if (opts.onDisconnected) {
          try { opts.onDisconnected(reason); } catch (e) {}
        }
      });

      _log('viewer', 'connecting…', url);
      return room.connect(url, token, connectOpts).then(function () {
        _log('viewer', 'connected OK, remote participants:', room.remoteParticipants.size);
        room.remoteParticipants.forEach(function (p) {
          p.trackPublications.forEach(function (pub) {
            if (pub.track) attachIfRemote(pub.track, p, pub);
          });
        });
        if (opts.onConnected) {
          try { opts.onConnected(room); } catch (e) {}
        }
        return room;
      });
    });
  }

  function hostConnect(opts) {
    return loadScript().then(function () {
      var L = getLib();
      var Room = L.Room;
      var Track = L.Track;
      var room = new Room({ disconnectOnPageLeave: true });
      _wireRoomDebug(room, 'host');
      room.on(L.RoomEvent.Disconnected, function () {
        _closeHostResources(room);
      });
      var connectOpts = {};
      var rtcConfig = _buildRtcConfig(opts);
      if (rtcConfig) connectOpts.rtcConfig = rtcConfig;
      if (opts.peerConnectionTimeout) connectOpts.peerConnectionTimeout = opts.peerConnectionTimeout;

      _log('host', 'connecting…', opts.url);
      return room.connect(opts.url, opts.token, connectOpts).then(function () {
        _log('host', 'connected OK, publishing tracks…');
        var pubOpts = { name: 'program', simulcast: true };
        if (Track && Track.Source) {
          pubOpts.source = Track.Source.ScreenShare;
        }
        function publishAudio(track, name, source) {
          if (!track || track.readyState !== 'live') {
            return Promise.resolve();
          }
          var aopts = { name: name };
          if (Track && Track.Source && source) aopts.source = source;
          _log('host', 'publishing audio track: ' + name);
          return room.localParticipant.publishTrack(track, aopts);
        }
        var chain = Promise.resolve();
        if (opts.videoTrack && opts.videoTrack.readyState === 'live') {
          _log('host', 'publishing video track');
          chain = room.localParticipant.publishTrack(opts.videoTrack, pubOpts);
        }
        return chain
          .then(function () {
            return _buildMixedAudio(opts, Track).then(function (mixed) {
              if (!mixed || !mixed.track || mixed.track.readyState !== 'live') {
                _log('host', 'no live audio track available to publish');
                return;
              }
              room.__uskingCleanup = mixed.cleanup;
              _log('host', 'publishing mixed audio track', mixed.name);
              return publishAudio(mixed.track, mixed.name, mixed.source);
            });
          })
          .then(function () {
            _log('host', 'all tracks published');
            return room;
          });
      });
    });
  }

  function disconnect(room) {
    if (room && typeof room.disconnect === 'function') {
      _closeHostResources(room);
      try { room.disconnect(); } catch (e) {}
    }
  }

  global.USKingLiveKit = {
    loadScript: loadScript,
    viewerConnect: viewerConnect,
    hostConnect: hostConnect,
    disconnect: disconnect,
  };
})(typeof window !== 'undefined' ? window : this);
