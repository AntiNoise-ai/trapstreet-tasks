"""Per-case judge for the follow_instructions task.

Verifies that the model's output satisfies each declared IFEval-style constraint.
Constraint verifiers are implemented directly (subset of Google IFEval); each
case's answer.json lists the constraints to check.

Case scores 1.0 only if EVERY constraint passes. This is intentional — real
instruction-following in agent workflows is all-or-nothing (a JSON output with
one wrong field breaks the downstream parser).
"""
from __future__ import annotations

import json
import os
import re
import string
from pathlib import Path
from typing import Any


HEDGE_PHRASES = [
    "i cannot", "i can't", "i am unable", "i'm unable",
    "as an ai", "as a language model",
    "i don't know", "i do not know",
]


def normalise(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def word_count(s: str) -> int:
    return len(re.findall(r"\S+", s))


def sentence_count(s: str) -> int:
    # Split on . ! ? followed by whitespace or end
    parts = re.split(r"[.!?]+(?:\s|$)", s.strip())
    return len([p for p in parts if p.strip()])


def paragraph_count(s: str) -> int:
    # IFEval convention: paragraphs separated by ***
    if "***" in s:
        return len([p for p in s.split("***") if p.strip()])
    # Fallback: double newline
    return len([p for p in re.split(r"\n\s*\n", s.strip()) if p.strip()])


def relation_pass(actual: int, relation: str, target: int) -> bool:
    if relation == "at least":
        return actual >= target
    if relation == "at most":
        return actual <= target
    if relation in ("less than", "fewer than"):
        return actual < target
    if relation in ("more than", "greater than"):
        return actual > target
    return actual == target


# ─── Constraint verifiers ──────────────────────────────────────────────────

def v_no_comma(response: str, kw: dict) -> tuple[bool, str]:
    if "," in response:
        return False, "found comma in response"
    return True, "no comma"


def v_lowercase(response: str, kw: dict) -> tuple[bool, str]:
    if response != response.lower():
        return False, "response is not all lowercase"
    return True, "all lowercase"


def v_capital(response: str, kw: dict) -> tuple[bool, str]:
    if response != response.upper():
        return False, "response is not all uppercase"
    return True, "all uppercase"


def v_forbidden_words(response: str, kw: dict) -> tuple[bool, str]:
    forbidden = kw.get("forbidden_words", [])
    low = response.lower()
    hits = [w for w in forbidden if re.search(rf"\b{re.escape(w.lower())}\b", low)]
    if hits:
        return False, f"forbidden words present: {hits}"
    return True, f"no forbidden words (checked {forbidden})"


def v_existence(response: str, kw: dict) -> tuple[bool, str]:
    required = kw.get("keywords", [])
    low = response.lower()
    missing = [w for w in required if w.lower() not in low]
    if missing:
        return False, f"missing keywords: {missing}"
    return True, f"all keywords present ({required})"


def v_frequency(response: str, kw: dict) -> tuple[bool, str]:
    keyword = kw.get("keyword", "")
    relation = kw.get("relation", "at least")
    target = kw.get("frequency", 1)
    n = len(re.findall(rf"\b{re.escape(keyword)}\b", response, re.IGNORECASE))
    if relation_pass(n, relation, target):
        return True, f"'{keyword}' appears {n}x ({relation} {target})"
    return False, f"'{keyword}' appears {n}x, wanted {relation} {target}"


def v_letter_frequency(response: str, kw: dict) -> tuple[bool, str]:
    letter = kw.get("letter", "")
    relation = kw.get("let_relation", "at least")
    target = kw.get("let_frequency", 1)
    n = response.lower().count(letter.lower())
    if relation_pass(n, relation, target):
        return True, f"letter '{letter}' appears {n}x ({relation} {target})"
    return False, f"letter '{letter}' appears {n}x, wanted {relation} {target}"


def v_quotation(response: str, kw: dict) -> tuple[bool, str]:
    s = response.strip()
    if s.startswith('"') and s.endswith('"') and len(s) >= 2:
        return True, "wrapped in double quotes"
    return False, "response not wrapped in double quotes"


def v_end_checker(response: str, kw: dict) -> tuple[bool, str]:
    end_phrase = kw.get("end_phrase", "")
    if response.rstrip().endswith(end_phrase.rstrip()):
        return True, f"ends with '{end_phrase}'"
    return False, f"does not end with '{end_phrase}'"


def v_repeat_prompt(response: str, kw: dict) -> tuple[bool, str]:
    prompt_to_repeat = kw.get("prompt_to_repeat", "")
    # Response must start with the prompt exactly
    if response.strip().startswith(prompt_to_repeat.strip()):
        return True, "prompt repeated at start"
    return False, "prompt not repeated at start"


def v_two_responses(response: str, kw: dict) -> tuple[bool, str]:
    if "******" in response:
        parts = [p.strip() for p in response.split("******") if p.strip()]
        if len(parts) == 2:
            return True, "two responses separated by ******"
        return False, f"found {len(parts)} response parts, wanted 2"
    return False, "no '******' separator found"


def v_num_words(response: str, kw: dict) -> tuple[bool, str]:
    relation = kw.get("relation", "at least")
    target = kw.get("num_words", 0)
    n = word_count(response)
    if relation_pass(n, relation, target):
        return True, f"{n} words ({relation} {target})"
    return False, f"{n} words, wanted {relation} {target}"


def v_num_sentences(response: str, kw: dict) -> tuple[bool, str]:
    relation = kw.get("relation", "at least")
    target = kw.get("num_sentences", 0)
    n = sentence_count(response)
    if relation_pass(n, relation, target):
        return True, f"{n} sentences ({relation} {target})"
    return False, f"{n} sentences, wanted {relation} {target}"


def v_num_paragraphs(response: str, kw: dict) -> tuple[bool, str]:
    target = kw.get("num_paragraphs", 0)
    n = paragraph_count(response)
    if n == target:
        return True, f"{n} paragraphs"
    return False, f"{n} paragraphs, wanted exactly {target}"


def v_num_highlighted(response: str, kw: dict) -> tuple[bool, str]:
    target = kw.get("num_highlights", 0)
    # Count *text* and **text** patterns
    single = re.findall(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", response)
    double = re.findall(r"\*\*([^*\n]+?)\*\*", response)
    n = len(single) + len(double)
    if n >= target:
        return True, f"{n} highlighted sections (need ≥{target})"
    return False, f"{n} highlighted sections, wanted ≥{target}"


def v_num_bullets(response: str, kw: dict) -> tuple[bool, str]:
    target = kw.get("num_bullets", 0)
    # Count lines starting with * or -
    n = len(re.findall(r"^\s*[\*\-]\s+", response, re.MULTILINE))
    if n == target:
        return True, f"{n} bullet points"
    return False, f"{n} bullet points, wanted exactly {target}"


def v_title(response: str, kw: dict) -> tuple[bool, str]:
    if re.search(r"<<[^>]+>>", response):
        return True, "title in <<...>> found"
    return False, "no title in <<...>> format found"


def v_json_format(response: str, kw: dict) -> tuple[bool, str]:
    s = response.strip()
    # Strip markdown fences
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    try:
        json.loads(s)
        return True, "valid JSON"
    except json.JSONDecodeError as e:
        return False, f"not valid JSON: {e}"


def v_num_placeholders(response: str, kw: dict) -> tuple[bool, str]:
    target = kw.get("num_placeholders", 0)
    n = len(re.findall(r"\[[^\]]+\]", response))
    if n >= target:
        return True, f"{n} placeholders (need ≥{target})"
    return False, f"{n} placeholders, wanted ≥{target}"


def v_postscript(response: str, kw: dict) -> tuple[bool, str]:
    marker = kw.get("postscript_marker", "P.S.")
    if marker in response:
        return True, f"postscript marker '{marker}' present"
    return False, f"postscript marker '{marker}' not found"


CONSTRAINT_VERIFIERS = {
    "punctuation:no_comma": v_no_comma,
    "change_case:english_lowercase": v_lowercase,
    "change_case:english_capital": v_capital,
    "keywords:forbidden_words": v_forbidden_words,
    "keywords:existence": v_existence,
    "keywords:frequency": v_frequency,
    "keywords:letter_frequency": v_letter_frequency,
    "startend:quotation": v_quotation,
    "startend:end_checker": v_end_checker,
    "combination:repeat_prompt": v_repeat_prompt,
    "combination:two_responses": v_two_responses,
    "length_constraints:number_words": v_num_words,
    "length_constraints:number_sentences": v_num_sentences,
    "length_constraints:number_paragraphs": v_num_paragraphs,
    "detectable_format:number_highlighted_sections": v_num_highlighted,
    "detectable_format:number_bullet_lists": v_num_bullets,
    "detectable_format:title": v_title,
    "detectable_format:json_format": v_json_format,
    "detectable_content:number_placeholders": v_num_placeholders,
    "detectable_content:postscript": v_postscript,
}


# ─── Matchers used in answer.json ──────────────────────────────────────────

def m_ifeval_constraints(answer: str, spec: dict) -> tuple[bool, str]:
    """Run every declared constraint verifier. All must pass."""
    constraints = spec.get("constraints", [])
    results = []
    all_ok = True
    for c in constraints:
        cid = c.get("constraint_id")
        kwargs = c.get("kwargs", {}) or {}
        fn = CONSTRAINT_VERIFIERS.get(cid)
        if fn is None:
            results.append(f"{cid}: [UNSUPPORTED]")
            all_ok = False
            continue
        ok, reason = fn(answer, kwargs)
        results.append(f"{cid}: {'PASS' if ok else 'FAIL'} — {reason}")
        if not ok:
            all_ok = False
    return all_ok, " | ".join(results)


def m_no_hedge(answer: str, spec: dict) -> tuple[bool, str]:
    norm = answer.lower()
    for p in HEDGE_PHRASES:
        if p in norm:
            return False, f"hedge phrase detected: {p!r}"
    return True, "no hedge phrases"


MATCHERS = {
    "ifeval_constraints": m_ifeval_constraints,
    "no_hedge": m_no_hedge,
}


def run_matchers(answer: str, matchers: list[dict]) -> tuple[float, list[dict]]:
    results = []
    all_ok = True
    for spec in matchers:
        kind = spec.get("kind")
        fn = MATCHERS.get(kind)
        if fn is None:
            results.append({"kind": kind, "pass": False, "reason": f"unknown matcher: {kind!r}"})
            all_ok = False
            continue
        ok, reason = fn(answer, spec)
        results.append({"kind": kind, "pass": ok, "reason": reason})
        if not ok:
            all_ok = False
    return (1.0 if all_ok else 0.0), results


def extract_agent_answer(stdout: str) -> str:
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


def main() -> None:
    m = json.loads(os.environ["TRAPTASK_MANIFEST"])
    stdout = Path(m["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(m["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(m["expected_dir"]) / "answer.json").read_text())

    agent_answer = extract_agent_answer(stdout)

    if exit_code != 0:
        print(json.dumps({
            "score": 0.0,
            "reason": f"solution exited {exit_code}",
            "agent_answer": agent_answer,
            "id": expected.get("id"),
            "category": expected.get("difficulty"),
        }))
        return

    if not agent_answer:
        print(json.dumps({
            "score": 0.0,
            "reason": "agent produced no answer",
            "agent_answer": "",
            "id": expected.get("id"),
            "category": expected.get("difficulty"),
        }))
        return

    matchers = expected.get("matchers", [])
    score, matcher_results = run_matchers(agent_answer, matchers)
    print(json.dumps({
        "score": score,
        "matcher_results": matcher_results,
        "agent_answer_preview": agent_answer[:500],
        "id": expected.get("id"),
        "type": expected.get("type"),
        "category": expected.get("difficulty"),
        "difficulty": expected.get("difficulty"),
        "num_constraints": expected.get("num_constraints"),
    }))


if __name__ == "__main__":
    main()
