import sys
import types
import unittest
from types import SimpleNamespace
from unittest import mock

_fake_jose = types.ModuleType("jose")
_fake_jose.jwt = types.SimpleNamespace(encode=lambda *args, **kwargs: "signed-jwt")
sys.modules.setdefault("jose", _fake_jose)

from server import live_media_providers as lmp


class LiveMediaProvidersTests(unittest.TestCase):
    def test_legacy_fallback_not_interactive(self):
        p = lmp.LegacyFallbackProvider()
        self.assertFalse(p.interactive_ready())
        payload: dict = {}
        p.attach_host_session(
            payload,
            user=SimpleNamespace(id=1, username="u", display_name="U"),
            stream=SimpleNamespace(is_live=True),
            region="us",
            room="r",
        )
        self.assertNotIn("livekit", payload)

    def test_apply_session_provider_metadata(self):
        payload: dict = {}
        lmp.apply_session_provider_metadata(payload, interactive_active=True)
        self.assertEqual(payload["providers"]["interactive"]["id"], "managed_livekit")
        self.assertTrue(payload["providers"]["interactive"]["active"])
        self.assertEqual(payload["providers"]["fallback"]["id"], "legacy_jpeg")

    @mock.patch.object(lmp, "_livekit_access_token", return_value="jwt-token")
    @mock.patch("server.live_media.livekit_ws_url_for_region", return_value="wss://lk.example/ws")
    @mock.patch("server.live_media.build_turn_ice_servers", return_value=[{"urls": ["turn:1"]}])
    def test_managed_livekit_host_session(self, _ice, _ws, _tok):
        user = SimpleNamespace(id=42, username="hoster", display_name="Hoster")
        stream = SimpleNamespace(is_live=True)
        payload: dict = {}
        p = lmp.ManagedLiveKitProvider()
        p.attach_host_session(payload, user=user, stream=stream, region="eu", room="usking-live-hoster")
        self.assertEqual(payload["livekit"]["token"], "jwt-token")
        self.assertEqual(payload["livekit"]["ws_url"], "wss://lk.example/ws")
        self.assertEqual(payload["ice_servers"], [{"urls": ["turn:1"]}])

    @mock.patch.object(lmp, "_livekit_access_token", return_value="v-jwt")
    @mock.patch("server.live_media.livekit_ws_url_for_region", return_value="wss://lk/ws")
    @mock.patch("server.live_media.build_turn_ice_servers", return_value=[])
    def test_managed_livekit_viewer_session(self, _ice, _ws, _tok):
        host = SimpleNamespace(id=1, username="h", display_name="H")
        viewer = SimpleNamespace(id=2, username="v", display_name="V")
        stream = SimpleNamespace(is_live=True)
        payload: dict = {}
        p = lmp.ManagedLiveKitProvider()
        p.attach_viewer_session(
            payload,
            host=host,
            viewer=viewer,
            stream=stream,
            delivery={"interactive_allowed": True},
            identity="viewer:2",
            region="us",
            room="usking-live-h",
        )
        self.assertEqual(payload["livekit"]["token"], "v-jwt")

    @mock.patch.object(lmp.ManagedLiveKitProvider, "interactive_ready", return_value=False)
    def test_get_managed_returns_none_when_not_ready(self, _ir):
        self.assertIsNone(lmp.get_managed_livekit_provider())


if __name__ == "__main__":
    unittest.main()
