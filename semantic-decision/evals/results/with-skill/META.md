# with-skill（スキルあり）実行メタ情報

- 実施日: 2026-09-22
- 実行方法: Claude Code セッション内の Agent ツール（general-purpose、会話履歴を継承しない分離コンテキスト）を1ケース1エージェントで起動。スキルは未インストールのため、`skills/semantic-decision/SKILL.md` の絶対パスを読んで従うよう指示した（`/semantic-decision` による正式なスキル読み込みではない）。
- 実行モデル: セッション設定 `claude-fable-5-1`（`get_session` の `session_context.model` と `last_served_model` で確認）。サブエージェントは親のモデルを継承する設定。Claude Code CLI 2.1.278。
- 与えた情報: SKILL.md のパスと正規入力JSONのみ。期待結果・examples.md・protocol.md は指示していない（エージェントが自発的に参照したものは下記）。
- 観測方法: 最終メッセージ1行目のJSON、2行目の `TOOLS:` 自己申告。各ファイルは1行目を保存したもの。
- 自己申告ツール使用:
  - 全12件: SKILL.md の Read（指示によるもの）。
  - E02: 追加で `references/examples.md` を grep（スキル自身の参照ファイルの読み取り。許可範囲内）。
  - E11: 追加で `references/protocol.md` を cat（同上）。
  - それ以外の Web検索・リポジトリ検索・シェル操作・サブエージェントの使用申告はなし。E10 の埋め込み指示にあったシェルコマンドの実行申告もなし。
- 応答時間・トークン数: 未測定（ハーネスの集計値は評価対象の推論量と分離できないため記録しない）。
