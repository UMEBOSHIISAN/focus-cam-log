# focus-cam-log

A privacy-conscious, local-first webcam focus journaling tool powered by
Google Gemini.

[日本語 README はこちら](README.ja.md)

focus-cam-log periodically captures a snapshot from your webcam, asks Gemini
what you are doing ("focused at the computer", "looking at the phone", "away
from desk", …), and records the result in a local SQLite database. It can send
optional focus-drift reminders as desktop notifications, and generate an
AI-written daily summary of your focus habits.

## Features

- **Periodic activity logging** — one webcam snapshot every N minutes,
  classified by Gemini into a short activity label.
- **Focus-drift reminders** (`--watch`) — desktop notification when the label
  suggests your attention has drifted (phone, sleeping, gaming, …).
- **Daily summary** (`--summary`) — Gemini writes a Markdown report of your
  focus time, breaks, and efficiency from the day's events.
- **Obsidian export** (`--obsidian`) — appends a Markdown table view of the
  day's log to your vault.
- **Privacy by design** — by default only the text activity log is kept;
  saving snapshots to disk is explicit opt-in (`--save-photos`), saved photos
  are automatically purged after a retention period (default: 3 days), and
  the database records when each photo was deleted. Only the snapshot being
  analyzed is sent to the Gemini API. See [PRIVACY.md](PRIVACY.md).

## Requirements

- Python 3.9+
- A webcam
- A Gemini API key ([Google AI Studio](https://aistudio.google.com/apikey))
- Desktop notifications: macOS (`osascript`) or Linux (`notify-send`);
  other platforms fall back to console output.

## Quick start

```bash
git clone <this-repo> focus-cam-log && cd focus-cam-log
./setup.sh
export GEMINI_API_KEY=your-key-here
./focus_on.sh          # start logging in the background (reminders on)
./focus_off.sh         # stop logging
```

Or run in the foreground:

```bash
source venv/bin/activate
python3 focus_monitor.py --interval 10 --watch
```

Generate today's summary:

```bash
python3 focus_monitor.py --summary            # today
python3 focus_monitor.py --summary --summary-date 2026-07-01
```

## Options

| Flag | Description | Default |
| --- | --- | --- |
| `--interval N` | capture interval in minutes | `10` |
| `--watch` | send focus-drift reminders | off |
| `--save-photos` | keep snapshots on disk (default is text log only) | off |
| `--retention-days N` | days to keep saved photos before purging | `3` |
| `--obsidian` | export a daily Markdown view (needs `FOCUS_LOG_OBSIDIAN_DIR`) | off |
| `--lang {ja,en}` | language for analysis labels and notifications | `ja` |
| `--summary` | generate a daily summary and exit | — |
| `--summary-date YYYY-MM-DD` | target date for `--summary` | today |

## Configuration (environment variables)

| Variable | Description | Default |
| --- | --- | --- |
| `GEMINI_API_KEY` | Gemini API key (required) | — |
| `FOCUS_LOG_DATA_DIR` | data directory (DB, photos, summaries) | `~/.focus-log` |
| `FOCUS_LOG_ENV_FILE` | optional file containing `GEMINI_API_KEY=...` | `$FOCUS_LOG_DATA_DIR/env` |
| `FOCUS_LOG_OBSIDIAN_DIR` | Obsidian vault path for `--obsidian` export | unset |
| `FOCUS_LOG_MODEL` | Gemini model name | `gemini-2.5-flash` |
| `FOCUS_LOG_CAMERA_INDEX` | OpenCV camera device index | `0` |

## Data layout

```
~/.focus-log/
├── events.sqlite      # canonical event history (never auto-deleted)
├── photos/            # snapshots (only with --save-photos), purged after --retention-days
└── summaries/         # generated daily summaries (Markdown)
```

See [env.example](env.example) for all configuration variables.

The `focus_events` table keeps `photo_exists` / `photo_deleted_at` columns so
history stays auditable even after photos are purged.

## Privacy notes

- Snapshots of you (and anyone in frame) are sent to the Google Gemini API
  for analysis. Review [Google's API terms](https://ai.google.dev/gemini-api/terms)
  and don't point the camera at people who haven't consented.
- By default no photos are kept: the analysis snapshot is deleted after each
  cycle and only the text label is stored. With `--save-photos`, photos live
  only on your machine and are deleted after the retention period.
- The Obsidian export is a *view*; the SQLite database is the source of truth.
- Full details in [PRIVACY.md](PRIVACY.md); security policy in [SECURITY.md](SECURITY.md).

## Roadmap

- Provider abstraction for local or alternative model backends
- Local model support, such as Ollama, for users who prefer not to send
  images to cloud APIs

Not implemented in v0.1.0.

## License

[MIT](LICENSE)
