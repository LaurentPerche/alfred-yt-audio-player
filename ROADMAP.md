# Roadmap

## Current

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
