"""Per-case judge for influencer_marketing_disclosure.

I/O contract: reads TRAPTASK_MANIFEST (trap-cli). See
references/traptask-contract.md for the exact manifest shape.

Scoring is fully deterministic (no LLM judge) -- see README.md for the
rationale and the score_case() docstring below for the exact rubric.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

MAX_FINDINGS_SCORED = 5

# Multi-word phrases only -- a bare single word is exploitable by an
# unrelated sentence that happens to contain it. See
# references/scoring-design.md.

GIFTING_DISCLOSURE_PHRASES = [
    "still requires disclosure", "still needs disclosure", "still need to disclose",
    "not a loophole", "isn't a loophole", "is not a loophole",
    "material connection", "material relationship",
    "gifted post still", "gifting still", "free product still",
    "clear and conspicuous", "clearly and conspicuously",
    "spoken in the video", "spoken aloud", "not buried in hashtags",
    "brand is liable", "brand liability", "you're responsible for your creators",
    "even a family", "family relationship", "personal relationship still",
    "even a free trial", "free trial still",
]

ATTRIBUTION_PHRASES = [
    "unique promo code", "unique discount code", "dedicated promo code",
    "vanity url", "vanity link", "dedicated landing page",
    "utm link", "utm tracking", "utm parameter",
    "post-purchase survey", "how did you hear about us",
    "branded search", "attribution blind spot",
    "links aren't clickable", "links are not clickable", "no clickable link",
    "cost per qualified outcome",
]

NO_SCRIPT_PHRASES = [
    "won't write a word-for-word", "will not write a word-for-word",
    "don't script", "shouldn't script", "should not script",
    "instead of a script", "rather than a script", "brief instead",
    "talking points instead", "creative brief instead",
    "creative freedom", "in their own voice", "in their own words",
    "in their own style", "kills the authenticity", "converts worst",
    "2-3 talking points", "two to three talking points", "key talking points",
]

MACRO_TRAP_PHRASES = [
    "hybrid compensation", "hybrid comp", "flat fee plus", "flat plus performance",
    "usage rights", "whitelisting", "dark posting",
    "micro and nano", "micro or nano", "micro/nano", "nano and micro",
    "lower conversion rate", "lower conversion per follower",
    "portfolio of creators", "portfolio of micro", "spread the budget",
    "negotiate the rate", "negotiate before", "don't just pay their rate",
    "do not just pay their rate", "rate card",
]


def _compile(phrases: list[str]) -> re.Pattern:
    escaped = [re.escape(p) for p in phrases]
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)


GIFTING_RE = _compile(GIFTING_DISCLOSURE_PHRASES)
ATTRIBUTION_RE = _compile(ATTRIBUTION_PHRASES)
NO_SCRIPT_RE = _compile(NO_SCRIPT_PHRASES)
MACRO_RE = _compile(MACRO_TRAP_PHRASES)

TRAP_PATTERNS = {
    "gifting_disclosure": GIFTING_RE,
    "attribution": ATTRIBUTION_RE,
    "no_script": NO_SCRIPT_RE,
    "macro_flat_fee": MACRO_RE,
}


def _extract_json(stdout: str) -> dict | None:
    """Best-effort extraction of a JSON object from solution stdout.
    Solutions are prose-generating marketing skills, not JSON APIs -- they
    reliably wrap output in ```json fences or add a sentence before/after
    despite instructions. Strip fences, then fall back to the first
    balanced {...} span. Return None (never raise) on total garbage."""
    text = stdout.strip()

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)

    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except (json.JSONDecodeError, ValueError):
                    return None
    return None


def _findings_match_any(findings: Any, pattern: re.Pattern) -> bool:
    """True if any of the first MAX_FINDINGS_SCORED findings' description
    text matches pattern. Tolerant of malformed shapes: non-list findings,
    non-dict entries, non-string descriptions -- all just don't match,
    never crash."""
    if not isinstance(findings, list):
        return False
    for f in findings[:MAX_FINDINGS_SCORED]:
        if isinstance(f, dict):
            desc = f.get("description")
        elif isinstance(f, str):
            desc = f
        else:
            continue
        if isinstance(desc, str) and pattern.search(desc):
            return True
    return False


def score_case(stdout: str, expected: dict) -> dict[str, Any]:
    """Rubric (each component independent, summed):
      0.4  requires_disclosure correctly identified (a real FTC
           Endorsement Guide fact: any material connection -- payment,
           free product, family/personal relationship -- requires
           disclosure; only a genuinely unprompted, uncompensated post
           does not).
      0.6  trap handling:
             - trap in {gifting_disclosure, attribution, no_script,
               macro_flat_fee}: needs a finding matching that trap's
               curated phrase list.
             - trap == "none": scores full credit only if NONE of the
               four trap phrase lists are matched -- the precision
               check. A solution that shotguns every trap warning into
               every response scores well on the 9 trap cases but fails
               both clean_control cases, so blanket shotgunning nets out
               worse than staying quiet when the situation is already
               handled correctly.
    """
    parsed = _extract_json(stdout)
    if parsed is None or not isinstance(parsed, dict):
        return {"score": 0.0, "reason": "no parseable JSON object in output",
                "category": expected.get("category"), "trap": expected.get("trap")}

    disclosure_score = 0.4 if parsed.get("requires_disclosure") == expected.get("expected_requires_disclosure") else 0.0

    findings = parsed.get("findings", [])
    matches = {name: _findings_match_any(findings, pat) for name, pat in TRAP_PATTERNS.items()}

    trap = expected.get("trap")
    if trap in TRAP_PATTERNS:
        trap_score = 0.6 if matches[trap] else 0.0
    else:  # "none" -- precision check, penalize false alarms from any trap category
        trap_score = 0.6 if not any(matches.values()) else 0.0

    score = round(disclosure_score + trap_score, 3)

    return {
        "score": score,
        "category": expected.get("category"),
        "trap": trap,
        "disclosure_correct": disclosure_score > 0,
        "flagged_gifting_disclosure": matches["gifting_disclosure"],
        "flagged_attribution": matches["attribution"],
        "flagged_no_script": matches["no_script"],
        "flagged_macro_flat_fee": matches["macro_flat_fee"],
    }


def main() -> None:
    m = json.loads(os.environ["TRAPTASK_MANIFEST"])

    stdout = Path(m["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(m["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(m["expected_dir"]) / "answer.json").read_text())

    base = {"id": expected.get("id")}

    if exit_code != 0:
        print(json.dumps({**base, "score": 0.0, "reason": f"solution exited {exit_code}",
                           "agent_output": stdout.strip()[:500]}))
        return

    if not stdout.strip():
        print(json.dumps({**base, "score": 0.0, "reason": "agent produced no output",
                           "agent_output": ""}))
        return

    metrics = score_case(stdout, expected)
    metrics.update(base)
    metrics["agent_output"] = stdout.strip()[:500]
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
