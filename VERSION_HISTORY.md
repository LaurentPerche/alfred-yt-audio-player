# Version History

Total estimated effort so far: ~6 hours

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
* SHA-256: `404867ffa03f85d159963fd35c410716f63e056dee7110ba05df00573978edb0`
