#!/usr/bin/env python3
"""Run one semantic-decision request in an isolated Codex CLI session.

The caller supplies a canonical request JSON file. Only a validated result goes to
stdout; process, model, and contract failures go to stderr without an inline retry.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from validate import MAX_INPUT_BYTES, analyze_request_bytes, parse_strict_json, validate_result


SKILL_DIR = Path(__file__).resolve().parent.parent
WORKER_MARKER = "SEMANTIC_DECISION_WORKER_V1"


def run(request_file: Path) -> int:
    if os.environ.get("SEMANTIC_DECISION_WORKER") == "1":
        print("nested codex exec is not allowed", file=sys.stderr)
        return 1

    try:
        with request_file.open("rb") as source:
            request_bytes = source.read(MAX_INPUT_BYTES + 1)
    except OSError:
        print("request file cannot be read", file=sys.stderr)
        return 1

    request_state = analyze_request_bytes(request_bytes)
    if request_state.kind != "valid":
        print("request contract invalid", file=sys.stderr)
        return 2

    prompt = f"$semantic-decision\n{WORKER_MARKER}\n{request_bytes.decode('utf-8')}\n"
    child_env = os.environ.copy()
    child_env["SEMANTIC_DECISION_WORKER"] = "1"

    try:
        with tempfile.TemporaryDirectory(prefix="semantic-decision-") as directory:
            root = Path(directory)
            git = subprocess.run(
                ["git", "init", "--quiet", str(root)],
                capture_output=True, check=False,
            )
            if git.returncode != 0:
                print("temporary Git repository could not be initialized", file=sys.stderr)
                return 1

            link = root / ".agents" / "skills" / "semantic-decision"
            link.parent.mkdir(parents=True)
            link.symlink_to(SKILL_DIR, target_is_directory=True)

            child = subprocess.run(
                [
                    "codex", "exec", "-C", str(root),
                    "--ephemeral", "--sandbox", "read-only",
                    "--model", "gpt-6-luna",
                    "-c", 'model_reasoning_effort="low"',
                    "-c", 'approval_policy="never"',
                    "--disable", "multi_agent", "--color", "never", "-",
                ],
                input=prompt, text=True, capture_output=True, check=False,
                timeout=180, env=child_env,
            )
    except (OSError, subprocess.TimeoutExpired):
        print("codex exec could not start or timed out", file=sys.stderr)
        return 1

    if child.returncode != 0:
        detail = next(
            (line.strip()[:300] for line in reversed(child.stderr.splitlines())
             if line.startswith("Error:")),
            "",
        )
        suffix = f": {detail}" if detail else ""
        print(f"codex exec failed (exit status {child.returncode}){suffix}", file=sys.stderr)
        return 1

    result_bytes = child.stdout.encode("utf-8")
    if len(result_bytes) > MAX_INPUT_BYTES:
        print("worker output is too large", file=sys.stderr)
        return 2
    result, parse_errors = parse_strict_json(result_bytes)
    if parse_errors:
        print("worker output is not one JSON object", file=sys.stderr)
        return 2
    if validate_result(result, request_state):
        print("result contract invalid", file=sys.stderr)
        return 2

    sys.stdout.write(child.stdout.rstrip("\n") + "\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request_file", type=Path, help="canonical request JSON file")
    args = parser.parse_args()
    return run(args.request_file)


if __name__ == "__main__":
    sys.exit(main())
