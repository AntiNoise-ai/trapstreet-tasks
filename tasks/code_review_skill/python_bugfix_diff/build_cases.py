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
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

PROMPT_TEMPLATE = """You are reviewing a code change. Below is one file from \
the change, shown with its real line numbers.

File: {file_path}

{numbered_snippet}

Find the most significant bug in this code and report it. Respond with ONLY \
a JSON object in this exact shape, and nothing else:
{{"findings": [{{"file": "<file path>", "line": <line number>, "description": "<1-2 sentence description of the issue>"}}, ...]}}

List findings in order of confidence, most likely real bug first. You may \
report more than one finding, but only your first 5 will be scored.

Optional: this file is part of a real, public repository. If it would help \
your review, `repo_context.json` (in this same input directory) gives you \
the repo and an exact commit you can check out to see the surrounding \
codebase as it existed at that point -- you are not limited to the snippet \
above if your review process benefits from more context.
"""

REQUIRED_FIELDS = [
    "id", "bug_category", "source_repo", "source_commit_url", "license",
    "file_path", "snippet_start_line", "snippet_text", "buggy_line",
    "line_tolerance", "keywords", "bug_description", "parent_commit_sha",
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

    if not SHA_RE.match(case["parent_commit_sha"]):
        raise ValueError(
            f"{cid}: parent_commit_sha must be a 40-char lowercase hex SHA, "
            f"got {case['parent_commit_sha']!r}"
        )

    # Safety-critical: parent_commit_sha must NEVER equal the fix commit --
    # that would hand solutions the literal answer via a clonable ref. Extract
    # via regex (not naive rsplit("/")) and casefold both sides so a query
    # string or a differently-cased same commit can't silently bypass this.
    fix_sha_match = re.search(r"[0-9a-fA-F]{40}", case["source_commit_url"])
    if not fix_sha_match:
        raise ValueError(
            f"{cid}: source_commit_url does not contain a 40-char hex commit SHA: "
            f"{case['source_commit_url']!r}"
        )
    fix_sha = fix_sha_match.group(0).lower()
    if case["parent_commit_sha"].lower() == fix_sha:
        raise ValueError(
            f"{cid}: parent_commit_sha equals the fix commit SHA -- this would leak "
            f"the answer. It must be the fix commit's PARENT (pre-fix state)."
        )


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

        # Optional real-repo access for solutions that want more than the
        # snippet: repo + the PRE-fix commit only. Never the fix commit
        # itself (validate_case already refuses to build if it matches).
        repo_context = {
            "repo": f"https://github.com/{case['source_repo']}",
            "parent_commit_sha": case["parent_commit_sha"],
            "note": (
                "Optional. Shallow-fetch this exact commit if your review "
                "process wants the full repo, e.g.: git init && git remote "
                "add origin <repo> && git fetch --depth 1 origin "
                "<parent_commit_sha> && git checkout FETCH_HEAD. This commit "
                "predates the bug being found/fixed -- it will not reveal "
                "which commit fixed it."
            ),
        }
        (in_dir / "repo_context.json").write_text(json.dumps(repo_context, indent=2))

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
        (exp_dir / "answer.json").write_text(json.dumps(answer, indent=2))

    print(f"Built {len(data['cases'])} cases.")


if __name__ == "__main__":
    build()
