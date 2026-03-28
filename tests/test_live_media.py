import unittest
from types import SimpleNamespace
from unittest import mock
import sys
import types


_fake_jose = types.ModuleType("jose")
_fake_jose.jwt = types.SimpleNamespace(encode=lambda *args, **kwargs: "token")
sys.modules.setdefault("jose", _fake_jose)

from server import live_media


class LiveMediaRoutingTests(unittest.TestCase):
    def test_edge_region_context_uses_country_header(self):
        ctx = live_media.edge_region_context({"cf-ipcountry": "SG"})
        self.assertEqual(ctx["country"], "SG")
        self.assertEqual(ctx["region"], "apac")

    def test_hls_manifest_prefers_regional_base(self):
        with mock.patch.object(
            live_media,
            "LIVE_HLS_REGION_BASE_URLS",
            {"apac": "https://apac-cdn.example.com/live"},
        ):
            url = live_media.hls_manifest_for_username("brando", "apac")
        self.assertEqual(url, "https://apac-cdn.example.com/live/brando/master.m3u8")

    def test_viewer_delivery_forced_broadcast_country(self):
        host = SimpleNamespace(id="host1", username="hoster", display_name="Hoster")
        viewer = SimpleNamespace(id="viewer1", username="viewer", display_name="Viewer")
        with mock.patch.object(live_media, "LIVE_FORCE_BROADCAST_COUNTRIES", ["CN"]), mock.patch.object(
            live_media, "LIVE_INTERACTIVE_ROLLOUT_PERCENT", 100
        ), mock.patch.object(live_media, "_interactive_available", return_value=True), mock.patch.object(
            live_media, "_broadcast_available", return_value=True
        ):
            delivery = live_media._viewer_delivery(
                host=host,
                viewer=viewer,
                headers={"cf-ipcountry": "CN"},
                intent="auto",
            )
        self.assertEqual(delivery["selected_plane"], "broadcast")
        self.assertEqual(delivery["reason"], "forced_broadcast_country")


if __name__ == "__main__":
    unittest.main()
