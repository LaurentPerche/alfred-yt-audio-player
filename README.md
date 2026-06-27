# Alfred YT Audio Player

Play YouTube links as background audio directly from Alfred on macOS using `yt-dlp` and `ffplay`, without keeping YouTube open in Chrome or any other browser.

Current release: `v0.9.1`

This is an early public release. It works well in local testing, but it has not been fully tested across different macOS and Alfred setups yet. Feedback, bug reports, and edge cases are very welcome.

## What It Does

* Type `yt <youtube-url>` to play a YouTube video as audio from Alfred.
* Type `yt` with no URL to play the YouTube link currently in the clipboard.
* Play audio in the background without leaving YouTube open in a web browser.
* Stop the current audio automatically when a new item is played.
* Pause, resume, or stop playback from Alfred while audio is active.
* Reopen one of the last five videos you played from recent history.
* See Alfred notifications when playback starts, pauses, resumes, stops, or fails.

## Why It Exists

This workflow is for people who already live in Alfred and want a fast way to:

* turn a YouTube URL into background audio
* listen to long videos, talks, interviews, or music without keeping a browser tab open
* switch between a fresh link, the clipboard, and recent history with minimal friction

## Screenshots

Search results with clipboard playback and recent history:

![Alfred search results showing clipboard playback and recent items](docs/screenshots/alfred-search-results.png)

Active playback controls inside Alfred:

![Alfred showing pause and stop controls for the current audio session](docs/screenshots/alfred-playback-controls.png)

## Release Notes

`v0.9.1` improves compatibility after Python and architecture-related macOS environment changes.

Highlights:

* use `python3` from `PATH` instead of a hardcoded Python framework path
* work more reliably across Intel and Apple Silicon Homebrew and Python setups
* keep the same Alfred-first playback, clipboard, history, and background-audio workflow

Known caveat:

* this release is still not fully tested on every macOS, Alfred, Python, or `ffplay` setup yet

## Requirements

* Alfred with Powerpack
* macOS
* `yt-dlp`
* `ffplay`
* `python3`

The workflow now runs `python3` from `PATH`, so standard Homebrew or system Python setups should work on both Intel and Apple Silicon Macs as long as `python3` is available in Alfred's shell environment.

## Supported URL Formats

The workflow currently accepts common YouTube link formats including:

* `https://www.youtube.com/watch?v=...`
* `https://youtu.be/...`
* `https://www.youtube.com/shorts/...`
* `https://www.youtube.com/live/...`

## Repo Layout

* `workflow/`
  Contains the Alfred workflow source, including `info.plist` and the Python script Alfred runs.
* `tests/`
  Contains unit tests for URL parsing, history handling, and Script Filter behavior.
* `scripts/package_workflow.sh`
  Packages the `workflow/` directory into an `.alfredworkflow` file in `dist/`.

## Install

1. Run:

```zsh
./scripts/package_workflow.sh
```

2. Open the generated file:

`dist/YT Audio Player.alfredworkflow`

3. Import it into Alfred.

For the easiest install path after publishing, download the latest `.alfredworkflow` file from the GitHub Releases page and open it directly.

## Usage

* `yt https://www.youtube.com/watch?v=...`
* `yt https://youtu.be/...`
* `yt`

When you type only `yt`, Alfred shows:

* playback controls first when audio is already active
* `Play clipboard URL` if the clipboard contains a valid YouTube URL
* the five most recent videos underneath

## State Storage

The workflow stores runtime state in Alfred's workflow data directory:

* `state.json`
  Tracks the active playback PID, URL, title, and start time
* `history.json`
  Tracks the five most recent unique plays

## Known Limits

* v1 only supports YouTube URLs
* pause and resume are process-level controls built on `ffplay`, so very occasional stream reconnection quirks may still need a fresh play action
* error handling is surfaced through Alfred result rows and script failures rather than a custom UI

## Ideal GitHub Topics

If you publish this repo on GitHub, these topics are a good fit:

* `alfred-workflow`
* `alfred`
* `youtube`
* `youtube-audio`
* `yt-dlp`
* `ffplay`
* `macos`
* `productivity`

## Feedback

If you try this workflow and hit a bug, confusing interaction, or compatibility issue, feedback is welcome. The most useful reports include:

* your macOS version
* your Alfred version
* whether `yt-dlp` and `ffplay` are installed through Homebrew or another method
* the Alfred debug log lines around the failing action

## Keywords

Search terms for discoverability:

* Alfred workflow
* Alfred YouTube player
* Alfred YouTube audio
* Alfred audio player
* Alfred background audio
* Alfred clipboard workflow
* yt-dlp Alfred
* ffplay Alfred
* macOS YouTube audio player
* YouTube audio workflow
* Play YouTube audio from Alfred
* Listen to YouTube in Alfred
* Play YouTube without browser
* Background YouTube audio on macOS
* Alfred media control
* Alfred recent history workflow
