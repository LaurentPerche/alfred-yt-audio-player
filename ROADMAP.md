# Roadmap

## Current

### v0.12.1 (development)

* Add persistent Max (100%), Medium (55%), and Low (25%) workflow-specific audio levels
* Expose the preset chooser through `yt volume` and show the current level in the default Alfred results
* Keep macOS system volume and audio from other apps unchanged
* Apply a changed preset to current playback by briefly reconnecting near the current position; evaluate `mpv` separately if seamless live adjustment becomes a priority

### v0.11.0

* Show up to three most-played videos first as quick picks when `yt` opens in Alfred
* Use icon-only categorization for quick picks and recent items instead of text prefixes
* Refresh playback and action icons with a more modern custom visual style

### v0.10.0

* Simplify noisy recent-video titles automatically in Alfred history results
* Show a per-video play count directly in the Alfred recent-items subtitle
* Keep the same five-item recent history and URL-based deduplication model

### v0.9.1

* Compatibility fix for Python path changes after macOS and tooling updates
* Use `python3` from `PATH` instead of a hardcoded `/Library/Frameworks/.../python3` path
* Keep the workflow working across Intel and Apple Silicon setups with standard Homebrew or system Python installs

### v0.9

* Public beta release of the Alfred YouTube audio player
* Support typed URL playback through the `yt` keyword
* Support clipboard fallback when `yt` is typed with no argument
* Replace any currently playing session when a new item is selected
* Show visible pause, resume, and stop controls when playback is active
* Show the five most recent unique videos in Alfred results
* Gather real-world feedback before a more stable `v1.0`

## Later

* Add richer metadata in history results, such as channel name or duration
* Add packaging and release notes automation
* Evaluate whether to support `mpv` or additional media sources
