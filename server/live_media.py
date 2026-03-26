from __future__ import annotations

import json
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
    return {
        "backend": LIVE_MEDIA_BACKEND,
        "publish_mode": LIVE_PUBLISH_MODE,
        "playback_mode": LIVE_PLAYBACK_MODE,
        "fallback_enabled": LIVE_FALLBACK_ENABLED,
        "fallback_mode": LIVE_FALLBACK_MODE,
        "signaling_url": LIVE_SIGNALING_URL,
        "turn_urls": LIVE_TURN_URLS,
        "livekit": {
            "enabled": LIVE_MEDIA_BACKEND == "livekit",
            "ready": livekit_ready(),
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
                "primary_program": "canvas.captureStream + mixed audio",
                "layout_presets": [
                    "screenOnly",
                    "screenPlusPipCam",
                    "screenAndCamSideBySide",
                ],
            },
        },
    }
    if LIVE_MEDIA_BACKEND == "livekit" and livekit_ready():
        payload["livekit"] = {
            "ws_url": LIVEKIT_WS_URL,
            "room_name": room,
            "token": _livekit_token(
                identity=f"host:{user.id}",
                room=room,
                can_publish=True,
                can_subscribe=True,
                name=user.display_name or user.username,
                metadata={"role": "host", "username": user.username},
            ),
        }
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
        }
    return payload
