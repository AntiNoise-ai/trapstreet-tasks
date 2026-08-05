"""One-shot helper that writes gold.cases.json (the case grid).

Run once; gold.cases.json is then the checked-in source of truth and is what
build_cases.py reads. Re-running regenerates the same 64 cases in the same
order, so case ids stay stable.

Grid, per the pre-registered design in README.md:

  For each of the 8 intent families:
    (n=6,   position=mid,   clean)        (n=6,   position=mid,   adversarial)
    (n=60,  position=mid,   clean)        (n=60,  position=mid,   adversarial)
    (n=300, position=mid,   clean)        (n=300, position=mid,   adversarial)
    (n=300, position=early, adversarial)  (n=300, position=late,  adversarial)

  = 8 cells x 8 families = 64 cases.

Position is crossed only at the largest N and only in the adversarial arm:
v1 of this task found position completely flat across 270 scores, so spending
the case budget on eight independent difficulty constructs buys more than
spending it on a factor with no prior support. Where position could plausibly
bite -- a 300-tool, ~56k-token catalog -- it is still measured.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

CELLS = [
    (6, "mid", "clean"),
    (6, "mid", "adversarial"),
    (60, "mid", "clean"),
    (60, "mid", "adversarial"),
    (300, "mid", "clean"),
    (300, "mid", "adversarial"),
    (300, "early", "adversarial"),
    (300, "late", "adversarial"),
]


def main() -> None:
    families = json.loads((HERE / "families.json").read_text())["families"]
    cases = []
    n = 0
    for fam in families:
        for n_tools, position, ambiguity in CELLS:
            n += 1
            cases.append({
                "id": f"case_{n:02d}",
                "intent": fam["intent"],
                "n_tools": n_tools,
                "position": position,
                "ambiguity": ambiguity,
                "category": f"{'adv' if ambiguity == 'adversarial' else 'clean'}_n{n_tools}_{position}",
            })

    out = {
        "_doc": (
            "Source of truth for core_tool_selection_at_scale. Declares the case grid; "
            "the tool catalogs themselves are composed deterministically by build_cases.py "
            "from families.json + filler_pool.json (inlining 64 catalogs of up to 300 "
            "verbose schemas would be ~30MB of unreviewable JSON). inputs/ and expected/ "
            "are GENERATED -- edit here, never there."
        ),
        "cases": cases,
    }
    (HERE / "gold.cases.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote gold.cases.json: {len(cases)} cases.")


if __name__ == "__main__":
    main()
