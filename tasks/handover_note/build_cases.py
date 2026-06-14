"""Source-of-truth generator for the handover_note task — inference, unprimed.

Real, terse ops handover note (game-key storefront) using undefined in-house
shorthand (PO / No-PO). The model must work out FOR ITSELF that this is a royalty
situation and infer the rule from the note — we do NOT supply a glossary or hint
the answer. The traps are SCOPE and TIMING:

  - the bundle's *correct* pack is a PO (already-paid) pack, so NOTHING from this
    bundle should ever hit the publisher's royalty statement — not just the 517
    error sales the note explicitly mentions;
  - the fix at 10:15 on 21/05 swapped to the correct PO pack, so sales *after*
    the fix also carry no royalty (a naive read assumes "fixed => royalty resumes").

The only stated fact is "the [517 error] sales must not appear on the royalty
statement." Everything else must be inferred via the chain: swapping No-PO -> PO
is what removes royalty, therefore PO = no royalty, therefore the whole bundle
(and all future sales) = no royalty.

Answers are yes/no or a number, graded by the matcher judge (leading_word /
leading_numeric). No multiple choice, no glossary, no leading explanation.

Run:  python3 build_cases.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

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
        "id": cid, "answer": answer, "type": "inference",
        "matchers": matchers, "category": category, "difficulty": difficulty,
        "_notes": note,
    }, indent=2) + "\n")
    META.append({"id": cid, "category": category, "difficulty": difficulty,
                 "answer": answer, "notes": note})


emit(
    "all_off_statement", "scope", "hard",
    "Read the attached handover note (note.txt). Should every key sold from the "
    "\"Prestige Collection XL EDITION - Build your Own Bundle\" be kept OFF this "
    "publisher's royalty statement? Answer yes or no.",
    "yes",
    [{"kind": "leading_word", "value": "yes"}, {"kind": "no_hedge"}],
    "The correct pack is a PO (paid) pack => no royalty on any of it; the 517 error sales were "
    "reclassified to PO too. So ALL of the bundle stays off the statement. Trap: thinking only "
    "the explicitly-mentioned 517 are off and normal sales owe royalty (-> 'no').",
)

emit(
    "after_fix_royalty", "timing", "hard",
    "Read the attached handover note (note.txt). Do keys from this bundle sold AFTER "
    "10:15 on 21/05/2026 count toward royalty for this publisher? Answer yes or no.",
    "no",
    [{"kind": "leading_word", "value": "no"}, {"kind": "no_hedge"}],
    "After the fix the bundle uses the correct PO (paid) pack => no royalty. Trap: assuming "
    "'now it's fixed, so royalty resumes normally' (-> 'yes').",
)

emit(
    "the_517_owe", "inference", "medium",
    "Read the attached handover note (note.txt). Do the 517 keys sold during the error "
    "owe royalty to this publisher? Answer yes or no.",
    "no",
    [{"kind": "leading_word", "value": "no"}, {"kind": "no_hedge"}],
    "They were reclassified to PO and the note says they must not appear on the royalty "
    "statement => no royalty owed. Trap: 'they were sold as No-PO, which owes royalty' (-> 'yes').",
)

emit(
    "count_on_statement", "scope", "hard",
    "Read the attached handover note (note.txt). How many keys sold from this bundle "
    "should appear on this publisher's royalty statement? Answer with a single number.",
    "0",
    [{"kind": "leading_numeric", "value": 0.0, "tolerance": 0.01}],
    "None — the whole bundle is a PO (paid) pack. Trap: answering 517 (the count the note "
    "foregrounds) or some non-zero number.",
)


emit(
    "po_in_royalty", "rule", "hard",
    "Read the attached handover note (note.txt). In general (not just for the 517 "
    "error keys), should sales of PO SKUs appear on this publisher's royalty report? "
    "Answer yes or no.",
    "no",
    [{"kind": "leading_word", "value": "no"}, {"kind": "no_hedge"}],
    "PO = already-paid stock => no royalty => not on the report. Derivable: the fix for the "
    "royalty problem was to swap TO PO, so PO is the no-royalty state. Trap: 'PO is the correct/"
    "normal pack, so it bills royalty' (-> 'yes').",
)

emit(
    "nonpo_in_royalty", "rule", "hard",
    "Read the attached handover note (note.txt). In general (not just for the 517 "
    "error keys), should sales of No-PO SKUs appear on this publisher's royalty report? "
    "Answer yes or no.",
    "yes",
    [{"kind": "leading_word", "value": "yes"}, {"kind": "no_hedge"}],
    "No-PO = not pre-paid => royalty owed => on the report. Derivable: the note bothers to say "
    "the (No-PO) error sales 'must not appear', which is only needed if No-PO normally WOULD "
    "appear. Trap: the note excludes THESE No-PO sales, so a model generalizes 'No-PO => not on "
    "report' (-> 'no'); the 517 are an exception (reclassified to PO).",
)


emit(
    "correct_also_off", "inference", "hard",
    "Read the attached handover note (note.txt). The wrong SKUs were kept off this "
    "publisher's royalty statement, and the bundle has since been corrected to the proper "
    "PO SKUs. Should the proper PO SKUs be kept off the royalty statement as well? "
    "Answer yes or no.",
    "yes",
    [{"kind": "leading_word", "value": "yes"}, {"kind": "no_hedge"}],
    "Yes — the correct pack is PO (pre-paid) => no royalty => also kept off the statement. The "
    "whole bundle is no-royalty; the error was only that the wrong SKU type was used. Trap: "
    "'the correct pack is normal, so it bills royalty -> no, it should appear'.",
)


def main():
    lines = ["dirs:", "  inputs: inputs/", "  expected: expected/", "", "cases:"]
    for m in META:
        desc = m["notes"].replace('"', "'")
        lines += [f"- id: {m['id']}", f'  description: "{desc}"', "  tags:",
                  f"  - {m['category']}", f"  - {m['difficulty']}", ""]
    lines += ["judge:", "  cmd: python3 judge.py", "", "grader:", "  cmd: python3 grader.py", ""]
    (HERE / "traptask.yaml").write_text("\n".join(lines))
    (HERE / "gold.cases.json").write_text(json.dumps(META, indent=2) + "\n")
    print(f"generated {len(META)} handover_note cases into {HERE}")


if __name__ == "__main__":
    main()
