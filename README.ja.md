# focus-cam-log

Google Gemini を使った、プライバシー配慮・ローカルファーストの
Web カメラ集中ログツール。

[English README](README.md)

focus-cam-log は一定間隔で Web カメラのスナップショットを撮影し、Gemini に
「何をしているか」（集中してPCに向かっている / スマホを見ている / 席を外している
など）を分類させ、ローカルの SQLite データベースに記録します。集中状態の記録に加えて、
必要に応じてフォーカスのゆらぎをデスクトップ通知でリマインドし、1日の集中状況を
AI がまとめた日次サマリも生成できます。

## 機能

- **定期的な行動ログ** — N分ごとにスナップショットを撮影し、Gemini が短い行動ラベルに分類。
- **フォーカスのゆらぎ通知** (`--watch`) — スマホ・寝ている・ゲーム等、集中が逸れた
  ラベルを検知したときにデスクトップ通知でリマインド。
- **日次サマリ** (`--summary`) — その日のイベントから集中時間・休憩・効率を Gemini が Markdown レポート化。
- **Obsidian エクスポート** (`--obsidian`) — 当日のログを Markdown テーブルとして vault に追記。
- **プライバシー設計** — デフォルトではテキストの行動ログのみ保存。写真のディスク保存は
  `--save-photos` による明示オプトインで、保存写真は保持期間（デフォルト3日）経過後に
  自動削除され、削除日時は DB に記録されます。外部に送信されるのは分析対象の
  スナップショットのみ（Gemini API）。詳細は [PRIVACY.md](PRIVACY.md)。

## 前提条件

- Python 3.9+
- Web カメラ
- Gemini API キー（[Google AI Studio](https://aistudio.google.com/apikey)）
- デスクトップ通知: macOS（`osascript`）/ Linux（`notify-send`）。
  それ以外はコンソール出力にフォールバック。

## クイックスタート

```bash
git clone <this-repo> focus-cam-log && cd focus-cam-log
./setup.sh
export GEMINI_API_KEY=your-key-here
./focus_on.sh          # バックグラウンドで記録開始（リマインド有効）
./focus_off.sh         # 記録停止
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
| `--watch` | フォーカスのゆらぎ通知（リマインド） | off |
| `--save-photos` | スナップショットをディスクに保存（デフォルトはテキストのみ） | off |
| `--retention-days N` | 保存写真の保持日数 | `3` |
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
├── photos/            # スナップショット（--save-photos 時のみ・保持期間後に削除）
└── summaries/         # 生成された日次サマリ（Markdown）
```

設定変数の一覧は [env.example](env.example) を参照。

`focus_events` テーブルは `photo_exists` / `photo_deleted_at` 列を持ち、
写真削除後も履歴の監査可能性を保ちます。

## プライバシーに関する注意

- あなた（および画角に入った人）のスナップショットが分析のため Google Gemini API に
  送信されます。[Google の API 規約](https://ai.google.dev/gemini-api/terms)を確認し、
  同意していない人にカメラを向けないでください。
- デフォルトでは写真は残りません: 分析用スナップショットは毎サイクル後に削除され、
  テキストラベルのみ保存されます。`--save-photos` 指定時も写真はローカルのみに保存され、
  保持期間後に削除されます。
- Obsidian エクスポートは「ビュー」であり、正本は SQLite データベースです。
- 詳細は [PRIVACY.md](PRIVACY.md)、セキュリティポリシーは [SECURITY.md](SECURITY.md)。

## Roadmap

- モデルバックエンドの provider 抽象化（ローカル/代替モデル対応）
- クラウド API に画像を送りたくないユーザー向けの Ollama 等ローカルモデル対応

v0.1.0 では未実装です。

## ライセンス

[MIT](LICENSE)
