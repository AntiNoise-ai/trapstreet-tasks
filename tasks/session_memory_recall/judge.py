"""Per-case judge for session_memory_recall.

I/O contract: reads TRAPTASK_MANIFEST (trap-cli).

Scoring is binary and fully deterministic (no LLM judge). The answer is a
machine-generated number or record id, never a sentence, so there is no
phrasing to argue about -- either the value came back or it did not.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

VOUCHER_RE = re.compile(r"\bAR-2026-\d{4}\b")
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
# Money as it may plausibly be written back: 12345.67, 12,345.67, $12,345.67.
# The trailing lookahead rejects a following digit, and a following period only
# when a digit follows it -- a sentence-ending period is not part of the number.
# Getting this wrong is not cosmetic: `(?![\w.])` made "27,940.01." match as
# "27" and "27940.01." match as nothing at all, so any value that ended a
# sentence was invisible here.
MONEY_RE = re.compile(
    r"(?<![\w.])\$?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?(?![\w])(?!\.\d)"
    r"|(?<![\w.])\$?\d+(?:\.\d{1,2})?(?![\w])(?!\.\d)"
)
STRIP = " \t\r\n\"'`*.,:;!?()[]{}"

# Mirrors assert_answer_hard_to_guess() in build_cases.py: every money answer
# carries at least four digits before the decimal point. Anything shorter is
# therefore not the answer -- it is a step number, a match count, a rank -- and
# counting it as a rival candidate only produced false negatives.
MIN_WHOLE_DIGITS = 4


def last_value_line(stdout: str) -> str:
    lines = [ln.strip(STRIP) for ln in stdout.splitlines()]
    lines = [ln for ln in lines if ln]
    return lines[-1] if lines else ""


def normalise_money(text: str) -> str | None:
    """'$12,345.67' -> '12345.67'. None if it is not a money-shaped token."""
    t = text.replace("$", "").replace(",", "").replace("USD", "").strip()
    try:
        return f"{float(t):.2f}"
    except ValueError:
        return None


def candidates(text: str, kind: str) -> set[str]:
    """Every token in `text` that could plausibly be an answer of this kind.

    Used to reject shotgun answers -- printing every figure in the ledger must
    not count as remembering the one that mattered. Which makes the set's
    precision matter in both directions: a token that could never be the answer
    must not land here, or it turns a correct answer into a rival candidate and
    the shotgun rule fires on a solution that did nothing wrong. Voucher ids
    and ISO dates are removed before the money scan for exactly that reason --
    "AR-2026-0016" otherwise contributed 2026.00 and 16.00.
    """
    if kind == "voucher":
        return set(VOUCHER_RE.findall(text))
    scrubbed = ISO_DATE_RE.sub(" ", VOUCHER_RE.sub(" ", text))
    out = set()
    for tok in MONEY_RE.findall(scrubbed):
        n = normalise_money(tok)
        if n is None or len(n.split(".")[0]) < MIN_WHOLE_DIGITS:
            continue
        out.add(n)
    return out


def score_case(stdout: str, expected: dict) -> dict[str, Any]:
    """1.0 iff the remembered value came back.

    The final line is the contract, so it is read first and it is decisive:
    if it carries a value of the right kind, that value is the answer the
    solution is giving, whether or not prose surrounds it.

      1. the final line IS the value                      -> 1.0
      2. the final line carries exactly one candidate      -> that candidate
      3. the final line carries several                    -> 0.0, ambiguous
      4. the final line carries none                       -> fall back to the
         whole output, crediting it only if the answer is the sole candidate

    Step 4 forgives a solution that trails off after answering. Steps 2-3 are
    what stop a shotgun: listing every figure in the ledger is not remembering
    the one that mattered.
    """
    answer = expected["answer"]
    kind = expected.get("answer_kind", "money")
    category = expected.get("category")

    tail = last_value_line(stdout)
    tail_norm = tail if kind == "voucher" else (normalise_money(tail) or tail)
    if tail.upper() == "UNKNOWN":
        return {
            "score": 0.0,
            "reason": "solution reported UNKNOWN -- value did not survive into session 2",
            "category": category,
            "reported": "UNKNOWN",
        }

    if tail_norm.lower() == answer.lower():
        return {"score": 1.0, "reason": "exact match on final line", "category": category,
                "reported": tail}

    tail_found = candidates(tail, kind)
    if tail_found:
        if answer in tail_found and len(tail_found) == 1:
            return {
                "score": 1.0,
                "reason": "value on the final line (surrounding prose tolerated)",
                "category": category,
                "reported": answer,
            }
        if answer in tail_found:
            return {
                "score": 0.0,
                "reason": f"final line carries {len(tail_found)} candidates -- shotgun not credited",
                "category": category,
                "reported": tail,
                "n_candidates": len(tail_found),
            }
        return {
            "score": 0.0,
            "reason": "final line reports a different value",
            "category": category,
            "reported": tail,
            "n_candidates": len(tail_found),
        }

    found = candidates(stdout, kind)
    if answer in found and len(found) == 1:
        return {
            "score": 1.0,
            "reason": "value present and unambiguous (preamble tolerated)",
            "category": category,
            "reported": answer,
        }

    if answer in found:
        return {
            "score": 0.0,
            "reason": f"value present but {len(found)} candidates in output -- shotgun not credited",
            "category": category,
            "reported": tail,
            "n_candidates": len(found),
        }

    return {
        "score": 0.0,
        "reason": "value absent from output",
        "category": category,
        "reported": tail,
        "n_candidates": len(found),
    }


def main() -> None:
    m = json.loads(os.environ["TRAPTASK_MANIFEST"])
    stdout = Path(m["run"]["stdout"]).read_text(errors="replace")
    exit_code = json.loads(Path(m["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(m["expected_dir"]) / "answer.json").read_text())

    if exit_code != 0:
        result = {"score": 0.0, "reason": f"solution exited {exit_code}",
                  "category": expected.get("category")}
    elif not stdout.strip():
        result = {"score": 0.0, "reason": "empty stdout",
                  "category": expected.get("category")}
    else:
        result = score_case(stdout, expected)

    result["id"] = expected["id"]
    print(json.dumps(result))


if __name__ == "__main__":
    main()
