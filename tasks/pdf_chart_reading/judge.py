"""Per-case judge for pdf_chart_reading.

Every question in this task asks for a small integer -- a number of
participants, a number of ranges, a number of levels. That makes the anti-
shotgun problem acute in a way pdf_mixed_scan's six-digit figures never were:
an answer that lists a whole distribution contains the right small number by
accident, and "the last number wins" turns any trailing aside ("out of 18
participants") into a wrong answer.

So this judge does not guess which number the model meant. Each question ends
with `End your reply with a line of the form ANSWER: <value>`, and the judge
grades that line. The fallback, for a model that ignores the contract, is
lenient only when there is nothing to be lenient about: if the whole reply
contains at most three numbers there is no shotgun to catch, so the reply
itself is read as the answer. Beyond that it scores zero with the reason
stated, which is a format failure and is reported as one.

Matchers:
  committed_value  {"value": 9, "tolerance": 0}   first number of the committed answer
  committed_has_value {"value": 8}                 the figure appears in a compound answer
  committed_regex  {"pattern": "1\\.9\\s*-\\s*2\\.0"}  pattern over the committed answer
  regex_required   {"pattern": "..."}             pattern over the whole reply
  no_hedge         {}                             reject a visible punt
  not_derivable    {"pattern": "..."}             require a punt, WITH a stated reason
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

HEDGE_PHRASES = [
    "i cannot", "i can't", "i am unable", "i'm unable", "cannot be determined",
    "can't be determined", "cannot determine", "unable to determine", "not derivable",
    "cannot be derived", "not possible to determine", "does not identify",
    "is not identified", "not shown", "not reported", "no way to tell", "unknowable",
]

NUM = re.compile(r"[-−–(]?\s*\d[\d,]*(?:\.\d+)?\s*\)?")

# Numbers that are part of how the answer is phrased rather than the answer:
# the bin the bar sits in, the figure it came from, the year of the panel.
# "ANSWER: The 3.5-3.6 bar holds 9 participants" commits to 9, not to 3.5.
SCAFFOLDING = [
    re.compile(r"\d+\.\d+\s*(?:to|[-−–—‐―])\s*\d+\.\d+"),   # a bin label
    re.compile(r"\b(?:figure|fig\.?|table|panel|page)\s*\d+(?:\.\w+)?", re.IGNORECASE),
    re.compile(r"\b(?:19|20)\d{2}\b"),                          # a year
]


def strip_scaffolding(s: str) -> str:
    stripped = s
    for pat in SCAFFOLDING:
        stripped = pat.sub(" ", stripped)
    # Never strip an answer away entirely: a case whose answer is itself a year
    # or a range would otherwise be left with nothing to compare.
    return stripped if NUM.search(stripped) else s


def to_float(tok: str) -> float | None:
    t = tok.strip()
    neg = t.startswith(("-", "−", "–")) or (t.startswith("(") and t.endswith(")"))
    t = t.strip("()-−– ")
    # A comma groups thousands when the digits come in threes, else it is a decimal point.
    if "," in t:
        head, _, tail = t.rpartition(",")
        t = t.replace(",", "") if len(tail) == 3 and tail.isdigit() else t.replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def numbers(s: str) -> list[float]:
    out = []
    for m in NUM.finditer(s):
        v = to_float(m.group())
        if v is not None:
            out.append(v)
    return out


def strip_markup(s: str) -> str:
    return s.replace("**", "").replace("*", "").replace("`", "").strip(" .")


def committed_answer(reply: str) -> tuple[str | None, str]:
    """The value the model committed to, and how it was obtained."""
    hits = list(re.finditer(r"ANSWER\s*[:：]\s*(.+)", reply, re.IGNORECASE))
    if hits:
        return strip_markup(hits[-1].group(1)), "answer line"
    # No contract line. A reply short on numbers has nothing to shotgun with, so
    # read the figure it ends on -- "the 3.5-3.6 bar holds 9" commits to 9, not
    # to the bin label it opens with.
    found = list(NUM.finditer(reply))
    if 0 < len(found) <= 3:
        return strip_markup(found[-1].group()), "no answer line; read the closing figure"
    return None, "no ANSWER line, and the reply carries more than three numbers"


def m_committed_value(reply: str, committed: str | None, spec: dict) -> tuple[bool, str]:
    if committed is None:
        return False, "no committed answer"
    got = numbers(strip_scaffolding(committed))
    if not got:
        return False, f"committed answer carries no number: {committed!r}"
    want, tol = float(spec["value"]), float(spec.get("tolerance", 0))
    ok = abs(got[0] - want) <= tol + 1e-9
    return ok, f"committed {got[0]:g}, expected {want:g}"


def m_committed_has_value(reply: str, committed: str | None, spec: dict) -> tuple[bool, str]:
    """For questions that ask for more than one thing.

    `committed_value` reads the first number, which is right when the answer IS
    a number and wrong the moment the question asks for a name as well: a
    correct "in the 2028 panel, 1.9-2.0 and 2.1-2.2 are tied at 8 each" leads
    with 2028. Here the figure only has to appear, and the accompanying
    regex matchers are what pin down the rest of the answer.
    """
    if committed is None:
        return False, "no committed answer"
    want, tol = float(spec["value"]), float(spec.get("tolerance", 0))
    got = numbers(strip_scaffolding(committed))
    ok = any(abs(g - want) <= tol + 1e-9 for g in got)
    return ok, f"expected {want:g} among {[f'{g:g}' for g in got]}"


def m_committed_regex(reply: str, committed: str | None, spec: dict) -> tuple[bool, str]:
    if committed is None:
        return False, "no committed answer"
    ok = bool(re.search(spec["pattern"], committed, re.IGNORECASE))
    return ok, f"pattern {spec['pattern']!r} against {committed!r}"


def m_regex_required(reply: str, committed: str | None, spec: dict) -> tuple[bool, str]:
    ok = bool(re.search(spec["pattern"], reply, re.IGNORECASE))
    return ok, f"pattern {spec['pattern']!r} {'found' if ok else 'absent'}"


def m_no_hedge(reply: str, committed: str | None, spec: dict) -> tuple[bool, str]:
    """Scoped to the committed answer, not the whole reply.

    The premise of this task is that the figure is not printed anywhere, so
    "the count is not shown numerically, but the bar reaches 9" is the natural
    shape of a CORRECT answer. Scanning the whole reply for "not shown" scored
    that zero. Once a model has committed a value, a caveat in the prose above
    it is not a punt.
    """
    if committed is None:
        return True, "nothing committed; committed_value carries the failure"
    low = committed.lower()
    hit = next((p for p in HEDGE_PHRASES if p in low), None)
    return hit is None, f"hedge {hit!r} in the committed answer" if hit else "committed a value"


def m_not_derivable(reply: str, committed: str | None, spec: dict) -> tuple[bool, str]:
    """The reason IS the evidence of the refusal.

    Requiring a phrase from HEDGE_PHRASES as well rejected "the figure does not
    attribute dots to individuals, so no participant can be named" -- a refusal
    phrased as a statement about the document rather than about the model.
    """
    # The refusal has to be what the model committed to, not something it said
    # on the way to naming somebody. "The figure does not attribute dots to
    # individuals, but it was the Chair. ANSWER: the Chair" scored 1.0 before
    # this: the reason was present, and it was reciting it while inventing an
    # answer anyway. When there is an ANSWER line it is the only thing read;
    # without one, a reply that is nothing but the refusal still counts.
    target = committed if re.search(r"ANSWER\s*[:：]", reply, re.IGNORECASE) else reply
    if target and re.search(spec["pattern"], target, re.IGNORECASE):
        return True, "declined, naming why the figure cannot supply it"
    return False, "no stated reason in the committed answer; a name was invented"


MATCHERS = {
    "committed_value": m_committed_value,
    "committed_has_value": m_committed_has_value,
    "committed_regex": m_committed_regex,
    "regex_required": m_regex_required,
    "no_hedge": m_no_hedge,
    "not_derivable": m_not_derivable,
}


def main() -> None:
    manifest = json.loads(os.environ["TRAPTASK_MANIFEST"])
    expected = json.loads((Path(manifest["expected_dir"]) / "answer.json").read_text())
    reply = Path(manifest["run"]["stdout"]).read_text().strip()

    committed, how = committed_answer(reply)
    details, score = [], 1.0
    for spec in expected["matchers"]:
        fn = MATCHERS.get(spec["kind"])
        if fn is None:
            details.append({"kind": spec["kind"], "passed": False, "detail": "unknown matcher"})
            score = 0.0
            continue
        ok, detail = fn(reply, committed, spec)
        details.append({"kind": spec["kind"], "passed": ok, "detail": detail})
        if not ok:
            score = 0.0

    print(json.dumps({
        "score": score,
        "passed": score == 1.0,
        "figure": expected.get("figure"),
        "panel": expected.get("panel"),
        "category": expected.get("type"),
        "difficulty": expected.get("difficulty"),
        "committed": committed,
        "committed_via": how,
        "reason": ("; ".join(f"{d['kind']}: {d['detail']}" for d in details if not d["passed"])
                   + ("" if committed is not None else f" ({how})")).strip()
                  or "all matchers passed",
        "matchers": details,
    }))


if __name__ == "__main__":
    sys.exit(main())
