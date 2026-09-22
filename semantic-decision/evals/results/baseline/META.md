# baseline（スキルなし）実行メタ情報

- 実施日: 2026-09-22
- 実行方法: Claude Code セッション内の Agent ツール（general-purpose、会話履歴を継承しない分離コンテキスト）を1ケース1エージェントで起動。
- 実行モデル: セッション設定 `claude-fable-5-1`（`get_session` の `session_context.model` と `last_served_model` で確認）。サブエージェントは親のモデルを継承する設定。
- 与えた情報: 正規入力JSONと出力契約の要約のみ。SKILL.md・protocol.md・examples.md・期待結果は与えていない。
- 観測方法: 最終メッセージ1行目のJSON、2行目の `TOOLS:` 自己申告。各ファイルは1行目を保存したもの。
- 自己申告ツール使用: 4件とも `TOOLS: none`。
- 応答時間・トークン数: 未測定（ハーネスの集計値は評価対象の推論量と分離できないため記録しない）。
