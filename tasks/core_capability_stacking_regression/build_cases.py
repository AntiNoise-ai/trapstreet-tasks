"""Generate inputs/<id>/prompt.txt and expected/<id>/answer.json from
gold.cases.json, composed against catalog.json + scenarios.json, validating
authoring invariants first.

Run:  python3 build_cases.py
inputs/ and expected/ are GENERATED -- never edit them by hand.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE / "gold.cases.json"
CATALOG = HERE / "catalog.json"
SCENARIOS = HERE / "scenarios.json"

# L4 carries the same three packs as L3 plus the shared bulk filler, so it
# raises catalog size without changing how many competitors a scenario faces.
LEVEL_PACKS = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 3}
CURVE_LEVELS = ["L0", "L1", "L2", "L3"]
BULK_LEVELS = {"L4"}
ARM_KEY = {"high": "high_overlap_packs", "low": "low_overlap_packs"}
DIFFICULTIES = ("easy", "medium", "hard", "edge")
PRIMARY_TIERS = ("medium", "hard")

_catalog = json.loads(CATALOG.read_text())
_scenarios = {s["id"]: s for s in json.loads(SCENARIOS.read_text())["scenarios"]}
_filler = json.loads((HERE / "filler_pool.json").read_text())["tools"]
_base_by_name = {t["name"]: t for t in _catalog["base"]}


def arm_packs(arm: str) -> list[list[dict]]:
    return _catalog[ARM_KEY[arm]]


def assert_arm_parity() -> None:
    """Both arms must add the same NUMBER of skills at every level.

    This is the control the whole comparison rests on. If the high-overlap arm
    were also the larger arm, any gap between them would be catalog size --
    the axis core_tool_selection_at_scale already tested to 300 tools and found
    inert -- wearing overlap's clothes.
    """
    high, low = arm_packs("high"), arm_packs("low")
    if len(high) != len(low):
        raise ValueError(f"arm pack counts differ: high={len(high)}, low={len(low)}")
    for i, (h, l) in enumerate(zip(high, low), start=1):
        if len(h) != len(l):
            raise ValueError(
                f"pack {i} size differs between arms: high={len(h)}, low={len(l)} -- "
                "an unequal arm makes any measured gap uninterpretable"
            )


def competitor_dose(scenario_id: str, case: dict) -> int:
    """How many skills competing with THIS scenario are in this case's catalog.

    The stack level counts packs added; it is not the same thing as how much
    overlap the scenario is actually under, because a pack is a fixed set of
    skills and not every skill in it competes with every scenario.
    """
    if case["overlap_class"] != "high":
        return 0
    n_packs = LEVEL_PACKS[case["stack_level"]]
    return sum(
        1
        for pack in arm_packs("high")[:n_packs]
        for entry in pack
        if scenario_id in entry.get("targets", [])
    )


def assert_dose_is_monotone() -> None:
    """Every scenario must gain at least one new competitor at every level.

    A pack that happens to add no competitor for some scenario makes that
    scenario's segment of the degradation curve flat BY CONSTRUCTION. Averaged
    into `curve_high_overlap`, that reads as a plateau in the curve -- and the
    curve's shape is exactly what the pre-registered linear-vs-inflection call
    is made from. This was a real defect in the first build: pack 2 carried no
    competitor for s05 at all.
    """
    for sid in _scenarios:
        doses = []
        if _scenarios[sid].get("difficulty") not in PRIMARY_TIERS:
            continue  # only the tiers carrying the primary test need a clean ladder
        for level in CURVE_LEVELS:
            doses.append(competitor_dose(sid, {"stack_level": level, "overlap_class": "high"}))
        gains = [b - a for a, b in zip(doses, doses[1:])]
        if any(g <= 0 for g in gains):
            raise ValueError(
                f"{sid}: competitor dose {doses} does not strictly increase at every level "
                f"(gains {gains}) -- a level that adds no competitor for this scenario would "
                "flatten its curve by construction, not by measurement"
            )


def assert_targets_are_real() -> None:
    for i, pack in enumerate(_catalog["high_overlap_packs"], start=1):
        for entry in pack:
            name = entry["tool"]["name"]
            targets = entry.get("targets")
            if not targets:
                raise ValueError(f"pack {i}/{name}: no targets declared")
            for t in targets:
                if t not in _scenarios:
                    raise ValueError(f"pack {i}/{name}: unknown target {t!r}")

            if entry.get("kind") == "instruction_bleed":
                if "competes_with" in entry:
                    raise ValueError(
                        f"pack {i}/{name}: an instruction-bleed skill adds work rather than "
                        "replacing any, so it can have no competes_with -- declaring one would "
                        "fabricate an interfering pair"
                    )
                continue

            base = entry.get("competes_with")
            if base not in _base_by_name:
                raise ValueError(f"pack {i}/{name}: competes_with {base!r} is not a base skill")
            for t in targets:
                uses = {c["name"] for c in _scenarios[t]["required_calls"]}
                if base in uses:
                    continue
                # One legitimate exception, and stating it here is what keeps the
                # edge design explicit: an edge scenario tempts a call that should
                # NOT be made at all, so the competitor is not standing in for a
                # required call -- there is nothing for it to displace.
                if _scenarios[t]["difficulty"] == "edge":
                    continue
                raise ValueError(
                    f"pack {i}/{name}: targets {t}, which never calls {base}. Only an edge "
                    "scenario may be tempted by a competitor whose base skill it does not use"
                )


def assert_no_answer_leak(scenario: dict) -> None:
    """The request must never name a tool that is part of its own answer.

    A request reading 'create a draft email' hands over `mail_create_draft`
    without the model having to discriminate against mail_send_message,
    mail_schedule_send or mail_create_template at all -- the case would score
    the prompt rather than the catalog.
    """
    text = scenario["request"].lower()
    for call in scenario["required_calls"]:
        name = call["name"].lower()
        if name in text:
            raise ValueError(f"{scenario['id']}: request contains the tool name {name!r}")
        # also catch the name spelled with spaces, e.g. "create draft"
        spaced = name.replace("_", " ")
        if spaced in text:
            raise ValueError(f"{scenario['id']}: request contains {spaced!r}, which names the answer")


def compose_catalog(case: dict) -> list[dict]:
    """base + the first N packs of the case's arm, deterministically shuffled.

    The shuffle is seeded on (scenario, stack_level) and NOT on the arm, so at
    a matched level the two arms draw the same permutation. Because both arms
    are the same length and the base skills occupy the same pre-shuffle
    indices, every base skill lands at an identical position in both arms --
    so position cannot differ between the arms being compared. Without this,
    'where the right skill sat' would vary with the thing under test.
    """
    # Build the FULL catalog order once per (scenario, arm), then take the
    # subsequence belonging to this level. A skill therefore keeps its
    # neighbours as levels grow -- new ones are interleaved around it, nothing
    # is rearranged.
    #
    # The earlier scheme reshuffled everything at each level, which left the
    # level axis confounded with position: the same skill sat at index 9 at L1,
    # index 1 at L2 and index 14 at L3. Position was controlled BETWEEN the arms
    # and uncontrolled ACROSS levels, so a dose-response curve could not be read
    # cleanly. The seed still omits the arm, so the two arms keep identical base
    # positions at every level.
    def slot(seed: str) -> str:
        return hashlib.md5(f"{case['scenario']}:{seed}".encode()).hexdigest()

    arm = case["overlap_class"]
    # (sort key, tool). A base skill and a filler key off their own name. An
    # ADDED skill keys off its slot -- pack index and position within the pack --
    # never its name, so the k-th skill of pack i lands at the same place in
    # both arms. That is what keeps base positions identical between the arms
    # being compared, which name-derived keys would have broken.
    tools = [(slot(t["name"]), dict(t)) for t in _catalog["base"]]
    n_packs = LEVEL_PACKS[case["stack_level"]]
    if arm != "none" and n_packs:
        for i, pack in enumerate(arm_packs(arm)[:n_packs], start=1):
            tools.extend((slot(f"pack{i}#{k}"), dict(e["tool"])) for k, e in enumerate(pack))
    if case["stack_level"] in BULK_LEVELS:
        tools.extend((slot(t["name"]), dict(t)) for t in _filler)

    # Order by a stable per-(scenario, tool) key rather than by shuffling the
    # assembled list. A shuffle's permutation depends on the list's LENGTH, so
    # the same seed reordered the base skills differently at every level -- the
    # level axis ended up confounded with position, and a dose-response curve
    # could not be read off it. Sorting on a content-derived key means adding
    # skills only ever interleaves new items between existing ones; every skill
    # already present keeps its neighbours. The key ignores the arm, so both
    # arms still place the base skills identically at every level.
    return [t for _, t in sorted(tools, key=lambda kt: kt[0])]


def names_of_kind(case: dict, kind: str) -> list[str]:
    """Names of added skills of a given competitor kind, for judge diagnostics."""
    n_packs = LEVEL_PACKS[case["stack_level"]]
    if not n_packs or case["overlap_class"] != "high":
        return []
    return [entry["tool"]["name"]
            for pack in arm_packs("high")[:n_packs]
            for entry in pack
            if entry.get("kind") == kind]


def bleed_strengths(case: dict) -> dict[str, str]:
    """name -> blunt/medium/subtle, so a run reports WHICH wording bled.

    The v2 probe fired on one bluntness, which establishes that the effect
    exists and nothing about where it stops. Carrying strength through to the
    judge turns that into a property of the catalog rather than another
    dimension of the grid.
    """
    n_packs = LEVEL_PACKS[case["stack_level"]]
    if not n_packs or case["overlap_class"] != "high":
        return {}
    return {entry["tool"]["name"]: entry["strength"]
            for pack in arm_packs("high")[:n_packs]
            for entry in pack
            if entry.get("kind") == "instruction_bleed"}


def added_names(case: dict) -> list[str]:
    n_packs = LEVEL_PACKS[case["stack_level"]]
    if not n_packs:
        return []
    out = []
    for pack in arm_packs(case["overlap_class"])[:n_packs]:
        out.extend(entry["tool"]["name"] for entry in pack)
    return out


def validate_case(case: dict) -> None:
    """Fail loudly on authoring mistakes."""
    for field in ("id", "scenario", "stack_level", "overlap_class"):
        if field not in case:
            raise ValueError(f"case missing field {field!r}: {case}")

    if case["stack_level"] not in LEVEL_PACKS:
        raise ValueError(f"{case['id']}: unknown stack_level {case['stack_level']!r}")
    if case["overlap_class"] not in ("none", "high", "low"):
        raise ValueError(f"{case['id']}: unknown overlap_class {case['overlap_class']!r}")

    is_l0 = case["stack_level"] == "L0"
    if is_l0 != (case["overlap_class"] == "none"):
        raise ValueError(
            f"{case['id']}: L0 is the shared baseline and must carry overlap_class 'none'; "
            f"every other level must carry a real arm (got {case['stack_level']}/{case['overlap_class']})"
        )

    sc = _scenarios.get(case["scenario"])
    if sc is None:
        raise ValueError(f"{case['id']}: unknown scenario {case['scenario']!r}")

    if sc.get("difficulty") not in DIFFICULTIES:
        raise ValueError(
            f"{sc['id']}: difficulty {sc.get('difficulty')!r} is not one of {DIFFICULTIES} -- "
            "the tier decides whether this scenario can enter the primary test, so it cannot "
            "be left implicit"
        )

    assert_no_answer_leak(sc)

    if not 2 <= len(sc["required_calls"]) <= 4:
        raise ValueError(
            f"{sc['id']}: {len(sc['required_calls'])} required calls; scenarios are 2-4 calls "
            "-- a single-call scenario is core_tool_selection_at_scale's shape, not this one"
        )

    seen_calls = set()
    for call in sc["required_calls"]:
        tool = _base_by_name.get(call["name"])
        if tool is None:
            raise ValueError(
                f"{sc['id']}: required call {call['name']!r} is not in the base catalog -- "
                "stacking must never remove the right answer, so every correct tool lives in base"
            )
        if call["name"] in seen_calls:
            raise ValueError(f"{sc['id']}: duplicate required call {call['name']!r}")
        seen_calls.add(call["name"])

        required = set(tool["parameters"].get("required", []))
        for arg in call["expected_args"]:
            if arg not in required:
                raise ValueError(
                    f"{sc['id']}/{call['name']}: expected arg {arg!r} is not marked required in "
                    "the tool's own schema -- the judge would be penalising an omission the "
                    "schema never asked for"
                )
        overlap = set(call.get("unchecked_required", [])) & set(call["expected_args"])
        if overlap:
            raise ValueError(f"{sc['id']}/{call['name']}: {overlap} listed as both checked and unchecked")
        declared = set(call["expected_args"]) | set(call.get("unchecked_required", []))
        if declared != required:
            raise ValueError(
                f"{sc['id']}/{call['name']}: checked+unchecked args {sorted(declared)} do not "
                f"account for the schema's required args {sorted(required)} -- every required "
                "arg must be either verified or explicitly recorded as unverified"
            )


def render_prompt(case: dict, tools: list[dict], scenario: dict) -> str:
    schemas = [{k: v for k, v in t.items() if k != "instructions"} for t in tools]
    guidance = [t for t in tools if t.get("instructions")]

    # House rules are identical in both arms at every level. They are where the
    # disqualifying knowledge lives for the redundant-backend competitors --
    # which is where it lives in practice, since no schema tells you which of
    # two working backends your organisation actually uses.
    rules = "\n".join(f"- {r}" for r in _catalog.get("house_rules", []))

    # Skill guidance is surfaced separately from schemas, the way a skills
    # runtime injects it. Both arms carry the same NUMBER of instruction-bearing
    # skills, so this block cannot make one arm's prompt longer than the other's.
    guide_block = ""
    if guidance:
        lines = "\n".join(f"- {t['name']}: {t['instructions']}" for t in guidance)
        guide_block = f"Some of the installed skills publish their own guidance:\n\n{lines}\n\n"

    return (
        f"How things are done here:\n\n{rules}\n\n"
        "You are an assistant with the following skills installed. Each is given as a "
        "JSON schema.\n\n"
        f"{json.dumps(schemas, indent=2)}\n\n"
        f"{guide_block}"
        "Request:\n"
        f"{scenario['request']}\n\n"
        "Emit the tool calls needed to carry out this request, as a JSON array:\n"
        '[{"name": "<tool_name>", "arguments": {"<arg>": <value>}}]\n\n'
        "Output only the JSON array, nothing else. The order of the calls is not scored. "
        "Every call you emit is scored: a call that the request did not need counts against "
        "you, so do not list extra skills speculatively.\n"
    )


def build() -> None:
    assert_arm_parity()
    assert_targets_are_real()
    assert_dose_is_monotone()

    data = json.loads(GOLD.read_text())
    seen_ids: set[str] = set()
    for case in data["cases"]:
        validate_case(case)
        cid = case["id"]
        if cid in seen_ids:
            raise ValueError(f"duplicate case id: {cid}")
        seen_ids.add(cid)

        sc = _scenarios[case["scenario"]]
        tools = compose_catalog(case)

        in_dir = HERE / "inputs" / cid
        in_dir.mkdir(parents=True, exist_ok=True)
        (in_dir / "prompt.txt").write_text(render_prompt(case, tools, sc))

        exp_dir = HERE / "expected" / cid
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "answer.json").write_text(json.dumps({
            "scenario": case["scenario"],
            "difficulty": sc["difficulty"],
            "stack_level": case["stack_level"],
            "overlap_class": case["overlap_class"],
            "n_skills": len(tools),
            "n_competitors": competitor_dose(case["scenario"], case),
            "required_calls": [
                {"name": c["name"], "expected_args": c["expected_args"]}
                for c in sc["required_calls"]
            ],
            "added_names": added_names(case),
            "bleed_names": names_of_kind(case, "instruction_bleed"),
            "bleed_strength": bleed_strengths(case),
            "competes_with": {
                entry["tool"]["name"]: entry["competes_with"]
                for pack in arm_packs("high")[:LEVEL_PACKS[case["stack_level"]]]
                for entry in pack
                if entry.get("competes_with")
            } if case["overlap_class"] == "high" else {},
            "backend_names": names_of_kind(case, "redundant_backend"),
            "base_names": [t["name"] for t in _catalog["base"]],
        }, indent=2) + "\n")

    print(f"Built {len(data['cases'])} cases.")


if __name__ == "__main__":
    build()
