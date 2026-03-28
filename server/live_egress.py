from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from typing import Any, Mapping, Optional

import httpx
from jose import JWTError, jwt

from .config import (
    LIVE_HLS_BASE_URL,
    LIVE_HLS_OUTPUT_DIR,
    LIVEKIT_API_KEY,
    LIVEKIT_API_SECRET,
    LIVEKIT_API_URL,
    LIVEKIT_EGRESS_CALLBACK_URL,
    LIVEKIT_EGRESS_ENABLED,
    LIVEKIT_EGRESS_LAYOUT,
    LIVEKIT_EGRESS_PRESET,
    LIVEKIT_EGRESS_SEGMENT_DURATION,
    LIVEKIT_WS_URL,
)
from .live_observability import list_recording_jobs, update_recording_job
from .models import LiveStream

_ROOM_PREFIX = "usking-live-"
_TERMINAL_STATUSES = {"completed", "failed", "stopped", "disabled"}


def livekit_egress_enabled() -> bool:
    return bool(
        LIVEKIT_EGRESS_ENABLED
        and LIVEKIT_API_KEY
        and LIVEKIT_API_SECRET
        and LIVEKIT_WS_URL
        and LIVE_HLS_BASE_URL
        and LIVE_HLS_OUTPUT_DIR
    )


def _livekit_api_url() -> str:
    if LIVEKIT_API_URL:
        return LIVEKIT_API_URL.rstrip("/")
    raw = (LIVEKIT_WS_URL or "").strip()
    if raw.startswith("wss://"):
        return f"https://{raw[6:].rstrip('/')}"
    if raw.startswith("ws://"):
        return f"http://{raw[5:].rstrip('/')}"
    return raw.rstrip("/")


def _egress_token(identity: str = "usking-egress-control") -> str:
    now = int(time.time())
    payload = {
        "iss": LIVEKIT_API_KEY,
        "sub": identity,
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
        "video": {
            "roomRecord": True,
        },
    }
    return jwt.encode(payload, LIVEKIT_API_SECRET, algorithm="HS256")


def _recording_filename(stream_id: int) -> str:
    return f"stream-{stream_id}.mp4"


def _recording_url(username: str, stream_id: int) -> str:
    base = LIVE_HLS_BASE_URL.rstrip("/")
    return f"{base}/{username}/recordings/{_recording_filename(stream_id)}"


def _webhook_url(request: Any) -> str:
    if LIVEKIT_EGRESS_CALLBACK_URL:
        return LIVEKIT_EGRESS_CALLBACK_URL.strip()
    if request is None:
        return ""
    base = str(getattr(request, "base_url", "")).rstrip("/")
    return f"{base}/api/live/egress/livekit-webhook" if base else ""


def _parse_job_detail(row: Any) -> dict[str, Any]:
    raw = getattr(row, "detail_json", "") or ""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _detail_for_egress(rows: list[Any], egress_id: str) -> tuple[Optional[Any], dict[str, Any]]:
    for row in rows:
        detail = _parse_job_detail(row)
        if detail.get("egress_id") == egress_id:
            return row, detail
    return None, {}


def _rows_for_egress(rows: list[Any], egress_id: str) -> list[Any]:
    matched: list[Any] = []
    for row in rows:
        detail = _parse_job_detail(row)
        if detail.get("egress_id") == egress_id:
            matched.append(row)
    return matched


def _status_from_livekit(status: str, event_name: str = "") -> str:
    value = (status or "").strip().upper()
    if value == "EGRESS_STARTING":
        return "starting"
    if value in {"EGRESS_ACTIVE", "ACTIVE"}:
        return "running"
    if value == "EGRESS_ENDING":
        return "stopped" if event_name == "egress_ended" else "running"
    if value == "EGRESS_COMPLETE":
        return "completed"
    if value in {"EGRESS_ABORTED"}:
        return "stopped"
    if value in {"EGRESS_FAILED", "EGRESS_LIMIT_REACHED", "FAILED"}:
        return "failed"
    return "planned"


def _request_payload(
    *,
    username: str,
    stream_id: int,
    room_name: str,
    webhook_url: str,
    enable_recording: bool,
) -> dict[str, Any]:
    host_dir = os.path.join(LIVE_HLS_OUTPUT_DIR, username)
    os.makedirs(host_dir, exist_ok=True)
    recordings_dir = os.path.join(host_dir, "recordings")
    os.makedirs(recordings_dir, exist_ok=True)
    # Egress runs as uid 1001 / gid 0 in production; keep group-write on precreated dirs.
    for path in (host_dir, recordings_dir):
        try:
            os.chmod(path, 0o775)
        except OSError:
            pass
    payload: dict[str, Any] = {
        "room_name": room_name,
        "layout": LIVEKIT_EGRESS_LAYOUT,
        "preset": LIVEKIT_EGRESS_PRESET,
        "segment_outputs": [
            {
                "filename_prefix": os.path.join(host_dir, "segment"),
                "playlist_name": f"archive-{stream_id}.m3u8",
                "live_playlist_name": "master.m3u8",
                "segment_duration": LIVEKIT_EGRESS_SEGMENT_DURATION,
            }
        ],
    }
    if enable_recording:
        payload["file_outputs"] = [
            {
                "filepath": os.path.join(recordings_dir, _recording_filename(stream_id)),
                "file_type": "MP4",
            }
        ]
    if webhook_url:
        payload["webhooks"] = [{"url": webhook_url, "signing_key": LIVEKIT_API_KEY}]
    return payload


def _twirp(method: str, body: Mapping[str, Any]) -> dict[str, Any]:
    base = _livekit_api_url()
    if not base:
        raise RuntimeError("missing livekit api url")
    url = f"{base}/twirp/livekit.Egress/{method}"
    token = _egress_token()
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()
        data = response.json()
    return data if isinstance(data, dict) else {}


def start_livekit_egress_for_stream(
    db: Any,
    *,
    request: Any,
    host_username: str,
    stream: LiveStream,
    room_name: str,
    manifest_url: str,
    enable_recording: bool,
) -> dict[str, Any]:
    if not livekit_egress_enabled():
        return {"enabled": False, "reason": "disabled"}
    rows = list_recording_jobs(db, host_username=host_username, stream_id=stream.id, limit=10)
    for row in rows:
        detail = _parse_job_detail(row)
        if detail.get("egress_id") and row.status not in _TERMINAL_STATUSES:
            return {
                "enabled": True,
                "reused": True,
                "egress_id": detail.get("egress_id", ""),
                "status": row.status,
            }
    webhook_url = _webhook_url(request)
    payload = _request_payload(
        username=host_username,
        stream_id=stream.id,
        room_name=room_name,
        webhook_url=webhook_url,
        enable_recording=enable_recording,
    )
    result = _twirp("StartRoomCompositeEgress", payload)
    detail = {
        "egress_id": result.get("egress_id", ""),
        "livekit_status": result.get("status", "EGRESS_STARTING"),
        "room_name": room_name,
        "stream_id": stream.id,
        "webhook_url": webhook_url,
        "api_url": _livekit_api_url(),
    }
    status = _status_from_livekit(str(result.get("status", "EGRESS_STARTING")))
    update_recording_job(
        db,
        host_username=host_username,
        egress_type="hls",
        status=status,
        stream=stream,
        provider="livekit_egress",
        room_name=room_name,
        manifest_url=manifest_url,
        detail_json=json.dumps(detail, ensure_ascii=False),
    )
    if enable_recording:
        update_recording_job(
            db,
            host_username=host_username,
            egress_type="recording",
            status=status,
            stream=stream,
            provider="livekit_egress",
            room_name=room_name,
            recording_url=_recording_url(host_username, stream.id),
            detail_json=json.dumps(detail, ensure_ascii=False),
        )
    return {"enabled": True, "reused": False, "result": result}


def stop_livekit_egress_for_stream(db: Any, *, host_username: str, stream_id: int) -> dict[str, Any]:
    if not livekit_egress_enabled():
        return {"enabled": False, "reason": "disabled"}
    rows = list_recording_jobs(db, host_username=host_username, stream_id=stream_id, limit=10)
    egress_id = ""
    for row in rows:
        detail = _parse_job_detail(row)
        if detail.get("egress_id") and row.status not in _TERMINAL_STATUSES:
            egress_id = str(detail.get("egress_id", "")).strip()
            break
    if not egress_id:
        return {"enabled": True, "stopped": False, "reason": "missing_egress_id"}
    result = _twirp("StopEgress", {"egress_id": egress_id})
    return {"enabled": True, "stopped": True, "result": result}


def _normalize_segments_info(info: Mapping[str, Any]) -> Mapping[str, Any]:
    items = info.get("segmentResults") or info.get("segment_results") or []
    if isinstance(items, list) and items:
        item = items[0]
        if isinstance(item, dict):
            return item
    return {}


def _normalize_file_info(info: Mapping[str, Any]) -> Mapping[str, Any]:
    items = info.get("fileResults") or info.get("file_results") or []
    if isinstance(items, list) and items:
        item = items[0]
        if isinstance(item, dict):
            return item
    return {}


def _username_from_room(room_name: str) -> str:
    raw = (room_name or "").strip()
    return raw[len(_ROOM_PREFIX):] if raw.startswith(_ROOM_PREFIX) else ""


def validate_livekit_webhook(raw_body: bytes, auth_header: str) -> dict[str, Any]:
    if not auth_header.lower().startswith("bearer "):
        raise ValueError("missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    claims = jwt.decode(token, LIVEKIT_API_SECRET, algorithms=["HS256"], options={"verify_aud": False})
    if claims.get("iss") != LIVEKIT_API_KEY:
        raise ValueError("invalid webhook issuer")
    encoded_hash = str(claims.get("sha256") or "").strip()
    if not encoded_hash:
        raise ValueError("missing webhook body hash")
    padded_hash = encoded_hash + ("=" * (-len(encoded_hash) % 4))
    expected = base64.b64decode(padded_hash)
    actual = hashlib.sha256(raw_body).digest()
    if expected != actual:
        raise ValueError("invalid webhook body hash")
    payload = json.loads(raw_body.decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def apply_livekit_egress_webhook(db: Any, event: Mapping[str, Any]) -> list[dict[str, Any]]:
    event_name = str(event.get("event", "")).strip()
    info = event.get("egressInfo") or event.get("egress_info") or {}
    if not isinstance(info, dict):
        return []
    room_name = str(info.get("room_name") or info.get("roomName") or "").strip()
    host_username = _username_from_room(room_name)
    if not host_username:
        return []
    egress_id = str(info.get("egress_id") or info.get("egressId") or "").strip()
    status = _status_from_livekit(str(info.get("status") or ""), event_name)
    rows = list_recording_jobs(db, host_username=host_username, limit=20)
    matched_row, existing_detail = _detail_for_egress(rows, egress_id)
    matched_rows = _rows_for_egress(rows, egress_id)
    hls_row = next((row for row in matched_rows if getattr(row, "egress_type", "") == "hls"), None)
    recording_row = next((row for row in matched_rows if getattr(row, "egress_type", "") == "recording"), None)
    stream_id = getattr(matched_row, "stream_id", None)
    stream = db.query(LiveStream).filter(LiveStream.id == stream_id).first() if stream_id is not None else None
    segments = _normalize_segments_info(info)
    files = _normalize_file_info(info)
    manifest_url = (
        str(segments.get("live_playlist_location") or segments.get("livePlaylistLocation") or "")
        or str(segments.get("playlist_location") or segments.get("playlistLocation") or "")
        or (hls_row.manifest_url if hls_row else "")
        or f"{LIVE_HLS_BASE_URL.rstrip('/')}/{host_username}/master.m3u8"
    )
    recording_url = (
        str(files.get("location") or "")
        or (recording_row.recording_url if recording_row else "")
    )
    detail = {
        **existing_detail,
        "egress_id": egress_id,
        "event": event_name,
        "livekit_status": str(info.get("status") or ""),
        "error": str(info.get("error") or ""),
        "details": str(info.get("details") or ""),
        "updated_at": info.get("updated_at") or info.get("updatedAt"),
    }
    detail_json = json.dumps(detail, ensure_ascii=False)
    items = [
        update_recording_job(
            db,
            host_username=host_username,
            egress_type="hls",
            status=status,
            stream=stream,
            provider="livekit_egress",
            room_name=room_name,
            manifest_url=manifest_url,
            detail_json=detail_json,
        )
    ]
    if recording_url or (existing_detail and existing_detail.get("egress_id")):
        row = update_recording_job(
            db,
            host_username=host_username,
            egress_type="recording",
            status=status,
            stream=stream,
            provider="livekit_egress",
            room_name=room_name,
            recording_url=recording_url,
            detail_json=detail_json,
        )
        items.append(row)
    return [
        {
            "host_username": row.host_username,
            "egress_type": row.egress_type,
            "status": row.status,
            "stream_id": row.stream_id,
            "manifest_url": row.manifest_url,
            "recording_url": row.recording_url,
        }
        for row in items
    ]


def webhook_error(exc: Exception) -> str:
    if isinstance(exc, (ValueError, JWTError, json.JSONDecodeError)):
        return str(exc)
    return exc.__class__.__name__
