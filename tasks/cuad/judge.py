"""Per-case judge for the imported CUAD task — span extraction, harsh by design.

Reads the agent's stdout (plain text OR JSON `{"answer": "..."}`) and applies the
matchers declared in expected/{case_id}/answer.json. A case scores 1.0 only if
ALL matchers pass.

CUAD has two kinds of case, and they catch opposite failure modes:

  - PRESENT  (gold_present=true)  — the contract genuinely contains the clause.
                                    Graded by `span_f1`: did the model surface the
                                    actual clause text? A model that says "no clause
                                    found" here scores ~0 F1 → fail. This is the
                                    LAZINESS test (confidently missing a real clause).

  - ABSENT   (gold_present=false) — the contract has no such clause.
                                    Graded by `no_clause`: did the model correctly
                                    say so? A model that fabricates a span here fails.
                                    This is the HALLUCINATION test (Mike's "no dead
                                    links / no hallucinated answers" claim under fire).

Matcher kinds supported (CUAD-specific):
  - span_f1     {"kind":"span_f1","gold_spans":["..."],"threshold":0.5}
                Pass if max(token-F1, containment) against ANY gold span >= threshold.
                Token-F1 uses SQuAD normalisation (lowercase, drop articles &
                punctuation). `containment` = 1.0 when a normalised gold span is a
                substring of the normalised answer — lets a model that quotes the
                clause verbatim *plus* commentary still pass.
  - no_clause   {"kind":"no_clause"}
                Pass if the answer asserts the clause is absent (e.g. "NO CLAUSE
                FOUND", "the contract does not contain", "no such provision").
                Fails on a fabricated/quoted span with no absence language.

Outputs JSON on stdout — trap stores it as CaseResult.metrics. The grader reads
`metrics.score` plus `category` / `gold_present` to split the laziness vs
hallucination diagnostics.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

# --- answer extraction (mirrors the mmlu judge contract) -------------------

def extract_agent_answer(stdout: str) -> str:
    """Accept JSON {"answer": "..."} or plain text. Strip surrounding whitespace."""
    stdout = stdout.strip()
    if not stdout:
        return ""
    try:
        obj = json.loads(stdout)
        if isinstance(obj, dict) and "answer" in obj:
            return str(obj["answer"])
    except json.JSONDecodeError:
        pass
    return stdout


# --- SQuAD-style token F1 --------------------------------------------------

_ARTICLES_RE = re.compile(r"\b(a|an|the)\b")
_PUNCT_RE = re.compile(r"[^a-z0-9 ]")
_WS_RE = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    """SQuAD normalisation: lowercase, drop articles & punctuation, squeeze space."""
    s = s.lower()
    s = _ARTICLES_RE.sub(" ", s)
    s = _PUNCT_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def token_f1(pred: str, gold: str) -> float:
    """Token-overlap F1 between two strings, after SQuAD normalisation."""
    p = normalize_text(pred).split()
    g = normalize_text(gold).split()
    if not p or not g:
        return 0.0
    common = Counter(p) & Counter(g)
    same = sum(common.values())
    if same == 0:
        return 0.0
    precision = same / len(p)
    recall = same / len(g)
    return 2 * precision * recall / (precision + recall)


def span_score(pred: str, gold_spans: list[str]) -> tuple[float, str]:
    """Best score across gold spans: max(token_f1, containment).

    containment = 1.0 when a (normalised) gold span appears verbatim inside the
    (normalised) answer — rewards a model that quotes the clause even if it wraps
    it in commentary.
    """
    if not gold_spans:
        return 0.0, "no gold spans provided"
    npred = normalize_text(pred)
    best = 0.0
    best_reason = ""
    for span in gold_spans:
        f1 = token_f1(pred, span)
        ngold = normalize_text(span)
        contained = 1.0 if ngold and ngold in npred else 0.0
        s = max(f1, contained)
        if s > best:
            best = s
            best_reason = f"f1={f1:.2f} contained={'yes' if contained else 'no'} vs gold[:40]={span[:40]!r}"
    return best, best_reason or "no overlap with any gold span"


# --- absence assertion detection (the hallucination guard) -----------------

_ABSENCE_PATTERNS = [
    "no clause found",
    "no clause",
    "no such clause",
    "no such provision",
    "no relevant clause",
    "no relevant provision",
    "does not contain",
    "does not include",
    "does not address",
    "not contain any",
    "no provision",
    "not present",
    "not found",
    "not addressed",
    "no mention",
    "not mention",
    "not specified",
    "no reference to",
]
# whole-word indicators that would over-match as substrings
_ABSENCE_WORD_RE = re.compile(r"\b(none|absent|n/?a)\b", re.IGNORECASE)


def asserts_absence(answer: str) -> bool:
    norm = normalize_text(answer)
    if any(p in norm for p in (normalize_text(x) for x in _ABSENCE_PATTERNS)):
        return True
    if _ABSENCE_WORD_RE.search(answer):
        return True
    return False


# --- matchers (kind -> (bool, reason)) -------------------------------------

def m_span_f1(answer: str, spec: dict) -> tuple[bool, str]:
    gold_spans = spec.get("gold_spans") or []
    threshold = float(spec.get("threshold", 0.5))
    score, reason = span_score(answer, gold_spans)
    if score >= threshold:
        return True, f"span match ok (score={score:.2f} >= {threshold}; {reason})"
    return False, f"span miss (score={score:.2f} < {threshold}; {reason})"


def m_no_clause(answer: str, spec: dict) -> tuple[bool, str]:
    if asserts_absence(answer):
        return True, "correctly asserted clause is absent"
    return False, "did not assert absence — likely hallucinated a span"


MATCHERS = {
    "span_f1": m_span_f1,
    "no_clause": m_no_clause,
}


def run_matchers(answer: str, matchers: list[dict]) -> tuple[float, list[dict]]:
    """Run all matchers; all must pass. Returns (score, per-matcher results)."""
    results = []
    all_ok = True
    for spec in matchers:
        kind = spec.get("kind")
        fn = MATCHERS.get(kind)
        if fn is None:
            results.append({"kind": kind, "pass": False, "reason": f"unknown matcher kind: {kind!r}"})
            all_ok = False
            continue
        ok, reason = fn(answer, spec)
        results.append({"kind": kind, "pass": ok, "reason": reason})
        if not ok:
            all_ok = False
    return (1.0 if all_ok else 0.0), results


# --- main ------------------------------------------------------------------

def main() -> None:
    payload = json.loads(os.environ["TRAPTASK_PAYLOAD"])

    stdout = Path(payload["outputs"]["case_stdout"]).read_text()
    exit_code = json.loads(Path(payload["outputs"]["case_meta.json"]).read_text())["exit_code"]
    expected = json.loads(Path(payload["expected"]["answer.json"]).read_text())

    usage_record: dict[str, Any] = {}
    usage_path = payload["outputs"].get("usage.json")
    if usage_path and Path(usage_path).exists():
        try:
            usage_record = json.loads(Path(usage_path).read_text())
        except json.JSONDecodeError:
            usage_record = {}

    base = {
        "id": expected.get("id"),
        "type": expected.get("type"),
        "category": expected.get("category"),
        "gold_present": expected.get("gold_present"),
        "difficulty": expected.get("difficulty"),
    }

    agent_answer = extract_agent_answer(stdout)

    if exit_code != 0:
        print(json.dumps({"score": 0.0, "reason": f"solution exited {exit_code}",
                          "agent_answer": agent_answer, **base, **usage_record}))
        return

    if not agent_answer:
        print(json.dumps({"score": 0.0, "reason": "agent produced no answer",
                          "agent_answer": "", **base, **usage_record}))
        return

    matchers = expected.get("matchers")
    if not matchers:
        print(json.dumps({"score": None, "reason": "no matchers (case not gradeable)",
                          "agent_answer": agent_answer, **base, **usage_record}))
        return

    score, matcher_results = run_matchers(agent_answer, matchers)
    print(json.dumps({
        "score": score,
        "matcher_results": matcher_results,
        "agent_answer": agent_answer[:600],
        **base,
        **usage_record,
    }))


if __name__ == "__main__":
    main()
