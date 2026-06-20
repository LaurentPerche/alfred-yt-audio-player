import json
import io
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch


with patch.dict("os.environ", {"alfred_workflow_data": tempfile.mkdtemp()}):
    from workflow import yt_audio_workflow


class YouTubeUrlTests(unittest.TestCase):
    def test_accepts_watch_url(self) -> None:
        self.assertEqual(
            yt_audio_workflow.normalized_youtube_url("https://www.youtube.com/watch?v=abc123"),
            "https://www.youtube.com/watch?v=abc123",
        )

    def test_accepts_short_url(self) -> None:
        self.assertEqual(
            yt_audio_workflow.normalized_youtube_url("https://youtu.be/abc123?t=4"),
            "https://www.youtube.com/watch?v=abc123",
        )

    def test_accepts_url_without_scheme(self) -> None:
        self.assertEqual(
            yt_audio_workflow.normalized_youtube_url("www.youtube.com/watch?v=abc123"),
            "https://www.youtube.com/watch?v=abc123",
        )

    def test_recovers_mangled_pasted_url(self) -> None:
        self.assertEqual(
            yt_audio_workflow.normalized_youtube_url("s://www.youtube.com/watch?v=abc123"),
            "https://www.youtube.com/watch?v=abc123",
        )

    def test_rejects_non_youtube_url(self) -> None:
        self.assertFalse(yt_audio_workflow.is_youtube_url("https://example.com/watch?v=abc123"))


class FilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.data_dir = Path(self.tempdir.name)

    def patch_data_dir(self):
        return patch.object(yt_audio_workflow, "workflow_data_dir", return_value=self.data_dir)

    def patch_paths(self):
        return patch.multiple(
            yt_audio_workflow,
            STATE_PATH=self.data_dir / "state.json",
            HISTORY_PATH=self.data_dir / "history.json",
            YTDLP_BIN="/bin/echo",
            FFPLAY_BIN="/bin/echo",
        )

    def test_filter_uses_typed_url(self) -> None:
        with self.patch_data_dir(), self.patch_paths():
            payload = yt_audio_workflow.filter_items("https://youtu.be/abc123")
        self.assertEqual(payload["items"][0]["title"], "Play typed URL")
        self.assertEqual(
            json.loads(payload["items"][0]["arg"]),
            {"action": "play", "value": "https://www.youtube.com/watch?v=abc123"},
        )

    def test_filter_uses_clipboard_and_history(self) -> None:
        now = datetime.now()
        history = [
            {"url": "https://www.youtube.com/watch?v=first", "title": "First", "played_at": int(now.timestamp())},
            {
                "url": "https://www.youtube.com/watch?v=second",
                "title": "Second",
                "played_at": int((now - timedelta(days=1)).timestamp()),
            },
        ]
        with self.patch_data_dir(), self.patch_paths():
            (self.data_dir / "history.json").write_text(json.dumps(history))
            with patch.object(yt_audio_workflow, "clipboard_text", return_value="https://youtu.be/abc123"):
                payload = yt_audio_workflow.filter_items("")
        self.assertEqual(payload["items"][0]["title"], "Play clipboard URL")
        self.assertEqual(payload["items"][1]["title"], "Recent: First")
        self.assertEqual(payload["items"][2]["title"], "Recent: Second")
        self.assertEqual(payload["items"][1]["subtitle"], "Played today")
        self.assertEqual(payload["items"][2]["subtitle"], "Played yesterday")
        self.assertNotIn("youtube.com", payload["items"][1]["subtitle"])

    def test_filter_shows_pause_and_stop_controls_when_active(self) -> None:
        state = {
            "pid": 1234,
            "url": "https://www.youtube.com/watch?v=active",
            "title": "Active Video",
            "started_at": 1,
            "paused": False,
        }
        with self.patch_data_dir(), self.patch_paths():
            (self.data_dir / "state.json").write_text(json.dumps(state))
            with patch.object(yt_audio_workflow, "process_alive", return_value=True):
                payload = yt_audio_workflow.filter_items("https://youtu.be/abc123")
        self.assertEqual(payload["items"][0]["title"], "Play typed URL")
        self.assertEqual(payload["items"][1]["title"], "Pause current audio")
        self.assertEqual(payload["items"][2]["title"], "Stop current audio")
        self.assertIn("icon", payload["items"][1])
        self.assertIn("icon", payload["items"][2])

    def test_filter_shows_resume_when_paused(self) -> None:
        state = {
            "pid": 1234,
            "url": "https://www.youtube.com/watch?v=active",
            "title": "Active Video",
            "started_at": 1,
            "paused": True,
        }
        with self.patch_data_dir(), self.patch_paths():
            (self.data_dir / "state.json").write_text(json.dumps(state))
            with patch.object(yt_audio_workflow, "process_alive", return_value=True):
                payload = yt_audio_workflow.filter_items("")
        self.assertEqual(payload["items"][0]["title"], "Resume current audio")

    def test_active_recent_item_only_shows_status_not_url(self) -> None:
        history = [
            {"url": "https://www.youtube.com/watch?v=active", "title": "Active Video", "played_at": 1},
        ]
        state = {
            "pid": 1234,
            "url": "https://www.youtube.com/watch?v=active",
            "title": "Active Video",
            "started_at": 1,
            "paused": False,
        }
        with self.patch_data_dir(), self.patch_paths():
            (self.data_dir / "history.json").write_text(json.dumps(history))
            (self.data_dir / "state.json").write_text(json.dumps(state))
            with patch.object(yt_audio_workflow, "process_alive", return_value=True):
                with patch.object(yt_audio_workflow, "clipboard_text", return_value=""):
                    payload = yt_audio_workflow.filter_items("")
        recent_item = next(item for item in payload["items"] if item["title"] == "Recent: Active Video")
        self.assertEqual(recent_item["subtitle"], "Currently playing")

    def test_filter_shows_invalid_clipboard_message(self) -> None:
        with self.patch_data_dir(), self.patch_paths():
            with patch.object(yt_audio_workflow, "clipboard_text", return_value="not a url"):
                payload = yt_audio_workflow.filter_items("")
        self.assertEqual(payload["items"][0]["title"], "Clipboard does not contain a YouTube URL")
        self.assertFalse(payload["items"][0]["valid"])


class HistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.data_dir = Path(self.tempdir.name)

    def patch_paths(self):
        return patch.multiple(
            yt_audio_workflow,
            STATE_PATH=self.data_dir / "state.json",
            HISTORY_PATH=self.data_dir / "history.json",
        )

    def test_update_history_deduplicates_and_limits(self) -> None:
        seed = [
            {"url": f"https://www.youtube.com/watch?v={idx}", "title": f"Video {idx}", "played_at": idx}
            for idx in range(5)
        ]
        with self.patch_paths():
            (self.data_dir / "history.json").write_text(json.dumps(seed))
            yt_audio_workflow.update_history("https://www.youtube.com/watch?v=2", "Video 2")
            yt_audio_workflow.update_history("https://www.youtube.com/watch?v=new", "New Video")

            history = json.loads((self.data_dir / "history.json").read_text())

        self.assertEqual(len(history), 5)
        self.assertEqual(history[0]["url"], "https://www.youtube.com/watch?v=new")
        self.assertEqual(history[1]["url"], "https://www.youtube.com/watch?v=2")


class DispatchTests(unittest.TestCase):
    def test_dispatch_routes_play(self) -> None:
        with patch.object(yt_audio_workflow, "command_play", return_value=0) as command_play:
            result = yt_audio_workflow.command_dispatch(
                [json.dumps({"action": "play", "value": "https://www.youtube.com/watch?v=abc123"})]
            )
        self.assertEqual(result, 0)
        command_play.assert_called_once_with(["https://www.youtube.com/watch?v=abc123"])

    def test_dispatch_routes_pause(self) -> None:
        with patch.object(yt_audio_workflow, "command_pause", return_value=0) as command_pause:
            result = yt_audio_workflow.command_dispatch([json.dumps({"action": "pause", "value": ""})])
        self.assertEqual(result, 0)
        command_pause.assert_called_once_with([])

    def test_dispatch_reads_stdin_when_no_arg_is_passed(self) -> None:
        payload = json.dumps({"action": "play", "value": "https://www.youtube.com/watch?v=abc123"})
        with patch.object(yt_audio_workflow, "command_play", return_value=0) as command_play:
            with patch("sys.stdin", io.StringIO(payload)):
                result = yt_audio_workflow.command_dispatch([])
        self.assertEqual(result, 0)
        command_play.assert_called_once_with(["https://www.youtube.com/watch?v=abc123"])


if __name__ == "__main__":
    unittest.main()
