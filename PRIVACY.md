# Privacy

focus-cam-log is a webcam-based tool. Read this before running it.

## What it captures

- A single webcam snapshot every `--interval` minutes while running.
- Snapshots may contain sensitive personal information — your face, your
  screen, your surroundings, and anyone else in frame.

## Where data goes

- **Gemini provider (default)**: every captured snapshot is sent to the
  configured Google Gemini API for activity analysis. Google's handling of
  that data is governed by
  [Google's Gemini API terms](https://ai.google.dev/gemini-api/terms).
- **Ollama provider (`--provider ollama`)**: analysis runs on a local vision
  model through your Ollama instance. In this mode no image or text is sent
  to any external service.
- The startup banner always states the active mode (`Mode: local-only` or
  `Mode: cloud`), so you can verify where snapshots go before the first
  capture. See "Persistent local-only setup" in the README to make
  local-only survive restarts.
- **Local disk**: everything else stays on your machine, under
  `FOCUS_LOG_DATA_DIR` (default `~/.focus-log`):
  - `events.sqlite` — timestamped text activity labels (kept indefinitely)
  - `photos/` — snapshots, **only if you pass `--save-photos`**
  - `summaries/` — generated daily summaries
- **Focus-drift alerts** (`--watch`): shown locally via macOS's native
  notification center or `display dialog` (`FOCUS_LOG_ALERT_STYLE`) — never
  sent anywhere, regardless of which analysis provider you use.

## Retention

- Photos are saved only with explicit `--save-photos` (default is text log only).
- Saved photos are automatically deleted after `--retention-days` days
  (default: 3). The database records when each photo was purged.
- The temporary snapshot used for analysis is deleted after each cycle.
- The text event log and summaries are never auto-deleted; remove
  `~/.focus-log` yourself to erase history.

## Consent

Do not run focus-cam-log where it can capture people who have not consented —
shared offices, living rooms, video calls. You are responsible for complying
with local recording and privacy laws.
