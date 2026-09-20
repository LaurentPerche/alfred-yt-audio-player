import json
import io
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch


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
            SETTINGS_PATH=self.data_dir / "settings.json",
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
            {
                "url": "https://www.youtube.com/watch?v=first",
                "title": "First",
                "display_title": "First",
                "play_count": 3,
                "played_at": int(now.timestamp()),
            },
            {
                "url": "https://www.youtube.com/watch?v=second",
                "title": "Second",
                "display_title": "Second",
                "play_count": 1,
                "played_at": int((now - timedelta(days=1)).timestamp()),
            },
        ]
        with self.patch_data_dir(), self.patch_paths():
            (self.data_dir / "history.json").write_text(json.dumps(history))
            with patch.object(yt_audio_workflow, "clipboard_text", return_value="https://youtu.be/abc123"):
                payload = yt_audio_workflow.filter_items("")
        self.assertEqual(payload["items"][0]["title"], "Play clipboard URL")
        self.assertEqual(payload["items"][1]["title"], "Audio level: Max")
        self.assertEqual(payload["items"][2]["title"], "First")
        self.assertEqual(payload["items"][3]["title"], "Second")
        self.assertEqual(payload["items"][2]["subtitle"], "3 plays")
        self.assertEqual(payload["items"][3]["subtitle"], "Played yesterday • 1 play")
        self.assertNotIn("youtube.com", payload["items"][2]["subtitle"])
        self.assertNotEqual(
            payload["items"][2]["icon"]["path"],
            payload["items"][3]["icon"]["path"],
        )

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
            {
                "url": "https://www.youtube.com/watch?v=active",
                "title": "Active Video",
                "display_title": "Active Video",
                "play_count": 4,
                "played_at": 1,
            },
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
        recent_item = next(item for item in payload["items"] if item["title"] == "Active Video")
        self.assertEqual(recent_item["subtitle"], "Currently playing • 4 plays")

    def test_recent_items_fall_back_to_original_title_for_older_history(self) -> None:
        now = datetime.now()
        history = [
            {
                "url": "https://www.youtube.com/watch?v=legacy",
                "title": "Legacy Title",
                "played_at": int(now.timestamp()),
            },
        ]
        with self.patch_data_dir(), self.patch_paths():
            (self.data_dir / "history.json").write_text(json.dumps(history))
            with patch.object(yt_audio_workflow, "clipboard_text", return_value=""):
                payload = yt_audio_workflow.filter_items("")
        recent_item = next(item for item in payload["items"] if item["title"] == "Legacy Title")
        self.assertEqual(recent_item["subtitle"], "Played today")

    def test_quick_picks_are_limited_to_top_three_and_removed_from_recents(self) -> None:
        now = datetime.now()
        history = [
            {
                "url": f"https://www.youtube.com/watch?v={index}",
                "title": f"Video {index}",
                "display_title": f"Video {index}",
                "play_count": play_count,
                "played_at": int((now - timedelta(minutes=index)).timestamp()),
            }
            for index, play_count in enumerate((7, 6, 5, 4, 1), start=1)
        ]
        with self.patch_data_dir(), self.patch_paths():
            (self.data_dir / "history.json").write_text(json.dumps(history))
            with patch.object(yt_audio_workflow, "clipboard_text", return_value="https://youtu.be/abc123"):
                payload = yt_audio_workflow.filter_items("")

        quick_pick_titles = [item["title"] for item in payload["items"][2:5]]
        self.assertEqual(quick_pick_titles, ["Video 1", "Video 2", "Video 3"])
        self.assertEqual(payload["items"][2]["subtitle"], "7 plays")
        self.assertEqual(payload["items"][4]["subtitle"], "5 plays")
        remaining_titles = [item["title"] for item in payload["items"][5:]]
        self.assertEqual(remaining_titles, ["Video 4", "Video 5"])

    def test_filter_shows_invalid_clipboard_message(self) -> None:
        with self.patch_data_dir(), self.patch_paths():
            with patch.object(yt_audio_workflow, "clipboard_text", return_value="not a url"):
                payload = yt_audio_workflow.filter_items("")
        self.assertEqual(payload["items"][0]["title"], "Clipboard does not contain a YouTube URL")
        self.assertFalse(payload["items"][0]["valid"])

    def test_volume_query_shows_three_presets_and_current_level(self) -> None:
        with self.patch_data_dir(), self.patch_paths():
            (self.data_dir / "settings.json").write_text(json.dumps({"volume_level": "medium"}))
            payload = yt_audio_workflow.filter_items("volume")

        self.assertEqual([item["title"] for item in payload["items"]], ["Max", "Medium", "Low"])
        self.assertEqual(payload["items"][1]["subtitle"], "55% • Current level")
        self.assertEqual(
            json.loads(payload["items"][2]["arg"]),
            {"action": "set_volume", "value": "low"},
        )

    def test_volume_query_can_filter_to_one_preset(self) -> None:
        with self.patch_data_dir(), self.patch_paths():
            payload = yt_audio_workflow.filter_items("volume low")

        self.assertEqual([item["title"] for item in payload["items"]], ["Low"])


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
            {
                "url": f"https://www.youtube.com/watch?v={idx}",
                "title": f"Video {idx}",
                "display_title": f"Video {idx}",
                "play_count": 1,
                "played_at": idx,
            }
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
        self.assertEqual(history[0]["play_count"], 1)
        self.assertEqual(history[1]["play_count"], 2)
        self.assertEqual(history[0]["display_title"], "New Video")

    def test_update_history_generates_simplified_display_title(self) -> None:
        with self.patch_paths():
            yt_audio_workflow.update_history(
                "https://www.youtube.com/watch?v=raycast",
                "Introducing Raycast Dictation | Raycast",
            )
            history = json.loads((self.data_dir / "history.json").read_text())

        self.assertEqual(history[0]["title"], "Introducing Raycast Dictation | Raycast")
        self.assertEqual(history[0]["display_title"], "Introducing Raycast Dictation")
        self.assertEqual(history[0]["play_count"], 1)


class VolumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.data_dir = Path(self.tempdir.name)

    def patch_paths(self):
        return patch.multiple(
            yt_audio_workflow,
            STATE_PATH=self.data_dir / "state.json",
            HISTORY_PATH=self.data_dir / "history.json",
            SETTINGS_PATH=self.data_dir / "settings.json",
        )

    def test_default_level_preserves_full_volume(self) -> None:
        with self.patch_paths():
            self.assertEqual(yt_audio_workflow.load_volume_level(), "max")

    def test_selected_level_is_saved(self) -> None:
        with self.patch_paths():
            yt_audio_workflow.set_volume_level("LOW")
            self.assertEqual(yt_audio_workflow.load_volume_level(), "low")

    def test_start_playback_passes_selected_volume_to_ffplay(self) -> None:
        process = Mock(pid=4321)
        with self.patch_paths():
            yt_audio_workflow.set_volume_level("low")
            with patch.object(yt_audio_workflow, "dependency_errors", return_value=[]), patch.object(
                yt_audio_workflow, "stop_existing_playback"
            ), patch.object(yt_audio_workflow, "notify"), patch.object(
                yt_audio_workflow,
                "resolve_audio",
                return_value=("Test title", "https://stream.example/audio"),
            ), patch.object(yt_audio_workflow.subprocess, "Popen", return_value=process) as popen:
                yt_audio_workflow.start_playback("https://youtu.be/abc123")

        command = popen.call_args.args[0]
        self.assertEqual(command[command.index("-volume") + 1], "25")


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

    def test_dispatch_routes_volume_selection(self) -> None:
        with patch.object(yt_audio_workflow, "command_set_volume", return_value=0) as command_set_volume:
            result = yt_audio_workflow.command_dispatch(
                [json.dumps({"action": "set_volume", "value": "medium"})]
            )
        self.assertEqual(result, 0)
        command_set_volume.assert_called_once_with(["medium"])


if __name__ == "__main__":
    unittest.main()
