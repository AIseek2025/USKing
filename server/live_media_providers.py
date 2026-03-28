"""
USKing 直播媒体 Provider 适配层（Phase A）。

将 LiveKit 签发与 legacy 占位从 live_media 的散落的 if/else 中抽出，
后续新增托管厂商时实现新 Provider 并注册即可。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from jose import jwt

from .config import (
    LIVE_FALLBACK_ENABLED,
    LIVE_INTERACTIVE_VENDOR,
    LIVEKIT_API_KEY,
    LIVEKIT_API_SECRET,
)


def _livekit_access_token(
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


class MediaProvider(ABC):
    """单一媒体后端能力（互动 RTC、legacy 等）。"""

    id: str

    @abstractmethod
    def interactive_ready(self) -> bool:
        """是否可为观众签发互动 RTC 凭证。"""

    @abstractmethod
    def attach_host_session(
        self,
        payload: dict[str, Any],
        *,
        user: Any,
        stream: Any,
        region: str,
        room: str,
    ) -> None:
        """在已有 payload 上写入 host 侧 RTC 凭证（如适用）。"""

    @abstractmethod
    def attach_viewer_session(
        self,
        payload: dict[str, Any],
        *,
        host: Any,
        viewer: Optional[Any],
        stream: Optional[Any],
        delivery: Mapping[str, Any],
        identity: str,
        region: str,
        room: str,
    ) -> None:
        """在已有 payload 上写入 viewer 侧 RTC 凭证（如适用）。"""


class ManagedLiveKitProvider(MediaProvider):
    """托管 LiveKit：签发 join token 与 ICE（与现有 live_media ICE 工具衔接）。"""

    id = "managed_livekit"

    def interactive_ready(self) -> bool:
        from . import live_media as lm

        return "livekit" in LIVE_INTERACTIVE_VENDOR and lm.livekit_ready()

    def attach_host_session(
        self,
        payload: dict[str, Any],
        *,
        user: Any,
        stream: Any,
        region: str,
        room: str,
    ) -> None:
        from . import live_media as lm

        hid = f"host:{user.id}"
        ice = lm.build_turn_ice_servers(hid, region)
        payload["livekit"] = {
            "ws_url": lm.livekit_ws_url_for_region(region),
            "room_name": room,
            "token": _livekit_access_token(
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

    def attach_viewer_session(
        self,
        payload: dict[str, Any],
        *,
        host: Any,
        viewer: Optional[Any],
        stream: Optional[Any],
        delivery: Mapping[str, Any],
        identity: str,
        region: str,
        room: str,
    ) -> None:
        from . import live_media as lm

        if not stream or not stream.is_live:
            return
        if not delivery.get("interactive_allowed"):
            return
        ice = lm.build_turn_ice_servers(identity, region)
        payload["livekit"] = {
            "ws_url": lm.livekit_ws_url_for_region(region),
            "room_name": room,
            "token": _livekit_access_token(
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


class LegacyFallbackProvider(MediaProvider):
    """JPEG 轮询 + 站内音频 WS：不签发 RTC，仅占位与后续扩展。"""

    id = "legacy_jpeg"

    def interactive_ready(self) -> bool:
        return False

    def attach_host_session(
        self,
        payload: dict[str, Any],
        *,
        user: Any,
        stream: Any,
        region: str,
        room: str,
    ) -> None:
        return

    def attach_viewer_session(
        self,
        payload: dict[str, Any],
        *,
        host: Any,
        viewer: Optional[Any],
        stream: Optional[Any],
        delivery: Mapping[str, Any],
        identity: str,
        region: str,
        room: str,
    ) -> None:
        return


def get_managed_livekit_provider() -> Optional[ManagedLiveKitProvider]:
    p = ManagedLiveKitProvider()
    return p if p.interactive_ready() else None


def get_legacy_fallback_provider() -> LegacyFallbackProvider:
    return LegacyFallbackProvider()


def apply_session_provider_metadata(payload: dict[str, Any], *, interactive_active: bool) -> None:
    """统一会话上的 provider 元信息，便于前端与运维识别。"""
    payload.setdefault("providers", {})
    payload["providers"]["interactive"] = {
        "id": ManagedLiveKitProvider.id,
        "active": interactive_active,
    }
    payload["providers"]["fallback"] = {
        "id": LegacyFallbackProvider.id,
        "active": bool(LIVE_FALLBACK_ENABLED),
    }
