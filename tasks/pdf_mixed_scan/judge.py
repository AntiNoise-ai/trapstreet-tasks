"""Per-case judge for the pdf_tables task — harsh by design.

Forked from tasks/pdf_reader_v2. Two matchers are added here and one inherited
matcher must not be used: see `m_sci_value` for why `numeric`/`leading_numeric`
are unusable on a document written entirely in scientific notation, and
`m_regex_forbidden` for the anti-shotgun rule the structure cases depend on.
`currency_amount` is inherited but unused — this document has no money in it.


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
                     The FIRST number in the answer must match. AVOID for
                     money questions: any answer that cites its source first
                     ("Based on clause 1.9b, the rent is GBP 2,100") leads with
                     the clause number and fails despite being correct. Kept
                     for cases where a bare number really is the required
                     format. Use `currency_amount` instead.
  - currency_amount  {"kind":"currency_amount","value":1234.5,"tolerance":0.01}
                     The LAST currency-formatted amount in the answer must
                     match. "Last" is the commitment: a model may quote the
                     whole rent schedule while reasoning, but the figure it
                     ends on is the one it is answering with. Ignores clause
                     numbers, dates and month counts entirely, because those
                     are never currency-formatted.
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


_CURRENCY_RE = re.compile(r"(?:£|GBP\s*)\s?(\d[\d,]*(?:\.\d+)?)", re.I)


def m_currency_amount(answer: str, spec: dict) -> tuple[bool, str]:
    """The LAST currency-formatted amount must match within tolerance.

    `leading_numeric` cannot be used for the money questions in this task. Every
    solution that cites its source ("Based on clause 1.9b, the rent for the
    period 05/09/2023 to 04/09/2024 is GBP 2,100.00") leads with a clause number
    or a date, and was scored wrong while holding the right answer — measured on
    three of five money cases across three different solutions.

    Anchoring on currency formatting sidesteps that: clause numbers, month
    counts and dates are never currency-formatted, so only candidate *amounts*
    are considered. Taking the last one preserves the anti-decoy property the
    original matcher was for — a model may walk through the whole rent schedule,
    but the amount it finishes on is the one it is committing to.
    """
    found = [float(m.replace(",", "")) for m in _CURRENCY_RE.findall(answer)]
    if not found:
        return False, "no currency-formatted amount found in answer"
    target = float(spec["value"])
    tol = float(spec.get("tolerance", 0.01))
    if abs(found[-1] - target) <= tol:
        return True, f"currency ok (committed {found[-1]} == target {target}; all amounts={found})"
    return False, f"committed amount {found[-1]} != target {target} (all amounts={found})"


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


def m_regex_forbidden(answer: str, spec: dict) -> tuple[bool, str]:
    """Fails if the pattern appears anywhere. The anti-shotgun primitive.

    Several cases here ask which single column/row has a property. Without
    this, an answer that lists every candidate ("B1 through B7 all carry
    values") satisfies a `regex_required` on the correct one and scores as if
    it had found it.
    """
    flags = 0
    if "i" in spec.get("flags", "i"):
        flags |= re.IGNORECASE
    m = re.search(spec["pattern"], answer, flags)
    if m:
        return False, f"forbidden pattern {spec['pattern']!r} matched {m.group(0)!r}"
    return True, "forbidden pattern absent"


# Scientific notation, tolerating a space around the E and a comma decimal
# separator (the EPD's own footnote writes its conversion factor as "3,07").
# Models and OCR engines write minus signs several ways, and the figures in a
# financial table are often parenthesised rather than signed. Normalising first
# means the patterns below only ever see an ASCII hyphen. Without this, an
# answer of "−179,225" (U+2212, which is what the rendered page shows) parsed
# as +179,225 and a correct answer scored zero.
_DASHES = {0x2212: "-", 0x2013: "-", 0x2014: "-", 0x2010: "-", 0x2011: "-",
           0xFF0D: "-", 0x00AD: "-", 0xFF0B: "+"}
_PAREN_NEG = re.compile(r"\(\s*([\d,][\d,.\s]*)\s*\)")


# This table prints the sign in its own column, so a figure can legitimately
# reach the judge as "- 1,867" with a gap. Closing that gap must not turn a
# range ("100 - 200") into a negative, so the sign is only pulled onto the
# digits when it is not itself preceded by a figure.
_DETACHED_SIGN = re.compile(r"(?<!\d\s)([-+])\s+(?=\d)")


def _normalise_signs(s: str) -> str:
    s = s.translate(_DASHES)
    s = _PAREN_NEG.sub(lambda m: "-" + m.group(1), s)      # (1,234) -> -1,234
    return _DETACHED_SIGN.sub(r"\1", s)                     # "- 1,867" -> "-1,867"


_SCI_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?\s*[Ee]\s*[+-]?\s*\d+")
# Thousands-grouped numbers first, so "1,719,915" is one token rather than
# stopping at "1,719".
_PLAIN_RE = re.compile(r"[-+]?\d{1,3}(?:,\d{3})+|[-+]?\d+(?:[.,]\d+)?")

_GROUPED = re.compile(r"^[-+]?\d{1,3}(?:,\d{3})+$")
_DEC_COMMA = re.compile(r"^[-+]?\d+,\d{1,2}$")


def _to_float(tok: str) -> float | None:
    """Parse a figure written in either convention this repo's documents use.

    A comma is a thousands separator in "748,255" and a decimal point in
    "3,07". Treating every comma as a decimal point — which this did
    originally, because the EPD's own footnote writes its factor as "3,07" —
    turns 748,255 into 748.255 and silently fails sixteen of twenty cases.
    Which convention applies is decided by the grouping, not guessed.
    """
    t = re.sub(r"\s+", "", tok)
    try:
        if "e" in t.lower():                 # mantissa may carry either style
            return float(t.replace(",", "."))
        if _GROUPED.match(t):                # 1,719,915 / 748,255
            return float(t.replace(",", ""))
        if _DEC_COMMA.match(t):              # 3,07 / 2,28
            return float(t.replace(",", "."))
        return float(t.replace(",", ""))
    except ValueError:
        return None


def m_sci_value(answer: str, spec: dict) -> tuple[bool, str]:
    """Value match for a document written entirely in scientific notation.

    Three things the inherited `numeric` matcher cannot do here:

    1. `NUMBER_RE` splits "2.25E+01" into [2.25, 1] — the value 22.5 is never
       produced, so every cell-lookup case would be unscoreable.
    2. These figures span 1E-15 to 1E+03. A fixed absolute tolerance is either
       meaningless at the top of that range or impossible at the bottom, so
       the comparison is relative.
    3. Unit strings in this document carry digits — "kg CO2e", "kg CFC-11e",
       "kBq U235e". Preferring E-notation tokens when any are present keeps
       those digits from being read as candidate answers.

    Semantics: if the answer contains scientific-notation numbers, the LAST one
    is the committed answer (same anti-decoy rule as the tenancy task's
    currency matcher — a model may walk a whole row before settling). If it
    contains none, fall back to accepting any plain number that matches, so an
    answer of "22.5" is not punished for expanding the notation.
    """
    answer = _normalise_signs(answer)
    target = float(spec["value"])
    rel = float(spec.get("rel_tolerance", 0.005))
    abs_tol = float(spec.get("abs_tolerance", 1e-18))

    # A ratio is written either way: "0.62%" or "0.0062". Both are the same
    # answer, and which one a model picks is formatting. Cases that ask for a
    # share set accept_percent_forms so neither is punished.
    targets = [target]
    if spec.get("accept_percent_forms"):
        targets += [target / 100.0, target * 100.0]

    def close(x: float) -> bool:
        return any(abs(x - t) <= max(abs(t) * rel, abs_tol) for t in targets)

    sci = [v for tok in _SCI_RE.findall(answer) if (v := _to_float(tok)) is not None]

    # mode="any": pass if the value appears anywhere. Required when a correct
    # answer legitimately states several figures and the target is not the one
    # it ends on — case_18 names two component rows and then their sum, so the
    # default last-wins rule would score it against the sum. Use "any" only
    # where a separate matcher already forces the model to identify what the
    # figure belongs to; on its own it gives up the anti-decoy property.
    if spec.get("mode") == "any":
        cands = sci or [v for tok in _PLAIN_RE.findall(answer) if (v := _to_float(tok)) is not None]
        if not cands:
            return False, "no numeric value found in answer"
        if any(close(v) for v in cands):
            return True, f"value present (target {target:g}; all={[f'{v:g}' for v in cands]})"
        return False, f"target {target:g} absent (found={[f'{v:g}' for v in cands]})"

    if sci:
        if close(sci[-1]):
            return True, f"sci ok (committed {sci[-1]:g} == target {target:g}; all={[f'{v:g}' for v in sci]})"
        return False, f"committed {sci[-1]:g} != target {target:g} (all={[f'{v:g}' for v in sci]})"

    plain = [v for tok in _PLAIN_RE.findall(answer) if (v := _to_float(tok)) is not None]
    if not plain:
        return False, "no numeric value found in answer"

    # Anti-shotgun, fourth revision. The three before it all rejected correct
    # answers, each time in a shape I had not anticipated: a figure cap that
    # counted the two numbers inside a date; a closing window that assumed the
    # answer comes last; a first-or-last window that broke on the commonest
    # analytical shape of all —
    #
    #   "On Wednesday, July 29, 2026: ... **Difference: $355,125 million** ...
    #    This makes sense conceptually because ..."
    #
    # preamble, answer, explanation. The figure is in the middle by design.
    #
    # Position turns out to be the wrong signal. What protects these cases is a
    # property of the questions: most ask for a figure the document does not
    # print — a ratio, a difference, a reconstructed base — so reproducing the
    # document cannot produce the answer. The few whose gold IS printed carry a
    # name requirement (the district, the account) that a bare list of numbers
    # cannot satisfy. The cap survives only against dumping a whole page.
    #
    # `require_commitment` restores positional scoring for a case that needs it.
    cap = int(spec.get("max_figures", 25))
    if len(plain) > cap:
        return False, (f"answer lists {len(plain)} figures (cap {cap}) — treated as a "
                       f"shotgun, not a committed answer")
    if spec.get("require_commitment"):
        tail = int(spec.get("commit_window", 3))
        cand = plain[:1] + plain[-tail:]
        for v in cand:
            if close(v):
                return True, f"plain-decimal ok ({v:g} == target {target:g}; committed)"
        return False, (f"target {target:g} is neither the opening figure nor among the "
                       f"last {tail}; all={[f'{v:g}' for v in plain]}")
    for v in plain:
        if close(v):
            return True, f"plain-decimal ok ({v:g} == target {target:g}; of {len(plain)} figures)"
    return False, f"target {target:g} absent (found={[f'{v:g}' for v in plain]})"


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
    "currency_amount": m_currency_amount,
    "sci_value": m_sci_value,
    "regex_required": m_regex_required,
    "regex_forbidden": m_regex_forbidden,
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
    manifest = json.loads(os.environ["TRAPTASK_MANIFEST"])

    stdout = Path(manifest["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(manifest["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(manifest["expected_dir"]) / "answer.json").read_text())

    # Pick up usage.json if the solution captured it (Sonnet + caching runs)
    usage_record: dict[str, Any] = {}
    usage_path = Path(manifest["outputs_dir"]) / "usage.json"
    if usage_path.exists():
        try:
            usage_record = json.loads(usage_path.read_text())
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
