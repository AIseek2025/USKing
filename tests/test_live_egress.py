import unittest
import sys
import types
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_fake_jose = types.ModuleType("jose")
_fake_jose.jwt = types.SimpleNamespace(encode=lambda *args, **kwargs: "token", decode=lambda *args, **kwargs: {})
_fake_jose.JWTError = Exception
sys.modules["jose"] = _fake_jose

from server import api, live_observability, models
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


if __name__ == "__main__":
    unittest.main()
