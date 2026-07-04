# focus-log

Google Gemini を使った、プライバシー配慮型の Web カメラ集中ログツール。

[English README](README.md)

focus-log は一定間隔で Web カメラのスナップショットを撮影し、Gemini に
「何をしているか」（集中してPCに向かっている / スマホを見ている / 席を外している
など）を分類させ、ローカルの SQLite データベースに記録します。サボりを検知すると
デスクトップ通知で警告し、1日の集中状況を AI がまとめた日次サマリも生成できます。

## 機能

- **定期的な行動ログ** — N分ごとにスナップショットを撮影し、Gemini が短い行動ラベルに分類。
- **サボり警告** (`--watch`) — スマホ・寝ている・ゲーム等のキーワード検知でデスクトップ通知。
- **日次サマリ** (`--summary`) — その日のイベントから集中時間・休憩・効率を Gemini が Markdown レポート化。
- **Obsidian エクスポート** (`--obsidian`) — 当日のログを Markdown テーブルとして vault に追記。
- **プライバシー設計** — データはすべてローカル保存。写真は保持期間（デフォルト3日）
  経過後に自動削除され、削除日時は DB に記録されます。外部に送信されるのは
  分析対象のスナップショットのみ（Gemini API）。

## 前提条件

- Python 3.9+
- Web カメラ
- Gemini API キー（[Google AI Studio](https://aistudio.google.com/apikey)）
- デスクトップ通知: macOS（`osascript`）/ Linux（`notify-send`）。
  それ以外はコンソール出力にフォールバック。

## クイックスタート

```bash
git clone <this-repo> focus-log && cd focus-log
./setup.sh
export GEMINI_API_KEY=your-key-here
./focus_on.sh          # バックグラウンドで監視開始（watch モード）
./focus_off.sh         # 監視停止
```

フォアグラウンド実行:

```bash
source venv/bin/activate
python3 focus_monitor.py --interval 10 --watch
```

日次サマリの生成:

```bash
python3 focus_monitor.py --summary            # 今日
python3 focus_monitor.py --summary --summary-date 2026-07-01
```

## オプション

| フラグ | 説明 | デフォルト |
| --- | --- | --- |
| `--interval N` | 撮影間隔（分） | `10` |
| `--watch` | サボり検知時に通知 | off |
| `--no-photos` | スナップショットを保存しない（テキストのみ記録） | off |
| `--retention-days N` | 写真の保持日数 | `3` |
| `--obsidian` | 日次 Markdown ビューを出力（`FOCUS_LOG_OBSIDIAN_DIR` 必須） | off |
| `--lang {ja,en}` | 分析ラベル・通知の言語 | `ja` |
| `--summary` | 日次サマリを生成して終了 | — |
| `--summary-date YYYY-MM-DD` | `--summary` の対象日 | 今日 |

## 設定（環境変数）

| 変数 | 説明 | デフォルト |
| --- | --- | --- |
| `GEMINI_API_KEY` | Gemini API キー（必須） | — |
| `FOCUS_LOG_DATA_DIR` | データディレクトリ（DB・写真・サマリ） | `~/.focus-log` |
| `FOCUS_LOG_ENV_FILE` | `GEMINI_API_KEY=...` を書いた任意ファイル | `$FOCUS_LOG_DATA_DIR/env` |
| `FOCUS_LOG_OBSIDIAN_DIR` | `--obsidian` 出力先の vault パス | 未設定 |
| `FOCUS_LOG_MODEL` | Gemini モデル名 | `gemini-2.5-flash` |
| `FOCUS_LOG_CAMERA_INDEX` | OpenCV カメラデバイス番号 | `0` |

## データ配置

```
~/.focus-log/
├── events.sqlite      # 行動履歴の正本（自動削除されない）
├── photos/            # スナップショット（--retention-days 経過後に削除）
└── summaries/         # 生成された日次サマリ（Markdown）
```

`focus_events` テーブルは `photo_exists` / `photo_deleted_at` 列を持ち、
写真削除後も履歴の監査可能性を保ちます。

## プライバシーに関する注意

- あなた（および画角に入った人）のスナップショットが分析のため Google Gemini API に
  送信されます。[Google の API 規約](https://ai.google.dev/gemini-api/terms)を確認し、
  同意していない人にカメラを向けないでください。
- 写真はローカルにのみ保存され、保持期間後に削除されます。テキストのみの記録には
  `--no-photos` を使ってください。
- Obsidian エクスポートは「ビュー」であり、正本は SQLite データベースです。

## ライセンス

[MIT](LICENSE)
