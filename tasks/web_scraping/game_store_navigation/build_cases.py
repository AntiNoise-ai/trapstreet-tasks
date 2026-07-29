"""Generate inputs/<id>/... and expected/<id>/answer.json from
gold.cases.json, validating authoring invariants first.

Run:  python3 build_cases.py
inputs/ and expected/ are GENERATED -- never edit them by hand.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE / "gold.cases.json"
SITE_SRC = HERE / "site_src"

KNOWN_MECHANISMS = {
    "static", "js_computed", "image_text_combined", "bundle_tier_value",
    "bundle_tier_marginal", "bundle_disambiguation", "dlc_vs_edition",
    "filter_sort", "pagination_count", "region_pricing",
}

INSTRUCTIONS = """\
This case includes an offline copy of a small game storefront (NebulaKey \
Store) as static files in this same directory. Start a local web server \
before navigating -- fetch()-based pages (bundle tiers, the catalog) need \
http:// to work; opening the files directly via file:// will not work \
correctly:

    python3 serve.py            # serves at http://localhost:8000/index.html
    python3 serve.py 8080        # or pick a different port

Then browse the site to answer the question below. Print ONLY the final \
numeric answer to stdout -- a bare number, optionally with a leading \
currency symbol -- no extra prose.

Question: {question}
"""


def validate_case(case: dict) -> None:
    """Fail loudly on authoring mistakes."""
    for field in ("id", "mechanism", "question", "gold"):
        if field not in case:
            raise ValueError(f"case missing required field {field!r}: {case}")
    if not case["id"].startswith("case_") or not case["id"][5:].isdigit():
        raise ValueError(f"case id {case['id']!r} is not opaque (expected case_NN)")
    if case["mechanism"] not in KNOWN_MECHANISMS:
        raise ValueError(f"case {case['id']}: unknown mechanism {case['mechanism']!r}")
    try:
        float(case["gold"])
    except ValueError:
        raise ValueError(f"case {case['id']}: gold {case['gold']!r} is not numeric") from None


def verify_gold_answers(cases: list[dict]) -> None:
    """Recompute every case's expected answer directly from site_src's own
    data files and assert it matches gold.cases.json's stored value. This
    exists because hand-counting/hand-computing these numbers is exactly how
    a real mistake was caught during this task's design (a filter that was
    supposed to match 9 games actually matched 10) -- the site's own data is
    the single source of truth, gold.cases.json must agree with it, not the
    other way around.
    """
    games = json.loads((SITE_SRC / "games.json").read_text())
    b1 = json.loads((SITE_SRC / "bundle-data.json").read_text())
    b2 = json.loads((SITE_SRC / "bundle-data2.json").read_text())
    by_id = {c["id"]: c for c in cases}

    def check(case_id: str, computed: float) -> None:
        expected = float(by_id[case_id]["gold"])
        if round(computed, 2) != round(expected, 2):
            raise ValueError(
                f"{case_id}: gold.cases.json says {expected}, "
                f"recomputed from site_src is {round(computed, 2)}"
            )

    def find(name: str) -> dict:
        return next(g for g in games if g["name"] == name)

    check("case_01", find("Ironclad Vanguard")["price"])
    check("case_02", 29.99 * (1 - 40 / 100))
    check("case_03", find("Hollow Meridian")["price"] * (1 - 30 / 100))

    per_game = [t["price"] / len(t["games"]) for t in b1["tiers"]]
    check("case_04", min(per_game))

    t2 = next(t for t in b1["tiers"] if t["tier"] == 2)
    t3 = next(t for t in b1["tiers"] if t["tier"] == 3)
    check("case_05", t3["price"] - t2["price"])

    t1 = next(t for t in b1["tiers"] if t["tier"] == 1)
    check("case_06", t1["price"])

    wraithbound = find("Wraithbound")["price"]
    ashes_dlc, deluxe = 6.99, 34.99
    check("case_07", deluxe - (wraithbound + ashes_dlc))

    action90 = sorted(
        (g for g in games if g["category"] == "Action" and g["rating"] >= 90),
        key=lambda g: g["price"],
    )
    check("case_08", action90[0]["price"])

    check("case_09", sum(1 for g in games if g["rating"] >= 90))

    check("case_10", wraithbound * 0.93)


def build() -> None:
    data = json.loads(GOLD.read_text())
    cases = data["cases"]
    verify_gold_answers(cases)

    seen_ids: set[str] = set()
    for case in cases:
        validate_case(case)
        cid = case["id"]
        if cid in seen_ids:
            raise ValueError(f"duplicate case id: {cid}")
        seen_ids.add(cid)

        in_dir = HERE / "inputs" / cid
        if in_dir.exists():
            shutil.rmtree(in_dir)
        shutil.copytree(SITE_SRC, in_dir)
        (in_dir / "question.txt").write_text(INSTRUCTIONS.format(question=case["question"]))

        exp_dir = HERE / "expected" / cid
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "answer.json").write_text(json.dumps({
            "id": cid,
            "mechanism": case["mechanism"],
            "gold": case["gold"],
            # Judge-only copy of the bare question text (no shared
            # boilerplate) -- used to compute confound numbers (e.g. "Tier
            # 3" in a question about tiers). The boilerplate instructions in
            # question.txt must NEVER be used for this: an earlier version
            # used a literal "$14.99" as a generic format example in that
            # boilerplate, which coincidentally matched case_01's real gold
            # value and got excluded as a false confound.
            "question": case["question"],
        }, indent=2))

    print(f"Built {len(cases)} cases.")


if __name__ == "__main__":
    build()
