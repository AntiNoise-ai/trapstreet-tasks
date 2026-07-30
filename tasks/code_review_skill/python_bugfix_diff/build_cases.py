"""Generate inputs/<id>/question.txt and expected/<id>/answer.json from
gold.cases.json, validating authoring invariants first.

Run:  python3 build_cases.py
inputs/ and expected/ are GENERATED -- never edit them by hand.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE / "gold.cases.json"

ALLOWED_LICENSES = {"MIT", "Apache-2.0", "BSD-3-Clause"}
ID_RE = re.compile(r"^case_\d\d$")

PROMPT_TEMPLATE = """You are reviewing a code change. Below is one file from \
the change, shown with its real line numbers.

File: {file_path}

{numbered_snippet}

Find the most significant bug in this code and report it. Respond with ONLY \
a JSON object in this exact shape, and nothing else:
{{"findings": [{{"file": "<file path>", "line": <line number>, "description": "<1-2 sentence description of the issue>"}}, ...]}}

List findings in order of confidence, most likely real bug first. You may \
report more than one finding, but only your first 5 will be scored.
"""

REQUIRED_FIELDS = [
    "id", "bug_category", "source_repo", "source_commit_url", "license",
    "file_path", "snippet_start_line", "snippet_text", "buggy_line",
    "line_tolerance", "keywords", "bug_description",
]


def validate_case(case: dict) -> None:
    cid = case.get("id", "<no id>")
    for field in REQUIRED_FIELDS:
        if field not in case or case[field] in (None, ""):
            raise ValueError(f"{cid}: missing required field '{field}'")

    if not ID_RE.match(case["id"]):
        raise ValueError(f"{cid}: id must match pattern 'case_NN'")

    if case["license"] not in ALLOWED_LICENSES:
        raise ValueError(
            f"{cid}: license must be one of {sorted(ALLOWED_LICENSES)}, got {case['license']!r}"
        )

    n_lines = case["snippet_text"].count("\n") + (0 if case["snippet_text"].endswith("\n") else 1)
    start = case["snippet_start_line"]
    end = start + n_lines - 1
    if not (start <= case["buggy_line"] <= end):
        raise ValueError(
            f"{cid}: buggy_line {case['buggy_line']} out of snippet range [{start}, {end}]"
        )

    if len(case["keywords"]) < 2:
        raise ValueError(f"{cid}: needs at least 2 keywords, got {len(case['keywords'])}")


def render_snippet(start_line: int, text: str) -> str:
    """Render `text` with real absolute line numbers, e.g. '  1276| <code>'."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(f"{start_line + i:5d}| {line}" for i, line in enumerate(lines))


def build() -> None:
    data = json.loads(GOLD.read_text())
    seen_ids: set[str] = set()
    for case in data["cases"]:
        validate_case(case)
        cid = case["id"]
        if cid in seen_ids:
            raise ValueError(f"duplicate case id: {cid}")
        seen_ids.add(cid)

        in_dir = HERE / "inputs" / cid
        in_dir.mkdir(parents=True, exist_ok=True)
        numbered = render_snippet(case["snippet_start_line"], case["snippet_text"])
        (in_dir / "question.txt").write_text(
            PROMPT_TEMPLATE.format(file_path=case["file_path"], numbered_snippet=numbered)
        )

        exp_dir = HERE / "expected" / cid
        exp_dir.mkdir(parents=True, exist_ok=True)
        answer = {
            "id": cid,
            "bug_category": case["bug_category"],
            "file_path": case["file_path"],
            "buggy_line": case["buggy_line"],
            "line_tolerance": case["line_tolerance"],
            "keywords": case["keywords"],
            "bug_description": case["bug_description"],
            "source_commit_url": case["source_commit_url"],
            "license": case["license"],
        }
        if "keyword_groups" in case:
            answer["keyword_groups"] = case["keyword_groups"]
        (exp_dir / "answer.json").write_text(json.dumps(answer, indent=2))

    print(f"Built {len(data['cases'])} cases.")


if __name__ == "__main__":
    build()
