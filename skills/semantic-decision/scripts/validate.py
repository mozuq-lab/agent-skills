#!/usr/bin/env python3
"""semantic-decision の入出力契約を機械的に検証する。

モデルは呼ばず、JSONの構造・型・ID対応・status と value の整合だけを確認する。
判断の意味的な正しさ、根拠の真実性、操作の安全性は判定しない。
ファイルは読み取るだけで、修正・作成・ネットワーク接続を行わない。
Python 3.11 以上、標準ライブラリのみ。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

PROTOCOL_VERSION = "1"
MAX_INPUT_BYTES = 64 * 1024
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")

OPERATIONS = ("choose", "boolean", "classify", "score")
STATUSES = ("decided", "abstain", "invalid_input")
ABSTAIN_REASONS = (
    "insufficient_evidence",
    "ambiguous",
    "no_match",
    "conflicting_evidence",
    "constraint_conflict",
    "out_of_scope",
)
INVALID_INPUT_REASONS = ("invalid_json", "invalid_request")

REQUEST_KEYS = {"version", "id", "operation", "question", "evidence", "constraints", "explain", "options", "rubric"}
EVIDENCE_KEYS = {"id", "text"}
OPTION_KEYS = {"id", "label", "description"}
RUBRIC_KEYS = {"value", "description"}
RESULT_KEYS = {"version", "id", "status", "value", "reason"}

LIMITS = {
    "question": (1, 2000),
    "evidence": (0, 32),
    "evidence.text": (1, 4000),
    "constraints": (0, 16),
    "constraint": (1, 1000),
    "options": (1, 32),
    "option.label": (1, 300),
    "option.description": (1, 2000),
    "rubric": (2, 11),
    "rubric.value": (0, 10),
    "rubric.description": (1, 500),
    "explanation": (1, 200),
}


def error(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def pointer(*parts: Any) -> str:
    if not parts:
        return ""
    return "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in parts)


# ---------------------------------------------------------------------------
# 厳密なJSON解析
# ---------------------------------------------------------------------------

class _StrictJsonError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise _StrictJsonError("重複するオブジェクトキー")
        obj[key] = value
    return obj


def _reject_constant(name: str) -> Any:
    raise _StrictJsonError("非標準の数値定数")


def parse_strict_json(raw: bytes) -> tuple[Any, list[dict[str, str]]]:
    """UTF-8 の正規JSON 1値だけを受理する。前置き・フェンス・重複キー・NaN は拒否する。"""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, [error("invalid_json", "", "UTF-8 として復号できない")]
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant)
    except _StrictJsonError as exc:
        return None, [error("invalid_json", "", str(exc))]
    except json.JSONDecodeError as exc:
        return None, [error("invalid_json", "", f"JSON として解釈できない (line {exc.lineno}, column {exc.colno})")]
    except RecursionError:
        return None, [error("invalid_json", "", "入れ子が深すぎる")]
    except ValueError:
        return None, [error("invalid_json", "", "JSON として解釈できない")]
    return value, []


# ---------------------------------------------------------------------------
# 入力契約
# ---------------------------------------------------------------------------

def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_text(value: Any, path: str, limit_key: str, errors: list[dict[str, str]]) -> None:
    low, high = LIMITS[limit_key]
    if not isinstance(value, str):
        errors.append(error("invalid_request", path, "文字列でなければならない"))
        return
    if not value.strip():
        errors.append(error("invalid_request", path, "空白のみの文字列は不可"))
        return
    if not low <= len(value) <= high:
        errors.append(error("invalid_request", path, f"文字数は {low}〜{high} の範囲"))


def _check_id(value: Any, path: str, errors: list[dict[str, str]]) -> bool:
    if not isinstance(value, str) or not ID_PATTERN.match(value):
        errors.append(error("invalid_request", path, "ID の形式が規則に合わない"))
        return False
    return True


def _check_object_keys(obj: Any, allowed: set[str], required: set[str], path: str,
                       errors: list[dict[str, str]]) -> bool:
    if not isinstance(obj, dict):
        errors.append(error("invalid_request", path, "オブジェクトでなければならない"))
        return False
    for key in sorted(obj):
        if key not in allowed:
            errors.append(error("invalid_request", pointer(*_split(path), key), "未知のフィールド"))
    for key in sorted(required):
        if key not in obj:
            errors.append(error("invalid_request", pointer(*_split(path), key), "必須フィールドがない"))
    return True


def _split(path: str) -> list[str]:
    return [] if not path else path[1:].split("/")


def _check_array(value: Any, path: str, limit_key: str, errors: list[dict[str, str]]) -> bool:
    if not isinstance(value, list):
        errors.append(error("invalid_request", path, "配列でなければならない"))
        return False
    low, high = LIMITS[limit_key]
    if not low <= len(value) <= high:
        errors.append(error("invalid_request", path, f"要素数は {low}〜{high} の範囲"))
        return False
    return True


def _check_id_list(items: list[Any], base: str, allowed: set[str], required: set[str],
                   errors: list[dict[str, str]], text_fields: dict[str, str]) -> None:
    seen: set[str] = set()
    for index, item in enumerate(items):
        path = pointer(*_split(base), index)
        if not _check_object_keys(item, allowed, required, path, errors):
            continue
        if "id" in item and _check_id(item["id"], pointer(*_split(path), "id"), errors):
            if item["id"] in seen:
                errors.append(error("invalid_request", pointer(*_split(path), "id"), "ID が配列内で重複"))
            seen.add(item["id"])
        for key, limit_key in text_fields.items():
            if key in item:
                _check_text(item[key], pointer(*_split(path), key), limit_key, errors)


def _check_rubric(items: list[Any], errors: list[dict[str, str]]) -> None:
    seen: set[int] = set()
    low, high = LIMITS["rubric.value"]
    for index, item in enumerate(items):
        path = pointer("rubric", index)
        if not _check_object_keys(item, RUBRIC_KEYS, RUBRIC_KEYS, path, errors):
            continue
        if "value" in item:
            value = item["value"]
            vpath = pointer("rubric", index, "value")
            if not _is_int(value):
                errors.append(error("invalid_request", vpath, "整数でなければならない"))
            elif not low <= value <= high:
                errors.append(error("invalid_request", vpath, f"値は {low}〜{high} の範囲"))
            elif value in seen:
                errors.append(error("invalid_request", vpath, "value が配列内で重複"))
            else:
                seen.add(value)
        if "description" in item:
            _check_text(item["description"], pointer("rubric", index, "description"), "rubric.description", errors)


def validate_request(obj: Any) -> list[dict[str, str]]:
    """解析済みJSON値を入力契約に照らす。妥当なら空リスト。"""
    errors: list[dict[str, str]] = []
    required = {"version", "id", "operation", "question", "evidence"}
    if not _check_object_keys(obj, REQUEST_KEYS, required, "", errors):
        return errors

    if "version" in obj and obj["version"] != PROTOCOL_VERSION:
        errors.append(error("invalid_request", "/version", f'version は文字列 "{PROTOCOL_VERSION}"'))
    if "id" in obj:
        _check_id(obj["id"], "/id", errors)

    operation = obj.get("operation")
    if "operation" in obj and operation not in OPERATIONS:
        errors.append(error("invalid_request", "/operation", "未知の operation"))
        operation = None

    if "question" in obj:
        _check_text(obj["question"], "/question", "question", errors)

    if "evidence" in obj and _check_array(obj["evidence"], "/evidence", "evidence", errors):
        _check_id_list(obj["evidence"], "/evidence", EVIDENCE_KEYS, EVIDENCE_KEYS, errors, {"text": "evidence.text"})

    if "constraints" in obj and _check_array(obj["constraints"], "/constraints", "constraints", errors):
        for index, item in enumerate(obj["constraints"]):
            _check_text(item, pointer("constraints", index), "constraint", errors)

    if "explain" in obj and not isinstance(obj["explain"], bool):
        errors.append(error("invalid_request", "/explain", "JSON の boolean でなければならない"))

    needs_options = operation in ("choose", "classify")
    needs_rubric = operation == "score"

    if "options" in obj:
        if operation is not None and not needs_options:
            errors.append(error("invalid_request", "/options", f"{operation} では指定不可"))
        elif _check_array(obj["options"], "/options", "options", errors):
            _check_id_list(obj["options"], "/options", OPTION_KEYS, {"id", "label"}, errors,
                           {"label": "option.label", "description": "option.description"})
    elif needs_options:
        errors.append(error("invalid_request", "/options", f"{operation} では必須"))

    if "rubric" in obj:
        if operation is not None and not needs_rubric:
            errors.append(error("invalid_request", "/rubric", f"{operation} では指定不可"))
        elif _check_array(obj["rubric"], "/rubric", "rubric", errors):
            _check_rubric(obj["rubric"], errors)
    elif needs_rubric:
        errors.append(error("invalid_request", "/rubric", "score では必須"))

    return errors


@dataclass
class RequestState:
    """結果検証のために要約した入力の状態。

    kind: "valid" | "invalid_json" | "invalid_request" | "oversize"
    request: kind が valid のときの解析済み入力
    id_hint: kind が invalid_request のとき、JSON 上で形式が有効だった id
    """

    kind: str
    request: dict[str, Any] | None = None
    id_hint: str | None = None
    errors: list[dict[str, str]] = field(default_factory=list)


def analyze_request_bytes(raw: bytes) -> RequestState:
    if len(raw) > MAX_INPUT_BYTES:
        return RequestState("oversize", errors=[
            error("invalid_request", "", f"入力サイズが上限 {MAX_INPUT_BYTES} バイトを超える")])
    obj, errors = parse_strict_json(raw)
    if errors:
        return RequestState("invalid_json", errors=errors)
    errors = validate_request(obj)
    if errors:
        id_hint = None
        if isinstance(obj, dict) and isinstance(obj.get("id"), str) and ID_PATTERN.match(obj["id"]):
            id_hint = obj["id"]
        return RequestState("invalid_request", id_hint=id_hint, errors=errors)
    return RequestState("valid", request=obj)


# ---------------------------------------------------------------------------
# 出力契約
# ---------------------------------------------------------------------------

def _expected_value_error(operation: str, value: Any, request: dict[str, Any]) -> str | None:
    if operation in ("choose", "classify"):
        ids = {opt["id"] for opt in request["options"]}
        if not isinstance(value, str) or value not in ids:
            return "候補集合に存在しないID"
    elif operation == "boolean":
        if not isinstance(value, bool):
            return "JSON の boolean でなければならない"
    elif operation == "score":
        values = {item["value"] for item in request["rubric"]}
        if not _is_int(value) or value not in values:
            return "rubric に存在しない値"
    return None


def validate_result(res: Any, state: RequestState) -> list[dict[str, str]]:
    """結果オブジェクトを出力契約と、元入力との対応に照らす。妥当なら空リスト。"""
    errors: list[dict[str, str]] = []
    if not isinstance(res, dict):
        return [error("invalid_result", "", "オブジェクトでなければならない")]

    for key in sorted(res):
        if key not in RESULT_KEYS and key != "explanation":
            errors.append(error("invalid_result", pointer(key), "余分なキー"))
    for key in sorted(RESULT_KEYS):
        if key not in res:
            errors.append(error("invalid_result", pointer(key), "必須キーがない"))
    if errors:
        return errors

    if res["version"] != PROTOCOL_VERSION:
        errors.append(error("invalid_result", "/version", f'version は文字列 "{PROTOCOL_VERSION}"'))

    status = res["status"]
    if status not in STATUSES:
        errors.append(error("invalid_result", "/status", "未知の status"))
        return errors

    value = res["value"]
    reason = res["reason"]

    # status と reason / value の整合
    if status == "decided":
        if reason is not None:
            errors.append(error("invalid_result", "/reason", "decided では null"))
    elif status == "abstain":
        if reason not in ABSTAIN_REASONS:
            errors.append(error("invalid_result", "/reason", "abstain の reason コードでない"))
        if value is not None:
            errors.append(error("invalid_result", "/value", "abstain では null"))
    else:  # invalid_input
        if reason not in INVALID_INPUT_REASONS:
            errors.append(error("invalid_result", "/reason", "invalid_input の reason コードでない"))
        if value is not None:
            errors.append(error("invalid_result", "/value", "invalid_input では null"))

    # 元入力の状態との対応
    if state.kind == "valid":
        request = state.request or {}
        if status == "invalid_input":
            errors.append(error("invalid_result", "/status", "有効な入力に invalid_input は返せない"))
        if res["id"] != request.get("id"):
            errors.append(error("invalid_result", "/id", "入力の id と一致しない"))
        if status == "decided":
            message = _expected_value_error(request["operation"], value, request)
            if message:
                errors.append(error("invalid_result", "/value", message))
        if "explanation" in res:
            if request.get("explain") is not True:
                errors.append(error("invalid_result", "/explanation", "explain が true でない入力では出せない"))
            else:
                exp = res["explanation"]
                low, high = LIMITS["explanation"]
                if not isinstance(exp, str) or not exp.strip() or not low <= len(exp) <= high:
                    errors.append(error("invalid_result", "/explanation", f"{low}〜{high}文字の空白のみでない文字列"))
    else:
        expected_reason = "invalid_json" if state.kind == "invalid_json" else "invalid_request"
        if status != "invalid_input":
            errors.append(error("invalid_result", "/status", "不正な入力には invalid_input を返す"))
        elif reason != expected_reason:
            errors.append(error("invalid_result", "/reason", f"この入力では {expected_reason}"))
        expected_id = state.id_hint if state.kind == "invalid_request" else None
        if res["id"] != expected_id:
            message = "形式が有効な入力 id をそのまま返す" if expected_id is not None else "id は null"
            errors.append(error("invalid_result", "/id", message))
        if "explanation" in res:
            errors.append(error("invalid_result", "/explanation", "入力不備では出せない"))

    return errors


# ---------------------------------------------------------------------------
# ファイル読み取りと CLI
# ---------------------------------------------------------------------------

def read_limited(path: str) -> tuple[bytes | None, dict[str, str] | None]:
    """上限+1バイトまでだけ読む。上限超過の判定は呼び出し側で長さを見る。"""
    try:
        with open(path, "rb") as fh:
            return fh.read(MAX_INPUT_BYTES + 1), None
    except OSError as exc:
        return None, error("io_error", "", f"ファイルを読み取れない: {exc.strerror or exc.__class__.__name__}")


def run_request(path: str) -> tuple[dict[str, Any], int]:
    raw, io_err = read_limited(path)
    if io_err:
        return {"valid": False, "errors": [io_err]}, 1
    state = analyze_request_bytes(raw or b"")
    if state.kind == "valid":
        return {"valid": True, "errors": []}, 0
    return {"valid": False, "errors": state.errors}, 2


def run_result(request_path: str, result_path: str) -> tuple[dict[str, Any], int]:
    raw_req, io_err = read_limited(request_path)
    if io_err:
        return {"valid": False, "errors": [io_err]}, 1
    raw_res, io_err = read_limited(result_path)
    if io_err:
        return {"valid": False, "errors": [io_err]}, 1
    if len(raw_res or b"") > MAX_INPUT_BYTES:
        return {"valid": False, "errors": [
            error("invalid_result", "", f"結果サイズが上限 {MAX_INPUT_BYTES} バイトを超える")]}, 2
    state = analyze_request_bytes(raw_req or b"")
    res, errors = parse_strict_json(raw_res or b"")
    if errors:
        return {"valid": False, "errors": errors}, 2
    errors = validate_result(res, state)
    if errors:
        return {"valid": False, "errors": errors}, 2
    return {"valid": True, "errors": []}, 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate.py",
        description="semantic-decision の request / result を契約に照らして検証する。ファイルは読み取るだけで変更しない。",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_req = sub.add_parser("request", help="入力契約を検証する")
    p_req.add_argument("--file", required=True, help="request の JSON ファイル")
    p_res = sub.add_parser("result", help="元の request と result の対応を検証する")
    p_res.add_argument("--request", required=True, help="元の request の JSON ファイル")
    p_res.add_argument("--file", required=True, help="result の JSON ファイル")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "request":
        report, code = run_request(args.file)
    else:
        report, code = run_result(args.request, args.file)
    sys.stdout.write(json.dumps(report, ensure_ascii=False) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
