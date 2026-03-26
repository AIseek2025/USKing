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

  function getLib() {
    var L = global.LivekitClient || global.livekit;
    if (!L || !L.Room) {
      throw new Error('livekit-client not loaded');
    }
    return L;
  }

  function loadScript() {
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
      return room.connect(url, token).then(function () {
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

      _log('host', 'connecting…', opts.url);
      return room.connect(opts.url, opts.token).then(function () {
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
            if (opts.audioPageTrack || opts.audioMicTrack) {
              var pageSrc =
                Track && Track.Source && Track.Source.ScreenShareAudio !== undefined
                  ? Track.Source.ScreenShareAudio
                  : Track && Track.Source ? Track.Source.ScreenShare : undefined;
              return publishAudio(opts.audioPageTrack, 'page', pageSrc).then(function () {
                return publishAudio(
                  opts.audioMicTrack, 'mic',
                  Track && Track.Source ? Track.Source.Microphone : undefined
                );
              });
            }
            if (opts.audioTrack && opts.audioTrack.readyState === 'live') {
              return publishAudio(
                opts.audioTrack, 'audio',
                Track && Track.Source ? Track.Source.Microphone : undefined
              );
            }
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
