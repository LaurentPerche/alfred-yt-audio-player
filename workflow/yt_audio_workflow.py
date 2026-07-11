#!/usr/bin/env python3

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
import re
from shutil import which
from typing import Any
from urllib.parse import parse_qs, urlparse


APP_NAME = "Alfred YT Audio Player"
HISTORY_LIMIT = 5
QUICK_PICK_LIMIT = 3
DISPLAY_TITLE_LIMIT = 56
YTDLP_BIN = which("yt-dlp") or "/usr/local/bin/yt-dlp"
FFPLAY_BIN = which("ffplay") or "/usr/local/bin/ffplay"
PYTHON_BIN = sys.executable
WORKFLOW_ROOT = Path(__file__).resolve().parent
ICON_DIR = WORKFLOW_ROOT / "icons"
PLAY_ICON = {"path": str(ICON_DIR / "play-url.png")}
QUICK_PICK_ICON = {"path": str(ICON_DIR / "quick-pick.png")}
RECENT_ICON = {"path": str(ICON_DIR / "recent.png")}
PAUSE_ICON = {"path": str(ICON_DIR / "pause.png")}
RESUME_ICON = {"path": str(ICON_DIR / "resume.png")}
STOP_ICON = {"path": str(ICON_DIR / "stop.png")}
WARNING_ICON = {"path": str(ICON_DIR / "warning.png")}


def workflow_data_dir() -> Path:
    path = os.environ.get("alfred_workflow_data")
    if path:
        directory = Path(path)
    else:
        directory = Path.home() / "Library" / "Application Support" / "Alfred" / "Workflow Data" / APP_NAME
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        directory = Path(tempfile.gettempdir()) / APP_NAME
        directory.mkdir(parents=True, exist_ok=True)
    return directory


STATE_PATH = workflow_data_dir() / "state.json"
HISTORY_PATH = workflow_data_dir() / "history.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2))


def simplified_history_title(title: str) -> str:
    cleaned = " ".join(title.split()).strip()
    if not cleaned:
        return ""

    cleaned = re.sub(r"\s+-\s+YouTube$", "", cleaned, flags=re.IGNORECASE)
    for separator in (" | ", " - "):
        if separator not in cleaned:
            continue
        head, tail = cleaned.rsplit(separator, 1)
        if len(head.strip()) >= 12 and len(tail.strip()) <= 30:
            cleaned = head.strip()
            break

    if len(cleaned) <= DISPLAY_TITLE_LIMIT:
        return cleaned
    return f"{cleaned[: DISPLAY_TITLE_LIMIT - 3].rstrip()}..."


def youtube_video_id(raw: str) -> str | None:
    candidate = extract_youtube_candidate(raw)
    if not candidate:
        return None

    parsed = urlparse(candidate)
    host = parsed.netloc.lower()
    path = parsed.path

    if host in {"youtu.be", "www.youtu.be"}:
        value = path.strip("/")
        return value or None

    if host.endswith("youtube.com"):
        if path == "/watch":
            query = parse_qs(parsed.query).get("v", [])
            return query[0] if query else None
        if path.startswith("/shorts/") or path.startswith("/live/"):
            value = path.split("/", 2)[2]
            return value or None
    return None


def extract_youtube_candidate(raw: str) -> str:
    candidate = raw.strip()
    if not candidate:
        return ""

    # Alfred occasionally hands us a partially mangled pasted URL when the
    # keyword consumes part of the leading scheme. Recover the YouTube portion
    # from the visible text instead of requiring a perfectly formed URL.
    patterns = [
        r"((?:https?://)?(?:www\.)?youtube\.com/watch\?[^\s]+)",
        r"((?:https?://)?(?:www\.)?youtube\.com/(?:shorts|live)/[^\s?/&#]+)",
        r"((?:https?://)?(?:www\.)?youtu\.be/[^\s?/&#]+(?:\?[^\s]+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, candidate, re.IGNORECASE)
        if not match:
            continue
        extracted = match.group(1)
        if "://" not in extracted:
            return f"https://{extracted}"
        return extracted

    return candidate


def is_youtube_url(raw: str) -> bool:
    return youtube_video_id(raw) is not None


def normalized_youtube_url(raw: str) -> str:
    video_id = youtube_video_id(raw)
    if not video_id:
        raise ValueError("Not a supported YouTube URL")
    return f"https://www.youtube.com/watch?v={video_id}"


def clipboard_text() -> str:
    try:
        result = subprocess.run(
            ["pbpaste"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return result.stdout.strip()


def alfred_item(
    title: str,
    subtitle: str,
    arg: str | None = None,
    valid: bool = True,
    uid: str | None = None,
    variables: dict[str, str] | None = None,
    icon: dict[str, str] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "title": title,
        "subtitle": subtitle,
        "valid": valid,
    }
    if arg is not None:
        item["arg"] = arg
    if uid is not None:
        item["uid"] = uid
    if variables:
        item["variables"] = variables
    if icon:
        item["icon"] = icon
    return item


def action_arg(action: str, value: str = "") -> str:
    return json.dumps({"action": action, "value": value})


def load_history() -> list[dict[str, Any]]:
    history = load_json(HISTORY_PATH, [])
    if not isinstance(history, list):
        return []
    return [entry for entry in history if isinstance(entry, dict) and entry.get("url")]


def current_state() -> dict[str, Any]:
    state = load_json(STATE_PATH, {})
    if not isinstance(state, dict):
        return {}

    pid = state.get("pid")
    if not isinstance(pid, int):
        return {}

    if process_alive(pid):
        return state

    clear_state()
    return {}


def clear_state() -> None:
    if STATE_PATH.exists():
        STATE_PATH.unlink()


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def stop_existing_playback() -> None:
    state = load_json(STATE_PATH, {})
    if not isinstance(state, dict):
        clear_state()
        return

    pid = state.get("pid")
    if not isinstance(pid, int):
        clear_state()
        return

    if not process_alive(pid):
        clear_state()
        return

    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        clear_state()
        return
    except PermissionError:
        os.kill(pid, signal.SIGTERM)

    deadline = time.time() + 3
    while time.time() < deadline and process_alive(pid):
        time.sleep(0.1)

    if process_alive(pid):
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            os.kill(pid, signal.SIGKILL)

    clear_state()


def update_state(**updates: Any) -> dict[str, Any]:
    state = current_state()
    if not state:
        return {}
    state.update(updates)
    save_json(STATE_PATH, state)
    return state


def pause_playback() -> dict[str, Any]:
    state = current_state()
    if not state:
        raise RuntimeError("No active playback to pause")
    if state.get("paused"):
        return state

    pid = state["pid"]
    try:
        os.killpg(pid, signal.SIGSTOP)
    except ProcessLookupError as exc:
        clear_state()
        raise RuntimeError("Playback process is no longer running") from exc
    except PermissionError:
        os.kill(pid, signal.SIGSTOP)

    return update_state(paused=True)


def resume_playback() -> dict[str, Any]:
    state = current_state()
    if not state:
        raise RuntimeError("No paused playback to resume")
    if not state.get("paused"):
        return state

    pid = state["pid"]
    try:
        os.killpg(pid, signal.SIGCONT)
    except ProcessLookupError as exc:
        clear_state()
        raise RuntimeError("Playback process is no longer running") from exc
    except PermissionError:
        os.kill(pid, signal.SIGCONT)

    return update_state(paused=False)


def update_history(url: str, title: str) -> None:
    now = int(time.time())
    existing = next((entry for entry in load_history() if entry.get("url") == url), {})
    history = [entry for entry in load_history() if entry.get("url") != url]
    history.insert(
        0,
        {
            "url": url,
            "title": title,
            "display_title": simplified_history_title(title) or title,
            "play_count": int(existing.get("play_count", 0)) + 1,
            "played_at": now,
        },
    )
    save_json(HISTORY_PATH, history[:HISTORY_LIMIT])


def played_label(played_at: Any) -> str:
    if not isinstance(played_at, int):
        return "Played recently"

    played_dt = datetime.fromtimestamp(played_at)
    now = datetime.now()
    days_ago = (now.date() - played_dt.date()).days
    if days_ago <= 0:
        return "Played today"
    if days_ago == 1:
        return "Played yesterday"
    return f"Played on {played_dt.strftime('%b %d')}"


def dependency_errors() -> list[str]:
    missing = []
    for binary in (YTDLP_BIN, FFPLAY_BIN):
        if not Path(binary).exists():
            missing.append(binary)
    return missing


def play_count_label(value: Any) -> str:
    if not isinstance(value, int) or value < 1:
        return ""
    if value == 1:
        return "1 play"
    return f"{value} plays"


def quick_pick_entries() -> list[dict[str, Any]]:
    picks = []
    ranked = sorted(
        load_history(),
        key=lambda entry: (
            -int(entry.get("play_count", 0)),
            -int(entry.get("played_at", 0)),
        ),
    )
    for entry in ranked:
        if int(entry.get("play_count", 0)) < 2:
            continue
        picks.append(entry)
        if len(picks) >= QUICK_PICK_LIMIT:
            break
    return picks


def history_item(
    entry: dict[str, Any],
    *,
    active_url: str | None,
    active_paused: bool,
    icon: dict[str, str],
    uid_prefix: str,
    prefer_play_count: bool,
) -> dict[str, Any]:
    title = entry.get("display_title") or entry.get("title") or entry["url"]
    count_label = play_count_label(entry.get("play_count"))

    if entry.get("url") == active_url:
        status = "Currently paused" if active_paused else "Currently playing"
        subtitle = status if not count_label else f"{status} • {count_label}"
    elif prefer_play_count and count_label:
        subtitle = count_label
    else:
        subtitle = played_label(entry.get("played_at"))
        if count_label:
            subtitle = f"{subtitle} • {count_label}"

    return alfred_item(
        title=title,
        subtitle=subtitle,
        arg=action_arg("play", entry["url"]),
        uid=f"{uid_prefix}::{entry['url']}",
        icon=icon,
    )


def recent_items(excluded_urls: set[str] | None = None) -> list[dict[str, Any]]:
    items = []
    excluded_urls = excluded_urls or set()
    state = current_state()
    active_url = state.get("url")
    active_paused = bool(state.get("paused"))
    for entry in load_history()[:HISTORY_LIMIT]:
        if entry.get("url") in excluded_urls:
            continue
        items.append(
            history_item(
                entry,
                active_url=active_url,
                active_paused=active_paused,
                icon=RECENT_ICON,
                uid_prefix="recent",
                prefer_play_count=False,
            )
        )
    return items


def active_control_items() -> list[dict[str, Any]]:
    state = current_state()
    if not state:
        return []

    title = state.get("title") or state.get("url") or "Current audio"
    paused = bool(state.get("paused"))
    items = [
        alfred_item(
            title="Resume current audio" if paused else "Pause current audio",
            subtitle=title,
            arg=action_arg("resume" if paused else "pause"),
            uid="control::toggle-pause",
            icon=RESUME_ICON if paused else PAUSE_ICON,
        ),
        alfred_item(
            title="Stop current audio",
            subtitle=title,
            arg=action_arg("stop"),
            uid="control::stop",
            icon=STOP_ICON,
        ),
    ]
    return items


def filter_items(query: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    missing = dependency_errors()
    if missing:
        joined = ", ".join(missing)
        items.append(
            alfred_item(
                title="Missing required dependency",
                subtitle=f"Install or expose these binaries in PATH: {joined}",
                valid=False,
                icon=WARNING_ICON,
            )
        )
        return {"items": items}

    controls = active_control_items()
    state = current_state()
    active_url = state.get("url")
    active_paused = bool(state.get("paused"))
    quick_pick_data = quick_pick_entries()
    quick_pick_urls = {entry["url"] for entry in quick_pick_data}
    quick_picks = [
        history_item(
            entry,
            active_url=active_url,
            active_paused=active_paused,
            icon=QUICK_PICK_ICON,
            uid_prefix="quick",
            prefer_play_count=True,
        )
        for entry in quick_pick_data
    ]
    recent = recent_items(quick_pick_urls)

    trimmed = query.strip()
    if trimmed:
        if is_youtube_url(trimmed):
            normalized = normalized_youtube_url(trimmed)
            items.append(
                alfred_item(
                    title="Play typed URL",
                    subtitle=normalized,
                    arg=action_arg("play", normalized),
                    uid=f"typed::{normalized}",
                    icon=PLAY_ICON,
                )
            )
            items.extend(controls)
        else:
            items.extend(controls)
            items.append(
                alfred_item(
                    title="Enter a valid YouTube URL",
                    subtitle="Supported formats: youtube.com/watch, youtu.be, /shorts, /live",
                    valid=False,
                    icon=WARNING_ICON,
                )
            )
    else:
        items.extend(controls)
        clipboard = clipboard_text()
        if is_youtube_url(clipboard):
            normalized = normalized_youtube_url(clipboard)
            items.append(
                alfred_item(
                    title="Play clipboard URL",
                    subtitle=normalized,
                    arg=action_arg("play", normalized),
                    uid=f"clipboard::{normalized}",
                    icon=PLAY_ICON,
                )
            )
        else:
            items.append(
                alfred_item(
                    title="Clipboard does not contain a YouTube URL",
                    subtitle="Copy a YouTube link or type one after yt",
                    valid=False,
                    icon=WARNING_ICON,
                )
            )
        items.extend(quick_picks)

    items.extend(recent)
    return {"items": items}


def resolve_audio(url: str) -> tuple[str, str]:
    command = [
        YTDLP_BIN,
        "--no-playlist",
        "--print",
        "%(title)s",
        "--get-url",
        url,
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        error_text = (result.stderr or result.stdout).strip() or "Unknown yt-dlp failure"
        raise RuntimeError(error_text)

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        raise RuntimeError("yt-dlp did not return both a title and an audio stream URL")

    title = lines[0]
    stream_url = lines[-1]
    return title, stream_url


def notify(title: str, message: str) -> None:
    script = f"display notification {json.dumps(message)} with title {json.dumps(title)}"
    subprocess.run(["osascript", "-e", script], check=False)


def start_playback(url: str) -> int:
    normalized = normalized_youtube_url(url)
    missing = dependency_errors()
    if missing:
        raise RuntimeError(f"Missing required dependencies: {', '.join(missing)}")

    stop_existing_playback()
    notify("YT Audio Player", "Resolving YouTube audio stream…")
    title, stream_url = resolve_audio(normalized)

    process = subprocess.Popen(
        [
            FFPLAY_BIN,
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "error",
            stream_url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid,
    )
    save_json(
        STATE_PATH,
        {
            "pid": process.pid,
            "url": normalized,
            "title": title,
            "started_at": int(time.time()),
            "paused": False,
        },
    )
    update_history(normalized, title)
    notify("Now playing", title)
    return process.pid


def command_filter(args: list[str]) -> int:
    query = args[0] if args else ""
    print(json.dumps(filter_items(query)))
    return 0


def first_payload(args: list[str]) -> str:
    if args and args[0]:
        return args[0]
    stdin_value = sys.stdin.read().strip()
    return stdin_value


def command_play(args: list[str]) -> int:
    if not args:
        message = "Usage: yt_audio_workflow.py play <youtube-url>"
        notify("Playback failed", message)
        print(message, file=sys.stderr)
        return 1
    try:
        pid = start_playback(args[0])
    except ValueError as exc:
        message = f"Invalid URL: {exc}"
        notify("Playback failed", message)
        print(message, file=sys.stderr)
        return 1
    except RuntimeError as exc:
        message = str(exc)
        notify("Playback failed", message)
        print(message, file=sys.stderr)
        return 1

    print(f"Started playback with pid {pid}")
    return 0


def command_pause(_: list[str]) -> int:
    state = pause_playback()
    title = state.get("title") or "Current audio"
    notify("Playback paused", title)
    print("Paused playback")
    return 0


def command_resume(_: list[str]) -> int:
    state = resume_playback()
    title = state.get("title") or "Current audio"
    notify("Playback resumed", title)
    print("Resumed playback")
    return 0


def command_stop(_: list[str]) -> int:
    stop_existing_playback()
    notify("Playback stopped", "Stopped the current YouTube audio session")
    print("Stopped playback")
    return 0


def command_dispatch(args: list[str]) -> int:
    raw_payload = first_payload(args)
    if not raw_payload:
        message = "No workflow action was provided"
        notify("Playback failed", message)
        print(message, file=sys.stderr)
        return 1

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        message = f"Invalid workflow action: {exc}"
        notify("Playback failed", message)
        print(message, file=sys.stderr)
        return 1

    action = payload.get("action")
    value = payload.get("value", "")
    if action == "play":
        return command_play([value])
    if action == "pause":
        return command_pause([])
    if action == "resume":
        return command_resume([])
    if action == "stop":
        return command_stop([])

    message = f"Unknown workflow action: {action}"
    notify("Playback failed", message)
    print(message, file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: yt_audio_workflow.py <filter|play|stop>", file=sys.stderr)
        return 1

    command = argv[1]
    args = argv[2:]
    if command == "filter":
        return command_filter(args)
    if command == "play":
        return command_play(args)
    if command == "pause":
        return command_pause(args)
    if command == "resume":
        return command_resume(args)
    if command == "stop":
        return command_stop(args)
    if command == "dispatch":
        return command_dispatch(args)

    print(f"Unknown command: {command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
