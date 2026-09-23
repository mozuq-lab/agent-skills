"""Codex 別セッション runner の外部境界を、モデルを呼ばずに検査する。"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from _helpers import SKILL_DIR


RUNNER = SKILL_DIR / "scripts" / "run_codex.py"
REQUEST = {
    "version": "1", "id": "runner-01", "operation": "choose",
    "question": "カフェインを避ける飲み物はどれか。",
    "evidence": [{"id": "E1", "text": "麦茶はカフェインなし。コーヒーはカフェインあり。"}],
    "constraints": ["カフェインを含まないこと"],
    "options": [{"id": "mugicha", "label": "麦茶"}, {"id": "coffee", "label": "コーヒー"}],
}
RESULT = {"version": "1", "id": "runner-01", "status": "decided", "value": "mugicha", "reason": None}
FAKE_CODEX = '''#!/usr/bin/env python3
import json, os, pathlib, sys
argv = sys.argv[1:]
workdir = pathlib.Path(argv[argv.index("-C") + 1])
payload = sys.stdin.read()
pathlib.Path(os.environ["FAKE_CODEX_LOG"]).write_text(json.dumps({
    "argv": argv,
    "prompt": payload,
    "git": (workdir / ".git").is_dir(),
    "skill": (workdir / ".agents/skills/semantic-decision/SKILL.md").is_file(),
    "workdir": str(workdir),
    "worker_env": os.environ.get("SEMANTIC_DECISION_WORKER"),
}), encoding="utf-8")
mode = os.environ["FAKE_CODEX_MODE"]
if mode == "failure":
    print("Error: model gpt-6-luna unavailable", file=sys.stderr)
    sys.exit(7)
if mode == "malformed":
    print("not JSON")
elif mode == "wrong_value":
    print(json.dumps({"version":"1","id":"runner-01","status":"decided","value":"tea","reason":None}))
else:
    print(json.dumps({"version":"1","id":"runner-01","status":"decided","value":"mugicha","reason":None}))
'''


class CodexRunner(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.request = self.root / "request.json"
        self.request.write_text(json.dumps(REQUEST, ensure_ascii=False), encoding="utf-8")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        fake = self.bin / "codex"
        fake.write_text(FAKE_CODEX, encoding="utf-8")
        fake.chmod(0o755)
        self.log = self.root / "invocation.json"

    def run_runner(self, mode="success", *, worker=False):
        env = os.environ.copy()
        env.update({
            "PATH": f"{self.bin}{os.pathsep}{env.get('PATH', '')}",
            "FAKE_CODEX_LOG": str(self.log),
            "FAKE_CODEX_MODE": mode,
        })
        if worker:
            env["SEMANTIC_DECISION_WORKER"] = "1"
        return subprocess.run(
            [sys.executable, str(RUNNER), str(self.request)],
            text=True, capture_output=True, env=env, check=False,
        )

    def test_launches_isolated_luna_low_worker_and_returns_valid_result(self):
        result = self.run_runner()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), RESULT)
        invocation = json.loads(self.log.read_text(encoding="utf-8"))
        self.assertEqual(invocation["argv"][:2], ["exec", "-C"])
        self.assertIn("--ephemeral", invocation["argv"])
        self.assertEqual(invocation["argv"][invocation["argv"].index("--sandbox") + 1], "read-only")
        self.assertEqual(invocation["argv"][invocation["argv"].index("--model") + 1], "gpt-6-luna")
        self.assertIn('model_reasoning_effort="low"', invocation["argv"])
        self.assertEqual(invocation["argv"][invocation["argv"].index("--disable") + 1], "multi_agent")
        self.assertEqual(invocation["worker_env"], "1")
        self.assertTrue(invocation["git"])
        self.assertTrue(invocation["skill"])
        self.assertTrue(invocation["prompt"].startswith("$semantic-decision\nSEMANTIC_DECISION_WORKER_V1\n"))
        self.assertIn('"id": "runner-01"', invocation["prompt"])
        self.assertFalse(pathlib.Path(invocation["workdir"]).exists())

    def test_cli_failure_never_returns_a_decision(self):
        result = self.run_runner("failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("codex exec", result.stderr)
        self.assertIn("model gpt-6-luna unavailable", result.stderr)

    def test_malformed_worker_output_never_returns_a_decision(self):
        result = self.run_runner("malformed")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("worker output", result.stderr)

    def test_result_outside_candidate_set_never_returns_a_decision(self):
        result = self.run_runner("wrong_value")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("result contract", result.stderr)

    def test_worker_cannot_launch_another_worker(self):
        result = self.run_runner(worker=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.log.exists())

    def test_invalid_canonical_request_does_not_launch_worker(self):
        self.request.write_text('{"version":"1"}', encoding="utf-8")
        result = self.run_runner()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("request contract", result.stderr)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
