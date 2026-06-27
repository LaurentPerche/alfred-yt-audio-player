# Version History

Total estimated effort so far: ~7 hours

## v0.9.1

Release status: public patch release

Approximate implementation and release effort: ~1 hour

Highlights:

* Replaced the hardcoded Python 3.11 framework path in the Alfred workflow with `python3` from `PATH`
* Improved compatibility after macOS, Homebrew, Python, and Intel-versus-Apple-Silicon environment changes
* Preserved the existing playback, clipboard fallback, controls, and recent-history behavior

Testing status:

* Unit-tested locally with `python3 -m unittest discover -s tests -p 'test_*.py'`
* Manually tested locally in Alfred after the fix and confirmed working

Release notes:

* This patch release ships seven days after `v0.9`
* Release artifact: `YT Audio Player.alfredworkflow`
* SHA-256: `d5fa408f93cc20cdd566ff295e12f61105fc4841f289b28b3453d8cad64593f4`

## v0.9

Release status: public beta

Approximate implementation and release effort: ~6 hours

Highlights:

* Created an Alfred workflow that plays YouTube audio through `yt-dlp` and `ffplay`
* Added typed URL playback and clipboard fallback through the `yt` keyword
* Added pause, resume, and stop controls for the current audio session
* Added recent-history switching for the last five unique videos
* Improved Alfred result presentation with icons, human-friendly recent labels, and better result ordering

Testing status:

* Unit-tested locally for URL parsing, result rendering, history behavior, and Alfred action dispatch
* Manually tested locally for play, switch, pause, resume, stop, clipboard playback, and recent-item playback
* Not fully tested across different machines, Alfred versions, Python layouts, or dependency installations yet

Release notes:

* Feedback is welcome, especially around setup differences, compatibility issues, and Alfred behavior edge cases
* Release artifact: `YT Audio Player.alfredworkflow`
* SHA-256: `58c14b78a9f707d58db039c239221e806107d8a3defe87adbe9f3a2327c39641`
