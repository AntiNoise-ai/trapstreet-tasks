"""Per-case judge for the code_review_skill/python_bugfix_diff task.

The skill under test receives one real (pre-fix) source file, shown with its
real line numbers, and reports findings as JSON. A finding "hits" the gold
bug only if it names the right file, points within a small line-number
window of the real bug line, AND its description contains at least one of
the case's pre-declared keywords. Only the FIRST 5 findings are considered
(anti-shotgun) -- a skill can't win by flagging every line.

This is deterministic (no LLM judge): the ground truth is a real historical
bugfix commit. Most cases use a flat "keywords" list (any literal phrase
hits). A case can instead declare "keyword_groups": a list of concept
groups, each a list of raw regexes (not literal-escaped, so they can use
stems/inflections like r"overwrit\\w*"); a finding's keyword_match requires
at least one regex hit from EVERY group (AND across groups, OR within a
group). Use groups for bugs whose correct description has a wide paraphrase
space (control-flow/structural bugs) instead of trying to enumerate every
literal phrasing -- require the co-occurrence of the core concepts instead.

I/O contract: reads TRAPTASK_MANIFEST (trap-cli).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

MAX_FINDINGS_SCORED = 5


def _strip_fences(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _finding_matches(finding: Any, expected: dict) -> dict[str, bool]:
    """Per-signal match flags for one finding against the gold bug."""
    if not isinstance(finding, dict):
        return {"file_match": False, "line_match": False, "keyword_match": False}

    file_match = False
    f = finding.get("file")
    if isinstance(f, str) and f.strip():
        file_match = Path(f.strip()).name == Path(expected["file_path"]).name

    line_match = False
    line = finding.get("line")
    if isinstance(line, (int, float)) and not isinstance(line, bool):
        try:
            line_match = abs(int(line) - expected["buggy_line"]) <= expected.get("line_tolerance", 2)
        except (OverflowError, ValueError):
            # int(float("inf"))/-inf raises OverflowError, int(float("nan")) raises
            # ValueError. json.loads accepts these non-standard literals by default,
            # so a solution can emit e.g. {"line": Infinity} and must degrade to a
            # clean miss here rather than crashing score_case().
            line_match = False

    keyword_match = False
    desc = finding.get("description")
    if isinstance(desc, str) and desc:
        groups = expected.get("keyword_groups")
        if groups:
            # Concept-group mode: the description must hit at least one
            # pattern from EVERY group (AND across groups, OR within a
            # group). Patterns are raw regexes (not literal-escaped) so
            # they can use stems/inflections (e.g. r"overwrit\w*") instead
            # of enumerating every literal phrasing of the same concept.
            keyword_match = all(
                any(re.search(pattern, desc, re.IGNORECASE) for pattern in group)
                for group in groups
            )
        else:
            keyword_match = any(
                re.search(rf"\b{re.escape(kw)}\b", desc, re.IGNORECASE)
                for kw in expected["keywords"]
            )

    return {"file_match": file_match, "line_match": line_match, "keyword_match": keyword_match}


def score_case(stdout: str, expected: dict) -> dict[str, Any]:
    s = _strip_fences(stdout)
    try:
        obj = json.loads(s)
    except (json.JSONDecodeError, TypeError, RecursionError):
        return {"score": 0.0, "hit_index": None, "n_findings_considered": 0,
                "format_ok": False, "reason": "output is not valid JSON"}

    if not isinstance(obj, dict) or not isinstance(obj.get("findings"), list):
        return {"score": 0.0, "hit_index": None, "n_findings_considered": 0,
                "format_ok": False, "reason": "missing 'findings' list"}

    # Anti-shotgun: only the first MAX_FINDINGS_SCORED findings are considered.
    considered = obj["findings"][:MAX_FINDINGS_SCORED]

    hit_index = None
    best_match_count = -1
    best_signals = {"file_match": False, "line_match": False, "keyword_match": False}
    for i, finding in enumerate(considered):
        signals = _finding_matches(finding, expected)
        match_count = sum(signals.values())
        if match_count > best_match_count:
            best_match_count = match_count
            best_signals = signals
        if all(signals.values()) and hit_index is None:
            hit_index = i

    score = 1.0 if hit_index is not None else 0.0
    return {
        "score": score,
        "format_ok": True,
        "hit_index": hit_index,
        "n_findings_total": len(obj["findings"]),
        "n_findings_considered": len(considered),
        "best_match_signals": best_signals,
    }


def main() -> None:
    m = json.loads(os.environ["TRAPTASK_MANIFEST"])

    stdout = Path(m["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(m["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(m["expected_dir"]) / "answer.json").read_text())

    base = {"id": expected.get("id"), "bug_category": expected.get("bug_category")}

    if exit_code != 0:
        print(json.dumps({**base, "score": 0.0, "reason": f"solution exited {exit_code}",
                           "agent_output": stdout.strip()[:500]}))
        return

    if not stdout.strip():
        print(json.dumps({**base, "score": 0.0, "reason": "agent produced no output",
                           "agent_output": ""}))
        return

    metrics = score_case(stdout, expected)
    metrics.update(base)
    metrics["agent_output"] = stdout.strip()[:500]
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
