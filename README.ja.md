<p align="center">
  <img src="assets/banner.svg" alt="focus-cam-log — privacy-first webcam focus journaling" width="100%">
</p>

プライバシー配慮・ローカルファーストの Web カメラ集中ログツール。
分析は Google Gemini（デフォルト）または Ollama 経由の完全ローカルモデルで実行。

[English README](README.md)

focus-cam-log は一定間隔で Web カメラのスナップショットを撮影し、vision モデルに
「何をしているか」（集中してPCに向かっている / スマホを見ている / 席を外している
など）を分類させ、ローカルの SQLite データベースに記録します。集中状態の記録に加えて、
必要に応じてフォーカスのゆらぎをデスクトップ通知でリマインドし、1日の集中状況を
AI がまとめた日次サマリも生成できます。

## 機能

- **定期的な行動ログ** — N分ごとにスナップショットを撮影し、vision モデルが短い行動ラベルに分類。
- **2つの分析プロバイダ** — Google Gemini（デフォルト）、または [Ollama](https://ollama.com)
  経由のローカル vision モデル（`--provider ollama`）。ローカルなら**画像は一切マシンから出ません**。
- **フォーカスのゆらぎ通知** (`--watch`) — スマホ・寝ている・ゲーム等、集中が逸れた
  ラベルを検知したときにリマインド。強さは選べます: 通知センターのバナー（デフォルト）か、
  クリックするまで画面に残るダイアログ（`FOCUS_LOG_ALERT_STYLE=dialog`）。
- **日次サマリ** (`--summary`) — その日のイベントから集中時間・休憩・効率を Gemini が Markdown レポート化。
- **Obsidian エクスポート** (`--obsidian`) — 当日のログを Markdown テーブルとして vault に追記。
- **プライバシー設計** — デフォルトではテキストの行動ログのみ保存。写真のディスク保存は
  `--save-photos` による明示オプトインで、保存写真は保持期間（デフォルト3日）経過後に
  自動削除され、削除日時は DB に記録されます。外部に送信されるのは分析対象の
  スナップショットのみ（Gemini API）。詳細は [PRIVACY.md](PRIVACY.md)。

## 前提条件

- Python 3.9+
- Web カメラ
- 次のいずれか:
  - Gemini API キー（[Google AI Studio](https://aistudio.google.com/apikey)）
  - [Ollama](https://ollama.com) + vision 対応モデル（例: `ollama pull qwen3-vl:4b`）
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

`focus_on.sh` は `nohup` で起動するため、**ターミナルのウィンドウを閉じても、
ターミナルアプリを終了しても動き続けます**。止まるのは `focus_off.sh` を実行するか
再起動したときだけです。使い終わったら `focus_off.sh` を実行してください。
そうしないと記録され続けます。

完全ローカル実行（API キー不要・画像がマシンから出ない）:

```bash
ollama pull qwen3-vl:4b
./focus_on.sh --provider ollama
```

フォアグラウンド実行:

```bash
source venv/bin/activate
python3 focus_monitor.py --interval 10 --watch
python3 focus_monitor.py --provider ollama --watch   # ローカル分析
```

日次サマリの生成:

```bash
python3 focus_monitor.py --summary            # 今日
python3 focus_monitor.py --summary --summary-date 2026-07-01
```

別ターミナルウィンドウで、今検知している内容をリアルタイムに眺める:

```bash
./focus_watch.sh   # ログを追跡し、行動/モード行だけをフィルタして表示
```

これは読み取り専用です。ログファイルを追うだけで、稼働中の monitor には
一切影響しません。いつでも Ctrl+C かウィンドウを閉じて止められます。

## 恒久的な local-only 設定

再起動しても、毎回 `--provider ollama` を付けなくても、**常に local-only** で
動かしたい場合は env ファイルに設定を書きます（起動時に読み込み。優先順位は
CLI 引数 > プロセス環境変数 > env ファイル > デフォルト）:

```bash
mkdir -p ~/.focus-log
cat > ~/.focus-log/env <<'ENV'
FOCUS_LOG_PROVIDER=ollama
FOCUS_LOG_VISION_MODEL=qwen3-vl:4b
FOCUS_LOG_SUMMARY_MODEL=qwen3-vl:4b
ENV

./focus_on.sh
```

この設定をすると `./focus_on.sh` だけで Ollama local-only モードで起動します。
起動バナーには常に現在のモードが表示されます（`Mode: local-only` / `Mode: cloud`）。
意図せず `Mode: cloud` と表示されたら、env ファイルが読まれていません。

`FOCUS_LOG_SUMMARY_MODEL` には任意の Ollama テキストモデルを指定できます
（vision 対応が必要なのは `FOCUS_LOG_VISION_MODEL` のみ）。

## フォーカスのゆらぎ通知を強くする

デフォルトの `--watch` 通知は macOS 通知センターのバナーです。数秒で消えるため、
集中が逸れている瞬間（＝画面を見ていない瞬間）こそ見逃しやすいという弱点があります。
`FOCUS_LOG_ALERT_STYLE=dialog` は代わりにネイティブの `display dialog` を使い、
OK を押すまで画面に残ります。全画面オーバーレイや新規 GUI 依存の追加ではなく、
同じ macOS ネイティブ通知を少し強くしただけです。

```bash
# ~/.focus-log/env
FOCUS_LOG_ALERT_STYLE=dialog
FOCUS_LOG_ALERT_COOLDOWN_MINUTES=20   # 毎サイクル積み上がらないように
```

`FOCUS_LOG_ALERT_STYLE=off` でフォーカスのゆらぎ通知自体を無効化できます
（日次サマリやログ記録には影響しません）。

### リファレンス構成（作者が実際に動かしている設定）

このツールは Apple Silicon Mac mini（M4・32GB）上の local-only モードで
毎日実運用されています（サボり通知 + Obsidian エクスポート有効）:

```bash
# ~/.focus-log/env
FOCUS_LOG_PROVIDER=ollama
FOCUS_LOG_VISION_MODEL=qwen3-vl:4b        # 約15秒/フレーム — 10分間隔には十分
FOCUS_LOG_SUMMARY_MODEL=gemma4:12b-it-qat # 日次サマリ用（任意のローカルテキストモデルで可）
```

```bash
./focus_on.sh   # 10分間隔・--watch 通知・完全ローカル
```

実運用からのメモ:

- クラウド provider との比較テストで、通常のフレームなら `qwen3-vl:4b` は
  同等の行動ラベルを返しました。8B はメモリ2倍の価値がありませんでした
- 日次サマリは Gemma 12B QAT ビルドが比較3モデル中（クラウド既定含む）
  主観的に最良でした
- 32GB マシンでは vision モデルは**1本に固定**してください。複数のローカル
  モデルを交互に呼ぶとモデル再ロードのスラッシングが起きます
  （実測: 約15秒/フレーム → 60〜94秒に劣化）

## オプション

| フラグ | 説明 | デフォルト |
| --- | --- | --- |
| `--provider {gemini,ollama}` | 分析バックエンド（クラウド/ローカル） | `gemini` |
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
| `FOCUS_LOG_PROVIDER` | 分析バックエンド: `gemini` / `ollama` | `gemini` |
| `GEMINI_API_KEY` | Gemini API キー（gemini プロバイダのみ必須） | — |
| `FOCUS_LOG_DATA_DIR` | データディレクトリ（DB・写真・サマリ） | `~/.focus-log` |
| `FOCUS_LOG_ENV_FILE` | env ファイル: `FOCUS_LOG_*` 全変数と `GEMINI_API_KEY` を読み込む | `$FOCUS_LOG_DATA_DIR/env` |
| `FOCUS_LOG_OBSIDIAN_DIR` | `--obsidian` 出力先の vault パス | 未設定 |
| `FOCUS_LOG_MODEL` | モデル名（vision・サマリ共通） | `gemini-2.5-flash` / `qwen3-vl:4b` |
| `FOCUS_LOG_VISION_MODEL` | 画像分析用モデル（`FOCUS_LOG_MODEL` より優先） | provider デフォルト |
| `FOCUS_LOG_SUMMARY_MODEL` | 日次サマリ用モデル（`FOCUS_LOG_MODEL` より優先） | vision モデルと同じ |
| `FOCUS_LOG_ALERT_STYLE` | フォーカスのゆらぎ通知の強さ: `notify`（バナー）/ `dialog`（クリックまで残る）/ `off` | `notify` |
| `FOCUS_LOG_ALERT_COOLDOWN_MINUTES` | 通知間の最短間隔（分） | `20` |
| `FOCUS_LOG_OLLAMA_HOST` | ollama プロバイダの接続先 | `http://localhost:11434` |
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

### 容量の目安（実測）

テキストのみモード（デフォルト）はごく僅かです。1イベントあたり
SQLite で約0.5KB なので、5分間隔でも1日あたり約150KBにしかなりません。

`--save-photos` を使う場合、640px幅のスナップショット1枚は約130KB。
5分間隔なら1日約288枚（約36MB/日・約1GB/月）ですが、`--retention-days`
（デフォルト3日）経過後は古い写真が削除されるため、ディスク使用量は
`130KB × 288 × retention_days` 程度（デフォルト設定で約110MB）で頭打ちに
なり、動かし続けても増え続けることはありません。

## プライバシーに関する注意

- デフォルトの `gemini` プロバイダでは、あなた（および画角に入った人）のスナップショットが
  分析のため Google Gemini API に送信されます。[Google の API 規約](https://ai.google.dev/gemini-api/terms)を確認し、
  同意していない人にカメラを向けないでください。
- `--provider ollama` ならローカル vision モデルで分析され、**画像もテキストも一切マシンから出ません**。
- デフォルトでは写真は残りません: 分析用スナップショットは毎サイクル後に削除され、
  テキストラベルのみ保存されます。`--save-photos` 指定時も写真はローカルのみに保存され、
  保持期間後に削除されます。
- Obsidian エクスポートは「ビュー」であり、正本は SQLite データベースです。
- 詳細は [PRIVACY.md](PRIVACY.md)、セキュリティポリシーは [SECURITY.md](SECURITY.md)。

## Roadmap

- ~~モデルバックエンドの provider 抽象化・Ollama 等ローカルモデル対応~~ — v0.2.0 で実装済み（`--provider ollama`）
- 同じ provider インターフェースでの他クラウドバックエンド対応（Claude・OpenAI 等）


## ライセンス

[MIT](LICENSE)
