# Privacy

focus-cam-log is a webcam-based tool. Read this before running it.

## What it captures

- A single webcam snapshot every `--interval` minutes while running.
- Snapshots may contain sensitive personal information — your face, your
  screen, your surroundings, and anyone else in frame.

## Where data goes

- **Gemini API**: every captured snapshot is sent to the configured Google
  Gemini API for activity analysis. This is inherent to how the tool works;
  there is no local-only analysis mode. Google's handling of that data is
  governed by [Google's Gemini API terms](https://ai.google.dev/gemini-api/terms).
- **Local disk**: everything else stays on your machine, under
  `FOCUS_LOG_DATA_DIR` (default `~/.focus-log`):
  - `events.sqlite` — timestamped text activity labels (kept indefinitely)
  - `photos/` — snapshots, **only if you pass `--save-photos`**
  - `summaries/` — generated daily summaries

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
