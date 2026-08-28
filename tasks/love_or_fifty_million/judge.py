"""Per-case judge for the love_or_fifty_million task.

There is no correct choice. The gold in `expected/` decides one thing only:
whether the model committed. Both labels score 1.0; a hedge, a missing choice
or a missing reason scores 0.0. That is the whole scoring surface — see
docs/judge-metrics-contract.md, "Gradable = there is a file in expected/ that
decides it."

The metrics dict is also the board. `no_ranking` tasks render through
ProfileList (trapstreet-web/src/components/profile-list.tsx), which walks every
leaf of the merged metrics and gives each one a sortable column — for a
single-case task the merge is literally `{...grader_output, ...case_metrics[0]}`,
so whatever this file prints is what the page shows. Two columns are promised
(`choice`, `reason`), so everything else emitted here has to be a key that
ProfileList's SKIP_LEAVES already drops, or an array/dict it skips structurally.
`NON_RENDERED_KEYS` below mirrors that list; adding a plain scalar key that
isn't in it silently grows a third column on the public page.

`reason` carries the model's own one-liner, truncated — the string cell has no
line-clamp, so an untruncated answer stretches the column across the table.
The full text still travels, under `agent_answer`, which SKIP_LEAVES drops.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

# Fields a solution may report about itself in usage.json. `model` and
# `persona` are what let the board tell two runs of one commit apart.
USAGE_FIELDS = (
    "model",
    "persona",
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "usd_cost",
)

# Keys ProfileList never renders (SKIP_LEAVES, or arrays it skips structurally).
# Anything emitted outside this set becomes a visible column.
NON_RENDERED_KEYS = frozenset({
    "agent_answer",
    "id",
    "category",
    "difficulty",
    "matcher_results",
})

# Decoration a model wraps its answer in: markdown, quotes, brackets, and the
# trailing punctuation of a one-word line.
_DECORATION = "*`#_ \t\"'“”‘’「」『』《》【】()（）[]<>"
_TRAILING = "。．.,，:：;；!！?？、~-—–_ \t"


def _strip_decoration(line: str, prefixes: list[str]) -> str:
    """Reduce a line to its bare answer token, if that is all it is."""
    s = line.strip().strip(_DECORATION).strip()
    # "答案：爱情", "Choice: MONEY" — drop a leading label and its separator.
    for p in sorted(prefixes, key=len, reverse=True):
        m = re.match(rf"^{re.escape(p)}\s*[:：\-—]*\s*", s, flags=re.IGNORECASE)
        if m:
            s = s[m.end():]
            break
    return s.strip(_DECORATION).strip(_TRAILING).strip()


def _alias_map(choices: dict[str, list[str]]) -> dict[str, str]:
    """alias (lowercased) -> canonical board label."""
    return {a.lower(): label for label, aliases in choices.items() for a in aliases}


def _has_hedge(text: str, markers: list[str]) -> str | None:
    low = text.lower()
    for m in markers:
        if m.lower() in low:
            return m
    return None


def _loose_choice(text: str, choices: dict[str, list[str]]) -> tuple[str, str] | None:
    """A short line that carries a choice plus a few extra words.

    Single-character aliases ("a", "b") are exact-match only — as substrings
    they would fire on almost any English sentence.
    """
    low = text.lower()
    hits: list[tuple[int, str, str]] = []
    for label, aliases in choices.items():
        for a in aliases:
            if len(a) < 2:
                continue
            i = low.find(a.lower())
            if i >= 0:
                hits.append((i, label, a))
    if not hits:
        return None
    if len({label for _, label, _ in hits}) > 1:
        return None  # says both — not a commitment
    i, label, alias = min(hits)
    # Strip the separator that led into the reason ("爱情 —— ..."), but leave
    # the reason's own end punctuation alone — it is a sentence, not a token.
    remainder = (text[:i] + text[i + len(alias):]).strip(_DECORATION).lstrip(_TRAILING).strip()
    return label, remainder


def classify(stdout: str, expected: dict[str, Any]) -> dict[str, Any]:
    """Decide the choice and pull out the model's reason."""
    choices = expected["choices"]
    aliases = _alias_map(choices)
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    checks: list[dict[str, Any]] = []

    if not lines:
        checks.append({"check": "committed", "pass": False, "reason": "empty output"})
        return {"choice": None, "reason": "", "matcher_results": checks}

    head = _strip_decoration(lines[0], expected["prefix_strips"])
    rest = lines[1:]

    # Tier A — line 1 is nothing but the answer.
    label = aliases.get(head.lower())
    inline_reason = ""

    # Tier B — line 1 is short, unhedged, and carries exactly one choice.
    if label is None:
        hedge = _has_hedge(head, expected["hedge_markers"])
        if hedge:
            checks.append({"check": "committed", "pass": False, "reason": f"hedge marker: {hedge}"})
            return {"choice": None, "reason": "", "matcher_results": checks}
        if len(head) <= expected["loose_first_line_max_chars"]:
            loose = _loose_choice(head, choices)
            if loose:
                label, inline_reason = loose

    if label is None:
        hedge = _has_hedge(stdout, expected["hedge_markers"])
        checks.append({
            "check": "committed",
            "pass": False,
            "reason": f"hedge marker: {hedge}" if hedge else "no choice on line 1",
        })
        return {"choice": None, "reason": "", "matcher_results": checks}

    reason = inline_reason or (rest[0].strip().strip(_DECORATION).strip() if rest else "")

    # A model can fill the slot and decline in the same breath — line 1 reads
    # `5000万`, line 2 reads "this involves real people, I can't continue".
    # Scoring that as a choice puts words in its mouth on a public board. The
    # marker list here is deliberately narrower than the one used on line 1:
    # line 1 is a slot, so any waffle there disqualifies it, but a genuine
    # reason may well say "there is no right answer, but I'd keep the money".
    # Only a first-person refusal counts.
    refusal = _has_hedge(reason, expected.get("reason_refusal_markers", []))
    if refusal:
        checks.append({
            "check": "committed",
            "pass": False,
            "reason": f"picked {label}, then declined in the reason: {refusal}",
        })
        return {"choice": None, "reason": "", "matcher_results": checks}

    checks.append({"check": "committed", "pass": True, "reason": label})
    return {"choice": label, "reason": reason, "matcher_results": checks}


def judge_case(stdout: str, expected: dict[str, Any]) -> dict[str, Any]:
    verdict = classify(stdout, expected)
    checks = verdict["matcher_results"]
    choice = verdict["choice"]
    reason = verdict["reason"]

    if choice is None:
        return {
            "score": 0.0,
            "choice": expected["refused_label"],
            "reason": expected["refused_display"],
            "matcher_results": checks,
            "agent_answer": stdout.strip()[:600],
        }

    # A bare label answers half the question. The choice still shows on the
    # board — it is the interesting datum — but the case does not pass.
    bare = reason.strip(_TRAILING).strip(_DECORATION).strip()
    if len(bare) < expected["min_reason_chars"]:
        checks.append({"check": "gave_reason", "pass": False, "reason": "no_reason"})
        return {
            "score": 0.0,
            "choice": choice,
            "reason": expected["no_reason_display"],
            "matcher_results": checks,
            "agent_answer": stdout.strip()[:600],
        }

    checks.append({"check": "gave_reason", "pass": True, "reason": f"{len(bare)} chars"})
    cap = expected["reason_display_chars"]
    display = reason if len(reason) <= cap else reason[:cap] + "…"
    return {
        "score": 1.0,
        "choice": choice,
        "reason": display,
        "matcher_results": checks,
        "agent_answer": stdout.strip()[:600],
    }


def main() -> None:
    manifest = json.loads(os.environ["TRAPTASK_MANIFEST"])

    stdout = Path(manifest["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(manifest["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(manifest["expected_dir"]) / "answer.json").read_text())

    usage_record: dict[str, Any] = {}
    usage_path = Path(manifest["outputs_dir"]) / "usage.json"
    if usage_path.exists():
        try:
            raw_usage = json.loads(usage_path.read_text())
        except json.JSONDecodeError:
            raw_usage = {}
        if isinstance(raw_usage, dict):
            usage_record = {k: v for k, v in raw_usage.items() if k in USAGE_FIELDS}

    if exit_code != 0:
        metrics: dict[str, Any] = {
            "score": 0.0,
            "choice": expected["refused_label"],
            "reason": expected["refused_display"],
            "matcher_results": [
                {"check": "committed", "pass": False, "reason": f"solution exited {exit_code}"}
            ],
            "agent_answer": stdout.strip()[:600],
        }
    else:
        metrics = judge_case(stdout, expected)

    metrics["id"] = expected.get("id")
    metrics["category"] = expected.get("category")
    metrics["difficulty"] = expected.get("difficulty")
    metrics.update(usage_record)
    print(json.dumps(metrics, ensure_ascii=False))


if __name__ == "__main__":
    main()
