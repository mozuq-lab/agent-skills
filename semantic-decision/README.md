# semantic-decision

与えられた候補・根拠・判断基準から、小さな判断を 1 個の JSON で返す Claude Code／Codex 用スキルの開発プロジェクトです。スキル本体は [`skills/semantic-decision/`](../skills/semantic-decision/) にあり、このディレクトリには検証・評価・手順だけを置きます。

## 目的

- 既に候補・判断基準・必要な情報が与えられている小さな判断を、余計な調査・長い説明・操作の実行へ広げずに処理する。
- `choose`（候補選択）／`boolean`（真偽）／`classify`（単一ラベル分類）／`score`（段階評価）を共通の入出力契約で扱う。
- 判断できないときは `false` や先頭候補で代用せず、`abstain` と理由コードで保留する。
- 同じスキル本体を Claude Code と Codex に配布できる。

「Jev 的」とは、有限の候補選択や判定を短い構造化結果として返す振る舞いだけを指します。TypeSafe AI の Jev（System One モデル）の API を呼ぶスキルではなく、Jev のモデル構造・推論速度・校正済み確率を再現するものでもありません。

## 非目的

- 外部 API、モデルアダプター、MCP サーバー、自動インストーラー、永続メモリ、バッチ処理は作りません。
- 判断結果からブラウザ操作・シェル操作・ファイル変更・外部送信を行う機能はありません。
- 高速化、トークン削減、校正済み確率、完全な JSON 保証、安全性の保証は謳いません。スキルはホストへの指示であり、独立した推論サービスでもセキュリティ境界でもありません。
- `confidence`、`runner_up`、複数ラベル、ランキング、複数項目の総合点は初版に含めません。

## 構成

```text
skills/semantic-decision/          # 配布対象（正本）
├── SKILL.md                       # スキル本文（英語、200行以内）
├── agents/openai.yaml             # Codex 用の表示名（このリポジトリの慣例）
├── references/protocol.md         # 入出力契約の厳密版
├── references/examples.md         # 入出力例
└── scripts/validate.py            # 契約の機械検証（標準ライブラリのみ）
semantic-decision/                 # 配布対象外
├── README.md                      # この文書
├── tests/                         # unittest（契約・配布・fixture 整合）
└── evals/                         # 振る舞い評価の fixture・手順・報告
```

仕様書の原案ではスキル本体を `semantic-decision/skills/semantic-decision/` に置く構成でしたが、このリポジトリの配布に使う skills CLI は `skills/` 直下を走査し、既存スキルが見つかると再帰探索を行いません。そのため、スキル本体はリポジトリ慣例どおり `skills/semantic-decision/` に置き、tests と evals を `semantic-decision/` に分けました。`validate.py` のコマンド例はリポジトリルートから実行する前提で、仕様書と同じパスになります。

## 呼び出し方

明示呼び出し:

```text
Claude Code:
/semantic-decision
次の候補から、ログインを確定するボタンを選んでください。
候補: A=サインイン(button)、B=アカウント新規登録(button)
```

```text
Codex CLI／IDE:
$semantic-decision
次の候補から、ログインを確定するボタンを選んでください。
候補: A=サインイン(button)、B=アカウント新規登録(button)
```

このように自然文で渡した場合、ホストが問い・候補・根拠を正規入力へ整理して判定します。生成してよいのは `version`、リクエスト ID、未採番の `C1`／`E1` 等の ID だけで、候補・事実・評価基準は補いません。正規入力の JSON を直接渡すこともできます。

親タスク中の局所的な判断に自動で使われることもありますが、ホストの判断に依存するため常に発火するとは限りません。「新しいサービスのアイデアを考える」「このコードを実装する」のような親タスク全体をこのスキルで置き換えることはなく、判断結果の次の通常会話は JSON に固定されません。

期待する結果の例:

```json
{"version":"1","id":"d-001","status":"decided","value":"A","reason":null}
```

契約の詳細は [`references/protocol.md`](../skills/semantic-decision/references/protocol.md)、例は [`references/examples.md`](../skills/semantic-decision/references/examples.md) を参照してください。

## 配置

このリポジトリの他のスキルと同じく、skills CLI でグローバル配置できます。

```sh
npx skills add mozuq-lab/agent-skills -g -a codex claude-code --skill semantic-decision
```

手動で配置する場合は `skills/semantic-decision/` ディレクトリだけを次の場所へコピーします。tests と evals は含めません。

| 利用先 | 個人全体で使う配置 | プロジェクト限定配置 |
|---|---|---|
| Claude Code | `~/.claude/skills/semantic-decision/` | `.claude/skills/semantic-decision/` |
| Codex | `~/.agents/skills/semantic-decision/` | `.agents/skills/semantic-decision/` |

配置先に同名ディレクトリがあれば無断で上書きしません。グローバル設定、権限、モデル設定、`CLAUDE.md`／`AGENTS.md` は変更しません。今回の作業では利用者の個人スキルディレクトリへのインストールは行っていません。

## Python 検証

`scripts/validate.py` は Python 3.11 以上、標準ライブラリのみで動きます。モデルは呼ばず、JSON の構造・型・ID 対応・`status` と `value` の整合だけを確認します。リポジトリルートから:

```sh
python3 skills/semantic-decision/scripts/validate.py request --file request.json
python3 skills/semantic-decision/scripts/validate.py result --request request.json --file response.json
```

stdout は `{"valid": true, "errors": []}` の形の JSON 1 個。終了コードは妥当なら 0、契約違反なら 2、読み取り不可などの運用エラーなら 1 です。`valid: true` は出力が契約に合うという意味だけで、判断の正しさや操作の安全性を意味しません。判定結果を機械実行へ渡す呼び出し元では、検証失敗を保留・停止として扱ってください。

## テスト

```sh
python3 -m unittest discover -s semantic-decision/tests -v
```

- `test_validate.py`: 入出力契約、厳密な JSON 解析、結果と入力の対応、CLI の終了コードとファイル非変更。
- `test_distribution.py`: 必須ファイル、frontmatter、相対参照、SKILL.md の行数上限、標準ライブラリのみの使用。
- `test_scenarios.py`: `evals/scenarios.jsonl` の 12 件が契約と整合すること。

## 振る舞い評価

評価の手順と結果は [`evals/README.md`](evals/README.md) と [`evals/REPORT.md`](evals/REPORT.md) を参照してください。単体テストが通ることと、モデルの判断品質・速度が検証されたことは区別します。

## 実装上の判断

- 空白のみの文字列は `question`・`evidence[].text`・`label`・`description`・`rubric[].description` に加え、`constraints[]` でも拒否します（仕様は文字数のみを規定）。
- 結果ファイルが 64 KiB を超える場合は `invalid_result`（終了コード 2）とします。
- `result` 検証で元の request が `invalid_request` かつ形式が有効な `id` を持つ場合、結果の `id` はその値と一致することを要求します。`null` は不可です。
- 深すぎる入れ子など Python の `json` が処理できない入力は、制御された `invalid_json` として扱います。
- `agents/openai.yaml` はこのリポジトリの他スキルとの整合のために置いた Codex 用の表示設定で、スキル本文は依存しません。自動適用を抑止する `policy` は付けていません（仕様が限定的な自動利用を許容するため）。
- SKILL.md の frontmatter は `name`／`description` と、Claude Code 向けの `context`／`agent`／`model`／`effort`／`background` だけです。`allowed-tools`、`disable-model-invocation`、hooks、`$ARGUMENTS` などの変数展開は使いません。

## 実行モデルと effort（Claude Code）

SKILL.md の frontmatter には、`name`／`description` に加えて Claude Code 向けの実行設定を置いています。

```yaml
context: fork
agent: general-purpose
model: claude-sonnet-5
effort: low
background: false
```

- Claude Code では、スキル本文をプロンプトとして general-purpose サブエージェントに渡し、会話履歴なしで実行します。`model` と `effort` はそのサブエージェントにだけ効き、親セッションのモデルや effort は変わりません。`background: false` により、判断結果を待ってから親の作業が続きます。
- 組織の `availableModels` で除外されたモデルや auto モード非対応のモデルは無視され、セッションのモデルで実行されます。
- Codex にはスキル単位でモデルや reasoning effort を指定する仕組みがなく、これらのフィールドは無視されます。Codex ではホストの設定に従ってインラインで実行されます。
- 仕様書 §9.1 は当初これらのフィールドに依存しない方針でしたが、軽いモデルで実行したいという利用者の要望により変更しました。スキル本文自体はこれらの設定が無くても動作するよう書かれています。

評価結果は [`evals/REPORT.md`](evals/REPORT.md) の追加評価 1・2 を参照してください。`context: fork` 相当の経路で、Sonnet 5 は 12 シナリオ + 追加 4 回の計 16 回すべてで JSON 1 個だけの結果を返し、判定も期待どおりでした。Haiku 4.5 は判定内容は概ね維持したものの出力契約を満たさないことが多く、採用していません。`effort: low` の影響は未検証です。

## 限界

- スキル本文の禁止指示だけでツール使用が技術的に封鎖されるわけではありません。厳密な封鎖が必要な呼び出し元は、ホストの権限設定や実行側コードで制御してください。
- 短い出力の指示は、内部推論量、ホストが消費するトークン、応答時間、正答率を保証しません。新しい API キーは不要ですが、ホストの通常の利用枠は消費します。
- 外部 API を使わないことは「入力が端末外に出ない」保証ではありません。
- 意味的な候補選択を、削除・支払い・公開・認可変更などの承認根拠にしないでください。

## 今後の候補（今回は実装しない）

同じ request／result 契約への実 API アダプター接続、独立判定の複数件処理、実測に基づくモデル選択。追加する場合も、自己申告の信頼度・モデル固有スコア・実データで校正された確率を混同しません。
