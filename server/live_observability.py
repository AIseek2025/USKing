from __future__ import annotations

import json
import threading
from collections import Counter
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import LivePlaybackSession, LiveQualityEvent, LiveRecordingJob, LiveStream, utcnow

_lock = threading.Lock()
_counters: Counter[str] = Counter()
_TERMINAL_RECORDING_STATUSES = {"completed", "failed", "stopped", "disabled"}


def bump_counter(name: str, count: int = 1) -> None:
    if not name:
        return
    with _lock:
        _counters[name] += count


def open_playback_session(
    db: Session,
    *,
    stream: Optional[LiveStream],
    host_username: str,
    viewer_id: str = "",
    session_token: str,
    plane: str,
    provider: str,
    region: str,
    country: str,
) -> LivePlaybackSession:
    row = (
        db.query(LivePlaybackSession)
        .filter(LivePlaybackSession.session_token == session_token)
        .first()
    )
    if row:
        row.plane = plane
        row.provider = provider
        row.region = region
        row.country = country
        if stream:
            row.stream_id = stream.id
    else:
        row = LivePlaybackSession(
            stream_id=stream.id if stream else None,
            host_username=host_username,
            viewer_id=viewer_id,
            session_token=session_token,
            plane=plane,
            provider=provider,
            region=region,
            country=country,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    bump_counter(f"playback_session_open:{plane}")
    return row


def close_playback_session(db: Session, *, session_token: str) -> bool:
    row = (
        db.query(LivePlaybackSession)
        .filter(LivePlaybackSession.session_token == session_token)
        .first()
    )
    if not row:
        return False
    row.closed_at = utcnow()
    db.commit()
    bump_counter(f"playback_session_close:{row.plane}")
    return True


def record_quality_event(
    db: Session,
    *,
    stream: Optional[LiveStream],
    host_username: str,
    viewer_id: str = "",
    session_token: str = "",
    plane: str = "",
    provider: str = "",
    region: str = "",
    country: str = "",
    event_name: str,
    ok: bool = True,
    metric_value: Optional[float] = None,
    metric_unit: str = "",
    detail_json: str = "",
) -> LiveQualityEvent:
    row = LiveQualityEvent(
        stream_id=stream.id if stream else None,
        host_username=host_username,
        viewer_id=viewer_id,
        session_token=session_token,
        plane=plane,
        provider=provider,
        region=region,
        country=country,
        event_name=event_name,
        ok=ok,
        metric_value=metric_value,
        metric_unit=metric_unit,
        detail_json=detail_json,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    bump_counter(f"quality_event:{event_name}")
    if not ok:
        bump_counter("quality_event:error")
    return row


def ensure_recording_jobs(
    db: Session,
    *,
    stream: LiveStream,
    host_username: str,
    room_name: str,
    provider: str,
    manifest_url: str,
    enable_recording: bool,
) -> list[LiveRecordingJob]:
    jobs: list[LiveRecordingJob] = []
    specs = [("hls", True), ("recording", enable_recording)]
    for egress_type, enabled in specs:
        row = (
            db.query(LiveRecordingJob)
            .filter(
                LiveRecordingJob.stream_id == stream.id,
                LiveRecordingJob.egress_type == egress_type,
            )
            .first()
        )
        if row:
            row.provider = provider
            row.room_name = room_name
            row.manifest_url = manifest_url if egress_type == "hls" else row.manifest_url
            if not enabled:
                row.status = "disabled"
            elif row.status in ("", "disabled", "planned"):
                row.status = "planned"
        else:
            row = LiveRecordingJob(
                stream_id=stream.id,
                host_username=host_username,
                provider=provider,
                room_name=room_name,
                egress_type=egress_type,
                status="planned" if enabled else "disabled",
                manifest_url=manifest_url if egress_type == "hls" else "",
            )
            db.add(row)
        jobs.append(row)
    db.commit()
    return jobs


def serialize_recording_job(row: LiveRecordingJob) -> dict[str, Any]:
    detail: Any = {}
    if row.detail_json:
        try:
            detail = json.loads(row.detail_json)
        except Exception:
            detail = row.detail_json
    return {
        "id": row.id,
        "stream_id": row.stream_id,
        "host_username": row.host_username,
        "provider": row.provider,
        "room_name": row.room_name,
        "egress_type": row.egress_type,
        "status": row.status,
        "manifest_url": row.manifest_url,
        "recording_url": row.recording_url,
        "detail": detail,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "ended_at": row.ended_at.isoformat() if row.ended_at else None,
    }


def list_recording_jobs(
    db: Session,
    *,
    host_username: str = "",
    stream_id: Optional[int] = None,
    limit: int = 20,
) -> list[LiveRecordingJob]:
    q = db.query(LiveRecordingJob)
    if host_username:
        q = q.filter(LiveRecordingJob.host_username == host_username)
    if stream_id is not None:
        q = q.filter(LiveRecordingJob.stream_id == stream_id)
    return q.order_by(LiveRecordingJob.id.desc()).limit(max(1, limit)).all()


def update_recording_job(
    db: Session,
    *,
    host_username: str,
    egress_type: str,
    status: str,
    stream: Optional[LiveStream] = None,
    provider: str = "",
    room_name: str = "",
    manifest_url: str = "",
    recording_url: str = "",
    detail_json: str = "",
) -> LiveRecordingJob:
    q = db.query(LiveRecordingJob).filter(
        LiveRecordingJob.host_username == host_username,
        LiveRecordingJob.egress_type == egress_type,
    )
    if stream is not None:
        q = q.filter(LiveRecordingJob.stream_id == stream.id)
    row = q.order_by(LiveRecordingJob.id.desc()).first()
    if not row:
        row = LiveRecordingJob(
            stream_id=stream.id if stream else None,
            host_username=host_username,
            provider=provider,
            room_name=room_name,
            egress_type=egress_type,
            status=status,
            manifest_url=manifest_url if egress_type == "hls" else "",
            recording_url=recording_url if egress_type == "recording" else "",
            detail_json=detail_json,
        )
        db.add(row)
    else:
        if stream is not None:
            row.stream_id = stream.id
        if provider:
            row.provider = provider
        if room_name:
            row.room_name = room_name
        row.status = status
        if manifest_url:
            row.manifest_url = manifest_url
        if recording_url:
            row.recording_url = recording_url
        if detail_json:
            row.detail_json = detail_json
    if status in _TERMINAL_RECORDING_STATUSES:
        row.ended_at = utcnow()
    else:
        row.ended_at = None
    db.commit()
    db.refresh(row)
    bump_counter(f"recording_job:{egress_type}:{status}")
    return row


def egress_status_for_stream(
    db: Session,
    *,
    stream: Optional[LiveStream],
    host_username: str,
    fallback_manifest_url: str = "",
) -> dict[str, Any]:
    rows = list_recording_jobs(
        db,
        host_username=host_username,
        stream_id=stream.id if stream else None,
        limit=20,
    )
    latest_by_type: dict[str, LiveRecordingJob] = {}
    for row in rows:
        latest_by_type.setdefault(row.egress_type, row)
    hls_row = latest_by_type.get("hls")
    recording_row = latest_by_type.get("recording")
    hls_manifest = ""
    if hls_row:
        hls_manifest = hls_row.manifest_url or fallback_manifest_url
    elif fallback_manifest_url:
        hls_manifest = fallback_manifest_url
    hls_status = hls_row.status if hls_row else "missing"
    hls_live_ready = bool(hls_manifest and hls_status == "running")
    recording_url = recording_row.recording_url if recording_row else ""
    recording_status = recording_row.status if recording_row else "missing"
    return {
        "hls": {
            "status": hls_status,
            "manifest_url": hls_manifest,
            "live_ready": hls_live_ready,
            "ready": bool(hls_manifest and hls_status in {"running", "completed", "stopped"}),
            "job": serialize_recording_job(hls_row) if hls_row else None,
        },
        "recording": {
            "status": recording_status,
            "recording_url": recording_url,
            "ready": bool(recording_url and recording_status in {"running", "completed", "stopped"}),
            "job": serialize_recording_job(recording_row) if recording_row else None,
        },
        "jobs": [serialize_recording_job(row) for row in rows],
    }


def mark_recording_jobs_stopped(db: Session, *, stream_id: int) -> None:
    rows = db.query(LiveRecordingJob).filter(LiveRecordingJob.stream_id == stream_id).all()
    changed = False
    for row in rows:
        if row.status not in ("completed", "failed", "disabled"):
            row.status = "stopped"
            row.ended_at = utcnow()
            changed = True
    if changed:
        db.commit()


def summary_snapshot(db: Session) -> dict[str, Any]:
    with _lock:
        counters = dict(_counters)
    ff_avg = db.query(func.avg(LiveQualityEvent.metric_value)).filter(
        LiveQualityEvent.event_name == "first_frame_ms",
        LiveQualityEvent.metric_value.isnot(None),
    ).scalar()
    fa_avg = db.query(func.avg(LiveQualityEvent.metric_value)).filter(
        LiveQualityEvent.event_name == "first_audio_ms",
        LiveQualityEvent.metric_value.isnot(None),
    ).scalar()
    active_playback_sessions = db.query(LivePlaybackSession).filter(
        LivePlaybackSession.closed_at.is_(None)
    ).count()
    planned_recordings = db.query(LiveRecordingJob).filter(
        LiveRecordingJob.status.in_(["planned", "running", "stopped"])
    ).count()
    recording_by_status = {
        status: count
        for status, count in db.query(LiveRecordingJob.status, func.count(LiveRecordingJob.id))
        .group_by(LiveRecordingJob.status)
        .all()
    }
    return {
        "counters": counters,
        "slo": {
            "first_frame_ms_avg": float(ff_avg) if ff_avg is not None else None,
            "first_audio_ms_avg": float(fa_avg) if fa_avg is not None else None,
        },
        "active_playback_sessions": active_playback_sessions,
        "recording_jobs": planned_recordings,
        "recording_jobs_by_status": recording_by_status,
    }
