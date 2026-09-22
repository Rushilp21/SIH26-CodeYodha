# BhumiSetu media guide

This directory is reserved for README screenshots, thumbnails, GIFs, and feature videos.

## Recommended files

```text
00-overview.mp4
00-overview-thumbnail.png
01-map-workspace.mp4
01-map-workspace-thumbnail.png
02-evidence-panel.mp4
02-evidence-panel-thumbnail.png
03-review-and-label.mp4
03-review-and-label-thumbnail.png
04-boundary-editor.mp4
04-boundary-editor-thumbnail.png
05-change-detection.mp4
05-change-detection-thumbnail.png
06-analytics.mp4
06-analytics-thumbnail.png
```

GitHub README pages do not consistently play repository MP4 files inline. The most reliable presentation is a thumbnail linked to a hosted video or GitHub-uploaded video URL:

```markdown
[![Watch the map workspace demo](docs/media/01-map-workspace-thumbnail.png)](YOUR_VIDEO_URL)
```

For a short interaction, an optimized GIF can be embedded directly:

```markdown
![Boundary editing demo](docs/media/04-boundary-editor.gif)
```

## Recording tips

- Record at 1080p with browser zoom near 100%.
- Keep the cursor movement deliberate and avoid long pauses.
- Use one feature per clip so judges can jump directly to it.
- Blur personal tabs, usernames, tokens, and machine identifiers.
- Start each clip on the relevant page and end after the result is visible.
- Keep voice-over concise: problem → action → evidence → outcome.

Replace each `video-placeholder.svg` block in the root `README.md` after its clip is ready. Keep video files reasonably small; for large files, prefer a hosted video URL and commit only the thumbnail.
