from __future__ import annotations

import base64
import hashlib
import hmac
import time
import uuid
from typing import Any, Mapping, Optional

from .config import (
    LIVE_BROADCAST_VENDOR,
    LIVE_CANARY_COUNTRIES,
    LIVE_CANARY_USERS,
    LIVE_DEFAULT_VIEWER_INTENT,
    LIVE_FALLBACK_MODE,
    LIVE_FALLBACK_ENABLED,
    LIVE_HLS_BASE_URL,
    LIVE_HLS_REGION_BASE_URLS,
    LIVE_FORCE_BROADCAST_COUNTRIES,
    LIVE_FORCE_INTERACTIVE_USERS,
    LIVE_INTERACTIVE_AUTHENTICATED_ONLY,
    LIVE_INTERACTIVE_ROLLOUT_PERCENT,
    LIVE_INTERACTIVE_VENDOR,
    LIVE_MEDIA_BACKEND,
    LIVE_MIGRATION_MODE,
    LIVE_PLAYBACK_MODE,
    LIVE_PUBLISH_MODE,
    LIVE_RECORDING_VENDOR,
    LIVE_REGION_HINT_MAP,
    LIVE_SIGNALING_URL,
    LIVE_TURN_URLS,
    LIVE_TURN_REGION_URLS,
    LIVE_VENDOR_STACK,
    LIVEKIT_API_KEY,
    LIVEKIT_API_SECRET,
    LIVE_RTC_REGION_WS_URLS,
    LIVEKIT_WS_URL,
    TURN_CREDENTIAL_TTL_SECONDS,
    TURN_ENABLED,
    TURN_REALM,
    TURN_SHARED_SECRET,
    TURN_STUN_URLS,
    TURN_TLS_URL,
    TURN_UDP_URL,
)
from .live_media_providers import apply_session_provider_metadata, get_managed_livekit_provider
from .models import LiveStream, User


def room_name_for_username(username: str) -> str:
    return f"usking-live-{(username or '').strip()}"


def _country_from_headers(headers: Optional[Mapping[str, str]]) -> tuple[str, str]:
    if not headers:
        return "", ""
    for key in (
        "cf-ipcountry",
        "x-vercel-ip-country",
        "x-country-code",
        "x-app-country",
    ):
        val = (headers.get(key) or headers.get(key.upper()) or "").strip().upper()
        if val:
            return val, key
    return "", ""


def _default_region_for_country(country: str) -> str:
    if not country:
        return "global"
    if country in {"US", "CA", "MX"}:
        return "us"
    if country in {
        "GB",
        "FR",
        "DE",
        "NL",
        "BE",
        "SE",
        "NO",
        "FI",
        "IT",
        "ES",
        "CH",
        "DK",
        "AT",
        "IE",
    }:
        return "eu"
    if country in {"CN", "HK", "MO", "TW", "SG", "JP", "KR", "IN", "AU", "NZ"}:
        return "apac"
    return "global"


def edge_region_context(headers: Optional[Mapping[str, str]] = None) -> dict[str, Any]:
    country, header = _country_from_headers(headers)
    region = _default_region_for_country(country)
    override = LIVE_REGION_HINT_MAP.get(country) if isinstance(LIVE_REGION_HINT_MAP, dict) else None
    if isinstance(override, str) and override.strip():
        region = override.strip().lower()
    return {
        "country": country,
        "region": region,
        "source": header or "default",
    }


def _region_map_str(data: object, region: str) -> str:
    if not isinstance(data, dict):
        return ""
    raw = data.get(region) or data.get("default") or data.get("global")
    return raw.strip() if isinstance(raw, str) else ""


def _region_map_urls(data: object, region: str) -> list[str]:
    if not isinstance(data, dict):
        return []
    raw = data.get(region) or data.get("default") or data.get("global")
    if isinstance(raw, str):
        return [u.strip() for u in raw.split(",") if u.strip()]
    if isinstance(raw, list):
        return [str(u).strip() for u in raw if str(u).strip()]
    return []


def livekit_ws_url_for_region(region: str) -> str:
    return _region_map_str(LIVE_RTC_REGION_WS_URLS, region) or LIVEKIT_WS_URL


def turn_urls_for_region(region: str) -> list[str]:
    region_urls = _region_map_urls(LIVE_TURN_REGION_URLS, region)
    if region_urls:
        return region_urls
    return LIVE_TURN_URLS[:]


def hls_manifest_for_username(username: str, region: str = "global") -> str:
    base = (_region_map_str(LIVE_HLS_REGION_BASE_URLS, region) or LIVE_HLS_BASE_URL or "").rstrip("/")
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
    return bool(livekit_ws_url_for_region("global") and LIVEKIT_API_KEY and LIVEKIT_API_SECRET)


def turn_configured(region: str = "global") -> bool:
    """独立 coturn：需启用开关、共享密钥，且至少配置一条 TURN URL。"""
    if not TURN_ENABLED or not TURN_SHARED_SECRET:
        return False
    return bool(turn_urls_for_region(region) or TURN_UDP_URL or TURN_TLS_URL)


def _turn_rest_credential(secret: str, username: str) -> str:
    """coturn static-auth-secret：password = base64(hmac_sha1(secret, username))。"""
    digest = hmac.new(
        secret.encode("utf-8"), username.encode("utf-8"), hashlib.sha1
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def build_turn_ice_servers(identity: str, region: str = "global") -> list[dict[str, Any]]:
    """
    生成浏览器 RTCPeerConnection.iceServers 兼容结构。
    identity 建议使用稳定字符串（如 host:uid / viewer:uid / anon:...），与 coturn 审计一致。
    """
    if not turn_configured(region):
        return []
    urls: list[str] = []
    urls.extend(turn_urls_for_region(region))
    if not urls and TURN_UDP_URL:
        urls.append(TURN_UDP_URL)
    if not urls and TURN_TLS_URL:
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


def _stable_bucket(seed: str) -> int:
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def _interactive_available() -> bool:
    return get_managed_livekit_provider() is not None


def _broadcast_available(region: str) -> bool:
    return bool(hls_manifest_for_username("__probe__", region))


def media_backend_summary(headers: Optional[Mapping[str, str]] = None) -> dict[str, Any]:
    edge = edge_region_context(headers)
    region = edge["region"]
    livekit_ok = livekit_ready()
    preferred_realtime = (
        "webrtc"
        if LIVE_MEDIA_BACKEND == "livekit" and livekit_ok and LIVE_PLAYBACK_MODE == "webrtc"
        else LIVE_PLAYBACK_MODE
    )
    tc = turn_configured(region)
    return {
        "backend": LIVE_MEDIA_BACKEND,
        "publish_mode": LIVE_PUBLISH_MODE,
        "playback_mode": LIVE_PLAYBACK_MODE,
        "preferred_realtime_mode": preferred_realtime,
        "fallback_enabled": LIVE_FALLBACK_ENABLED,
        "fallback_mode": LIVE_FALLBACK_MODE,
        "preview_mode": "jpeg_snapshot",
        "signaling_url": LIVE_SIGNALING_URL,
        "turn_urls": turn_urls_for_region(region),
        "turn_enabled": tc,
        "turn_realm": TURN_REALM,
        "turn_mode": "rest" if tc else "off",
        # 不含凭证；完整 ice_servers 仅由 host-session / viewer-session 返回
        "ice_servers": [],
        "stack": {
            "name": LIVE_VENDOR_STACK,
            "managed": True,
            "interactive_vendor": LIVE_INTERACTIVE_VENDOR,
            "broadcast_vendor": LIVE_BROADCAST_VENDOR,
            "recording_vendor": LIVE_RECORDING_VENDOR,
        },
        "routing": {
            "migration_mode": LIVE_MIGRATION_MODE,
            "default_viewer_intent": LIVE_DEFAULT_VIEWER_INTENT,
            "interactive_rollout_percent": LIVE_INTERACTIVE_ROLLOUT_PERCENT,
            "interactive_authenticated_only": LIVE_INTERACTIVE_AUTHENTICATED_ONLY,
            "canary_users": LIVE_CANARY_USERS,
            "canary_countries": LIVE_CANARY_COUNTRIES,
            "force_broadcast_countries": LIVE_FORCE_BROADCAST_COUNTRIES,
            "force_interactive_users": LIVE_FORCE_INTERACTIVE_USERS,
        },
        "edge": edge,
        "planes": {
            "interactive": {
                "enabled": _interactive_available(),
                "mode": "webrtc",
                "provider": LIVE_INTERACTIVE_VENDOR,
                "region": region,
                "ws_url": livekit_ws_url_for_region(region),
            },
            "broadcast": {
                "enabled": _broadcast_available(region),
                "mode": "hls",
                "provider": LIVE_BROADCAST_VENDOR,
                "region": region,
            },
            "fallback": {
                "enabled": LIVE_FALLBACK_ENABLED,
                "mode": LIVE_FALLBACK_MODE,
                "provider": "legacy_jpeg",
            },
        },
        "recording": {
            "enabled": True,
            "provider": LIVE_RECORDING_VENDOR,
        },
        "livekit": {
            "enabled": LIVE_MEDIA_BACKEND == "livekit" or "livekit" in LIVE_INTERACTIVE_VENDOR,
            "ready": livekit_ok,
            "ws_url": livekit_ws_url_for_region(region),
        },
    }


def _viewer_delivery(
    *,
    host: User,
    viewer: Optional[User],
    headers: Optional[Mapping[str, str]],
    intent: Optional[str],
) -> dict[str, Any]:
    edge = edge_region_context(headers)
    region = edge["region"]
    country = edge["country"]
    requested_intent = (intent or LIVE_DEFAULT_VIEWER_INTENT or "auto").strip().lower()
    if requested_intent not in {"auto", "interactive", "broadcast"}:
        requested_intent = "auto"
    interactive_ready = _interactive_available()
    broadcast_ready = _broadcast_available(region)
    viewer_name = (viewer.username if viewer else "").strip().lower()
    force_interactive = viewer_name in {u.lower() for u in LIVE_FORCE_INTERACTIVE_USERS}
    force_broadcast = country in set(LIVE_FORCE_BROADCAST_COUNTRIES)
    canary_user = viewer_name in {u.lower() for u in LIVE_CANARY_USERS}
    canary_country = country in set(LIVE_CANARY_COUNTRIES)
    seed = viewer.id if viewer else f"anon:{host.username}:{country or region}"
    bucket = _stable_bucket(seed)
    rollout_ok = (
        force_interactive
        or canary_user
        or canary_country
        or bucket < LIVE_INTERACTIVE_ROLLOUT_PERCENT
    )
    interactive_allowed = (
        interactive_ready
        and rollout_ok
        and (viewer is not None or not LIVE_INTERACTIVE_AUTHENTICATED_ONLY)
    )
    selected = "fallback"
    reason = "fallback_only"
    if LIVE_MIGRATION_MODE == "legacy_only":
        selected = "fallback"
        reason = "legacy_only"
    elif LIVE_MIGRATION_MODE == "broadcast_only":
        if broadcast_ready:
            selected = "broadcast"
            reason = "broadcast_only"
    elif LIVE_MIGRATION_MODE == "interactive_only":
        if interactive_allowed:
            selected = "interactive"
            reason = "interactive_only"
        elif broadcast_ready:
            selected = "broadcast"
            reason = "interactive_denied_fallback_broadcast"
    else:
        if force_broadcast and broadcast_ready:
            selected = "broadcast"
            reason = "forced_broadcast_country"
        elif requested_intent == "interactive" and interactive_allowed:
            selected = "interactive"
            reason = "viewer_requested_interactive"
        elif requested_intent == "broadcast" and broadcast_ready:
            selected = "broadcast"
            reason = "viewer_requested_broadcast"
        elif viewer is not None and interactive_allowed:
            selected = "interactive"
            reason = "managed_hybrid_interactive"
        elif broadcast_ready:
            selected = "broadcast"
            reason = "managed_hybrid_broadcast"
        elif interactive_allowed:
            selected = "interactive"
            reason = "broadcast_unavailable_promote_interactive"
    return {
        "selected_plane": selected,
        "requested_intent": requested_intent,
        "reason": reason,
        "interactive_allowed": interactive_allowed,
        "broadcast_ready": broadcast_ready,
        "edge": edge,
        "rollout": {
            "bucket": bucket,
            "rollout_percent": LIVE_INTERACTIVE_ROLLOUT_PERCENT,
            "canary_user": canary_user,
            "canary_country": canary_country,
            "force_interactive": force_interactive,
            "force_broadcast": force_broadcast,
            "migration_mode": LIVE_MIGRATION_MODE,
        },
    }


def stream_media_descriptor(
    username: str,
    stream: Optional[LiveStream],
    headers: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    edge = edge_region_context(headers)
    region = edge["region"]
    room = room_name_for_username(username)
    hls = hls_manifest_for_username(username, region)
    live = bool(stream and stream.is_live)
    return {
        **media_backend_summary(headers),
        "room_name": room,
        "is_live": live,
        "hls_manifest_url": hls,
        "legacy": legacy_transport_for_username(username),
        "publish": {
            "primary_plane": "interactive",
            "preview_plane": "preview",
            "broadcast_plane": "broadcast",
        },
        "preview": {
            "mode": "jpeg_snapshot",
            "source": "push-frame",
            "list_cards": True,
            "fallback_watch": True,
            "storage": "process_memory",
            "region": region,
        },
        "tracks": {
            "video": ["screen", "camera"],
            "audio": ["page", "mic"],
        },
    }


def host_session_payload(
    user: User,
    stream: LiveStream,
    headers: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    edge = edge_region_context(headers)
    region = edge["region"]
    room = room_name_for_username(user.username)
    payload = {
        **stream_media_descriptor(user.username, stream, headers),
        "role": "host",
        "identity": f"host:{user.id}",
        "egress": {
            "broadcast_provider": LIVE_BROADCAST_VENDOR,
            "recording_provider": LIVE_RECORDING_VENDOR,
            "hls_manifest_url": hls_manifest_for_username(user.username, region),
            "recording_enabled": True,
        },
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
    lk = get_managed_livekit_provider()
    apply_session_provider_metadata(payload, interactive_active=bool(lk))
    if lk:
        lk.attach_host_session(payload, user=user, stream=stream, region=region, room=room)
    payload["planes"]["interactive"]["room_name"] = room
    payload["planes"]["broadcast"]["manifest_url"] = hls_manifest_for_username(user.username, region)
    return payload


def viewer_session_payload(
    host: User,
    stream: Optional[LiveStream],
    viewer: Optional[User] = None,
    headers: Optional[Mapping[str, str]] = None,
    intent: Optional[str] = None,
) -> dict[str, Any]:
    delivery = _viewer_delivery(host=host, viewer=viewer, headers=headers, intent=intent)
    edge = delivery["edge"]
    region = edge["region"]
    room = room_name_for_username(host.username)
    # 匿名观众必须每人独立 identity，否则会在 SFU 内互踢
    if viewer:
        identity = f"viewer:{viewer.id}"
    else:
        identity = f"anon:{host.username}:{uuid.uuid4().hex[:12]}"
    payload = {
        **stream_media_descriptor(host.username, stream, headers),
        "role": "viewer",
        "identity": identity,
        "delivery": delivery,
        "session_token": uuid.uuid4().hex[:24],
    }
    payload["planes"]["interactive"]["room_name"] = room
    payload["planes"]["broadcast"]["manifest_url"] = hls_manifest_for_username(host.username, region)
    lk = get_managed_livekit_provider()
    will_attach = bool(lk and stream and stream.is_live and delivery["interactive_allowed"])
    apply_session_provider_metadata(payload, interactive_active=will_attach)
    if will_attach and lk:
        lk.attach_viewer_session(
            payload,
            host=host,
            viewer=viewer,
            stream=stream,
            delivery=delivery,
            identity=identity,
            region=region,
            room=room,
        )
    return payload
