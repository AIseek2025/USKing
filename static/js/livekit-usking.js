/**
 * USKing — LiveKit WebRTC 辅助（CDN 加载 livekit-client UMD）。
 * 业务仍由 FastAPI 发 token；此处仅负责浏览器 Room 连接与轨发布/订阅。
 */
(function (global) {
  'use strict';

  var SCRIPT_URL =
    'https://cdn.jsdelivr.net/npm/livekit-client@2.5.8/dist/livekit-client.umd.min.js';

  function getLib() {
    var L = global.LivekitClient || global.livekit;
    if (!L || !L.Room) {
      throw new Error('livekit-client 未加载');
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
        resolve();
      };
      s.onerror = function () {
        reject(new Error('无法加载 livekit-client'));
      };
      document.head.appendChild(s);
    });
  }

  /**
   * @param {{ url: string, token: string, videoEl: HTMLVideoElement|null, onConnected?: function, onError?: function, onTrackSubscribed?: function, onAudioTrack?: function, onAudioPlaybackBlocked?: function }} opts
   * @returns {Promise<object>} room
   */
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
      var videoEl = opts.videoEl;
      var url = opts.url;
      var token = opts.token;
      var firstVideo = false;

      function attachIfRemote(track, participant, publication) {
        if (!participant || participant.isLocal) return;
        if (opts.onTrackSubscribed) {
          try {
            opts.onTrackSubscribed(track, publication, participant);
          } catch (e) {}
        }
        if (track.kind === 'video' && videoEl) {
          track.attach(videoEl);
          videoEl.style.display = '';
          if (!firstVideo && opts.onFirstFrame) {
            firstVideo = true;
            try {
              opts.onFirstFrame();
            } catch (e) {}
          }
        }
        if (track.kind === 'audio') {
          var a = track.attach();
          a.style.display = 'none';
          a.dataset.lkTrackKind = 'audio';
          a.dataset.lkTrackName =
            (publication && (publication.trackName || publication.name)) || '';
          (videoEl && videoEl.parentNode ? videoEl.parentNode : document.body).appendChild(a);
          if (opts.onAudioTrack) {
            try {
              opts.onAudioTrack(track, publication, participant, a);
            } catch (e) {}
          }
          a.play().catch(function (err) {
            if (opts.onAudioPlaybackBlocked) {
              try {
                opts.onAudioPlaybackBlocked(err, track, publication, participant, a);
              } catch (e) {}
            }
          });
        }
      }

      room.on(RoomEvent.TrackSubscribed, function (track, publication, participant) {
        attachIfRemote(track, participant, publication);
      });

      room.on(RoomEvent.Disconnected, function () {
        if (opts.onDisconnected) {
          try {
            opts.onDisconnected();
          } catch (e) {}
        }
      });

      return room.connect(url, token).then(function () {
        room.remoteParticipants.forEach(function (p) {
          p.trackPublications.forEach(function (pub) {
            if (pub.track) {
              attachIfRemote(pub.track, p, pub);
            }
          });
        });
        if (opts.onConnected) {
          try {
            opts.onConnected(room);
          } catch (e) {}
        }
        return room;
      });
    });
  }

  /**
   * @param {{ url: string, token: string, videoTrack?: MediaStreamTrack, audioTrack?: MediaStreamTrack, audioPageTrack?: MediaStreamTrack, audioMicTrack?: MediaStreamTrack }} opts
   * audioPageTrack / audioMicTrack：双音轨（网页/系统音 与 麦克风）；与 audioTrack 互斥时优先双轨。
   */
  function hostConnect(opts) {
    return loadScript().then(function () {
      var L = getLib();
      var Room = L.Room;
      var Track = L.Track;
      var room = new Room({ disconnectOnPageLeave: true });
      return room.connect(opts.url, opts.token).then(function () {
        var pubOpts = { name: 'program', simulcast: true };
        if (Track && Track.Source) {
          pubOpts.source = Track.Source.ScreenShare;
        }
        function publishAudio(track, name, source) {
          if (!track || track.readyState !== 'live') {
            return Promise.resolve();
          }
          var aopts = { name: name };
          if (Track && Track.Source && source) {
            aopts.source = source;
          }
          return room.localParticipant.publishTrack(track, aopts);
        }
        var chain = Promise.resolve();
        if (opts.videoTrack && opts.videoTrack.readyState === 'live') {
          chain = room.localParticipant.publishTrack(opts.videoTrack, pubOpts);
        }
        return chain
          .then(function () {
            if (opts.audioPageTrack || opts.audioMicTrack) {
              var pageSrc =
                Track && Track.Source && Track.Source.ScreenShareAudio !== undefined
                  ? Track.Source.ScreenShareAudio
                  : Track && Track.Source
                    ? Track.Source.ScreenShare
                    : undefined;
              return publishAudio(opts.audioPageTrack, 'page', pageSrc).then(function () {
                return publishAudio(
                  opts.audioMicTrack,
                  'mic',
                  Track && Track.Source ? Track.Source.Microphone : undefined
                );
              });
            }
            if (opts.audioTrack && opts.audioTrack.readyState === 'live') {
              return publishAudio(
                opts.audioTrack,
                'audio',
                Track && Track.Source ? Track.Source.Microphone : undefined
              );
            }
          })
          .then(function () {
            return room;
          });
      });
    });
  }

  function disconnect(room) {
    if (room && typeof room.disconnect === 'function') {
      try {
        room.disconnect();
      } catch (e) {}
    }
  }

  global.USKingLiveKit = {
    loadScript: loadScript,
    viewerConnect: viewerConnect,
    hostConnect: hostConnect,
    disconnect: disconnect,
  };
})(typeof window !== 'undefined' ? window : this);
