# 個人用 Agent Skills

Codex・Claude Code で使う個人用スキルの原本を管理するリポジトリです。編集と変更履歴はこのリポジトリで管理し、ユーザー全体への配布・一覧確認・更新・削除には [Vercel skills CLI](https://github.com/vercel-labs/skills) を `npx` で使います。

## スキル一覧

| 名前 | 表示名 | 用途 | 原本 |
| --- | --- | --- | --- |
| `expand` | 思考を広げる | 明示的に呼び出した回答で、分析・批評・説明・相談・発想の幅と厚みを増やす | [SKILL.md](skills/expand/SKILL.md) |
| `execute-review` | 実行とレビュー | 依頼を独立した実行担当とレビュー担当のサブエージェントで処理し、修正を経て報告する。コーディングに限らず設計・文書・調査にも使う | [SKILL.md](skills/execute-review/SKILL.md) |
| `semantic-decision` | 小さな判断をJSONで返す | 与えられた候補・根拠から `choose`／`boolean`／`classify`／`score` の判定を1個のJSONで返す。判断不能は `abstain` とし、操作は実行しない。開発用のテスト・評価は [semantic-decision/](semantic-decision/README.md) | [SKILL.md](skills/semantic-decision/SKILL.md) |

付属ファイルは各スキルのディレクトリ内に置きます。`expand` と `execute-review` は本文 `SKILL.md`、Codex向け表示・呼び出し設定 `agents/openai.yaml`、小さなテスト例 `references/smoke-tests.md` の3ファイルで構成しています。`semantic-decision` は本文と `agents/openai.yaml` に加え、入出力契約と例の参照ファイル、標準ライブラリだけの検証スクリプト `scripts/validate.py` を持ち、単体テストと振る舞い評価は配布対象外の `semantic-decision/` に置いています。どのスキルも外部サービスや特定の開発プロジェクトへの依存はありません。

## 原本と利用用ファイル

skills CLI の通常のグローバル配置は次の構成です。CLI 1.5.24 の実装を確認しています。`CLAUDE_CONFIG_DIR` を指定している環境では、Claude Codeの参照先が変わる場合があります。`<name>` はスキル名です。

| 役割 | パス |
| --- | --- |
| 編集用の原本 | `<このリポジトリのローカル clone>/skills/<name>/` |
| CLIが配置する利用用ファイルの実体 | `~/.agents/skills/<name>/` |
| Codexの読み込み先 | `~/.agents/skills/<name>/` を直接参照 |
| Claude Code用のsymlink | `~/.claude/skills/<name>/` → `~/.agents/skills/<name>/` |

利用用ファイルは配布されたコピーです。編集はローカル clone で行い、インストール先を直接編集しません。symlink は各エージェントから利用用ファイルを参照するためのもので、編集用 clone や GitHub と自動同期する仕組みではありません。ローカル clone の変更を利用環境へ届けるには、commit・push 後に `skills update` を実行します。

Symlink方式を選んでも、共有ディレクトリを直接認識するCodexには追加のsymlinkを作らず、Claude Codeから共有ディレクトリへのsymlinkを作るのが、このCLIの動作です。

## インストール

Node.js と `npx` を利用できる環境で実行します。配置範囲はユーザー全体、配布先はCodex・Claude Codeです。スキルごとに `--skill` で対象を指定します。

```sh
npx skills add mozuq-lab/agent-skills -g -a codex claude-code --skill expand
npx skills add mozuq-lab/agent-skills -g -a codex claude-code --skill execute-review
npx skills add mozuq-lab/agent-skills -g -a codex claude-code --skill semantic-decision
```

インストール方式の選択では **Symlink** を選択します。確認画面でスキル名と対象エージェントを確かめて進めます。既存の同名スキルがある場合は、内容が原本に取り込まれていることを先に確認してください。

## 一覧確認

```sh
npx skills list -g -a codex claude-code
npx skills list -g -a codex claude-code --json
```

CLIの一覧とファイル・symlinkの確認は、各エージェントが実際にスキルを認識し実行したことの確認とは区別します。

## 編集と更新

ローカル clone のルートディレクトリで、以下の順に実行します。例は `expand` を編集する場合で、他のスキルは名前を読み替えます。

```sh
git pull --ff-only
```

`skills/expand/` 内の必要なファイルを編集し、frontmatter、参照リンク、呼び出し設定、そのスキルの `references/smoke-tests.md` で変更に関係する振る舞いを確認します。作業中の変更がある場合は、pullやcommitの前に差分を確認してください。

```sh
git diff --check
git diff -- skills/expand
git add skills/expand
git commit -m "expandの応答方針を調整"
git push origin main
npx skills update expand -g
npx skills list -g -a codex claude-code
```

`skills update expand -g` はグローバルの `expand` だけを更新します。更新元はCLIが記録したGitHubリポジトリで、未pushのローカル変更は反映されません。READMEも変更した場合は、その内容を確認して同じコミットへ含めます。

## 削除

```sh
npx skills remove expand -g -a codex claude-code
```

CLIの確認画面で対象を確かめて削除します。編集用の原本とGitHubの履歴は残ります。

## 呼び出し方と共通利用の範囲

- Codex: `$expand 質問`、`$execute-review 依頼`、`$semantic-decision 判断依頼`。引数なしなら、対象が明らかな直前の相談・依頼に適用します。
- Claude Code: `/expand 質問`、`/execute-review 依頼`、`/semantic-decision 判断依頼`。本文中の `$名前` はCodexの表記で、Claude Codeでは `/名前` による明示呼び出しとして使います。

`expand` は呼び出された一回答に適用し、明示された個数・長さ・形式を優先します。相談への呼び出しをコード変更や外部への書き込みの許可とは扱いません。

`semantic-decision` は、候補・根拠・判断基準が揃った小さな判断に使い、結果を JSON 1 個で返します。判断できなければ `abstain` で保留し、結果に基づく操作や承認は行いません。他の2つと異なり、親タスク中の局所的な判断で自動的に選択されることを許容しているため、`disable-model-invocation` と `allow_implicit_invocation: false` は付けていません。Claude Code では frontmatter の `context: fork`・`model: claude-sonnet-5`・`effort: low` により、会話履歴を持たないサブエージェントで軽いモデルとして実行されます。Codex ではこれらを実行設定として前提にしません。`codex-cli 0.155.1` の手動 smoke test では現在の frontmatter のまま明示呼び出しと JSON-only 応答に成功しましたが、各フィールドを解釈したか、どのモデル・effort・実行経路を使ったかは確認していません。詳細は [semantic-decision/README.md](semantic-decision/README.md) を参照してください。

`execute-review` は、呼び出されたエージェントを進行役にして、実行担当とレビュー担当を会話履歴を継承しないサブエージェントとして起動します。Claude Code では Agent ツール、Codex ではサブエージェント機能（`spawn_agent`）を使うため、Codex側は `features.multi_agent` が有効である必要があります。実行許可は元の依頼と環境に従い、依頼にない push・公開・送信は行いません。

本文は両エージェントで共有できますが、`agents/openai.yaml` の表示名と `policy.allow_implicit_invocation: false` はCodex向けの設定です。Claude Codeで設定レベルの自動呼び出し防止を行う仕組みは frontmatter の `disable-model-invocation: true` です。`expand` と `execute-review` は明示呼び出し専用なので、Claude Codeは frontmatter の `disable-model-invocation: true`、Codexは `openai.yaml` の `allow_implicit_invocation: false` で、それぞれ自動適用を抑止しています。Codex側の制御は `openai.yaml` に置き、Claude Code固有の frontmatter をCodexがどう解釈するかには依存しません。また Claude Codeでは、この設定があるスキルの description は会話の文脈に載らないため、description 中の「自動適用しない」という記述は実質Codex向けです。詳細は [Claude Codeのスキル仕様](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill) を参照してください。
