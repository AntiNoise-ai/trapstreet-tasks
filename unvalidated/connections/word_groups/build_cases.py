"""Generate inputs/<id>/question.txt and expected/<id>/answer.json from
gold.cases.json, validating authoring invariants first.

Run:  python3 build_cases.py
inputs/ and expected/ are GENERATED — never edit them by hand.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE / "gold.cases.json"

PROMPT_TEMPLATE = """You are playing Connections. Below are 16 words. Group them \
into EXACTLY 4 groups of EXACTLY 4 words each, where the words in each group \
share a hidden connection. Every word belongs to exactly one group. Some words \
look like they fit more than one group — only one grouping is correct.

Words:
{word_line}

Respond with ONLY a JSON object in this exact shape, and nothing else:
{{"groups": [{{"theme": "<short label>", "words": ["w", "w", "w", "w"]}}, {{"theme": "...", "words": ["...", "...", "...", "..."]}}, {{"theme": "...", "words": ["...", "...", "...", "..."]}}, {{"theme": "...", "words": ["...", "...", "...", "..."]}}]}}
"""


def validate_case(case: dict) -> None:
    cid = case.get("id", "<no id>")
    groups = case.get("groups", [])
    if len(groups) != 4:
        raise ValueError(f"{cid}: must have exactly 4 groups, got {len(groups)}")
    all_words: list[str] = []
    for g in groups:
        w = g.get("words", [])
        if len(w) != 4:
            raise ValueError(f"{cid}: group '{g.get('theme')}' must have 4 words, got {len(w)}")
        all_words.extend(x.strip().upper() for x in w)
    if len(set(all_words)) != 16:
        raise ValueError(f"{cid}: the 16 words must be distinct, got {len(set(all_words))} unique")
    traps = case.get("traps", [])
    if not traps:
        raise ValueError(f"{cid}: must declare at least one trap word")
    wordset = set(all_words)
    for t in traps:
        if t.strip().upper() not in wordset:
            raise ValueError(f"{cid}: trap '{t}' is not one of the 16 words")


def shuffled_words(case_id: str, words: list[str]) -> list[str]:
    """Deterministic per-case shuffle. random.Random seeded by the case id is
    stable across platforms (CPython seeds str via SHA-512)."""
    rng = random.Random(case_id)
    out = list(words)
    rng.shuffle(out)
    return out


def build() -> None:
    data = json.loads(GOLD.read_text())
    for case in data["cases"]:
        validate_case(case)
        cid = case["id"]
        words = [w.strip().upper() for g in case["groups"] for w in g["words"]]
        shuffled = shuffled_words(cid, words)

        in_dir = HERE / "inputs" / cid
        in_dir.mkdir(parents=True, exist_ok=True)
        (in_dir / "question.txt").write_text(
            PROMPT_TEMPLATE.format(word_line=", ".join(shuffled))
        )

        exp_dir = HERE / "expected" / cid
        exp_dir.mkdir(parents=True, exist_ok=True)
        answer = {
            "id": cid,
            "category": case["category"],
            "difficulty": case["category"],
            "groups": [
                {"theme": g["theme"], "tier": g["tier"],
                 "words": [w.strip().upper() for w in g["words"]]}
                for g in case["groups"]
            ],
            "traps": [t.strip().upper() for t in case["traps"]],
        }
        (exp_dir / "answer.json").write_text(json.dumps(answer, indent=2))
    print(f"Built {len(data['cases'])} cases.")


if __name__ == "__main__":
    build()
