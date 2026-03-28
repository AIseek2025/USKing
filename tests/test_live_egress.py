import unittest
import sys
import types
import base64
import hashlib
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_fake_jose = types.ModuleType("jose")
_fake_jose.jwt = types.SimpleNamespace(encode=lambda *args, **kwargs: "token", decode=lambda *args, **kwargs: {})
_fake_jose.JWTError = Exception
sys.modules["jose"] = _fake_jose

from server import api, live_egress, live_observability, models
from server.database import Base


class LiveEgressTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.Session()
        self.host = models.User(username="hoster", email="hoster@example.com", hashed_password="x")
        self.db.add(self.host)
        self.db.commit()
        self.db.refresh(self.host)
        self.stream = models.LiveStream(
            user_id=self.host.id,
            title="Phase C Live",
            is_live=True,
            started_at=models.utcnow(),
        )
        self.db.add(self.stream)
        self.db.commit()
        self.db.refresh(self.stream)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_ensure_recording_jobs_keeps_running_status(self):
        live_observability.ensure_recording_jobs(
            self.db,
            stream=self.stream,
            host_username=self.host.username,
            room_name="room1",
            provider="livekit_egress",
            manifest_url="https://cdn.example.com/live/master.m3u8",
            enable_recording=True,
        )
        live_observability.update_recording_job(
            self.db,
            host_username=self.host.username,
            egress_type="hls",
            status="running",
            stream=self.stream,
            provider="livekit_egress",
            manifest_url="https://cdn.example.com/live/master.m3u8",
        )
        live_observability.ensure_recording_jobs(
            self.db,
            stream=self.stream,
            host_username=self.host.username,
            room_name="room1",
            provider="livekit_egress",
            manifest_url="https://cdn.example.com/live/master.m3u8",
            enable_recording=True,
        )
        rows = live_observability.list_recording_jobs(
            self.db, host_username=self.host.username, stream_id=self.stream.id, limit=10
        )
        hls = next(row for row in rows if row.egress_type == "hls")
        self.assertEqual(hls.status, "running")

    def test_egress_status_snapshot_marks_live_ready(self):
        live_observability.update_recording_job(
            self.db,
            host_username=self.host.username,
            egress_type="hls",
            status="running",
            stream=self.stream,
            provider="livekit_egress",
            manifest_url="https://cdn.example.com/live/master.m3u8",
        )
        live_observability.update_recording_job(
            self.db,
            host_username=self.host.username,
            egress_type="recording",
            status="completed",
            stream=self.stream,
            provider="livekit_egress",
            recording_url="https://cdn.example.com/live/recording.mp4",
        )
        snapshot = live_observability.egress_status_for_stream(
            self.db,
            stream=self.stream,
            host_username=self.host.username,
            fallback_manifest_url="https://fallback.example.com/master.m3u8",
        )
        self.assertTrue(snapshot["hls"]["live_ready"])
        self.assertEqual(snapshot["hls"]["manifest_url"], "https://cdn.example.com/live/master.m3u8")
        self.assertTrue(snapshot["recording"]["ready"])
        self.assertEqual(snapshot["recording"]["recording_url"], "https://cdn.example.com/live/recording.mp4")

    def test_broadcast_session_reroutes_to_interactive_when_hls_not_ready(self):
        session = {
            "fallback_enabled": True,
            "delivery": {
                "selected_plane": "broadcast",
                "interactive_allowed": True,
            },
            "livekit": {"token": "viewer-token"},
            "egress_status": {
                "hls": {"live_ready": False},
            },
        }
        result = api._reroute_unready_broadcast_session(session)
        self.assertEqual(result["delivery"]["selected_plane"], "interactive")
        self.assertEqual(result["delivery"]["reason"], "broadcast_not_ready_promote_interactive")

    def test_broadcast_session_reroutes_to_fallback_without_livekit(self):
        session = {
            "fallback_enabled": True,
            "delivery": {
                "selected_plane": "broadcast",
                "interactive_allowed": False,
            },
            "egress_status": {
                "hls": {"live_ready": False},
            },
        }
        result = api._reroute_unready_broadcast_session(session)
        self.assertEqual(result["delivery"]["selected_plane"], "fallback")
        self.assertEqual(result["delivery"]["reason"], "broadcast_not_ready_fallback_legacy")

    def test_livekit_status_mapping(self):
        self.assertEqual(live_egress._status_from_livekit("EGRESS_STARTING"), "starting")
        self.assertEqual(live_egress._status_from_livekit("EGRESS_ACTIVE"), "running")
        self.assertEqual(live_egress._status_from_livekit("EGRESS_COMPLETE"), "completed")
        self.assertEqual(live_egress._status_from_livekit("EGRESS_ABORTED"), "stopped")
        self.assertEqual(live_egress._status_from_livekit("EGRESS_FAILED"), "failed")

    def test_apply_livekit_webhook_updates_jobs_by_egress_id(self):
        live_observability.update_recording_job(
            self.db,
            host_username=self.host.username,
            egress_type="hls",
            status="starting",
            stream=self.stream,
            provider="livekit_egress",
            room_name="usking-live-hoster",
            manifest_url="https://usking.vip/live-hls/hoster/master.m3u8",
            detail_json=json.dumps({"egress_id": "EG_123"}, ensure_ascii=False),
        )
        live_observability.update_recording_job(
            self.db,
            host_username=self.host.username,
            egress_type="recording",
            status="starting",
            stream=self.stream,
            provider="livekit_egress",
            room_name="usking-live-hoster",
            recording_url="https://usking.vip/live-hls/hoster/recordings/stream-1.mp4",
            detail_json=json.dumps({"egress_id": "EG_123"}, ensure_ascii=False),
        )
        jobs = live_egress.apply_livekit_egress_webhook(
            self.db,
            {
                "event": "egress_updated",
                "egressInfo": {
                    "egress_id": "EG_123",
                    "room_name": "usking-live-hoster",
                    "status": "EGRESS_ACTIVE",
                    "segment_results": [
                        {"live_playlist_location": "https://cdn.example.com/live/master.m3u8"}
                    ],
                    "file_results": [
                        {"location": "https://cdn.example.com/live/recording.mp4"}
                    ],
                },
            },
        )
        self.assertEqual(len(jobs), 2)
        rows = live_observability.list_recording_jobs(
            self.db, host_username=self.host.username, stream_id=self.stream.id, limit=10
        )
        hls = next(row for row in rows if row.egress_type == "hls")
        recording = next(row for row in rows if row.egress_type == "recording")
        self.assertEqual(hls.status, "running")
        self.assertEqual(hls.manifest_url, "https://cdn.example.com/live/master.m3u8")
        self.assertEqual(recording.status, "running")
        self.assertEqual(recording.recording_url, "https://cdn.example.com/live/recording.mp4")

    def test_apply_livekit_webhook_normalizes_local_output_paths(self):
        live_observability.update_recording_job(
            self.db,
            host_username=self.host.username,
            egress_type="hls",
            status="starting",
            stream=self.stream,
            provider="livekit_egress",
            room_name="usking-live-hoster",
            manifest_url="https://usking.vip/live-hls/hoster/master.m3u8",
            detail_json=json.dumps({"egress_id": "EG_456"}, ensure_ascii=False),
        )
        live_observability.update_recording_job(
            self.db,
            host_username=self.host.username,
            egress_type="recording",
            status="starting",
            stream=self.stream,
            provider="livekit_egress",
            room_name="usking-live-hoster",
            recording_url="https://usking.vip/live-hls/hoster/recordings/stream-1.mp4",
            detail_json=json.dumps({"egress_id": "EG_456"}, ensure_ascii=False),
        )
        old_base = live_egress.LIVE_HLS_BASE_URL
        old_root = live_egress.LIVE_HLS_OUTPUT_DIR
        try:
            live_egress.LIVE_HLS_BASE_URL = "https://usking.vip/live-hls"
            live_egress.LIVE_HLS_OUTPUT_DIR = "/data/live-hls"
            live_egress.apply_livekit_egress_webhook(
                self.db,
                {
                    "event": "egress_ended",
                    "egressInfo": {
                        "egress_id": "EG_456",
                        "room_name": "usking-live-hoster",
                        "status": "EGRESS_COMPLETE",
                        "segment_results": [
                            {"live_playlist_location": "/data/live-hls/hoster/master.m3u8"}
                        ],
                        "file_results": [
                            {"location": "/data/live-hls/hoster/recordings/stream-1.mp4"}
                        ],
                    },
                },
            )
        finally:
            live_egress.LIVE_HLS_BASE_URL = old_base
            live_egress.LIVE_HLS_OUTPUT_DIR = old_root
        rows = live_observability.list_recording_jobs(
            self.db, host_username=self.host.username, stream_id=self.stream.id, limit=10
        )
        hls = next(row for row in rows if row.egress_type == "hls")
        recording = next(row for row in rows if row.egress_type == "recording")
        self.assertEqual(hls.manifest_url, "https://usking.vip/live-hls/hoster/master.m3u8")
        self.assertEqual(recording.recording_url, "https://usking.vip/live-hls/hoster/recordings/stream-1.mp4")

    def test_validate_livekit_webhook_checks_body_hash(self):
        raw = json.dumps({"event": "egress_started"}, separators=(",", ":")).encode("utf-8")
        sha = base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii")
        old_decode = live_egress.jwt.decode
        old_key = live_egress.LIVEKIT_API_KEY
        try:
            live_egress.LIVEKIT_API_KEY = "test-key"
            live_egress.jwt.decode = lambda *args, **kwargs: {"iss": "", "sha256": sha}
            with self.assertRaises(ValueError):
                live_egress.validate_livekit_webhook(raw, "Bearer token")
            live_egress.jwt.decode = lambda *args, **kwargs: {
                "iss": live_egress.LIVEKIT_API_KEY,
                "sha256": sha,
            }
            payload = live_egress.validate_livekit_webhook(raw, "Bearer token")
            self.assertEqual(payload["event"], "egress_started")
        finally:
            live_egress.LIVEKIT_API_KEY = old_key
            live_egress.jwt.decode = old_decode


if __name__ == "__main__":
    unittest.main()
