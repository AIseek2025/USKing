from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import jwt

from .config import (
    LIVE_FALLBACK_MODE,
    LIVE_FALLBACK_ENABLED,
    LIVE_HLS_BASE_URL,
    LIVE_MEDIA_BACKEND,
    LIVE_PLAYBACK_MODE,
    LIVE_PUBLISH_MODE,
    LIVE_SIGNALING_URL,
    LIVE_TURN_URLS,
    LIVEKIT_API_KEY,
    LIVEKIT_API_SECRET,
    LIVEKIT_WS_URL,
    TURN_CREDENTIAL_TTL_SECONDS,
    TURN_ENABLED,
    TURN_REALM,
    TURN_SHARED_SECRET,
    TURN_STUN_URLS,
    TURN_TLS_URL,
    TURN_UDP_URL,
)
from .models import LiveStream, User


def room_name_for_username(username: str) -> str:
    return f"usking-live-{(username or '').strip()}"


def hls_manifest_for_username(username: str) -> str:
    base = (LIVE_HLS_BASE_URL or "").rstrip("/")
    if not base:
        return ""
    return f"{base}/{(username or '').strip()}/master.m3u8"


def legacy_transport_for_username(username: str) -> dict[str, Any]:
    un = (username or "").strip()
    return {
        "video": {
            "publish": "/api/live/push-frame",
            "poll": f"/api/live/last-frame/{un}",
            "mjpeg": f"/api/live/mjpeg/{un}",
        },
        "audio": {
            "publish_ws": "/api/ws/live/audio/publish",
            "watch_ws": f"/api/ws/live/audio/watch/{un}",
        },
    }


def livekit_ready() -> bool:
    return bool(LIVEKIT_WS_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET)


def turn_configured() -> bool:
    """独立 coturn：需启用开关、共享密钥，且至少配置一条 TURN URL。"""
    if not TURN_ENABLED or not TURN_SHARED_SECRET:
        return False
    return bool(TURN_UDP_URL or TURN_TLS_URL)


def _turn_rest_credential(secret: str, username: str) -> str:
    """coturn static-auth-secret：password = base64(hmac_sha1(secret, username))。"""
    digest = hmac.new(
        secret.encode("utf-8"), username.encode("utf-8"), hashlib.sha1
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def build_turn_ice_servers(identity: str) -> list[dict[str, Any]]:
    """
    生成浏览器 RTCPeerConnection.iceServers 兼容结构。
    identity 建议使用稳定字符串（如 host:uid / viewer:uid / anon:...），与 coturn 审计一致。
    """
    if not turn_configured():
        return []
    urls: list[str] = []
    if TURN_UDP_URL:
        urls.append(TURN_UDP_URL)
    if TURN_TLS_URL:
        urls.append(TURN_TLS_URL)
    if not urls:
        return []
    expiry = int(time.time()) + max(60, TURN_CREDENTIAL_TTL_SECONDS)
    uname = f"{expiry}:{identity}"
    cred = _turn_rest_credential(TURN_SHARED_SECRET, uname)
    servers: list[dict[str, Any]] = [
        {"urls": urls, "username": uname, "credential": cred}
    ]
    for stun in TURN_STUN_URLS:
        servers.append({"urls": [stun]})
    return servers


def _livekit_token(
    *,
    identity: str,
    room: str,
    can_publish: bool,
    can_subscribe: bool,
    can_publish_data: bool = True,
    name: str = "",
    metadata: Optional[dict[str, Any]] = None,
    ttl_hours: int = 6,
) -> str:
    now = datetime.now(timezone.utc)
    meta = metadata or {}
    payload = {
        "iss": LIVEKIT_API_KEY,
        "sub": identity,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(hours=ttl_hours)).timestamp()),
        "name": name or identity,
        "metadata": json.dumps(meta) if meta else "{}",
        "video": {
            "roomJoin": True,
            "room": room,
            "canPublish": can_publish,
            "canSubscribe": can_subscribe,
            "canPublishData": can_publish_data,
        },
    }
    return jwt.encode(payload, LIVEKIT_API_SECRET, algorithm="HS256")


def media_backend_summary() -> dict[str, Any]:
    livekit_ok = livekit_ready()
    preferred_realtime = (
        "webrtc"
        if LIVE_MEDIA_BACKEND == "livekit" and livekit_ok and LIVE_PLAYBACK_MODE == "webrtc"
        else LIVE_PLAYBACK_MODE
    )
    tc = turn_configured()
    return {
        "backend": LIVE_MEDIA_BACKEND,
        "publish_mode": LIVE_PUBLISH_MODE,
        "playback_mode": LIVE_PLAYBACK_MODE,
        "preferred_realtime_mode": preferred_realtime,
        "fallback_enabled": LIVE_FALLBACK_ENABLED,
        "fallback_mode": LIVE_FALLBACK_MODE,
        "preview_mode": "jpeg_snapshot",
        "signaling_url": LIVE_SIGNALING_URL,
        "turn_urls": LIVE_TURN_URLS,
        "turn_enabled": tc,
        "turn_realm": TURN_REALM,
        "turn_mode": "rest" if tc else "off",
        # 不含凭证；完整 ice_servers 仅由 host-session / viewer-session 返回
        "ice_servers": [],
        "livekit": {
            "enabled": LIVE_MEDIA_BACKEND == "livekit",
            "ready": livekit_ok,
            "ws_url": LIVEKIT_WS_URL,
        },
    }


def stream_media_descriptor(username: str, stream: Optional[LiveStream]) -> dict[str, Any]:
    room = room_name_for_username(username)
    hls = hls_manifest_for_username(username)
    live = bool(stream and stream.is_live)
    return {
        **media_backend_summary(),
        "room_name": room,
        "is_live": live,
        "hls_manifest_url": hls,
        "legacy": legacy_transport_for_username(username),
        "preview": {
            "mode": "jpeg_snapshot",
            "source": "push-frame",
            "list_cards": True,
            "fallback_watch": True,
            "storage": "process_memory",
        },
        "tracks": {
            "video": ["screen", "camera"],
            "audio": ["page", "mic"],
        },
    }


def host_session_payload(user: User, stream: LiveStream) -> dict[str, Any]:
    room = room_name_for_username(user.username)
    payload = {
        **stream_media_descriptor(user.username, stream),
        "role": "host",
        "identity": f"host:{user.id}",
        "capture_contract": {
            "video": [
                {"id": "screen", "source": "getDisplayMedia", "required": True},
                {"id": "camera", "source": "getUserMedia", "required": False},
            ],
            "audio": [
                {"id": "page", "source": "tab-or-system-audio", "required": False},
                {"id": "mic", "source": "getUserMedia", "required": False},
            ],
            "output": {
                "primary_program_video": "canvas.captureStream",
                "primary_program_audio": ["page track", "mic track"],
                "preview_jpeg": "low-frequency push-frame for live list and fallback preview",
                "layout_presets": [
                    "screenOnly",
                    "screenPlusPipCam",
                    "screenAndCamSideBySide",
                ],
            },
        },
    }
    ice: list[dict[str, Any]] = []
    if LIVE_MEDIA_BACKEND == "livekit" and livekit_ready():
        hid = f"host:{user.id}"
        ice = build_turn_ice_servers(hid)
        payload["livekit"] = {
            "ws_url": LIVEKIT_WS_URL,
            "room_name": room,
            "token": _livekit_token(
                identity=hid,
                room=room,
                can_publish=True,
                can_subscribe=True,
                name=user.display_name or user.username,
                metadata={"role": "host", "username": user.username},
            ),
            "ice_servers": ice,
        }
        payload["ice_servers"] = ice
    return payload


def viewer_session_payload(
    host: User,
    stream: Optional[LiveStream],
    viewer: Optional[User] = None,
) -> dict[str, Any]:
    room = room_name_for_username(host.username)
    # 匿名观众必须每人独立 identity，否则会在 SFU 内互踢
    if viewer:
        identity = f"viewer:{viewer.id}"
    else:
        identity = f"anon:{host.username}:{uuid.uuid4().hex[:12]}"
    payload = {
        **stream_media_descriptor(host.username, stream),
        "role": "viewer",
        "identity": identity,
    }
    if LIVE_MEDIA_BACKEND == "livekit" and livekit_ready() and stream and stream.is_live:
        ice = build_turn_ice_servers(identity)
        payload["livekit"] = {
            "ws_url": LIVEKIT_WS_URL,
            "room_name": room,
            "token": _livekit_token(
                identity=identity,
                room=room,
                can_publish=False,
                can_subscribe=True,
                name=(viewer.display_name if viewer else "") or identity,
                metadata={
                    "role": "viewer",
                    "host_username": host.username,
                    "viewer_id": viewer.id if viewer else "",
                },
            ),
            "ice_servers": ice,
        }
        payload["ice_servers"] = ice
    return payload
