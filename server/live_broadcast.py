"""
站内直播：主播推送 JPEG，观众拉流。

- WebSocket（需 Nginx Upgrade）：/api/ws/live/publish、/api/ws/live/watch/{username}
- HTTP：POST /api/live/push-frame（Cookie）；观众推荐轮询 GET /api/live/last-frame/{username}（单帧 JPEG，最耐缓冲）
- 可选：GET /api/live/mjpeg/{username}（multipart 长连接，部分 Nginx 会缓冲导致首帧迟迟不出）

约束：状态仅存进程内存；生产请 uvicorn --workers 1。
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from .auth import decode_token, require_user
from .database import SessionLocal
from .models import LiveStream, User

router = APIRouter(tags=["live-ws"])
_log = logging.getLogger("meiguwang.live_ws")

_state_lock = asyncio.Lock()
_publishers: Dict[str, WebSocket] = {}
_viewers: DefaultDict[str, List[WebSocket]] = defaultdict(list)
_last_jpeg: Dict[str, bytes] = {}
_frame_ver: Dict[str, int] = defaultdict(int)
_post_check_counter: DefaultDict[str, int] = defaultdict(int)

MJPEG_BOUNDARY = b"frame"
MJPEG_SEP = b"--frame\r\n"


def _jpeg_ok(data: bytes) -> bool:
    return 800 <= len(data) <= 1_800_000 and data[:3] == b"\xff\xd8\xff"


def username_has_frame(username: str) -> bool:
    """与 last-frame 同一套 key（strip 后的 username）。"""
    un = (username or "").strip()
    if not un:
        return False
    data = _last_jpeg.get(un)
    return bool(data and _jpeg_ok(data))


async def _broadcast_jpeg(un: str, data: bytes) -> None:
    _last_jpeg[un] = data
    _frame_ver[un] += 1
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


@router.post("/live/push-frame")
async def live_push_frame(request: Request, user: User = Depends(require_user)):
    """采集页通过普通 HTTP 上传 JPEG（不依赖 WebSocket Upgrade）。"""
    if not user.live_enabled:
        raise HTTPException(status_code=403, detail="直播权限已关闭")
    body = await request.body()
    if not _jpeg_ok(body):
        raise HTTPException(status_code=400, detail="无效 JPEG")

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
        raise HTTPException(status_code=409, detail="未在直播中，请先开始直播")

    n = _post_check_counter[user.id] + 1
    _post_check_counter[user.id] = n
    if n % 45 == 0:
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
            raise HTTPException(status_code=409, detail="直播已结束")

    un = user.username
    await _broadcast_jpeg(un, body)
    return {"ok": True}


@router.api_route("/live/last-frame/{username}", methods=["GET", "HEAD"])
async def live_last_frame(username: str, request: Request):
    """返回内存中最新一帧 JPEG（短请求，适合 Nginx 默认缓冲；观看页轮询）。"""
    un = username.strip()
    if not un:
        raise HTTPException(status_code=400, detail="无效用户名")
    data = _last_jpeg.get(un)
    if not data:
        raise HTTPException(status_code=404, detail="暂无画面")
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
        "Content-Length": str(len(data)),
    }
    if request.method == "HEAD":
        return Response(content=b"", media_type="image/jpeg", headers=headers)
    return Response(content=data, media_type="image/jpeg", headers=headers)


@router.get("/live/mjpeg/{username}")
async def live_mjpeg(username: str):
    """浏览器 <img src=...> 可播放的 MJPEG（multipart/x-mixed-replace），走普通 HTTP。"""
    un = username.strip()
    if not un:
        raise HTTPException(status_code=400, detail="无效用户名")

    async def gen():
        last_v = 0
        while True:
            data = _last_jpeg.get(un)
            v = _frame_ver.get(un, 0)
            if data and v > last_v:
                last_v = v
                header = (
                    MJPEG_SEP
                    + b"Content-Type: image/jpeg\r\nContent-Length: "
                    + str(len(data)).encode()
                    + b"\r\n\r\n"
                    + data
                    + b"\r\n"
                )
                yield header
            await asyncio.sleep(0.04)

    return StreamingResponse(
        gen(),
        media_type=f"multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY.decode()}",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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
            await _broadcast_jpeg(un, data)
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
