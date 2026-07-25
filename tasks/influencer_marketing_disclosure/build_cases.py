"""Generate inputs/<id>/... and expected/<id>/answer.json from
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

VALID_CATEGORIES = {"gifting_disclosure", "attribution", "no_script", "macro_flat_fee", "clean_control"}
VALID_TRAPS = {"gifting_disclosure", "attribution", "no_script", "macro_flat_fee", "none"}

CASE_ID_RE = re.compile(r"^case_\d\d$")

OUTPUT_FORMAT_BLOCK = """\
Respond with a single JSON object (no markdown fences, no extra prose \
before or after it) with exactly this shape:

{
  "requires_disclosure": true | false,
  "findings": [
    {"description": "<any recommendation, caution, or correction you'd \
give about this specific situation -- empty list if you see none>"}
  ]
}

"requires_disclosure" is whether the creator/partner in this specific \
situation needs to disclose a material connection with the brand (payment, \
free product, family/personal relationship, or any other benefit) under \
FTC endorsement guidelines. Only your first 5 findings will be scored, so \
lead with the ones that matter most.\
"""


def validate_case(case: dict) -> None:
    """Fail loudly on authoring mistakes -- missing fields, out-of-range
    values, inconsistent category/trap pairing, disallowed categories."""
    required = {
        "id", "category", "trap", "tags", "description", "scenario",
        "expected_requires_disclosure",
    }
    missing = required - case.keys()
    if missing:
        raise ValueError(f"case {case.get('id', '<no id>')} missing fields: {sorted(missing)}")

    cid = case["id"]
    if not CASE_ID_RE.match(cid):
        raise ValueError(f"case id {cid!r} must match ^case_\\d\\d$ (opaque, no answer-leaking labels)")

    if case["category"] not in VALID_CATEGORIES:
        raise ValueError(f"{cid}: category {case['category']!r} not in {VALID_CATEGORIES}")

    if case["trap"] not in VALID_TRAPS:
        raise ValueError(f"{cid}: trap {case['trap']!r} not in {VALID_TRAPS}")

    # category/trap consistency -- these two fields are meant to move together
    category_trap = {
        "gifting_disclosure": "gifting_disclosure",
        "attribution": "attribution",
        "no_script": "no_script",
        "macro_flat_fee": "macro_flat_fee",
        "clean_control": "none",
    }
    if category_trap[case["category"]] != case["trap"]:
        raise ValueError(
            f"{cid}: category {case['category']!r} implies trap "
            f"{category_trap[case['category']]!r}, got {case['trap']!r}"
        )

    if not isinstance(case["expected_requires_disclosure"], bool):
        raise ValueError(f"{cid}: expected_requires_disclosure must be a bool")

    if not isinstance(case["scenario"], str) or len(case["scenario"]) < 50:
        raise ValueError(f"{cid}: scenario must be a real paragraph (>=50 chars)")

    if not case["tags"]:
        raise ValueError(f"{cid}: tags must be non-empty")


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
        question = (
            "You are an expert in influencer and creator marketing, helping a team "
            "navigate a specific partnership situation. Read the situation below and "
            "respond.\n\n"
            f"{case['scenario']}\n\n"
            f"{OUTPUT_FORMAT_BLOCK}"
        )
        (in_dir / "question.txt").write_text(question)

        exp_dir = HERE / "expected" / cid
        exp_dir.mkdir(parents=True, exist_ok=True)
        answer = {
            "id": cid,
            "category": case["category"],
            "trap": case["trap"],
            "expected_requires_disclosure": case["expected_requires_disclosure"],
        }
        (exp_dir / "answer.json").write_text(json.dumps(answer, indent=2) + "\n")

    print(f"Built {len(data['cases'])} cases.")


if __name__ == "__main__":
    build()
