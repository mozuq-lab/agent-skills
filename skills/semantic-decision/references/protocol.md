# semantic-decision 入出力プロトコル（version "1"）

SKILL.md に書いた最小契約の厳密版。項目の上限や、入力が不正かどうかの判断に迷ったときに読む。
`scripts/validate.py` はこの文書と同じ規則を機械的に検査する。

## 1. 共通規則

- 正規入力・出力ともに UTF-8 の JSON オブジェクト 1 個。コードフェンス、前置き、結び、余分なキーは付けない。
- プロトコルのバージョン文字列は `"1"`。
- ID 規則（リクエスト ID・候補 ID・根拠 ID 共通）: 正規表現 `^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$`。一意性は同じ配列内でだけ検証する。
- 文字数は Unicode 文字数（コードポイント数）で数える。
- 入力ファイルの上限は UTF-8 で 64 KiB。超過は解析前に `invalid_request` とし、`id` は `null`。縮小しての再評価は行わない。
- JSON の重複キー、`NaN`／`Infinity`、BOM 付き、前後に文章やコードフェンスが付いた入力は正規 JSON として拒否し、`invalid_json` とする。

## 2. 入力

### 2.1 共通フィールド

| フィールド | 必須 | 規則 |
|---|---|---|
| `version` | 必須 | 文字列 `"1"` |
| `id` | 必須 | ID 規則に従う文字列 |
| `operation` | 必須 | `choose`／`boolean`／`classify`／`score` |
| `question` | 必須 | 文字列。空白のみ不可、1〜2,000 文字 |
| `evidence` | 必須 | `{ "id": string, "text": string }` の配列。0〜32 件。`id` は配列内で一意。`text` は空白のみ不可、1〜4,000 文字 |
| `constraints` | 任意 | 文字列配列。既定 `[]`。0〜16 件、各 1〜1,000 文字、空白のみ不可 |
| `explain` | 任意 | JSON boolean。既定 `false` |

`evidence: []` は形式として有効。候補名と説明だけで対応を決められる `choose` などでは空でよい。根拠が必要なのに無ければ `abstain` で表す（入力エラーではない）。

### 2.2 operation 固有フィールド

**`choose`／`classify`**: `options` 必須、`rubric` 指定不可。

- 1〜32 件の `{ "id": string, "label": string, "description"?: string }`。
- `id` は配列内で一意。`label` は重複してよく、重複は入力エラーではなく意味上の曖昧さとして評価する。
- `label` は空白のみ不可、1〜300 文字。`description` は任意、空白のみ不可、1〜2,000 文字。

**`boolean`**: `options`・`rubric` とも指定不可。

**`score`**: `rubric` 必須、`options` 指定不可。

- 2〜11 件の `{ "value": integer, "description": string }`。
- `value` は 0〜10 の整数で配列内で一意。連続である必要はない。`true`／`false`・小数は整数として受理しない。
- `description` は空白のみ不可、1〜500 文字。
- 表示順ではなく `value` で対応付ける。意味が重なって決められなければ `ambiguous`。

### 2.3 構造検証

未知のフィールド、型違い、必須項目不足、未知の operation、重複 ID、上記の範囲外は `invalid_request`。各オブジェクトは上に挙げたキーだけを許可する。

形式が有効なのに答える情報が足りない場合は `invalid_input` ではなく `abstain`。

### 2.4 自然言語からの整理

ホストは、明確に与えられた問い・候補・根拠を上記の形に整理してよい。生成してよい構造上の値は `version`、リクエスト ID、未採番候補の `C1` 等、未採番根拠の `E1` 等だけ。候補・事実・評価基準は作らない。利用者が指定した ID は保持し、省略可能項目は既定値を使う。

必須の問い・候補・rubric が無く正規入力を作れないときは `invalid_input`／`invalid_request`。部分情報が足りないだけなら `abstain`。スキルの中で追加質問を始めない。

## 3. 出力

```json
{"version":"1","id":"d-001","status":"decided","value":"signin","reason":null}
```

| フィールド | 規則 |
|---|---|
| `version` | 常に文字列 `"1"` |
| `id` | 有効な入力 ID をそのまま返す。取得できなければ `null` |
| `status` | `decided`／`abstain`／`invalid_input` |
| `value` | `decided` のとき operation ごとの値。それ以外は `null` |
| `reason` | `decided` では `null`。それ以外は下表のコード |
| `explanation` | 有効な入力で `explain: true` のときだけ任意。空白のみでない 1〜200 文字の 1 文 |

### 3.1 status と reason

| status | reason | 意味 |
|---|---|---|
| `decided` | `null` | 判定結果を返せる |
| `abstain` | `insufficient_evidence` | 情報不足 |
| `abstain` | `ambiguous` | 複数の候補・段階を区別できない |
| `abstain` | `no_match` | 適合する候補・カテゴリがない |
| `abstain` | `conflicting_evidence` | 根拠が矛盾し、優先規則がない |
| `abstain` | `constraint_conflict` | 制約同士が両立しない |
| `abstain` | `out_of_scope` | 依頼自体が調査・実装・複雑な計画を必要とする |
| `invalid_input` | `invalid_json` | 正規 JSON として解釈できない |
| `invalid_input` | `invalid_request` | JSON は読めるが入力契約違反（サイズ超過を含む） |

優先順: 構文・形式不備 → 範囲外 → 制約矛盾 → 根拠矛盾 → 情報不足 → 候補なし／曖昧 → 決定。`no_match` は候補集合を評価できるだけの根拠がある場合に使う。

### 3.2 整合規則

- 有効な入力では、出力 `id` は入力 `id` と一致し、`null` にしない。
- `choose`／`classify` の `value` は入力の `options[].id` に存在する文字列に限る。
- `boolean` の `value` は JSON の真偽値に限る。`"true"`、`0`、`1` は不可。
- `score` の `value` は入力 rubric に存在する整数に限る。同値の小数や boolean も不可。
- `abstain`／`invalid_input` の `value` は必ず `null`。
- `invalid_json` の `id` は `null`。壊れた JSON から正規表現などで ID を救出しない。
- `invalid_request` でも、JSON 上に形式が有効な `id` があればその値を返す。それ以外は `null`。サイズ超過は常に `null`。
- 形式上有効な入力へ `invalid_input` を返すのは契約違反。
- `explain: false` または入力不備では `explanation` キーを出さない。
- `explanation` は選択を支える観測事実だけを短く書き、内部の思考過程は出さない。
- `confidence`、`certainty`、`runner_up` などの追加キーは出さない。

## 4. validate.py

```bash
python3 skills/semantic-decision/scripts/validate.py request --file request.json
python3 skills/semantic-decision/scripts/validate.py result --request request.json --file response.json
```

- stdout は `{"valid": bool, "errors": [{"code","path","message"}]}` の 1 個。入力本文は出力しない。
- `code` は `invalid_json`／`invalid_request`／`invalid_result`／`io_error`。`path` は JSON Pointer、全体の問題なら空文字列。
- 終了コード: 妥当 0、契約違反 2、読み取り不可などの運用エラー 1。引数不備は usage と 2。
- `result` では、元の request が不正でも、その不正を正しく表す `invalid_input` 結果は妥当と判定する。
- `valid: true` は出力が契約に合うという意味だけで、判断の正しさ・操作の安全性・テストの成功を意味しない。
