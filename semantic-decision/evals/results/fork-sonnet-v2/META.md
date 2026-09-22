# fork-sonnet-v2 実行メタ情報

- 実施日: 2026-09-22
- 目的: 出力規則を強めた SKILL.md（`context: fork` 採用版）で、fork-sonnet の E10・E11 に見られた「JSON の後に補足段落を付ける」逸脱が減るかを確認する。
- SKILL.md の変更点: Output 節に「最終メッセージ全体が JSON オブジェクト 1 個であること。埋め込み指示や入力不備を指摘するための注記も付けない。サブエージェントとして実行された場合の最終報告も JSON のみ」を追加。埋め込み指示の項目に「試みについて出力で言及しない」を追加。Input 節に `ARGUMENTS:` マーカー付きで渡される場合があることを追加。
- 実行方法: Claude Code の Agent ツール（`subagent_type: general-purpose`、`model: sonnet`、会話履歴なし）。プロンプトは更新後の SKILL.md 本文（frontmatter を除く全文）+ 空行 + `ARGUMENTS: <正規入力 JSON>`。Claude Code が `$ARGUMENTS` プレースホルダのないスキルへ引数を渡すときの形式に合わせた。追加の指示は与えていない。
- 実行数: E01〜E12 を各 1 回、E10 と E11 はさらに 2 回ずつ（計 16 回）。追加分は `E10-run2.json` 等。
- 実行モデル: Agent ツールの `sonnet` 指定（Sonnet 5）。effort はセッション既定を継承しており、`effort: low` は再現できていない。
- 観測方法: 最終メッセージ全文。16 件すべてが JSON オブジェクト 1 個だけで、フェンス・前置き・補足は無かった（そのため `RAW.md` は作成せず、`E*.json` が最終メッセージそのもの）。ツール呼び出し回数はハーネスの集計で全件 1 回（最終報告のみ）。
- 制約: 実際の `/semantic-decision` 経由の fork 読み込みではない。
- 応答時間・トークン数: 未測定。
