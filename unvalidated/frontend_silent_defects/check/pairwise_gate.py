"""Stage-1 gate: can a pairwise judge reproduce the owner's comparisons?

Nine same-brief pairs, one forced choice each. Cross-brief comparisons are not
asked — a landing page and a dashboard are not the same question.

Ground truth is `labels/pairwise_2026-09-05.txt`, elicited the same way and
stable at 9/9 with no position bias. It is NOT `check/anchors/`: two of those
anchors are contradicted by it, which is why the earlier pointwise panel looked
worse than it was.

First/second order is balanced — her page goes first in four pairs and second in
five — so a judge that simply prefers whichever page it sees first lands near
5/9 and cannot be flattered or punished by the order I happened to choose.

    <=6/9  stop. Position bias is beside the point; it does not judge.
    >=7/9  buy stage 2: the same nine pairs, sides swapped, which separates a
           judgment from a coin that landed well.
    >=8/9  the gate (p~0.02 against chance).

Nine pairs is the whole instrument — nine pages exist, so nine same-brief
comparisons exist. No amount of re-running raises that ceiling. This is a screen
before spending on more pages, not a validation.

    ANTHROPIC_API_KEY=... python3 check/pairwise_gate.py
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

import anthropic

TASK = Path(__file__).resolve().parent.parent
PAGES = TASK / "labels" / "pages"
MODEL = os.environ.get("TRAP_PANEL_MODEL", "claude-sonnet-5")

# (brief, page shown first, page shown second, the page she chose)
TRIALS = [
    ("07", "07C", "07A", "07C"),
    ("07", "07A", "07B", "07B"),
    ("07", "07B", "07C", "07B"),
    ("08", "08C", "08B", "08B"),
    ("08", "08B", "08A", "08B"),
    ("08", "08A", "08C", "08C"),
    ("09", "09A", "09B", "09A"),
    ("09", "09B", "09C", "09C"),
    ("09", "09C", "09A", "09A"),
]

STANCE = (
    "You are reading two attempts at the same brief and deciding which is the "
    "better piece of work. You do not know who or what produced either, and "
    "speculating about that is out of scope."
)

# Deliberately the same words the human was given. Asking the judge a different
# question than the label was elicited with would make the comparison meaningless.
ASK = (
    "Same brief, two attempts. Pick the one you would rather put your name on. "
    "No ties — if it is close, choose anyway.\n\n"
    "Judge the work, not the taste: whether it made the right moves for this "
    "brief, whether the craft holds up, whether it did what was asked."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "choice": {"type": "string", "enum": ["first", "second"]},
        "why": {"type": "string", "description": "One sentence, the deciding observation."},
    },
    "required": ["choice", "why"],
    "additionalProperties": False,
}


def img(page: str) -> dict:
    return {"type": "image", "source": {
        "type": "base64", "media_type": "image/jpeg",
        "data": base64.standard_b64encode((PAGES / f"{page}.jpg").read_bytes()).decode()}}


def ask(client: anthropic.Anthropic, brief: str, first: str, second: str) -> dict:
    content = [
        {"type": "text", "text": f"The brief both were built from:\n\n{brief}"},
        {"type": "text", "text": "The first attempt:"}, img(first),
        {"type": "text", "text": "The second attempt:"}, img(second),
        {"type": "text", "text": ASK},
    ]
    resp = client.messages.create(
        model=MODEL, max_tokens=4000, system=STANCE,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA},
                       "effort": os.environ.get("TRAP_PANEL_EFFORT", "medium")},
        messages=[{"role": "user", "content": content}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(text)


def main() -> None:
    client = anthropic.Anthropic(max_retries=5)
    briefs = {b: (TASK / "inputs" / f"case_{b}" / "brief.md").read_text() for b in ("07", "08", "09")}

    rows, by_brief = [], {}
    for brief, first, second, hers in TRIALS:
        r = ask(client, briefs[brief], first, second)
        chose = first if r["choice"] == "first" else second
        ok = chose == hers
        by_brief.setdefault(brief, []).append(ok)
        rows.append({"brief": brief, "first": first, "second": second,
                     "hers": hers, "judge": chose, "ok": ok,
                     "her_page_position": "first" if hers == first else "second",
                     "why": r["why"]})
        print(f"  {first} vs {second}   hers={hers}  judge={chose}  {'ok' if ok else 'MISS'}")
        print(f"      {r['why'][:150]}")

    n = sum(r["ok"] for r in rows)
    print(f"\n  total {n}/9")
    for b, oks in by_brief.items():
        print(f"    brief {b}: {sum(oks)}/{len(oks)}")
    picked_first = sum(1 for r in rows if r["judge"] == r["first"])
    print(f"  judge picked the first-shown page {picked_first}/9  (her page was first in "
          f"{sum(1 for r in rows if r['her_page_position'] == 'first')}/9)")
    print("\n  " + ("GATE PASSED — buy stage 2" if n >= 8 else
                    "stage 2 is worth buying" if n == 7 else
                    "STOP — it does not judge"))
    (TASK / "labels" / "gate_stage1.json").write_text(json.dumps(
        {"model": MODEL, "total": n, "rows": rows}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
