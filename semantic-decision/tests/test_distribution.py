"""配布物の静的検査。固定形式の frontmatter だけを扱い、汎用YAMLパーサーは作らない。"""
from __future__ import annotations

import ast
import re
import sys
import unittest

from _helpers import EVALS_DIR, PROJECT_DIR, REPO_ROOT, SKILL_DIR

SKILL_MD = SKILL_DIR / "SKILL.md"
# name / description は Agent Skills 共通。残りは Claude Code 向けの実行設定で、Codex 側の
# フィールド解釈には依存しない。値を変えるときは README と評価レポートも更新する。
EXPECTED_FRONTMATTER = {
    "name": "semantic-decision",
    "description": None,
    "context": "fork",
    "agent": "general-purpose",
    "model": "claude-sonnet-5",
    "effort": "low",
    "background": "false",
}
STDLIB = set(sys.stdlib_module_names)


def read(path):
    return path.read_text(encoding="utf-8")


def parse_frontmatter(text):
    lines = text.split("\n")
    assert lines[0] == "---", "frontmatter は1行目の --- で始まる"
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        assert sep, f"frontmatter の行が key: value 形式でない: {line!r}"
        fields[key.strip()] = value.strip().strip('"')
    return fields, "\n".join(lines[end + 1:])


class RequiredFiles(unittest.TestCase):
    def test_skill_files_exist(self):
        for rel in ("SKILL.md", "references/protocol.md", "references/examples.md",
                    "scripts/validate.py", "agents/openai.yaml"):
            self.assertTrue((SKILL_DIR / rel).is_file(), rel)

    def test_project_files_exist(self):
        for path in (PROJECT_DIR / "README.md", EVALS_DIR / "scenarios.jsonl",
                     EVALS_DIR / "README.md", EVALS_DIR / "REPORT.md"):
            self.assertTrue(path.is_file(), path)

    def test_no_tests_or_evals_inside_skill_directory(self):
        names = {p.name for p in SKILL_DIR.iterdir()}
        self.assertEqual(names, {"SKILL.md", "references", "scripts", "agents"})


class SkillFrontmatter(unittest.TestCase):
    def test_frontmatter_fields(self):
        fields, _ = parse_frontmatter(read(SKILL_MD))
        self.assertEqual(sorted(fields), sorted(EXPECTED_FRONTMATTER))
        for key, value in EXPECTED_FRONTMATTER.items():
            if value is not None:
                self.assertEqual(fields[key], value, key)
        self.assertGreater(len(fields["description"]), 40)
        self.assertIn("Not for", fields["description"])

    def test_line_limit(self):
        count = read(SKILL_MD).count("\n")
        self.assertLessEqual(count, 200)

    def test_body_mentions_core_rules(self):
        _, body = parse_frontmatter(read(SKILL_MD))
        for needle in ("choose", "boolean", "classify", "score", "abstain",
                       "Japanese", "references/protocol.md", "references/examples.md"):
            self.assertIn(needle, body, needle)

    def test_no_permission_fields_hooks_or_variable_expansion(self):
        text = read(SKILL_MD)
        for forbidden in ("allowed-tools:", "disallowed-tools:", "disable-model-invocation:",
                          "hooks:", "$ARGUMENTS", "$0", "${CLAUDE", "!`"):
            self.assertNotIn(forbidden, text, forbidden)


class RelativeReferences(unittest.TestCase):
    def test_relative_paths_in_skill_and_references_resolve(self):
        pattern = re.compile(r"(?<![\w/])((?:references|scripts)/[\w.\-]+)")
        for md in (SKILL_MD, SKILL_DIR / "references" / "protocol.md",
                   SKILL_DIR / "references" / "examples.md"):
            for rel in set(pattern.findall(read(md))):
                self.assertTrue((SKILL_DIR / rel).is_file(), f"{md.name} -> {rel}")

    def test_codex_yaml_has_display_fields(self):
        text = read(SKILL_DIR / "agents" / "openai.yaml")
        self.assertIn("display_name:", text)
        self.assertIn("short_description:", text)


class DocumentationClaims(unittest.TestCase):
    def test_codex_runtime_claims_match_the_observed_smoke_test(self):
        root_readme = read(REPO_ROOT / "README.md")
        project_readme = read(PROJECT_DIR / "README.md")
        report = read(EVALS_DIR / "REPORT.md")
        combined = "\n".join((root_readme, project_readme, report))

        for stale_claim in (
            "Codex はこれらのフィールドを無視",
            "Codexは frontmatter のこのフィールドを解釈せず無視",
            "Codex にはスキル単位でモデルや reasoning effort を指定する仕組みがなく",
            "frontmatter に `name`／`description` だけを持ち",
            "Codex がこのスキルを一覧に表示し `$semantic-decision` で呼び出せることは未確認",
        ):
            self.assertNotIn(stale_claim, combined, stale_claim)

        self.assertIn("codex-cli 0.155.1", project_readme)
        self.assertIn("quick_validate.py", project_readme)
        self.assertIn("codex-cli 0.155.1", report)
        self.assertIn('"id":"smoke-01"', report)
        self.assertIn('"value":"mugicha"', report)
        self.assertIn("一覧表示", report)


class PythonSources(unittest.TestCase):
    def python_files(self):
        yield SKILL_DIR / "scripts" / "validate.py"
        yield from sorted(PROJECT_DIR.glob("tests/*.py"))

    def test_only_standard_library_imports(self):
        for path in self.python_files():
            tree = ast.parse(read(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [(node.module or "").split(".")[0]]
                else:
                    continue
                for name in names:
                    if name in ("_helpers", "__future__", ""):
                        continue
                    self.assertIn(name, STDLIB, f"{path.name} imports {name}")

    def test_validate_has_no_network_or_process_modules(self):
        text = read(SKILL_DIR / "scripts" / "validate.py")
        for forbidden in ("urllib", "http", "socket", "subprocess", "requests", "anthropic", "openai"):
            self.assertNotRegex(text, rf"^\s*(import|from)\s+{forbidden}\b", forbidden)

    def test_python_version_requirement_documented(self):
        self.assertIn("3.11", read(PROJECT_DIR / "README.md"))


if __name__ == "__main__":
    unittest.main()
