"""評価fixture (evals/scenarios.jsonl) が契約と整合していることを確認する。"""
from __future__ import annotations

import json
import unittest

from _helpers import EVALS_DIR, dumps, load_validate_module

V = load_validate_module()
EXPECTED_IDS = [f"E{i:02d}" for i in range(1, 13)]


def load_cases():
    cases = []
    with (EVALS_DIR / "scenarios.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                cases.append(json.loads(line))
    return cases


class ScenarioFixtures(unittest.TestCase):
    def test_twelve_cases_with_required_keys(self):
        cases = load_cases()
        self.assertEqual([c["case_id"] for c in cases], EXPECTED_IDS)
        for case in cases:
            self.assertEqual(sorted(case), ["case_id", "expected", "notes", "request"])
            self.assertEqual(sorted(case["expected"]), ["reason", "status", "value"])
            self.assertTrue(case["notes"].strip())

    def test_requests_validate_as_designed(self):
        for case in load_cases():
            state = V.analyze_request_bytes(dumps(case["request"]))
            if case["case_id"] == "E11":
                self.assertEqual(state.kind, "invalid_request", case["case_id"])
            else:
                self.assertEqual(state.kind, "valid", (case["case_id"], state.errors))

    def test_expected_results_satisfy_output_contract(self):
        for case in load_cases():
            state = V.analyze_request_bytes(dumps(case["request"]))
            expected = case["expected"]
            res = {"version": "1", "id": case["request"]["id"], **expected}
            self.assertEqual(V.validate_result(res, state), [], case["case_id"])

    def test_scenarios_cover_every_status_and_reason(self):
        cases = load_cases()
        reasons = {c["expected"]["reason"] for c in cases}
        statuses = {c["expected"]["status"] for c in cases}
        self.assertEqual(statuses, {"decided", "abstain", "invalid_input"})
        for reason in ("insufficient_evidence", "ambiguous", "no_match", "conflicting_evidence", "out_of_scope", "invalid_request"):
            self.assertIn(reason, reasons)
        values = {json.dumps(c["expected"]["value"]) for c in cases}
        self.assertTrue({"true", "false", "0"} <= values)


if __name__ == "__main__":
    unittest.main()
