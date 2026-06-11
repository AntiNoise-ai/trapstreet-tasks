"""Source-of-truth generator for the handover_note task.

A real, terse operations handover note (from a digital game-key storefront)
full of undefined domain shorthand. The trap is a conflicting signal: the keys
were *sold* under No-PO SKUs (which normally owe royalties), but the correction
reclassifies them to PO (already-paid) stock, so they must NOT appear on the
publisher's royalty statement — which the note states explicitly. A model that
over-reasons from the default rule ("non-PO => royalty") gets it backwards.

Domain (confirmed by the note's owner):
  - PO SKU    = purchase order, already in paid stock  -> NO royalty owed
  - No-PO SKU = not in paid stock                       -> royalty owed

Lane: model-eval (plain text in, reasoning out; no tools needed).

Run:  python3 build_cases.py
Emits: inputs/<id>/{note.txt, question.txt} + expected/<id>/answer.json
       + traptask.yaml + gold.cases.json
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The note, verbatim as written by the colleague (typo in the migration line is
# intentional — it's the real artifact; no question depends on that line).
NOTE = """\
Handover note — please action.

The store pack in Prestige Collection XL EDITION - Build your Own Bundle
mistakenly contained No-PO SKUs for Coffee Talk and Coffee Talk Episode 2
instead of the correct PO SKU Pack.

Correction: Swapped to the correct PO SKU Pack at 10:15 on 21/05/2026.

Inventory Migration: Transferred all 517 keys sold under the incorrect setup
from PO stocks over to Normal Stocks.

Royalty Impact: Sales for this incorrect pack must not appear on the royalty
statement for this publisher.
"""

META = []


def emit(cid, category, difficulty, question, answer, matchers, note):
    (HERE / "inputs" / cid).mkdir(parents=True, exist_ok=True)
    (HERE / "expected" / cid).mkdir(parents=True, exist_ok=True)
    (HERE / "inputs" / cid / "note.txt").write_text(NOTE)
    (HERE / "inputs" / cid / "question.txt").write_text(question.strip() + "\n")
    (HERE / "expected" / cid / "answer.json").write_text(json.dumps({
        "id": cid, "answer": answer, "type": "text",
        "matchers": matchers, "category": category, "difficulty": difficulty,
        "_notes": note,
    }, indent=2) + "\n")
    META.append({"id": cid, "category": category, "difficulty": difficulty, "notes": note})


# --- the two real traps --------------------------------------------------------
emit(
    "royalty_inclusion", "royalty", "hard",
    """
Read the attached handover note (note.txt).

These 517 keys were sold under No-PO SKUs, and No-PO SKUs normally require
royalty payments to the publisher. Based on the note, should the sales of this
incorrect pack be included on this publisher's royalty statement?

Answer "yes" or "no".
""",
    "no",
    [{"kind": "leading_word", "value": "no"}, {"kind": "no_hedge"}],
    "Core trap. The question primes the default rule (No-PO => royalty), but the note's correction "
    "reclassifies the keys to PO stock and explicitly excludes them. Correct answer: No.",
)

emit(
    "royalty_count", "royalty", "hard",
    """
Read the attached handover note (note.txt).

Of the 517 affected sales, how many should appear as royalty-bearing line items
on this publisher's royalty statement?

Answer with a single number.
""",
    "0",
    [{"kind": "leading_numeric", "value": 0.0, "tolerance": 0.01}],
    "False-premise / honesty trap. The note says these sales must not appear on the royalty "
    "statement, so the count is 0. A model that anchors on 517 fails.",
)

# --- extraction baseline (difficulty spread) ----------------------------------
emit(
    "affected_count", "extraction", "easy",
    """
Read the attached handover note (note.txt).

How many keys were sold under the incorrect setup? Answer with a single number.
""",
    "517",
    [{"kind": "leading_numeric", "value": 517.0, "tolerance": 0.01}],
    "Baseline extraction.",
)

emit(
    "correction_time", "extraction", "easy",
    """
Read the attached handover note (note.txt).

On what date and time was the pack corrected? Use the format: HH:MM on DD/MM/YYYY.
""",
    "10:15 on 21/05/2026",
    [{"kind": "keywords_all", "values": ["10:15", "21/05/2026"]}],
    "Baseline extraction of the correction timestamp.",
)

emit(
    "affected_titles", "extraction", "easy",
    """
Read the attached handover note (note.txt).

Which game titles were affected by the SKU error? List them.
""",
    "Coffee Talk and Coffee Talk Episode 2",
    [{"kind": "keywords_all", "values": ["Coffee Talk", "Episode 2"]}],
    "Baseline extraction of the two affected titles.",
)


def main():
    order = ["royalty_inclusion", "royalty_count",
             "affected_count", "correction_time", "affected_titles"]
    by_id = {m["id"]: m for m in META}
    lines = ["dirs:", "  inputs: inputs/", "  expected: expected/", "", "cases:"]
    for cid in order:
        m = by_id[cid]
        desc = m["notes"].replace('"', "'")
        lines += [f"- id: {cid}", f'  description: "{desc}"', "  tags:",
                  f"  - {m['category']}", f"  - {m['difficulty']}", ""]
    lines += ["judge:", "  cmd: python3 judge.py", "", "grader:", "  cmd: python3 grader.py", ""]
    (HERE / "traptask.yaml").write_text("\n".join(lines))
    (HERE / "gold.cases.json").write_text(json.dumps([by_id[c] for c in order], indent=2) + "\n")
    print(f"generated {len(order)} handover_note cases into {HERE}")


if __name__ == "__main__":
    main()
