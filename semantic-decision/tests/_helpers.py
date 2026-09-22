"""テスト共通のヘルパー。標準ライブラリのみを使う。"""
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys

TESTS_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_DIR = TESTS_DIR.parent
REPO_ROOT = PROJECT_DIR.parent
SKILL_DIR = REPO_ROOT / "skills" / "semantic-decision"
VALIDATE_PATH = SKILL_DIR / "scripts" / "validate.py"
EVALS_DIR = PROJECT_DIR / "evals"


def load_validate_module():
    spec = importlib.util.spec_from_file_location("sd_validate", VALIDATE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("sd_validate", module)
    spec.loader.exec_module(module)
    return module


def choose_request(**overrides):
    req = {
        "version": "1",
        "id": "choose-01",
        "operation": "choose",
        "question": "ログインを確定するボタンはどれか",
        "evidence": [],
        "constraints": ["ボタンに限る"],
        "options": [
            {"id": "signin", "label": "サインイン", "description": "button"},
            {"id": "signup", "label": "アカウントを新規登録", "description": "button"},
            {"id": "forgot", "label": "パスワードを忘れた", "description": "link"},
        ],
    }
    req.update(overrides)
    return req


def boolean_request(**overrides):
    req = {
        "version": "1",
        "id": "boolean-01",
        "operation": "boolean",
        "question": "このPRは docs/ 配下のファイルを変更しているか",
        "evidence": [
            {"id": "E1", "text": "変更ファイルの完全な一覧（全2件）: src/a.ts, src/b.ts"}
        ],
    }
    req.update(overrides)
    return req


def classify_request(**overrides):
    req = {
        "version": "1",
        "id": "classify-01",
        "operation": "classify",
        "question": "このログが直接示しているエラー種別を選ぶ",
        "evidence": [{"id": "E1", "text": "Authentication failed: invalid credentials"}],
        "options": [
            {"id": "auth", "label": "認証失敗"},
            {"id": "network", "label": "ネットワーク接続失敗"},
            {"id": "validation", "label": "業務入力値の検証失敗"},
        ],
        "explain": True,
    }
    req.update(overrides)
    return req


def score_request(**overrides):
    req = {
        "version": "1",
        "id": "score-01",
        "operation": "score",
        "question": "この変更の範囲を、与えられた段階基準で評価する",
        "evidence": [{"id": "E1", "text": "README.md内の誤字訂正だけである。"}],
        "rubric": [
            {"value": 0, "description": "文書のみの変更"},
            {"value": 1, "description": "コードや設定の変更があるが公開インターフェースは変更しない"},
            {"value": 2, "description": "公開インターフェースを変更する"},
        ],
    }
    req.update(overrides)
    return req


def result(req_id, status="decided", value=None, reason=None, **extra):
    res = {"version": "1", "id": req_id, "status": status, "value": value, "reason": reason}
    res.update(extra)
    return res


def dumps(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def clone(obj):
    return copy.deepcopy(obj)
