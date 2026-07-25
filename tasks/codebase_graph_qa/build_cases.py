"""Generate inputs/<id>/{repo/**, question.txt} and expected/<id>/answer.json
from gold.cases.json, validating authoring invariants first.

Run:  python3 build_cases.py
inputs/ and expected/ are GENERATED -- never edit them by hand.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE / "gold.cases.json"

ID_RE = re.compile(r"^case_\d\d$")
ALLOWED_CATEGORIES = {"call_chain", "import_chain", "schema_fk", "config_trace", "doc_code_xref"}
NOT_FOUND = "NOT_FOUND"

REQUIRED_FIELDS = ["id", "category", "files", "question", "answer"]

QUESTION_TEMPLATE = """You are given a small software repository at `repo/` \
(relative to this directory) and a question about its internal structure.

Question: {question}

Respond with ONLY a JSON object in this exact shape, and nothing else:
{{"answer": ["<identifier 1>", "<identifier 2>", ...]}}

Follow the identifier format specified in the question exactly. List every \
item you're confident belongs in the answer -- both missing correct items \
and incorrect extra items count against your score, so don't guess \
indiscriminately.
"""


def validate_case(case: dict) -> None:
    cid = case.get("id", "<no id>")
    for field in REQUIRED_FIELDS:
        if field not in case or case[field] in (None, "", [], {}):
            raise ValueError(f"{cid}: missing required field '{field}'")

    if not ID_RE.match(case["id"]):
        raise ValueError(f"{cid}: id must match pattern 'case_NN'")

    if case["category"] not in ALLOWED_CATEGORIES:
        raise ValueError(
            f"{cid}: category must be one of {sorted(ALLOWED_CATEGORIES)}, got {case['category']!r}"
        )

    files = case["files"]
    if not isinstance(files, dict) or not files:
        raise ValueError(f"{cid}: 'files' must be a non-empty dict of path -> content")
    for path, content in files.items():
        if path.startswith("/") or ".." in Path(path).parts:
            raise ValueError(f"{cid}: unsafe file path {path!r}")
        if not isinstance(content, str):
            raise ValueError(f"{cid}: content for {path!r} must be a string")

    if not isinstance(case["question"], str) or not case["question"].strip():
        raise ValueError(f"{cid}: 'question' must be a non-empty string")

    answer = case["answer"]
    if not isinstance(answer, list) or not answer:
        raise ValueError(f"{cid}: 'answer' must be a non-empty list")
    if len(set(answer)) != len(answer):
        raise ValueError(f"{cid}: 'answer' contains duplicate entries")
    for item in answer:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{cid}: answer entries must be non-empty strings")

    category = case["category"]

    if category == "doc_code_xref":
        if len(answer) != 1:
            raise ValueError(f"{cid}: doc_code_xref answers must have exactly one entry")

    if category == "schema_fk":
        schema_text = files.get("schema.sql", "")
        for table in answer:
            if not re.search(rf"\b{re.escape(table)}\b", schema_text, re.IGNORECASE):
                raise ValueError(
                    f"{cid}: answer table {table!r} does not appear anywhere in schema.sql -- "
                    "likely a typo"
                )
    else:
        # call_chain / import_chain / config_trace / doc_code_xref: every
        # answer item should either be a bare path that's a key in `files`,
        # or "<path>:<symbol>" where <path> is a key in `files`, or the
        # NOT_FOUND sentinel (doc_code_xref only).
        for item in answer:
            if item == NOT_FOUND:
                continue
            path_part = item.split(":", 1)[0]
            if path_part not in files:
                raise ValueError(
                    f"{cid}: answer entry {item!r} references file {path_part!r} "
                    f"which is not in this case's 'files' -- likely a typo"
                )


def render_question(question: str) -> str:
    return QUESTION_TEMPLATE.format(question=question)


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
        if in_dir.exists():
            shutil.rmtree(in_dir)
        repo_dir = in_dir / "repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        for rel_path, content in case["files"].items():
            dest = repo_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)
        (in_dir / "question.txt").write_text(render_question(case["question"]))

        exp_dir = HERE / "expected" / cid
        if exp_dir.exists():
            shutil.rmtree(exp_dir)
        exp_dir.mkdir(parents=True, exist_ok=True)
        answer = {
            "id": cid,
            "category": case["category"],
            "answer": case["answer"],
        }
        (exp_dir / "answer.json").write_text(json.dumps(answer, indent=2))

    print(f"Built {len(data['cases'])} cases.")


if __name__ == "__main__":
    build()
