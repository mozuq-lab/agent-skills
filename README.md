# 個人用 Agent Skills

Codex・Claude Code で使う個人用スキルの原本を管理するリポジトリです。編集と変更履歴はこのリポジトリで管理し、ユーザー全体への配布・一覧確認・更新・削除には [Vercel skills CLI](https://github.com/vercel-labs/skills) を `npx` で使います。

## スキル一覧

| 名前 | 表示名 | 用途 | 原本 |
| --- | --- | --- | --- |
| `expand` | 思考を広げる | 明示的に呼び出した回答で、分析・批評・説明・相談・発想の幅と厚みを増やす | [SKILL.md](skills/expand/SKILL.md) |

付属ファイルは各スキルのディレクトリ内に置きます。`expand` は本文、[Codex向け表示・呼び出し設定](skills/expand/agents/openai.yaml)、[小さなテスト例](skills/expand/references/smoke-tests.md) の3ファイルで構成されています。追加のスクリプト、外部サービス、特定の開発プロジェクトへの依存はありません。

## 原本と利用用ファイル

skills CLI の通常のグローバル配置は次の構成です。CLI 1.5.24 の実装を確認しています。`CLAUDE_CONFIG_DIR` を指定している環境では、Claude Codeの参照先が変わる場合があります。

| 役割 | パス |
| --- | --- |
| 編集用の原本 | `<このリポジトリのローカル clone>/skills/expand/` |
| CLIが配置する利用用ファイルの実体 | `~/.agents/skills/expand/` |
| Codexの読み込み先 | `~/.agents/skills/expand/` を直接参照 |
| Claude Code用のsymlink | `~/.claude/skills/expand/` → `~/.agents/skills/expand/` |

利用用ファイルは配布されたコピーです。編集はローカル clone で行い、インストール先を直接編集しません。symlink は各エージェントから利用用ファイルを参照するためのもので、編集用 clone や GitHub と自動同期する仕組みではありません。ローカル clone の変更を利用環境へ届けるには、commit・push 後に `skills update` を実行します。

Symlink方式を選んでも、共有ディレクトリを直接認識するCodexには追加のsymlinkを作らず、Claude Codeから共有ディレクトリへのsymlinkを作るのが、このCLIの動作です。

## インストール

Node.js と `npx` を利用できる環境で実行します。対象は `expand` だけ、配置範囲はユーザー全体、配布先はCodex・Claude Codeです。

```sh
npx skills add mozuq-lab/agent-skills -g -a codex claude-code --skill expand
```

インストール方式の選択では **Symlink** を選択します。確認画面でスキル名と対象エージェントを確かめて進めます。既存の同名スキルがある場合は、内容が原本に取り込まれていることを先に確認してください。

## 一覧確認

```sh
npx skills list -g -a codex claude-code
npx skills list -g -a codex claude-code --json
```

CLIの一覧とファイル・symlinkの確認は、各エージェントが実際にスキルを認識し実行したことの確認とは区別します。

## 編集と更新

ローカル clone のルートディレクトリで、以下の順に実行します。

```sh
git pull --ff-only
```

`skills/expand/` 内の必要なファイルを編集し、frontmatter、参照リンク、呼び出し設定、[テスト例](skills/expand/references/smoke-tests.md)で変更に関係する振る舞いを確認します。作業中の変更がある場合は、pullやcommitの前に差分を確認してください。

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

- Codex: `$expand 質問`。`$expand` だけなら、対象が明らかな直前の相談や回答を広げます。
- Claude Code: `/expand 質問`。本文中の `$expand` はCodexの表記で、Claude Codeでは `/expand` による明示呼び出しとして使います。

基本は呼び出された一回答に適用し、明示された個数・長さ・形式を優先します。相談への呼び出しをコード変更や外部への書き込みの許可とは扱いません。

本文は両エージェントで共有できますが、`agents/openai.yaml` の表示名と `policy.allow_implicit_invocation: false` はCodex向けの設定です。Claude Codeで同じ設定が適用されるとは扱いません。Claude Codeで設定レベルの自動呼び出し防止を行う仕組みは `disable-model-invocation: true` などであり、現在の共通本文にはそのフィールドを追加していません。Claude Codeでは本文・descriptionの明示呼び出し方針を使い、自動選択の抑止は設定レベルでは保証していない、という差があります。詳細は [Claude Codeのスキル仕様](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill) を参照してください。
