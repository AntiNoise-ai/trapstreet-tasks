"""Per-case judge for the tenancy_agreement task — harsh by design.

Reads the agent's stdout (plain text OR JSON `{"answer": "..."}`) and applies
matchers declared in expected/{case_id}/answer.json. A case scores 1.0 only if
ALL matchers pass — partial credit is intentionally not offered. The whole
point of this task is to expose agents that hedge, miss clauses, or skip parts
of multi-part questions; lenient grading would defeat that.

Matcher kinds supported:
  - numeric          {"kind":"numeric","value":1234.5,"tolerance":0.01}
                     Passes if ANY number in the answer matches. Use for
                     show-your-working questions where the model walks
                     through arithmetic before stating the total.
  - leading_numeric  {"kind":"leading_numeric","value":1234.5,"tolerance":0.01}
                     The FIRST number in the answer must match. Use for
                     simple extraction questions where listing decoy
                     numbers should not count as a pass.
  - regex_required   {"kind":"regex_required","pattern":"...","flags":"i"}
                     Pattern must match (re.search). Default flags = i.
  - leading_word     {"kind":"leading_word","value":"yes"}
                     First alphanumeric token must equal value (case-insens),
                     after stripping common prefixes like "Answer:" or
                     markdown bold. Forces the model to commit, not hedge.
  - keywords_all     {"kind":"keywords_all","values":["a","b"]}
                     Every value must appear (case-insens substring).
  - keywords_any     {"kind":"keywords_any","values":["a","b"]}
                     At least one value must appear (case-insens substring).
  - keywords_any_word {"kind":"keywords_any_word","values":["ICE","BOE"]}
                     At least one value must appear as a whole word (\b...\b,
                     case-insens). Use for short acronyms that would
                     false-positive as substrings (ICE in "price", BOE in
                     "Boeing").
  - no_hedge         {"kind":"no_hedge"}
                     Reject answers that visibly punt the question, e.g.
                     "I cannot determine", "unclear from the document",
                     "I don't have access", "as an AI", etc.
  - min_words        {"kind":"min_words","value":5}
                     Reject one-word answers when the question asked for
                     reasoning/explanation.

Fallback (when no `matchers` provided):
  Substring match of `answer` (and any `accepted` variants) against the
  normalised agent output. Lenient but kept for cases that haven't been
  hardened yet (e.g. scenario_* cases without a curated gold).

Outputs JSON on stdout — trap stores it as CaseResult.metrics. The grader
reads `metrics.score` plus category/difficulty/reason for the report.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

HEDGE_PHRASES = [
    "i cannot", "i can't", "i am unable", "i'm unable",
    "i don't have access", "i do not have access",
    "as an ai", "as a language model",
    "cannot determine", "unable to determine",
    "unclear from the document", "not clear from the document",
    "i don't know", "i do not know",
    "insufficient information", "not enough information",
    "i'm not sure", "i am not sure",
]

NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def normalise(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


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


def parse_numeric(s: str) -> float | None:
    """Extract the first plausible number from `s`. £, $, commas, spaces stripped."""
    nums = parse_all_numerics(s)
    return nums[0] if nums else None


def parse_all_numerics(s: str) -> list[float]:
    """Extract ALL plausible numbers from `s`. Used to match agents that show
    working (e.g. "£1,950 × 12 + ... = £77,400" — we want to find 77400)."""
    if not s:
        return []
    cleaned = s.replace("£", "").replace("$", "").replace(",", "")
    out: list[float] = []
    for m in NUMBER_RE.finditer(cleaned):
        try:
            out.append(float(m.group(0).replace(",", "")))
        except ValueError:
            continue
    return out


_LEADING_LABEL_RE = re.compile(
    r"^\s*(?:answer|a|response|reply)[\s*_`]*:\s*", re.IGNORECASE,
)
_LEADING_NOISE_RE = re.compile(r"^[\s*_`#>\-]+")


def leading_word(s: str) -> str:
    """First alpha token, after stripping markdown noise and labels like
    "Answer:" / "**Answer**:" / "> ". Lets models prefix their commit with
    a natural label without auto-failing the case."""
    s = _LEADING_NOISE_RE.sub("", s)
    s = _LEADING_LABEL_RE.sub("", s)
    s = _LEADING_NOISE_RE.sub("", s)
    m = re.search(r"[a-zA-Z]+", s)
    return m.group(0).lower() if m else ""


# --- Matcher implementations ----------------------------------------------

def m_numeric(answer: str, spec: dict) -> tuple[bool, str]:
    """Pass if ANY number in the answer matches the target within tolerance.
    This lets models that show working ("1950 × 12 + 2100 × 12 = 77400") pass
    as long as the right number appears somewhere — exposing the actual answer
    is what matters, not whether the model led with it. For simple extraction
    where listing decoys should NOT pass, use `leading_numeric` instead."""
    nums = parse_all_numerics(answer)
    if not nums:
        return False, "no number found in answer"
    target = float(spec["value"])
    tol = float(spec.get("tolerance", 0.01))
    for n in nums:
        if abs(n - target) <= tol:
            return True, f"numeric ok (matched {n} of {nums} against target={target} tol={tol})"
    return False, f"numeric mismatch (numbers found={nums} target={target} tol={tol})"


def m_leading_numeric(answer: str, spec: dict) -> tuple[bool, str]:
    """First number in the answer must match within tolerance. Rejects
    decoy-number dumps like "rent 1950, deposit 2250, rent yr2 2100"
    where the target appears but isn't the committed answer."""
    nums = parse_all_numerics(answer)
    if not nums:
        return False, "no number found in answer"
    target = float(spec["value"])
    tol = float(spec.get("tolerance", 0.01))
    if abs(nums[0] - target) <= tol:
        return True, f"leading number ok ({nums[0]} == target {target} tol {tol})"
    return False, f"leading number {nums[0]} ≠ target {target} (other numbers in answer: {nums[1:]})"


def m_regex_required(answer: str, spec: dict) -> tuple[bool, str]:
    flags = 0
    if "i" in spec.get("flags", "i"):
        flags |= re.IGNORECASE
    if re.search(spec["pattern"], answer, flags):
        return True, f"regex matched"
    return False, f"regex {spec['pattern']!r} did not match"


def m_leading_word(answer: str, spec: dict) -> tuple[bool, str]:
    got = leading_word(answer)
    want = str(spec["value"]).lower()
    if got == want:
        return True, f"leading word ok ({got!r})"
    return False, f"leading word {got!r} ≠ required {want!r}"


def m_keywords_all(answer: str, spec: dict) -> tuple[bool, str]:
    norm = normalise(answer)
    missing = [v for v in spec["values"] if v.lower() not in norm]
    if missing:
        return False, f"missing required keyword(s): {missing}"
    return True, "all keywords present"


def m_keywords_any(answer: str, spec: dict) -> tuple[bool, str]:
    norm = normalise(answer)
    if any(v.lower() in norm for v in spec["values"]):
        return True, "at least one keyword present"
    return False, f"none of {spec['values']} present"


def m_keywords_any_word(answer: str, spec: dict) -> tuple[bool, str]:
    """Whole-word variant of keywords_any — wraps each value in \\b...\\b so
    short acronyms (ICE, BOE) don't false-match inside "price", "Boeing", etc."""
    for v in spec["values"]:
        if re.search(rf"\b{re.escape(v)}\b", answer, re.IGNORECASE):
            return True, f"whole-word match: {v!r}"
    return False, f"none of {spec['values']} matched as whole word"


def m_no_hedge(answer: str, spec: dict) -> tuple[bool, str]:
    norm = normalise(answer)
    for phrase in HEDGE_PHRASES:
        if phrase in norm:
            return False, f"hedge phrase detected: {phrase!r}"
    return True, "no hedge phrases"


def m_min_words(answer: str, spec: dict) -> tuple[bool, str]:
    count = len(re.findall(r"\S+", answer))
    want = int(spec["value"])
    if count >= want:
        return True, f"word count ok ({count} ≥ {want})"
    return False, f"too short ({count} < {want})"


MATCHERS = {
    "numeric": m_numeric,
    "leading_numeric": m_leading_numeric,
    "regex_required": m_regex_required,
    "leading_word": m_leading_word,
    "keywords_all": m_keywords_all,
    "keywords_any": m_keywords_any,
    "keywords_any_word": m_keywords_any_word,
    "no_hedge": m_no_hedge,
    "min_words": m_min_words,
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


def fallback_substring(answer: str, expected: dict) -> tuple[float, str]:
    """Lenient substring match when no matchers defined. Used for scenarios
    that don't have a curated gold yet — they shouldn't fail builds outright,
    but they also shouldn't claim a passing score from nothing."""
    targets = [t for t in [expected.get("answer"), *(expected.get("accepted") or [])] if t]
    if not targets:
        return 0.0, "no gold answer set (skip-equivalent)"
    norm = normalise(answer)
    hit = next((t for t in targets if normalise(t) in norm), None)
    if hit:
        return 1.0, f"substring match ({hit!r})"
    return 0.0, f"no substring match against {targets}"


# --- Main ------------------------------------------------------------------

def main() -> None:
    payload = json.loads(os.environ["TRAPTASK_PAYLOAD"])

    stdout = Path(payload["outputs"]["case_stdout"]).read_text()
    exit_code = json.loads(Path(payload["outputs"]["case_meta.json"]).read_text())["exit_code"]
    expected = json.loads(Path(payload["expected"]["answer.json"]).read_text())

    # Pick up usage.json if the solution captured it (Sonnet + caching runs)
    usage_record: dict[str, Any] = {}
    usage_path = payload["outputs"].get("usage.json")
    if usage_path and Path(usage_path).exists():
        try:
            usage_record = json.loads(Path(usage_path).read_text())
        except json.JSONDecodeError:
            usage_record = {}

    agent_answer = extract_agent_answer(stdout)

    # Solution crashed → hard fail.
    if exit_code != 0:
        out: dict[str, Any] = {
            "score": 0.0,
            "reason": f"solution exited {exit_code}",
            "agent_answer": agent_answer,
            "id": expected.get("id"),
            "category": expected.get("category"),
            "difficulty": expected.get("difficulty"),
            **usage_record,
        }
        print(json.dumps(out))
        return

    # Empty stdout → hard fail (silently passing the test is the worst outcome).
    if not agent_answer:
        out = {
            "score": 0.0,
            "reason": "agent produced no answer",
            "agent_answer": "",
            "id": expected.get("id"),
            "category": expected.get("category"),
            "difficulty": expected.get("difficulty"),
            **usage_record,
        }
        print(json.dumps(out))
        return

    matchers = expected.get("matchers")
    if matchers:
        score, matcher_results = run_matchers(agent_answer, matchers)
        out = {
            "score": score,
            "matcher_results": matcher_results,
            "agent_answer": agent_answer,
            "expected_answer": expected.get("answer"),
            "id": expected.get("id"),
            "type": expected.get("type"),
            "category": expected.get("category"),
            "difficulty": expected.get("difficulty"),
            **usage_record,
        }
    else:
        score, reason = fallback_substring(agent_answer, expected)
        # If there's no gold and no matchers, surface score=None so the grader
        # can flag it as "not yet curated" rather than mark the agent failed.
        if expected.get("answer") is None:
            out = {
                "score": None,
                "reason": "no curated gold yet (case not gradeable)",
                "agent_answer": agent_answer,
                "id": expected.get("id"),
                "type": expected.get("type"),
                "category": expected.get("category"),
                "difficulty": expected.get("difficulty"),
                **usage_record,
            }
        else:
            out = {
                "score": score,
                "reason": reason,
                "agent_answer": agent_answer,
                "expected_answer": expected.get("answer"),
                "id": expected.get("id"),
                "type": expected.get("type"),
                "category": expected.get("category"),
                "difficulty": expected.get("difficulty"),
                **usage_record,
            }

    print(json.dumps(out))


if __name__ == "__main__":
    main()
