# 個人用 Agent Skills

Codex・Claude Code で使う個人用スキルの原本を管理するリポジトリです。編集と変更履歴はこのリポジトリで管理し、ユーザー全体への配布・一覧確認・更新・削除には [Vercel skills CLI](https://github.com/vercel-labs/skills) を `npx` で使います。

## スキル一覧

| 名前 | 表示名 | 用途 | 原本 |
| --- | --- | --- | --- |
| `expand` | 思考を広げる | 明示的に呼び出した回答で、分析・批評・説明・相談・発想の幅と厚みを増やす | [SKILL.md](skills/expand/SKILL.md) |
| `execute-review` | 実行とレビュー | 依頼を独立した実行担当とレビュー担当のサブエージェントで処理し、修正を経て報告する。コーディングに限らず設計・文書・調査にも使う | [SKILL.md](skills/execute-review/SKILL.md) |
| `casebrief-lite` | テスト観点と設計の入り口 | 小さな修正の diff・コミット範囲・PR・Issue・説明から、変更の要約・設計の入り口・テスト観点・仮定と確認事項を 1 画面で出す | [SKILL.md](skills/casebrief-lite/SKILL.md) |
| `security-audit` | セキュリティ監査 | リポジトリ全体や指定したファイル・ディレクトリを、Claude Code の `/security-review` と同じ観点で、悪用できる脆弱性に絞って監査する | [SKILL.md](skills/security-audit/SKILL.md) |

付属ファイルは各スキルのディレクトリ内に置きます。どのスキルも本文 `SKILL.md`、Codex向け表示・呼び出し設定 `agents/openai.yaml`、小さなテスト例 `references/smoke-tests.md` の3ファイルを基本とします。`casebrief-lite` は、観点と技法のメモ `references/viewpoints.md` を加えた4ファイルです。`security-audit` は、監査の観点 `references/criteria.md`、誤検知の除外規則 `references/false-positive-filter.md`、出典とライセンス `THIRD_PARTY_NOTICES.md` を加えた6ファイルです。追加のスクリプトや特定の開発プロジェクトへの依存はありません。外部サービスは、`casebrief-lite` が PR・Issue を読むときに `gh` を使うだけです。

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
npx skills add mozuq-lab/agent-skills -g -a codex claude-code --skill casebrief-lite
npx skills add mozuq-lab/agent-skills -g -a codex claude-code --skill security-audit
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

- Codex: `$expand 質問`、`$execute-review 依頼`、`$casebrief-lite 対象`、`$security-audit 対象と追加の指示`。引数なしなら、`expand` と `execute-review` は対象が明らかな直前の相談・依頼に、`casebrief-lite` は未コミットの差分に適用します。
- Claude Code: `/expand 質問`、`/execute-review 依頼`、`/casebrief-lite 対象`、`/security-audit 対象と追加の指示`。本文中の `$名前` はCodexの表記で、Claude Codeでは `/名前` による明示呼び出しとして使います。

`expand` は呼び出された一回答に適用し、明示された個数・長さ・形式を優先します。相談への呼び出しをコード変更や外部への書き込みの許可とは扱いません。

`execute-review` は、呼び出されたエージェントを進行役にして、実行担当とレビュー担当を会話履歴を継承しないサブエージェントとして起動します。Claude Code では Agent ツール、Codex ではサブエージェント機能（`spawn_agent`）を使うため、Codex側は `features.multi_agent` が有効である必要があります。実行許可は元の依頼と環境に従い、依頼にない push・公開・送信は行いません。

`casebrief-lite` の対象は、空（未コミットの差分と未追跡ファイル）、コミット範囲（`main...`）、ブランチ、PR（`#123`）、Issue（`issue 45`）、修正の説明文のいずれかです。サブエージェントは使わず、結果はチャットに出します。ファイルを書き出すのは、casebrief 向けの `source.md` の下書きを頼まれたときだけです。Claude Code では引数が本文の `$ARGUMENTS` に入り、Codex では `$casebrief-lite` に続く文字列を引数として読みます。明示呼び出し専用にしているのは、「テスト設計を作って」という依頼で casebrief の代わりに誤って起動しないようにするためです。

`security-audit` の引数は自由な文として読みます。文中のパス・ディレクトリ名・glob が対象で、省略するとリポジトリ全体（git 管理外なら作業ディレクトリ）です。名前が見つからないか複数に当たる場合は、尋ねて止まります。残りは追加の指示として、特に見てほしい「重点」と、範囲・報告への注文（テストも含める、LOW も報告する、ファイルに書き出すなど）に分けて扱います（例: `/security-audit src ディレクトリをレビューしてください。API キーの扱いを重点的に`）。重点に当たる観点には、元の除外規則（レート制限など）を当てません。呼び出されたエージェントが進行役になり、対象を約3,000行ずつの単位に分けて洗い出し担当を、候補ごとに検証担当を、それぞれ会話履歴を継承しないサブエージェントとして起動します（同時に5体まで）。単位が10を超える場合は、起動前に確認を求めます。サブエージェントを使えない環境では進行役が自分で行い、報告に独立検証なしと明記します。読み取りだけで監査し、結果はチャットに出します。ブランチの差分だけを見るなら Claude Code 組み込みの `/security-review` を使います。観点と除外規則は [anthropics/claude-code-security-review](https://github.com/anthropics/claude-code-security-review)（MIT License）の翻訳・改変です。

本文は両エージェントで共有できますが、`agents/openai.yaml` の表示名と `policy.allow_implicit_invocation: false` はCodex向けの設定です。Claude Codeで設定レベルの自動呼び出し防止を行う仕組みは frontmatter の `disable-model-invocation: true` です。どのスキルも明示呼び出し専用なので、Claude Codeは frontmatter の `disable-model-invocation: true`、Codexは `openai.yaml` の `allow_implicit_invocation: false` で、それぞれ自動適用を抑止しています。Codexは frontmatter のこのフィールドを解釈せず無視します。また Claude Codeでは、この設定があるスキルの description は会話の文脈に載らないため、description 中の「自動適用しない」という記述は実質Codex向けです。詳細は [Claude Codeのスキル仕様](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill) を参照してください。
