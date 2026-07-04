#!/usr/bin/env python3
"""focus-cam-log: a privacy-conscious webcam focus journaling tool powered by Gemini.

Periodically captures a webcam snapshot, asks Gemini what you are doing,
and stores the result in a local SQLite database. Optionally sends
focus-drift reminders and exports a daily Markdown view to Obsidian.

All data stays on your machine except the snapshot sent to the Gemini API
for analysis. By default only the text activity log is kept; snapshots are
saved to disk only with --save-photos, and are purged after a retention
period. The temporary analysis snapshot is deleted after each cycle.
"""

import argparse
import asyncio
import datetime
import os
import shutil
import sqlite3
import subprocess
import sys

import cv2
from google import genai
from google.genai import types

# --- Configuration (overridable via environment variables) ---------------

DATA_DIR = os.path.expanduser(os.environ.get("FOCUS_LOG_DATA_DIR", "~/.focus-log"))
DB_PATH = os.path.join(DATA_DIR, "events.sqlite")
PHOTOS_DIR = os.path.join(DATA_DIR, "photos")
SUMMARIES_DIR = os.path.join(DATA_DIR, "summaries")
TEMP_IMAGE_PATH = os.path.join(DATA_DIR, "snapshot_tmp.jpg")

OBSIDIAN_DIR = os.environ.get("FOCUS_LOG_OBSIDIAN_DIR", "")
MODEL = os.environ.get("FOCUS_LOG_MODEL", "gemini-2.5-flash")
CAMERA_INDEX = int(os.environ.get("FOCUS_LOG_CAMERA_INDEX", "0"))

PROMPTS = {
    "ja": (
        "画像に写っている人間の状態を分析し、何をしているか（例: 集中してPCに向かっている、"
        "スマホを見ている、勉強している、寝ている、席を外している、など）を日本語の短い1文"
        "（20文字以内）で回答してください。余計な説明は省き、状態のみを出力してください。"
    ),
    "en": (
        "Analyze the person in this image and describe what they are doing "
        "(e.g. focused at the computer, looking at their phone, studying, sleeping, "
        "away from desk) in one short English sentence (10 words or fewer). "
        "Output only the state, no extra explanation."
    ),
}

FOCUS_DRIFT_KEYWORDS = {
    "ja": ["スマホ", "遊んでいる", "寝ている", "ゲーム", "よそ見"],
    "en": ["phone", "sleeping", "game", "distracted", "away"],
}


def load_api_key():
    """Reads GEMINI_API_KEY from the environment or an optional env file."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return api_key

    env_file = os.environ.get("FOCUS_LOG_ENV_FILE", os.path.join(DATA_DIR, "env"))
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("export "):
                    line = line[len("export "):]
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip("'\"")
    return None


def notify(title, message):
    """Sends a desktop notification (macOS native; no-op elsewhere)."""
    if sys.platform == "darwin" and shutil.which("osascript"):
        script = f'display notification "{message}" with title "{title}" sound name "Glass"'
        subprocess.run(["osascript", "-e", script], check=False)
    elif shutil.which("notify-send"):
        subprocess.run(["notify-send", title, message], check=False)
    else:
        print(f"[notify] {title}: {message}")


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS focus_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER NOT NULL, -- epoch milliseconds
        activity TEXT NOT NULL,
        photo_path TEXT,
        photo_exists INTEGER DEFAULT 1, -- 1 = on disk, 0 = purged
        photo_deleted_at TEXT,          -- ISO timestamp when purged
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()


def save_to_db(timestamp_ms, activity, photo_path):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO focus_events (timestamp, activity, photo_path, photo_exists)"
        " VALUES (?, ?, ?, ?)",
        (timestamp_ms, activity, photo_path, 1 if photo_path else 0),
    )
    conn.commit()
    conn.close()


def cleanup_old_photos(retention_days):
    """Purges photos older than the retention period and marks them in the DB."""
    if not os.path.exists(PHOTOS_DIR):
        return

    cutoff = datetime.datetime.now() - datetime.timedelta(days=retention_days)
    conn = sqlite3.connect(DB_PATH)
    purged = 0
    for filename in os.listdir(PHOTOS_DIR):
        if not filename.endswith(".jpg"):
            continue
        path = os.path.join(PHOTOS_DIR, filename)
        try:
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
            if mtime < cutoff:
                os.remove(path)
                purged += 1
                deleted_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    "UPDATE focus_events SET photo_exists = 0, photo_deleted_at = ?"
                    " WHERE photo_path LIKE ?",
                    (deleted_at, f"%{filename}"),
                )
        except OSError as e:
            print(f"Error purging {filename}: {e}")
    conn.commit()
    conn.close()
    if purged:
        print(f"🧹 Purged {purged} photo(s) older than {retention_days} day(s).")


def capture_image(photo_filename, save_photo):
    """Captures one webcam frame. Returns the saved photo path (or None)."""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Error: could not open camera.")
        return False, None

    for _ in range(5):  # warm up
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return False, None

    h, w, _ = frame.shape
    resized = cv2.resize(frame, (640, int(h * (640 / w))))

    os.makedirs(DATA_DIR, exist_ok=True)
    cv2.imwrite(TEMP_IMAGE_PATH, resized)

    photo_path = None
    if save_photo:
        os.makedirs(PHOTOS_DIR, exist_ok=True)
        photo_path = os.path.join(PHOTOS_DIR, photo_filename)
        cv2.imwrite(photo_path, resized)
    return True, photo_path


def analyze_activity(client, lang):
    """Sends the captured snapshot to Gemini and returns the activity label."""
    if not os.path.exists(TEMP_IMAGE_PATH):
        return "(snapshot missing)"
    try:
        with open(TEMP_IMAGE_PATH, "rb") as f:
            image_bytes = f.read()
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        response = client.models.generate_content(
            model=MODEL,
            contents=[PROMPTS[lang], image_part],
        )
        return response.text.strip()
    except Exception as e:
        return f"(error: {e})"


def export_to_obsidian(activity, photo_path, retention_days):
    """Appends one Markdown table row to today's focus log note."""
    if not OBSIDIAN_DIR:
        return
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    base_dir = os.path.join(os.path.expanduser(OBSIDIAN_DIR), "Daily-Focus-Logs")
    note = os.path.join(base_dir, f"Focus-Log-{date_str}.md")
    os.makedirs(base_dir, exist_ok=True)

    if not os.path.exists(note):
        with open(note, "w", encoding="utf-8") as f:
            f.write(f"# Focus Log - {date_str}\n\n")
            f.write("> [!IMPORTANT]\n")
            f.write("> This file is a temporary viewing export. Photos are deleted "
                    f"after {retention_days} day(s) for privacy, after which image "
                    "links will break.\n")
            f.write(f"> The canonical event history lives in `{DB_PATH}`.\n\n")
            f.write("| Time | Activity | Image |\n")
            f.write("| :--- | :--- | :--- |\n")

    image_cell = f"![Photo](file://{photo_path})" if photo_path else "—"
    with open(note, "a", encoding="utf-8") as f:
        f.write(f"| {now.strftime('%H:%M:%S')} | {activity} | {image_cell} |\n")


SUMMARY_PROMPTS = {
    "ja": (
        "以下はユーザーの1日の行動ログです（時間とカメラによる行動推論）。\n"
        "このログから、ユーザーが何時間集中して何に取り組んでいたか、休憩の頻度、"
        "リマインド（通知）の回数、全体の作業効率などの要約を日本語で作成してください。\n"
        "助言や指示（「〜しましょう」等）は書かず、観測された事実と傾向のみを記述してください。\n"
        "出力は以下のフォーマットに沿ったマークダウンにしてください。\n\n"
        "# Focus Summary - {date}\n\n"
        "## 概要\n(全体の傾向)\n\n"
        "## 集中時間と効率\n(効率の分析)\n\n"
        "## 休憩・低集中状況\n(休憩の質や集中のゆらぎ)\n\n"
        "## 観測された傾向\n(例: この時間帯は集中が途切れやすい傾向がありました)\n\n"
        "---\n### 原材料（Raw Events）\n{events}"
    ),
    "en": (
        "Below is one day of the user's activity log (timestamps plus "
        "camera-inferred activity).\n"
        "Summarize in English: hours of focused work and on what, break frequency, "
        "number of focus-drift reminders, and overall efficiency.\n"
        "Describe observed facts and patterns only; do not give advice, "
        "instructions, or recommendations.\n"
        "Output Markdown following this format.\n\n"
        "# Focus Summary - {date}\n\n"
        "## Overview\n(overall trend)\n\n"
        "## Focus Time & Efficiency\n(analysis)\n\n"
        "## Breaks & Low-Focus Periods\n(quality of breaks, focus drift)\n\n"
        "## Observed Patterns\n(e.g. focus tended to drift in this time range)\n\n"
        "---\n### Raw Events\n{events}"
    ),
}


def generate_daily_summary(client, lang, target_date_str=None):
    """Generates a Markdown daily summary from SQLite via Gemini."""
    if not target_date_str:
        target_date_str = datetime.datetime.now().strftime("%Y-%m-%d")

    init_db()
    start_dt = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
    end_dt = start_dt + datetime.timedelta(days=1)

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT timestamp, activity FROM focus_events"
        " WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp ASC",
        (int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000)),
    ).fetchall()
    conn.close()

    if not rows:
        print(f"No events found for {target_date_str}.")
        return False

    events_text = "\n".join(
        f"- [{datetime.datetime.fromtimestamp(ts / 1000).strftime('%H:%M:%S')}] {act}"
        for ts, act in rows
    )
    prompt = SUMMARY_PROMPTS[lang].format(date=target_date_str, events=events_text)

    print("Generating daily summary with Gemini...")
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        os.makedirs(SUMMARIES_DIR, exist_ok=True)
        summary_path = os.path.join(SUMMARIES_DIR, f"Focus-Summary-{target_date_str}.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(response.text.strip())
        print(f"Daily summary written to: {summary_path}")
        return True
    except Exception as e:
        print(f"Error generating daily summary: {e}")
        return False


async def main_loop(args, client):
    init_db()

    print("=== focus-cam-log: Gemini Focus Monitor ===")
    print(f"Interval: {args.interval} minutes")
    print(f"Watch mode (focus-drift reminders): {'ON' if args.watch else 'OFF'}")
    print(f"Photo saving: {f'ON (purged after {args.retention_days} days)' if args.save_photos else 'OFF (text log only)'}")
    print(f"Obsidian export: {'ON -> ' + OBSIDIAN_DIR if args.obsidian else 'OFF'}")
    print(f"SQLite DB: {DB_PATH}")
    print("Press Ctrl+C to stop.")

    notify("Focus Monitor", "Focus logging started."
           if args.lang == "en" else "集中ログの記録を開始しました！")

    while True:
        try:
            now = datetime.datetime.now()
            photo_filename = f"focus_snapshot_{now.strftime('%Y%m%d_%H%M%S')}.jpg"

            ok, photo_path = capture_image(photo_filename, save_photo=args.save_photos)
            if ok:
                activity = analyze_activity(client, args.lang)
                try:
                    os.remove(TEMP_IMAGE_PATH)  # never leave the analysis snapshot behind
                except OSError:
                    pass
                save_to_db(int(now.timestamp() * 1000), activity, photo_path)
                print(f"[{now.strftime('%H:%M:%S')}] Logged: {activity}")

                if args.obsidian:
                    export_to_obsidian(activity, photo_path, args.retention_days)

                cleanup_old_photos(args.retention_days)

                if args.watch and any(k in activity for k in FOCUS_DRIFT_KEYWORDS[args.lang]):
                    notify(
                        "🚨 Focus Monitor",
                        f"Focus drift: \"{activity}\""
                        if args.lang == "en"
                        else f"フォーカスのゆらぎ: 「{activity}」",
                    )
            else:
                print("Failed to capture image.")
        except Exception as e:
            print(f"Error in monitor loop: {e}")

        await asyncio.sleep(args.interval * 60)


def main():
    parser = argparse.ArgumentParser(
        description="focus-cam-log: webcam focus journaling tool powered by Gemini")
    parser.add_argument("--interval", type=float, default=10.0,
                        help="capture interval in minutes (default: 10)")
    parser.add_argument("--watch", action="store_true",
                        help="send focus-drift reminders")
    parser.add_argument("--save-photos", action="store_true",
                        help="keep snapshot photos on disk (default: text log only)")
    parser.add_argument("--obsidian", action="store_true",
                        help="export a daily Markdown view (set FOCUS_LOG_OBSIDIAN_DIR)")
    parser.add_argument("--retention-days", type=int, default=3,
                        help="days to keep photos before purging (default: 3)")
    parser.add_argument("--lang", choices=["ja", "en"], default="ja",
                        help="language for analysis and notifications (default: ja)")
    parser.add_argument("--summary", action="store_true",
                        help="generate a daily summary and exit")
    parser.add_argument("--summary-date", type=str, default=None,
                        help="target date for --summary (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.obsidian and not OBSIDIAN_DIR:
        print("Error: --obsidian requires FOCUS_LOG_OBSIDIAN_DIR to be set.")
        sys.exit(1)

    api_key = load_api_key()
    if not api_key:
        print("Error: GEMINI_API_KEY not found. Set it in your environment or in"
              f" {os.path.join(DATA_DIR, 'env')}.")
        sys.exit(1)
    client = genai.Client(api_key=api_key)

    if args.summary:
        sys.exit(0 if generate_daily_summary(client, args.lang, args.summary_date) else 1)

    try:
        asyncio.run(main_loop(args, client))
    except KeyboardInterrupt:
        print("\nMonitoring stopped. Keep focusing!")


if __name__ == "__main__":
    main()
