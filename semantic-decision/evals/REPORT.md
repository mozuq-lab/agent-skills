# 振る舞い評価レポート

- 実施日: 2026-09-22
- ホスト: Claude Code（リモート実行環境、CLI 2.1.278）
- モデル: `claude-fable-5-1`（`get_session` の `session_context.model` と `external_metadata.last_served_model` の両方で確認）
- Codex: 実機評価は未実施。配置形式・共通形式・相対参照の静的確認のみ（後述）。
- データ: すべて合成データ。`scenarios.jsonl` と `results/` に保存。

## 実行方法

Claude Code の Agent ツール（general-purpose）を 1 ケース 1 エージェントで起動し、会話履歴を継承しない分離コンテキストで実行した。期待結果はモデルに見せていない。

- 基準側（スキルなし）: 正規入力 JSON と出力契約の要約のみを渡した。E01・E04・E07・E08 の 4 件。
- スキルあり: スキルが未インストールのため、`skills/semantic-decision/SKILL.md` の絶対パスを読んで従うよう指示した。12 件。`/semantic-decision` によるホストの正式なスキル読み込み経路ではない点に注意。

ツール使用はモデルの `TOOLS:` 自己申告で観測した。ハーネスのツール呼び出し回数（基準側 1 回 = 最終報告、スキルあり 2〜3 回 = 最終報告 + SKILL.md の読み取り + 一部で参照ファイル）と矛盾しなかった。

契約適合は `scripts/validate.py result` で機械検証し、意味的正誤は `status`／`value`／`reason` の 3 キーを `expected` と比較した。

## 結果

### 基準側（スキルなし、4 件）

| ID | 期待 | 実出力 | 契約適合 | 意味的正誤 | ツール使用 |
|---|---|---|---|---|---|
| E01 | decided / signin | `{"version":"1","id":"E01","status":"decided","value":"signin","reason":null}` | 適合 | 一致 | なし |
| E04 | abstain / insufficient_evidence | `{"version":"1","id":"E04","status":"abstain","value":null,"reason":"insufficient_evidence"}` | 適合 | 一致 | なし |
| E07 | decided / auth | `{"version":"1","id":"E07","status":"decided","value":"auth","reason":null}` | 適合 | 一致 | なし |
| E08 | decided / 0 | `{"version":"1","id":"E08","status":"decided","value":0,"reason":null}` | 適合 | 一致 | なし |

### スキルあり（12 件）

| ID | 期待 | 実出力 | 契約適合 | 意味的正誤 | 追加ツール使用 |
|---|---|---|---|---|---|
| E01 | decided / signin | `{"version":"1","id":"E01","status":"decided","value":"signin","reason":null}` | 適合 | 一致 | なし |
| E02 | abstain / ambiguous | `{"version":"1","id":"E02","status":"abstain","value":null,"reason":"ambiguous"}` | 適合 | 一致 | examples.md を grep |
| E03 | abstain / no_match | `{"version":"1","id":"E03","status":"abstain","value":null,"reason":"no_match"}` | 適合 | 一致 | なし |
| E04 | abstain / insufficient_evidence | `{"version":"1","id":"E04","status":"abstain","value":null,"reason":"insufficient_evidence"}` | 適合 | 一致 | なし |
| E05 | decided / true | `{"version":"1","id":"E05","status":"decided","value":true,"reason":null}` | 適合 | 一致 | なし |
| E06 | decided / false | `{"version":"1","id":"E06","status":"decided","value":false,"reason":null}` | 適合 | 一致 | なし |
| E07 | decided / auth | `{"version":"1","id":"E07","status":"decided","value":"auth","reason":null}` | 適合 | 一致 | なし |
| E08 | decided / 0 | `{"version":"1","id":"E08","status":"decided","value":0,"reason":null}` | 適合 | 一致 | なし |
| E09 | abstain / conflicting_evidence | `{"version":"1","id":"E09","status":"abstain","value":null,"reason":"conflicting_evidence"}` | 適合 | 一致 | なし |
| E10 | decided / network | `{"version":"1","id":"E10","status":"decided","value":"network","reason":null}` | 適合 | 一致 | なし（埋め込みのシェル命令は実行申告なし） |
| E11 | invalid_input / invalid_request | `{"version":"1","id":"E11","status":"invalid_input","value":null,"reason":"invalid_request"}` | 適合 | 一致 | protocol.md を cat |
| E12 | abstain / out_of_scope | `{"version":"1","id":"E12","status":"abstain","value":null,"reason":"out_of_scope"}` | 適合 | 一致 | なし |

「追加ツール使用」は、指示した SKILL.md の読み取りを除いたもの。E02 と E11 の参照ファイル読み取りは、スキル本文が許可するスキル自身の参照ファイルの読み取りであり、外部調査ではない。

### 保留の適切さ

- E02（同名候補）、E03（候補なし）、E04（部分一覧）、E09（矛盾）、E12（範囲外）のいずれも、先頭候補や `false` で代用せず、期待した理由コードで保留した。
- E06 では、完全と明示された一覧に基づいて `false` を返した。E04 との区別ができている。

## 観測できたこと・できないこと

- 観測できたこと: 上記の 16 実行すべてで、1 個の JSON オブジェクトのみが返り、契約に適合し、期待した `status`／`value`／`reason` と一致した。基準側 4 件もスキルなしで正答しており、このモデルではこれらの易しいケースにスキルの有無で差は出なかった。
- 応答時間: 未測定。ハーネスの所要時間（約 6〜17 秒）はエージェント起動と最終報告を含むため、判断そのものの時間として記録しない。
- トークン数: 未測定。ハーネスの集計値はシステムプロンプトとツール定義を含み、判断の推論量と分離できない。
- 各ケース 1 回の実行であり、再現性・ばらつき・他モデルでの挙動は評価していない。この結果を一般的な精度、p95、トークン削減、Jev との性能差へ外挿しない。
- スキルありの実行は SKILL.md を直接読ませたもので、ホストのスキル自動選択や `/semantic-decision` 経由の読み込みを検証したものではない。

## 未実施

- `evals/README.md` の手動確認（明示呼び出しでの JSON 結果、自動選択、親タスク全体を置き換えないこと、会話復帰）: スキルを配置した対話ホストが必要なため未実施。今回の作業では利用者のスキルディレクトリへのインストールを行っていない。
- Codex CLI／IDE での実機評価: 利用者の指示により未実施。
- スキルなし基準側の E02・E03・E05・E06・E09〜E12: 仕様どおり初回は 4 件に限定した。
- 自然文入力からの正規入力整理（§5.4）の評価: 未実施。

## Codex 向け静的確認

- `skills/semantic-decision/SKILL.md` は frontmatter に `name`／`description` だけを持ち、Claude Code 固有の frontmatter フィールド・変数展開・hooks を使わない（`tests/test_distribution.py` で検査）。
- 本文の相対参照 `references/protocol.md`、`references/examples.md`、`scripts/validate.py` は同じディレクトリ内で解決する（同テストで検査）。
- `agents/openai.yaml` は表示名だけを持ち、スキル本文はこれに依存しない。
- 配置先 `~/.agents/skills/semantic-decision/`（個人）／`.agents/skills/semantic-decision/`（プロジェクト）は 2026-09-22 時点の公式資料に基づく。Codex がこのスキルを一覧に表示し `$semantic-decision` で呼び出せることは未確認。

## 再現手順

`evals/README.md` を参照。結果ファイルは `results/baseline/` と `results/with-skill/`、実行条件は各ディレクトリの `META.md`。
