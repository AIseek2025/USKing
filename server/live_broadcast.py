"""
站内直播：主播在 /app/live.html 通过 WebSocket 推送 JPEG 帧，服务器广播给所有观看 /live/{username} 的访客。

约束：状态仅存进程内存；uvicorn 多 worker 时各进程独立，请生产使用 --workers 1 或后续接 Redis 广播。
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from .auth import decode_token
from .database import SessionLocal
from .models import LiveStream, User

router = APIRouter(tags=["live-ws"])
_log = logging.getLogger("meiguwang.live_ws")

_state_lock = asyncio.Lock()
_publishers: Dict[str, WebSocket] = {}
_viewers: DefaultDict[str, List[WebSocket]] = defaultdict(list)
_last_jpeg: Dict[str, bytes] = {}


def _jpeg_ok(data: bytes) -> bool:
    return 800 <= len(data) <= 1_800_000 and data[:3] == b"\xff\xd8\xff"


async def _auth_publisher(websocket: WebSocket) -> Optional[User]:
    token = websocket.cookies.get("token")
    if not token:
        return None
    uid = decode_token(token)
    if not uid:
        return None
    db: Session = SessionLocal()
    try:
        return db.query(User).filter(User.id == uid, User.is_active == True).first()
    finally:
        db.close()


@router.websocket("/ws/live/publish")
async def ws_live_publish(websocket: WebSocket):
    await websocket.accept()
    user = await _auth_publisher(websocket)
    if not user:
        await websocket.close(code=1008)
        return
    if not user.live_enabled:
        await websocket.close(code=1008)
        return

    db: Session = SessionLocal()
    try:
        stream = (
            db.query(LiveStream)
            .filter(LiveStream.user_id == user.id, LiveStream.is_live == True)
            .first()
        )
    finally:
        db.close()

    if not stream:
        await websocket.close(code=1008)
        return

    un = user.username
    async with _state_lock:
        old = _publishers.get(un)
        if old is not None and old is not websocket:
            try:
                await old.close(code=1000)
            except Exception:
                pass
        _publishers[un] = websocket

    _log.info("live publish connect user=%s", un)
    frame_i = 0
    try:
        while True:
            raw = await websocket.receive()
            if raw["type"] == "websocket.disconnect":
                break
            data = raw.get("bytes")
            if data is None:
                continue
            if not _jpeg_ok(data):
                continue
            frame_i += 1
            if frame_i % 45 == 0:
                db_chk: Session = SessionLocal()
                try:
                    still = (
                        db_chk.query(LiveStream)
                        .filter(
                            LiveStream.user_id == user.id,
                            LiveStream.is_live == True,
                        )
                        .first()
                    )
                finally:
                    db_chk.close()
                if not still:
                    await websocket.close(code=1008)
                    break
            _last_jpeg[un] = data
            dead: List[WebSocket] = []
            for vw in list(_viewers.get(un, [])):
                try:
                    await vw.send_bytes(data)
                except Exception:
                    dead.append(vw)
            if dead:
                async with _state_lock:
                    lst = _viewers.get(un)
                    if lst:
                        for w in dead:
                            if w in lst:
                                lst.remove(w)
    except WebSocketDisconnect:
        pass
    finally:
        async with _state_lock:
            if _publishers.get(un) is websocket:
                del _publishers[un]
        _log.info("live publish disconnect user=%s", un)


@router.websocket("/ws/live/watch/{username}")
async def ws_live_watch(websocket: WebSocket, username: str):
    await websocket.accept()
    un = username.strip()
    if not un:
        await websocket.close(code=1008)
        return

    async with _state_lock:
        _viewers[un].append(websocket)
        snap = _last_jpeg.get(un)

    if snap:
        try:
            await websocket.send_bytes(snap)
        except Exception:
            pass

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with _state_lock:
            lst = _viewers.get(un)
            if lst and websocket in lst:
                lst.remove(websocket)
