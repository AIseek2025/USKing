"""
站内直播 fallback：主播推送 JPEG，观众拉流。

- WebSocket（需 Nginx Upgrade）：/api/ws/live/publish、/api/ws/live/watch/{username}
- HTTP：POST /api/live/push-frame（Cookie）；观众推荐轮询 GET /api/live/last-frame/{username}（单帧 JPEG，最耐缓冲）
- 可选：GET /api/live/mjpeg/{username}（multipart 长连接，部分 Nginx 会缓冲导致首帧迟迟不出）

约束：状态仅存进程内存；生产请 uvicorn --workers 1。
说明：正式主链路应迁移到独立媒体平面（WebRTC/RTMP/HLS），本模块保留作 fallback / 诊断。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional, Set

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

_live_users: Dict[str, float] = {}
_LIVE_CHECK_INTERVAL = 30.0

MJPEG_BOUNDARY = b"frame"
MJPEG_SEP = b"--frame\r\n"

_WS_SEND_TIMEOUT = 3.0

_audio_viewers: DefaultDict[str, List[WebSocket]] = defaultdict(list)
_audio_publishers: Dict[str, WebSocket] = {}
_audio_sr: Dict[str, int] = {}
_AUDIO_CH_PAGE = 0
_AUDIO_CH_MIC = 1
_MAX_AUDIO_PACKET = 256 * 1024
# 单主播上行 PCM 粗限流（防异常客户端拖垮事件循环）；约 1.2MB/s，远高于正常 48kHz mono
_MAX_AUDIO_BYTES_PER_SEC = 1_200_000
_audio_pub_rate: Dict[str, tuple] = {}


def _check_audio_publish_rate(un: str, nbytes: int) -> bool:
    now = time.monotonic()
    entry = _audio_pub_rate.get(un)
    if not entry or now - entry[0] >= 1.0:
        _audio_pub_rate[un] = (now, nbytes)
        return nbytes <= _MAX_AUDIO_BYTES_PER_SEC
    st, acc = entry
    acc += nbytes
    if acc > _MAX_AUDIO_BYTES_PER_SEC:
        return False
    _audio_pub_rate[un] = (st, acc)
    return True


async def disconnect_live_audio_room(username: str) -> None:
    """停播时关闭该房间全部音频 WS（观众与主播推音频）。"""
    un = (username or "").strip()
    if not un:
        return
    async with _state_lock:
        viewers = list(_audio_viewers.pop(un, []))
        pub = _audio_publishers.pop(un, None)
    _audio_sr.pop(un, None)
    _audio_pub_rate.pop(un, None)
    for vw in viewers:
        try:
            await vw.close(code=1000)
        except Exception:
            pass
    if pub:
        try:
            await pub.close(code=1000)
        except Exception:
            pass


async def _fanout_audio_bytes(un: str, data: bytes) -> None:
    viewers = list(_audio_viewers.get(un, []))
    if not viewers:
        return
    dead: Set[WebSocket] = set()

    async def _send(vw: WebSocket) -> None:
        try:
            await asyncio.wait_for(vw.send_bytes(data), timeout=_WS_SEND_TIMEOUT)
        except Exception:
            dead.add(vw)

    await asyncio.gather(*(_send(vw) for vw in viewers))
    if dead:
        async with _state_lock:
            lst = _audio_viewers.get(un)
            if lst:
                _audio_viewers[un] = [w for w in lst if w not in dead]


async def _fanout_audio_text(un: str, text: str) -> None:
    viewers = list(_audio_viewers.get(un, []))
    if not viewers:
        return
    dead: Set[WebSocket] = set()

    async def _send(vw: WebSocket) -> None:
        try:
            await asyncio.wait_for(vw.send_text(text), timeout=_WS_SEND_TIMEOUT)
        except Exception:
            dead.add(vw)

    await asyncio.gather(*(_send(vw) for vw in viewers))
    if dead:
        async with _state_lock:
            lst = _audio_viewers.get(un)
            if lst:
                _audio_viewers[un] = [w for w in lst if w not in dead]


def _jpeg_ok(data: bytes) -> bool:
    return 800 <= len(data) <= 1_800_000 and data[:3] == b"\xff\xd8\xff"


def username_has_frame(username: str) -> bool:
    """与 last-frame 同一套 key（strip 后的 username）。"""
    un = (username or "").strip()
    if not un:
        return False
    data = _last_jpeg.get(un)
    return bool(data and _jpeg_ok(data))


def mark_user_live(user_id: str) -> None:
    """start_stream 时由 api 调用，写入内存缓存，后续 push-frame 可跳过 DB。"""
    _live_users[user_id] = time.monotonic()


def clear_user_frame(username: str, user_id: str | None = None) -> None:
    """stop_stream 时由 api 调用，清除该用户的所有内存帧与缓存。"""
    un = (username or "").strip()
    if un:
        _last_jpeg.pop(un, None)
        _frame_ver.pop(un, None)
    if user_id:
        _live_users.pop(user_id, None)


def _user_is_cached_live(user_id: str) -> bool:
    ts = _live_users.get(user_id)
    if ts is None:
        return False
    return (time.monotonic() - ts) < _LIVE_CHECK_INTERVAL


def live_memory_recent(user_id: str) -> bool:
    """与开播/start、推帧、心跳共享的短期内存标记（约 30s 内有效）。"""
    return _user_is_cached_live(user_id)


async def _broadcast_jpeg(un: str, data: bytes) -> None:
    _last_jpeg[un] = data
    _frame_ver[un] += 1
    viewers = list(_viewers.get(un, []))
    if not viewers:
        return
    dead: Set[WebSocket] = set()

    async def _safe_send(ws: WebSocket) -> None:
        try:
            await asyncio.wait_for(ws.send_bytes(data), timeout=_WS_SEND_TIMEOUT)
        except Exception:
            dead.add(ws)

    await asyncio.gather(*(_safe_send(vw) for vw in viewers))
    if dead:
        async with _state_lock:
            lst = _viewers.get(un)
            if lst:
                _viewers[un] = [w for w in lst if w not in dead]


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

    if not _user_is_cached_live(user.id):
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
            _live_users.pop(user.id, None)
            raise HTTPException(status_code=409, detail="未在直播中，请先开始直播")
        _live_users[user.id] = time.monotonic()

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
    mark_user_live(user.id)
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
            if not _user_is_cached_live(user.id):
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
                _live_users[user.id] = time.monotonic()
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


@router.websocket("/ws/live/audio/publish")
async def ws_audio_publish(websocket: WebSocket):
    """主播推送 PCM：每帧 [uint8 声道 0=画面系统音 1=麦克风][int16le mono ...]；首包可发 JSON 文本 sample_rate。"""
    await websocket.accept()
    token = (websocket.query_params.get("token") or "").strip()
    if not token:
        token = (websocket.cookies.get("token") or "").strip()
    uid = decode_token(token) if token else None
    if not uid:
        await websocket.close(code=4401)
        return
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == uid, User.is_active == True).first()
    finally:
        db.close()
    if not user or not user.live_enabled:
        await websocket.close(code=4403)
        return
    db2: Session = SessionLocal()
    try:
        stream = (
            db2.query(LiveStream)
            .filter(LiveStream.user_id == user.id, LiveStream.is_live == True)
            .first()
        )
    finally:
        db2.close()
    if not stream:
        await websocket.close(code=4409)
        return
    un = user.username
    async with _state_lock:
        old_pub = _audio_publishers.get(un)
        if old_pub is not None and old_pub is not websocket:
            try:
                await old_pub.close(code=4000)
            except Exception:
                pass
        _audio_publishers[un] = websocket
    try:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if msg.get("type") != "websocket.receive":
                continue
            data_b = msg.get("bytes")
            if data_b is not None:
                if len(data_b) < 3 or len(data_b) > _MAX_AUDIO_PACKET:
                    continue
                ch = data_b[0]
                if ch not in (_AUDIO_CH_PAGE, _AUDIO_CH_MIC):
                    continue
                if not _check_audio_publish_rate(un, len(data_b)):
                    continue
                await _fanout_audio_bytes(un, data_b)
                continue
            data_t = msg.get("text")
            if data_t is not None:
                try:
                    o = json.loads(data_t)
                    if o.get("type") == "audio_cfg":
                        sr = int(o.get("sample_rate", 0))
                        if 8000 <= sr <= 96000:
                            _audio_sr[un] = sr
                            await _fanout_audio_text(
                                un,
                                json.dumps({"type": "audio_cfg", "sample_rate": sr}),
                            )
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        async with _state_lock:
            if _audio_publishers.get(un) is websocket:
                del _audio_publishers[un]
        _audio_pub_rate.pop(un, None)


@router.websocket("/ws/live/audio/watch/{username}")
async def ws_audio_watch(websocket: WebSocket, username: str):
    await websocket.accept()
    un = username.strip()
    if not un:
        await websocket.close(code=1008)
        return
    async with _state_lock:
        _audio_viewers[un].append(websocket)
    sr = _audio_sr.get(un)
    if sr:
        try:
            await websocket.send_text(
                json.dumps({"type": "audio_cfg", "sample_rate": sr})
            )
        except Exception:
            pass
    try:
        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        pass
    finally:
        async with _state_lock:
            lst = _audio_viewers.get(un)
            if lst and websocket in lst:
                lst.remove(websocket)
