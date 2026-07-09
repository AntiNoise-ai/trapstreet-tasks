"""Per-case judge for the code_syntax_generation task.

Grades HumanEval-style code generation by running the canonical unit tests
against the model's submitted function. Case scores 1.0 only if all
assertions in the test pass.

Executes model code in a subprocess with a 10-second timeout for basic
isolation. Model code that hangs, crashes, or fails assertions → 0.0.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


HEDGE_PHRASES = [
    "i cannot", "i can't", "i am unable", "i'm unable",
    "as an ai", "as a language model",
    "i don't know", "i do not know",
]


def extract_code(response: str) -> str:
    """Strip ```python fences from response, tolerating variations."""
    s = response.strip()
    # Handle ```python or ``` opening
    m = re.match(r"^```(?:python|py)?\s*\n(.+?)\n```\s*$", s, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Handle just leading ```
    m = re.match(r"^```(?:python|py)?\s*\n(.+)$", s, re.DOTALL)
    if m:
        code = m.group(1).strip()
        # Try to trim trailing fence
        if code.endswith("```"):
            code = code[:-3].rstrip()
        return code
    return s


def m_python_unit_test(answer: str, spec: dict) -> tuple[bool, str]:
    """Extract model code, prepend prompt (for imports/type hints), run test."""
    code = extract_code(answer)
    test_code = spec["test_code"]
    entry_point = spec["entry_point"]
    prompt_prefix = spec.get("prompt_prefix", "")

    # If the model returned just the function body (no def), prepend the prompt
    # so the def is properly formed. This helps models that follow the prompt
    # convention of "continue from the def" strictly.
    if f"def {entry_point}" not in code:
        code = prompt_prefix + code

    # Compose the full program
    program = f"{code}\n\n{test_code}\n\ncheck({entry_point})\n"

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(program)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, "all assertions passed"
        # Check for common failure modes
        stderr = result.stderr.strip()[-300:]
        return False, f"exit={result.returncode}: {stderr}"
    except subprocess.TimeoutExpired:
        return False, "timeout (>10s)"
    except Exception as e:
        return False, f"exec error: {e}"
    finally:
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass


def m_no_hedge(answer: str, spec: dict) -> tuple[bool, str]:
    norm = answer.lower()
    for p in HEDGE_PHRASES:
        if p in norm:
            return False, f"hedge phrase detected: {p!r}"
    return True, "no hedge phrases"


MATCHERS = {
    "python_unit_test": m_python_unit_test,
    "no_hedge": m_no_hedge,
}


def run_matchers(answer: str, matchers: list[dict]) -> tuple[float, list[dict]]:
    results = []
    all_ok = True
    for spec in matchers:
        kind = spec.get("kind")
        fn = MATCHERS.get(kind)
        if fn is None:
            results.append({"kind": kind, "pass": False, "reason": f"unknown matcher: {kind!r}"})
            all_ok = False
            continue
        ok, reason = fn(answer, spec)
        results.append({"kind": kind, "pass": ok, "reason": reason})
        if not ok:
            all_ok = False
    return (1.0 if all_ok else 0.0), results


def extract_agent_answer(stdout: str) -> str:
    stdout = stdout.strip()
    if not stdout:
        return ""
    try:
        obj = json.loads(stdout)
        if isinstance(obj, dict) and "answer" in obj:
            return str(obj["answer"])
    except json.JSONDecodeError:
        pass
    return stdout


def main() -> None:
    m = json.loads(os.environ["TRAPTASK_MANIFEST"])
    stdout = Path(m["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(m["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(m["expected_dir"]) / "answer.json").read_text())

    agent_answer = extract_agent_answer(stdout)

    if exit_code != 0:
        print(json.dumps({
            "score": 0.0,
            "reason": f"solution exited {exit_code}",
            "id": expected.get("id"),
            "category": expected.get("difficulty"),
        }))
        return

    if not agent_answer:
        print(json.dumps({
            "score": 0.0,
            "reason": "agent produced no answer",
            "id": expected.get("id"),
            "category": expected.get("difficulty"),
        }))
        return

    matchers = expected.get("matchers", [])
    score, matcher_results = run_matchers(agent_answer, matchers)
    print(json.dumps({
        "score": score,
        "matcher_results": matcher_results,
        "agent_answer_preview": agent_answer[:500],
        "id": expected.get("id"),
        "type": expected.get("type"),
        "category": expected.get("difficulty"),
        "difficulty": expected.get("difficulty"),
        "task_id": expected.get("task_id"),
        "entry_point": expected.get("entry_point"),
    }))


if __name__ == "__main__":
    main()
