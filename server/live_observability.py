from __future__ import annotations

import threading
from collections import Counter
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import LivePlaybackSession, LiveQualityEvent, LiveRecordingJob, LiveStream, utcnow

_lock = threading.Lock()
_counters: Counter[str] = Counter()


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
            row.status = "planned" if enabled else "disabled"
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
    return {
        "counters": counters,
        "slo": {
            "first_frame_ms_avg": float(ff_avg) if ff_avg is not None else None,
            "first_audio_ms_avg": float(fa_avg) if fa_avg is not None else None,
        },
        "active_playback_sessions": active_playback_sessions,
        "recording_jobs": planned_recordings,
    }
