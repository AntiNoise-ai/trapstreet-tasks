"""Tests for build_cases.py's validation and for the invariants the whole
comparison rests on.

The count/position parity checks here are not decoration: if the high-overlap
arm were also the larger arm, or if the right skill sat in a different place in
the two arms, any gap between them would be catalog size or position wearing
overlap's clothes -- and catalog size is the axis
core_tool_selection_at_scale already tested to 300 tools and found inert.
"""
from __future__ import annotations

import copy
import json
from collections import Counter
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import build_cases as bc  # noqa: E402

GRID = {c["id"]: c for c in json.loads((HERE / "gold.cases.json").read_text())["cases"]}
CATALOG = json.loads((HERE / "catalog.json").read_text())
SCENARIOS = {s["id"]: s for s in json.loads((HERE / "scenarios.json").read_text())["scenarios"]}
BASE_NAMES = [t["name"] for t in CATALOG["base"]]


def catalog_names(case_id: str) -> list[str]:
    """The prompt now carries a house-rules block before the schemas and a
    skill-guidance block after them, so the array is decoded in place rather
    than sliced between fixed markers."""
    txt = (HERE / "inputs" / case_id / "prompt.txt").read_text()
    start = txt.index("[", txt.index("JSON schema."))
    tools, _ = json.JSONDecoder().raw_decode(txt[start:])
    return [t["name"] for t in tools]


def case_for(scenario: str, level: str, arm: str) -> str:
    return next(
        cid for cid, c in GRID.items()
        if c["scenario"] == scenario and c["stack_level"] == level and c["overlap_class"] == arm
    )


# --- the controls --------------------------------------------------------

def test_arm_sizes_are_equal_at_every_level():
    """Both arms add the same NUMBER of skills; only their overlap differs."""
    sizes = {}
    for cid, c in GRID.items():
        sizes.setdefault((c["stack_level"], c["overlap_class"]), set()).add(len(catalog_names(cid)))
    for key, vals in sizes.items():
        assert len(vals) == 1, f"{key} has inconsistent catalog sizes: {vals}"
    for level in ("L1", "L2", "L3", "L4"):
        assert sizes[(level, "high")] == sizes[(level, "low")], (
            f"arm sizes differ at {level} -- the comparison would be measuring bulk"
        )


def test_stacking_is_monotone_and_nested():
    """L1 subset of L2 subset of L3 within an arm: growing the stack means the
    same skills plus more, never a different catalog."""
    for scenario in SCENARIOS:
        for arm in ("high", "low"):
            n1 = set(catalog_names(case_for(scenario, "L1", arm)))
            n2 = set(catalog_names(case_for(scenario, "L2", arm)))
            n3 = set(catalog_names(case_for(scenario, "L3", arm)))
            assert n1 < n2 < n3, f"{scenario}/{arm} packs are not nested"


def test_base_skills_sit_at_identical_positions_in_both_arms():
    for scenario in SCENARIOS:
        for level in ("L1", "L2", "L3", "L4"):
            hi = {n: i for i, n in enumerate(catalog_names(case_for(scenario, level, "high"))) if n in BASE_NAMES}
            lo = {n: i for i, n in enumerate(catalog_names(case_for(scenario, level, "low"))) if n in BASE_NAMES}
            assert hi == lo, f"{scenario}/{level}: base skill positions differ between arms"


def test_every_correct_tool_is_present_at_every_level():
    """Stacking never removes the right answer -- it only adds neighbours."""
    for cid, c in GRID.items():
        present = set(catalog_names(cid))
        for call in SCENARIOS[c["scenario"]]["required_calls"]:
            assert call["name"] in present, f"{cid}: correct tool {call['name']} missing"


def test_added_packs_never_contain_a_correct_answer():
    added = {e["tool"]["name"] for p in CATALOG["high_overlap_packs"] + CATALOG["low_overlap_packs"] for e in p}
    required = {c["name"] for s in SCENARIOS.values() for c in s["required_calls"]}
    assert not (added & required)
    assert not (added & set(BASE_NAMES)), "an added skill shadows a base skill by name"


def test_inputs_never_carry_the_answer():
    """expected/ is judge-only. A prompt that named the right tools, or shipped
    the answer file's content, would hand the case over."""
    for cid, c in GRID.items():
        prompt = (HERE / "inputs" / cid / "prompt.txt").read_text().lower()
        assert "expected_args" not in prompt
        assert "required_calls" not in prompt
        request = SCENARIOS[c["scenario"]]["request"].lower()
        for call in SCENARIOS[c["scenario"]]["required_calls"]:
            assert call["name"].lower() not in request


def test_anti_shotgun_rule_is_stated_in_the_prompt():
    """A scoring rule the solution was never told about is a hidden gotcha."""
    prompt = (HERE / "inputs" / "case_01" / "prompt.txt").read_text()
    assert "counts against you" in prompt


# --- validation fires on authoring mistakes ------------------------------

def test_unequal_arms_are_rejected():
    original = CATALOG["high_overlap_packs"]
    bc._catalog["high_overlap_packs"] = [original[0][:-1]] + original[1:]
    try:
        with pytest.raises(ValueError, match="pack 1 size differs"):
            bc.assert_arm_parity()
    finally:
        bc._catalog["high_overlap_packs"] = original


def test_answer_leak_in_request_is_rejected():
    sc = copy.deepcopy(SCENARIOS["s04"])
    sc["request"] = "Please storage_copy_object the forecast into /finance and tell #finance."
    with pytest.raises(ValueError, match="contains the tool name"):
        bc.assert_no_answer_leak(sc)


def test_spaced_tool_name_in_request_is_also_rejected():
    sc = copy.deepcopy(SCENARIOS["s04"])
    sc["request"] = "Use chat post message to tell #finance, and copy the file into /finance."
    with pytest.raises(ValueError, match="names the answer"):
        bc.assert_no_answer_leak(sc)


def test_expected_arg_must_be_required_by_the_schema():
    bc._scenarios["_tmp"] = {
        "id": "_tmp",
        "difficulty": "medium",
        "request": "Log the lunch and tell the channel.",
        "required_calls": [
            {"name": "sheets_append_row", "expected_args": {"sheet": ["x"]}, "unchecked_required": ["values"]},
            # destination_folder is not in chat_post_message's required list
            {"name": "chat_post_message", "expected_args": {"channel": ["#x"], "destination_folder": ["y"]},
             "unchecked_required": ["text"]},
        ],
    }
    try:
        with pytest.raises(ValueError, match="not marked required"):
            bc.validate_case({"id": "case_xx", "scenario": "_tmp", "stack_level": "L0", "overlap_class": "none"})
    finally:
        del bc._scenarios["_tmp"]


def test_unaccounted_required_arg_is_rejected():
    """Every required arg must be either verified or explicitly recorded as
    unverified -- silence about one is how a scoring looseness goes unnoticed."""
    bc._scenarios["_tmp"] = {
        "id": "_tmp",
        "difficulty": "medium",
        "request": "Book it and log it.",
        "required_calls": [
            {"name": "sheets_append_row", "expected_args": {"sheet": ["x"]}, "unchecked_required": []},
            {"name": "chat_post_message", "expected_args": {"channel": ["#x"]}, "unchecked_required": ["text"]},
        ],
    }
    try:
        with pytest.raises(ValueError, match="do not account for"):
            bc.validate_case({"id": "case_xx", "scenario": "_tmp", "stack_level": "L0", "overlap_class": "none"})
    finally:
        del bc._scenarios["_tmp"]


def test_l0_must_be_the_shared_baseline():
    with pytest.raises(ValueError, match="shared baseline"):
        bc.validate_case({"id": "case_xx", "scenario": "s01", "stack_level": "L0", "overlap_class": "high"})
    with pytest.raises(ValueError, match="shared baseline"):
        bc.validate_case({"id": "case_xx", "scenario": "s01", "stack_level": "L3", "overlap_class": "none"})


def test_grid_is_complete_and_ids_are_opaque():
    assert len(GRID) == len(SCENARIOS) * 9
    for cid, c in GRID.items():
        assert cid.startswith("case_")
        assert c["scenario"] not in cid and c["stack_level"] not in cid


# --- competitor dose: the axis the curve is actually made of -------------

def test_every_scenario_gains_a_competitor_at_every_level():
    """A pack that adds no competitor for a scenario flattens that scenario's
    segment of the curve BY CONSTRUCTION. Pack 2 originally carried none for
    s05; this is the assertion that would have caught it."""
    bc.assert_dose_is_monotone()


def test_dose_assertion_actually_fires():
    original = bc._catalog["high_overlap_packs"]
    stripped = [[{**e, "targets": [t for t in e["targets"] if t != "s04"]} for e in p]
                for p in original]
    bc._catalog["high_overlap_packs"] = stripped
    try:
        with pytest.raises(ValueError, match="does not strictly increase"):
            bc.assert_dose_is_monotone()
    finally:
        bc._catalog["high_overlap_packs"] = original


def test_every_high_overlap_skill_declares_real_targets():
    bc.assert_targets_are_real()
    for pack in CATALOG["high_overlap_packs"]:
        for entry in pack:
            assert entry["targets"], entry["tool"]["name"]
            assert set(entry["targets"]) <= set(SCENARIOS)


def test_low_overlap_arm_carries_zero_dose():
    """If a 'distant' skill were actually a competitor, the control arm would
    be treating the case too, and the comparison would understate the effect."""
    for cid, c in GRID.items():
        exp = json.loads((HERE / "expected" / cid / "answer.json").read_text())
        if c["overlap_class"] != "high":
            assert exp["n_competitors"] == 0, cid
        else:
            assert exp["n_competitors"] > 0, cid


def test_filler_never_collides_with_a_base_or_pack_skill():
    filler = json.loads((HERE / "filler_pool.json").read_text())["tools"]
    names = {t["name"] for t in filler}
    packs = {e["tool"]["name"] for p in CATALOG["high_overlap_packs"] + CATALOG["low_overlap_packs"] for e in p}
    assert not (names & set(BASE_NAMES))
    assert not (names & packs)
    assert len(names) == len(filler), "duplicate filler name"


def test_l4_adds_bulk_without_adding_competitors():
    """L4 answers 'is 26 skills even a stack'. If it also moved the overlap
    dose, a bulk effect could be read as an overlap inflection."""
    for scenario in SCENARIOS:
        l3 = json.loads((HERE / "expected" / case_for(scenario, "L3", "high") / "answer.json").read_text())
        l4 = json.loads((HERE / "expected" / case_for(scenario, "L4", "high") / "answer.json").read_text())
        assert l4["n_skills"] > l3["n_skills"] + 90
        assert l4["n_competitors"] == l3["n_competitors"]


def test_every_scenario_declares_a_difficulty_tier():
    for sid, sc in SCENARIOS.items():
        assert sc["difficulty"] in bc.DIFFICULTIES, sid
    tiers = {sid: sc["difficulty"] for sid, sc in SCENARIOS.items()}
    assert any(t in bc.PRIMARY_TIERS for t in tiers.values()), "no scenario can carry the primary test"


# --- mechanisms the first version could not express ----------------------

def test_house_rules_appear_in_every_prompt_and_name_no_tool():
    """House rules carry the disqualifier for the redundant-backend
    competitors. If they named a tool they would telegraph the answer; if they
    varied between arms they would be a confound."""
    all_names = set(BASE_NAMES) | {
        e["tool"]["name"] for p in CATALOG["high_overlap_packs"] + CATALOG["low_overlap_packs"] for e in p
    }
    seen = set()
    for cid in GRID:
        txt = (HERE / "inputs" / cid / "prompt.txt").read_text()
        assert "How things are done here" in txt, cid
        block = txt[: txt.index("You are an assistant")]
        seen.add(block)
        for n in all_names:
            assert n not in block, f"{cid}: house rules name the tool {n}"
    assert len(seen) == 1, "house rules must be identical in every case"


def test_both_arms_carry_the_same_number_of_instruction_bearing_skills():
    """The guidance block is the treatment in the high arm. If only that arm
    had one, its prompt would also be longer, and a bulk difference would
    masquerade as instruction interference."""
    hi = sum(1 for p in CATALOG["high_overlap_packs"] for e in p if e["tool"].get("instructions"))
    lo = sum(1 for p in CATALOG["low_overlap_packs"] for e in p if e["tool"].get("instructions"))
    assert hi == lo > 0


def test_instruction_bleed_and_backend_skills_exist_only_in_the_high_arm():
    for cid, c in GRID.items():
        exp = json.loads((HERE / "expected" / cid / "answer.json").read_text())
        high = c["overlap_class"] == "high"
        # bleeding skills start at L1 so the mechanism's dose rises with level;
        # confining them to pack 3 would put the curve's drop at L3 by
        # construction. Redundant backends live in pack 3 only.
        assert bool(exp["bleed_names"]) == (high and c["stack_level"] != "L0"), cid
        assert bool(exp["backend_names"]) == (high and c["stack_level"] in ("L3", "L4")), cid
        if not high:
            assert not exp["bleed_strength"], cid


def test_bleed_dose_rises_with_level_and_spans_three_strengths():
    """One bluntness fired 6/6 in the v2 probe, which says the effect exists and
    nothing about where it stops. A gradient in the catalog answers that from
    the same run, without another dimension of grid."""
    for scenario in ("s01", "s02", "s04"):
        doses = []
        for level in ("L1", "L2", "L3"):
            exp = json.loads((HERE / "expected" / case_for(scenario, level, "high") / "answer.json").read_text())
            doses.append(len([n for n in exp["bleed_names"]
                              if scenario in next(e["targets"] for p in CATALOG["high_overlap_packs"]
                                                  for e in p if e["tool"]["name"] == n)]))
        assert doses == sorted(doses) and doses[-1] > doses[0], f"{scenario}: {doses}"

    strengths = {e["strength"] for p in CATALOG["high_overlap_packs"] for e in p
                 if e.get("kind") == "instruction_bleed"}
    assert strengths == {"blunt", "medium", "subtle"}


def test_redundant_backends_are_ruled_out_by_house_rules_not_by_their_own_description():
    """These skills genuinely perform the action. That is the point -- the
    disqualifying knowledge is organisational, which is where it sits in
    practice, and no schema states it."""
    for p in CATALOG["high_overlap_packs"]:
        for e in p:
            if e.get("kind") == "redundant_backend":
                assert "house rules" in e["disqualifier"].lower(), e["tool"]["name"]


def test_filler_pool_is_not_one_compressible_pattern():
    """A single template lattice lets a reader dismiss the whole bulk at a
    glance, which makes L4's skill count overstate the effective load."""
    filler = json.loads((HERE / "filler_pool.json").read_text())["tools"]
    shapes = {"".join("a" if ch.isalpha() else ch for ch in t["name"]) for t in filler}
    assert len(shapes) > len(filler) // 2, f"only {len(shapes)} name shapes across {len(filler)} skills"
    lengths = {len(t["description"]) for t in filler}
    assert len(lengths) > 20, f"only {len(lengths)} distinct description lengths"


def test_base_skill_order_is_stable_across_levels_as_well_as_between_arms():
    """Two position controls, and the second one was missing.

    Between arms: base skills at identical indices, so the arm comparison
    cannot be a position effect. That one was always tested.

    ACROSS levels: base skills in the same relative order at L0 and at every
    level above it, so the dose-response curve cannot be a position effect
    either. This was NOT held. The composer shuffled the assembled list, and a
    shuffle's permutation depends on the list's length, so every level
    reordered everything -- one bleeding skill sat at index 9 at L1, index 1 at
    L2 and index 14 at L3. The level axis was confounded with position and the
    curve could not be read.
    """
    for scenario in SCENARIOS:
        ref = [n for n in catalog_names(case_for(scenario, "L0", "none")) if n in BASE_NAMES]
        for level in ("L1", "L2", "L3", "L4"):
            for arm in ("high", "low"):
                got = [n for n in catalog_names(case_for(scenario, level, arm)) if n in BASE_NAMES]
                assert got == ref, f"{scenario}/{level}/{arm}: base order changed with level"


def test_adding_a_level_only_interleaves_and_never_reorders():
    """Whatever was in the catalog at level N keeps its relative order at N+1."""
    for scenario in SCENARIOS:
        for arm in ("high", "low"):
            prev = catalog_names(case_for(scenario, "L1", arm))
            for level in ("L2", "L3"):
                cur = catalog_names(case_for(scenario, level, arm))
                assert [n for n in cur if n in set(prev)] == prev, f"{scenario}/{level}/{arm}"
                prev = cur


# --- the design that keeps nine scenarios from measuring one thing -------

PRIMARY = [i for i, s in SCENARIOS.items() if s["difficulty"] in bc.PRIMARY_TIERS]


def test_every_primary_scenario_meets_each_instruction_strength_exactly_once():
    """Strength must be orthogonal to level.

    If subtle skills sat in pack 1 and blunt ones in pack 3, the instructions
    would get more forceful as the stack grows, and a dose effect would be a
    strength effect in disguise. Each scenario meets subtle, medium and blunt
    exactly once across L1-L3, and the ORDER differs between scenario groups.
    """
    orders = set()
    for sid in PRIMARY:
        seq = [e["strength"] for p in CATALOG["high_overlap_packs"] for e in p
               if e.get("kind") == "instruction_bleed" and sid in e["targets"]]
        assert sorted(seq) == ["blunt", "medium", "subtle"], f"{sid}: {seq}"
        orders.add(tuple(seq))
    assert len(orders) > 1, "every scenario meets the strengths in the same order"


def test_bleed_dose_rises_by_exactly_one_per_level_for_every_primary_scenario():
    for sid in PRIMARY:
        cum, n = [], 0
        for p in CATALOG["high_overlap_packs"]:
            n += sum(1 for e in p if e.get("kind") == "instruction_bleed" and sid in e["targets"])
            cum.append(n)
        assert cum == [1, 2, 3], f"{sid}: {cum}"


def test_the_nine_primary_scenarios_are_tempted_on_more_than_one_surface():
    """Nine scenarios all rehearsing the same trap would inflate n without
    adding information. The surface is derived from the catalog rather than
    declared per scenario -- a hand-maintained copy drifts as soon as a
    bleeding skill's targets change, which is how this test first failed."""
    def surfaces_for(sid: str) -> set[str]:
        return {e["bleed_surface"] for p in CATALOG["high_overlap_packs"] for e in p
                if e.get("kind") == "instruction_bleed" and sid in e["targets"]}

    all_surfaces = set().union(*(surfaces_for(sid) for sid in PRIMARY))
    assert len(all_surfaces) >= 3, all_surfaces
    for surface in all_surfaces:
        covered = [sid for sid in PRIMARY if surface in surfaces_for(sid)]
        assert len(covered) < len(PRIMARY), f"{surface} tempts every primary scenario"
    for sid in PRIMARY:
        assert surfaces_for(sid), f"{sid} faces no instruction-bleed temptation at all"


def test_tier_mix_matches_what_the_statistic_needs():
    tiers = Counter(s["difficulty"] for s in SCENARIOS.values())
    assert tiers["easy"] == 1, "one canary; L0 is already the per-scenario floor check"
    assert tiers["medium"] + tiers["hard"] >= 8, "the permutation test needs 8-9 primary scenarios"
    assert tiers["edge"] >= 2
