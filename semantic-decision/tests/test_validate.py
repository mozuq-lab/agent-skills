"""validate.py の契約テスト。標準ライブラリ unittest のみを使う。"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from _helpers import (
    VALIDATE_PATH,
    boolean_request,
    choose_request,
    classify_request,
    clone,
    dumps,
    load_validate_module,
    result,
    score_request,
)

V = load_validate_module()


def codes(errors):
    return sorted({e["code"] for e in errors})


def paths(errors):
    return sorted({e["path"] for e in errors})


class RequestValidNormalCases(unittest.TestCase):
    def test_choose_request_is_valid(self):
        self.assertEqual(V.validate_request(choose_request()), [])

    def test_boolean_request_is_valid(self):
        self.assertEqual(V.validate_request(boolean_request()), [])

    def test_classify_request_with_explain_is_valid(self):
        self.assertEqual(V.validate_request(classify_request()), [])

    def test_score_request_is_valid(self):
        self.assertEqual(V.validate_request(score_request()), [])

    def test_empty_evidence_and_omitted_optional_fields_are_valid(self):
        req = choose_request()
        del req["constraints"]
        req["evidence"] = []
        self.assertEqual(V.validate_request(req), [])


class RequestStructureErrors(unittest.TestCase):
    def test_missing_required_fields(self):
        req = choose_request()
        del req["question"]
        errors = V.validate_request(req)
        self.assertEqual(codes(errors), ["invalid_request"])
        self.assertIn("/question", paths(errors))

    def test_unknown_top_level_and_nested_keys(self):
        req = choose_request()
        req["extra"] = 1
        req["options"][0]["weight"] = 3
        errors = V.validate_request(req)
        self.assertIn("/extra", paths(errors))
        self.assertIn("/options/0/weight", paths(errors))

    def test_unknown_operation(self):
        req = choose_request(operation="rank")
        self.assertIn("/operation", paths(V.validate_request(req)))

    def test_version_must_be_string_one(self):
        self.assertIn("/version", paths(V.validate_request(choose_request(version=1))))
        self.assertIn("/version", paths(V.validate_request(choose_request(version="2"))))

    def test_duplicate_option_evidence_and_rubric_ids(self):
        req = choose_request()
        req["options"][1]["id"] = "signin"
        self.assertIn("/options/1/id", paths(V.validate_request(req)))

        req = boolean_request(evidence=[{"id": "E1", "text": "a"}, {"id": "E1", "text": "b"}])
        self.assertIn("/evidence/1/id", paths(V.validate_request(req)))

        req = score_request()
        req["rubric"][2]["value"] = 0
        self.assertIn("/rubric/2/value", paths(V.validate_request(req)))

    def test_empty_options_and_too_short_rubric(self):
        self.assertIn("/options", paths(V.validate_request(choose_request(options=[]))))
        req = score_request(rubric=[{"value": 0, "description": "x"}])
        self.assertIn("/rubric", paths(V.validate_request(req)))

    def test_type_mismatches(self):
        self.assertIn("/explain", paths(V.validate_request(choose_request(explain="true"))))
        self.assertIn("/evidence", paths(V.validate_request(boolean_request(evidence="none"))))
        req = score_request()
        req["rubric"][0]["value"] = False
        self.assertIn("/rubric/0/value", paths(V.validate_request(req)))
        req = score_request()
        req["rubric"][0]["value"] = 0.0
        self.assertIn("/rubric/0/value", paths(V.validate_request(req)))
        req = score_request()
        req["rubric"][0]["value"] = 11
        self.assertIn("/rubric/0/value", paths(V.validate_request(req)))

    def test_operation_specific_field_presence(self):
        req = boolean_request(options=[{"id": "a", "label": "A"}])
        self.assertIn("/options", paths(V.validate_request(req)))
        req = choose_request(rubric=[{"value": 0, "description": "x"}, {"value": 1, "description": "y"}])
        self.assertIn("/rubric", paths(V.validate_request(req)))
        req = score_request()
        del req["rubric"]
        self.assertIn("/rubric", paths(V.validate_request(req)))
        req = classify_request()
        del req["options"]
        self.assertIn("/options", paths(V.validate_request(req)))

    def test_id_pattern_and_text_limits(self):
        self.assertIn("/id", paths(V.validate_request(choose_request(id="-bad"))))
        self.assertIn("/id", paths(V.validate_request(choose_request(id="a" * 65))))
        self.assertIn("/id", paths(V.validate_request(choose_request(id="日本語"))))
        self.assertIn("/question", paths(V.validate_request(choose_request(question="   "))))
        self.assertIn("/question", paths(V.validate_request(choose_request(question="あ" * 2001))))
        req = choose_request()
        req["options"][0]["label"] = "x" * 301
        self.assertIn("/options/0/label", paths(V.validate_request(req)))
        req = boolean_request(evidence=[{"id": "E1", "text": "a" * 4001}])
        self.assertIn("/evidence/0/text", paths(V.validate_request(req)))
        self.assertIn("/constraints/0", paths(V.validate_request(choose_request(constraints=[""]))))
        self.assertIn("/constraints", paths(V.validate_request(choose_request(constraints=["c"] * 17))))
        self.assertEqual(V.validate_request(choose_request(question="あ" * 2000)), [])

    def test_non_object_top_level(self):
        self.assertIn("", paths(V.validate_request([choose_request()])))
        self.assertIn("", paths(V.validate_request("text")))


class StrictJsonParsing(unittest.TestCase):
    def assert_invalid_json(self, raw: bytes):
        state = V.analyze_request_bytes(raw)
        self.assertEqual(state.kind, "invalid_json", raw[:40])
        self.assertEqual(codes(state.errors), ["invalid_json"])
        self.assertIsNone(state.id_hint)

    def test_duplicate_keys_rejected(self):
        self.assert_invalid_json(b'{"version":"1","version":"1","id":"a","operation":"boolean","question":"q","evidence":[]}')

    def test_nonstandard_numbers_rejected(self):
        self.assert_invalid_json(b'{"version":"1","id":"a","operation":"boolean","question":"q","evidence":[],"explain":NaN}')
        self.assert_invalid_json(b'{"version":"1","id":"a","operation":"boolean","question":"q","evidence":[],"explain":Infinity}')

    def test_surrounding_text_and_code_fences_rejected(self):
        body = dumps(boolean_request())
        self.assert_invalid_json(b"Here is the request:\n" + body)
        self.assert_invalid_json(body + b"\nthanks")
        self.assert_invalid_json(b"```json\n" + body + b"\n```")

    def test_broken_json_and_deep_nesting_are_controlled_errors(self):
        self.assert_invalid_json(b'{"version":"1",')
        self.assert_invalid_json(b"")
        self.assert_invalid_json(b"[" * 20000 + b"]" * 20000)  # 40 KiB、深さ超過

    def test_bom_and_invalid_utf8_rejected(self):
        self.assert_invalid_json(b"\xef\xbb\xbf" + dumps(boolean_request()))
        self.assert_invalid_json(b'{"version":"1","id":"\xff"}')

    def test_valid_bytes_yield_valid_state(self):
        state = V.analyze_request_bytes(dumps(boolean_request()))
        self.assertEqual(state.kind, "valid")
        self.assertEqual(state.errors, [])
        self.assertEqual(state.request["id"], "boolean-01")

    def test_invalid_request_state_keeps_well_formed_id_only(self):
        req = choose_request(operation="rank")
        state = V.analyze_request_bytes(dumps(req))
        self.assertEqual(state.kind, "invalid_request")
        self.assertEqual(state.id_hint, "choose-01")

        state = V.analyze_request_bytes(dumps(choose_request(id="-bad", operation="rank")))
        self.assertEqual(state.kind, "invalid_request")
        self.assertIsNone(state.id_hint)

        state = V.analyze_request_bytes(b"[1,2]")
        self.assertEqual(state.kind, "invalid_request")
        self.assertIsNone(state.id_hint)

    def test_oversize_input_is_invalid_request_without_parsing(self):
        req = boolean_request(evidence=[{"id": "E1", "text": "a" * 3000}] * 1)
        raw = dumps(req)
        padded = raw[:-1] + b', "constraints": ["' + b"x" * (V.MAX_INPUT_BYTES) + b'"]}'
        self.assertGreater(len(padded), V.MAX_INPUT_BYTES)
        state = V.analyze_request_bytes(padded)
        self.assertEqual(state.kind, "oversize")
        self.assertEqual(codes(state.errors), ["invalid_request"])
        self.assertEqual(paths(state.errors), [""])
        self.assertIsNone(state.id_hint)


def valid_state(req):
    return V.analyze_request_bytes(dumps(req))


class ResultNormalCases(unittest.TestCase):
    def test_decided_choose(self):
        self.assertEqual(V.validate_result(result("choose-01", value="signin"), valid_state(choose_request())), [])

    def test_boolean_false_is_a_valid_decision(self):
        self.assertEqual(V.validate_result(result("boolean-01", value=False), valid_state(boolean_request())), [])

    def test_score_zero_is_a_valid_decision(self):
        self.assertEqual(V.validate_result(result("score-01", value=0), valid_state(score_request())), [])

    def test_classify_with_and_without_explanation(self):
        st = valid_state(classify_request())
        self.assertEqual(V.validate_result(result("classify-01", value="auth"), st), [])
        res = result("classify-01", value="auth", explanation="ログに認証失敗と明示されている。")
        self.assertEqual(V.validate_result(res, st), [])

    def test_abstain_results_for_each_reason(self):
        st = valid_state(choose_request())
        for reason in V.ABSTAIN_REASONS:
            self.assertEqual(V.validate_result(result("choose-01", "abstain", None, reason), st), [], reason)

    def test_abstain_with_explanation_when_explain_true(self):
        st = valid_state(classify_request())
        res = result("classify-01", "abstain", None, "ambiguous", explanation="複数候補が同程度に該当する。")
        self.assertEqual(V.validate_result(res, st), [])

    def test_key_order_is_not_a_condition(self):
        res = {"reason": None, "value": "signin", "status": "decided", "id": "choose-01", "version": "1"}
        self.assertEqual(V.validate_result(res, valid_state(choose_request())), [])


class ResultCorrespondenceErrors(unittest.TestCase):
    def assert_result_error(self, res, state, path):
        errors = V.validate_result(res, state)
        self.assertEqual(codes(errors), ["invalid_result"], errors)
        self.assertIn(path, paths(errors), errors)

    def test_value_outside_option_set(self):
        self.assert_result_error(result("choose-01", value="other"), valid_state(choose_request()), "/value")
        self.assert_result_error(result("choose-01", value="サインイン"), valid_state(choose_request()), "/value")

    def test_request_id_mismatch_or_null(self):
        self.assert_result_error(result("choose-99", value="signin"), valid_state(choose_request()), "/id")
        self.assert_result_error(result(None, value="signin"), valid_state(choose_request()), "/id")

    def test_score_value_outside_rubric_or_wrong_type(self):
        st = valid_state(score_request())
        self.assert_result_error(result("score-01", value=3), st, "/value")
        self.assert_result_error(result("score-01", value=0.0), st, "/value")
        self.assert_result_error(result("score-01", value=False), st, "/value")
        self.assert_result_error(result("score-01", value="0"), st, "/value")

    def test_boolean_value_must_be_json_boolean(self):
        st = valid_state(boolean_request())
        self.assert_result_error(result("boolean-01", value="true"), st, "/value")
        self.assert_result_error(result("boolean-01", value=0), st, "/value")
        self.assert_result_error(result("boolean-01", value=1), st, "/value")
        self.assert_result_error(result("boolean-01", value=None), st, "/value")


class ResultStatusConsistency(unittest.TestCase):
    def assert_result_error(self, res, state, path):
        errors = V.validate_result(res, state)
        self.assertEqual(codes(errors), ["invalid_result"], errors)
        self.assertIn(path, paths(errors), errors)

    def test_abstain_must_not_carry_value(self):
        self.assert_result_error(result("choose-01", "abstain", "signin", "ambiguous"), valid_state(choose_request()), "/value")

    def test_decided_must_not_carry_reason(self):
        self.assert_result_error(result("choose-01", "decided", "signin", "ambiguous"), valid_state(choose_request()), "/reason")

    def test_invalid_reason_codes(self):
        st = valid_state(choose_request())
        self.assert_result_error(result("choose-01", "abstain", None, "unsure"), st, "/reason")
        self.assert_result_error(result("choose-01", "abstain", None, "invalid_json"), st, "/reason")
        self.assert_result_error(result("choose-01", "abstain", None, None), st, "/reason")
        self.assert_result_error(result("choose-01", "unknown", None, None), st, "/status")

    def test_valid_request_cannot_get_invalid_input(self):
        st = valid_state(choose_request())
        self.assert_result_error(result("choose-01", "invalid_input", None, "invalid_request"), st, "/status")

    def test_explanation_rules(self):
        st_false = valid_state(choose_request())
        self.assert_result_error(result("choose-01", value="signin", explanation="x"), st_false, "/explanation")
        st_true = valid_state(classify_request())
        self.assert_result_error(result("classify-01", value="auth", explanation="x" * 201), st_true, "/explanation")
        self.assert_result_error(result("classify-01", value="auth", explanation="   "), st_true, "/explanation")
        self.assert_result_error(result("classify-01", value="auth", explanation=5), st_true, "/explanation")

    def test_result_shape_errors(self):
        st = valid_state(choose_request())
        res = result("choose-01", value="signin")
        del res["reason"]
        self.assert_result_error(res, st, "/reason")
        self.assert_result_error(result("choose-01", value="signin", confidence=0.9), st, "/confidence")
        self.assert_result_error(result("choose-01", value="signin", version="2"), st, "/version")
        errors = V.validate_result(["not", "an", "object"], st)
        self.assertEqual(codes(errors), ["invalid_result"])
        self.assertIn("", paths(errors))


class ResultsForInvalidRequests(unittest.TestCase):
    def test_invalid_json_request_accepts_only_matching_invalid_input(self):
        st = V.analyze_request_bytes(b"{not json")
        self.assertEqual(V.validate_result(result(None, "invalid_input", None, "invalid_json"), st), [])
        self.assertTrue(V.validate_result(result("x", "invalid_input", None, "invalid_json"), st))
        self.assertTrue(V.validate_result(result(None, "invalid_input", None, "invalid_request"), st))
        self.assertTrue(V.validate_result(result(None, "decided", True, None), st))
        self.assertTrue(V.validate_result(result(None, "abstain", None, "insufficient_evidence"), st))
        self.assertTrue(V.validate_result(result(None, "invalid_input", None, "invalid_json", explanation="e"), st))

    def test_invalid_request_with_well_formed_id_must_echo_it(self):
        st = V.analyze_request_bytes(dumps(choose_request(operation="rank")))
        self.assertEqual(V.validate_result(result("choose-01", "invalid_input", None, "invalid_request"), st), [])
        self.assertTrue(V.validate_result(result(None, "invalid_input", None, "invalid_request"), st))
        self.assertTrue(V.validate_result(result("choose-01", "invalid_input", None, "invalid_json"), st))
        self.assertTrue(V.validate_result(result("choose-01", "decided", "signin", None), st))

    def test_invalid_request_without_well_formed_id_requires_null(self):
        st = V.analyze_request_bytes(dumps(choose_request(id="-bad", operation="rank")))
        self.assertEqual(V.validate_result(result(None, "invalid_input", None, "invalid_request"), st), [])
        self.assertTrue(V.validate_result(result("-bad", "invalid_input", None, "invalid_request"), st))

    def test_oversize_request_requires_null_id_and_invalid_request(self):
        raw = b'{"id":"big","version":"1","operation":"boolean","question":"q","evidence":[],"constraints":["' + b"x" * V.MAX_INPUT_BYTES + b'"]}'
        st = V.analyze_request_bytes(raw)
        self.assertEqual(st.kind, "oversize")
        self.assertEqual(V.validate_result(result(None, "invalid_input", None, "invalid_request"), st), [])
        self.assertTrue(V.validate_result(result("big", "invalid_input", None, "invalid_request"), st))
        self.assertTrue(V.validate_result(result(None, "invalid_input", None, "invalid_json"), st))


class CommandLineInterface(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data: bytes):
        p = self.dir / name
        p.write_bytes(data)
        return p

    def run_cli(self, *args):
        proc = subprocess.run(
            [sys.executable, str(VALIDATE_PATH), *args],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        return proc

    def test_request_valid_exit_0_json_stdout(self):
        req = self.write("request.json", dumps(choose_request()))
        before = req.read_bytes()
        proc = self.run_cli("request", "--file", str(req))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), {"valid": True, "errors": []})
        self.assertEqual(req.read_bytes(), before)
        self.assertEqual(sorted(os.listdir(self.dir)), ["request.json"])

    def test_request_contract_violation_exit_2(self):
        secret = "SENTINEL-DO-NOT-ECHO-4471"
        req = self.write("request.json", dumps(choose_request(operation="rank", question=secret)))
        proc = self.run_cli("request", "--file", str(req))
        self.assertEqual(proc.returncode, 2)
        report = json.loads(proc.stdout)
        self.assertFalse(report["valid"])
        self.assertTrue(report["errors"])
        for err in report["errors"]:
            self.assertEqual(sorted(err), ["code", "message", "path"])
        self.assertNotIn(secret, proc.stdout)
        self.assertNotIn(secret, proc.stderr)

    def test_request_invalid_json_exit_2(self):
        req = self.write("request.json", b"```json\n{}\n```")
        proc = self.run_cli("request", "--file", str(req))
        self.assertEqual(proc.returncode, 2)
        self.assertEqual({e["code"] for e in json.loads(proc.stdout)["errors"]}, {"invalid_json"})

    def test_missing_file_exit_1_io_error(self):
        proc = self.run_cli("request", "--file", str(self.dir / "missing.json"))
        self.assertEqual(proc.returncode, 1)
        report = json.loads(proc.stdout)
        self.assertFalse(report["valid"])
        self.assertEqual({e["code"] for e in report["errors"]}, {"io_error"})

    def test_result_subcommand_valid_and_mismatch(self):
        req = self.write("request.json", dumps(choose_request()))
        ok = self.write("ok.json", dumps(result("choose-01", value="signin")))
        bad = self.write("bad.json", dumps(result("choose-01", value="nope")))
        proc = self.run_cli("result", "--request", str(req), "--file", str(ok))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(json.loads(proc.stdout), {"valid": True, "errors": []})
        proc = self.run_cli("result", "--request", str(req), "--file", str(bad))
        self.assertEqual(proc.returncode, 2)
        self.assertEqual({e["code"] for e in json.loads(proc.stdout)["errors"]}, {"invalid_result"})
        self.assertEqual(sorted(os.listdir(self.dir)), ["bad.json", "ok.json", "request.json"])

    def test_result_subcommand_accepts_invalid_input_for_broken_request(self):
        req = self.write("request.json", b"{broken")
        res = self.write("result.json", dumps(result(None, "invalid_input", None, "invalid_json")))
        proc = self.run_cli("result", "--request", str(req), "--file", str(res))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        wrong = self.write("wrong.json", dumps(result(None, "abstain", None, "insufficient_evidence")))
        proc = self.run_cli("result", "--request", str(req), "--file", str(wrong))
        self.assertEqual(proc.returncode, 2)

    def test_result_file_not_json_exit_2(self):
        req = self.write("request.json", dumps(choose_request()))
        res = self.write("result.json", b"decided: signin")
        proc = self.run_cli("result", "--request", str(req), "--file", str(res))
        self.assertEqual(proc.returncode, 2)
        self.assertEqual({e["code"] for e in json.loads(proc.stdout)["errors"]}, {"invalid_json"})

    def test_result_oversize_file_is_contract_violation(self):
        req = self.write("request.json", dumps(choose_request()))
        big = dumps(result("choose-01", value="signin", explanation="x"))[:-2] + b" " * (V.MAX_INPUT_BYTES + 10) + b'"}'
        res = self.write("result.json", big)
        proc = self.run_cli("result", "--request", str(req), "--file", str(res))
        self.assertEqual(proc.returncode, 2)
        self.assertEqual({e["code"] for e in json.loads(proc.stdout)["errors"]}, {"invalid_result"})

    def test_usage_errors_and_help(self):
        proc = self.run_cli()
        self.assertEqual(proc.returncode, 2)
        proc = self.run_cli("request")
        self.assertEqual(proc.returncode, 2)
        proc = self.run_cli("--help")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("request", proc.stdout)


if __name__ == "__main__":
    unittest.main()
