"""Build/authoring invariant tests -- these are what make a measured effect
attributable rather than an artifact. Run: python3 -m pytest tests/ -v"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from build_cases import CLEAN_COMPANIONS, FORBIDDEN_IN_FILLER, compose_catalog, stable_seed  # noqa: E402

GRID = json.loads((HERE / "gold.cases.json").read_text())["cases"]
FAMILIES = json.loads((HERE / "families.json").read_text())["families"]
FILLER = json.loads((HERE / "filler_pool.json").read_text())["tools"]
BY_INTENT = {f["intent"]: f for f in FAMILIES}

FENCE_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


def catalog_names(case_id: str) -> list[str]:
    text = (HERE / "inputs" / case_id / "prompt.txt").read_text()
    return [t["name"] for t in json.loads(FENCE_RE.search(text).group(1))]


def answer(case_id: str) -> dict:
    return json.loads((HERE / "expected" / case_id / "answer.json").read_text())


# --- grid --------------------------------------------------------------------

def test_grid_is_eight_families_by_eight_cells():
    assert len(GRID) == 64
    assert len({c["intent"] for c in GRID}) == 8
    for fam in FAMILIES:
        assert sum(1 for c in GRID if c["intent"] == fam["intent"]) == 8


def test_every_case_was_rendered():
    for case in GRID:
        assert (HERE / "inputs" / case["id"] / "prompt.txt").exists()
        assert (HERE / "expected" / case["id"] / "answer.json").exists()


# --- per-case invariants -----------------------------------------------------

@pytest.mark.parametrize("case", GRID, ids=[c["id"] for c in GRID])
def test_catalog_size_matches_declared_n(case):
    assert len(catalog_names(case["id"])) == case["n_tools"]


@pytest.mark.parametrize("case", GRID, ids=[c["id"] for c in GRID])
def test_no_duplicate_tools_in_catalog(case):
    names = catalog_names(case["id"])
    assert len(names) == len(set(names))


@pytest.mark.parametrize("case", GRID, ids=[c["id"] for c in GRID])
def test_correct_tool_sits_exactly_where_recorded(case):
    names = catalog_names(case["id"])
    a = answer(case["id"])
    assert names.count(a["correct_tool_name"]) == 1
    assert names[a["position_index"]] == a["correct_tool_name"]


@pytest.mark.parametrize("case", GRID, ids=[c["id"] for c in GRID])
def test_arms_carry_the_right_companions(case):
    """Adversarial catalogs contain all five own near-misses; clean catalogs
    contain none of them."""
    fam = BY_INTENT[case["intent"]]
    own = {nm["tool"]["name"] for nm in fam["near_misses"]}
    present = own & set(catalog_names(case["id"]))
    if case["ambiguity"] == "adversarial":
        assert present == own
    else:
        assert present == set()


@pytest.mark.parametrize("case", GRID, ids=[c["id"] for c in GRID])
def test_both_arms_carry_six_hand_authored_schemas(case):
    """Style parity: if the clean arm held one hand-written tool among 299
    generated ones, the answer could be found by prose style alone and the
    ambiguity effect would be an authoring artifact."""
    hand_written = {f["correct_tool"]["name"] for f in FAMILIES}
    for f in FAMILIES:
        hand_written |= {nm["tool"]["name"] for nm in f["near_misses"]}
    assert len(hand_written & set(catalog_names(case["id"]))) == 6


# --- the controls that v1 lacked ---------------------------------------------

def test_position_variants_are_content_identical():
    """The three position variants of a cell must differ ONLY by where the
    correct tool sits -- otherwise a 'position effect' is a content effect."""
    cells: dict[tuple, list[str]] = {}
    for c in GRID:
        cells.setdefault((c["intent"], c["n_tools"], c["ambiguity"]), []).append(c["id"])

    checked = 0
    for key, ids in cells.items():
        if len(ids) < 2:
            continue
        ref = set(catalog_names(ids[0]))
        for other in ids[1:]:
            assert set(catalog_names(other)) == ref, f"cell {key} varies in content"
        checked += 1
    assert checked == 8, "expected one multi-position cell per family"


def test_position_variants_actually_move_the_tool():
    by_cell: dict[tuple, dict[str, int]] = {}
    for c in GRID:
        if c["n_tools"] != 300 or c["ambiguity"] != "adversarial":
            continue
        by_cell.setdefault(c["intent"], {})[c["position"]] = answer(c["id"])["position_index"]
    for intent, pos in by_cell.items():
        assert pos["early"] < pos["mid"] < pos["late"], intent
        assert pos["early"] <= 10 and pos["late"] >= 289, intent


def test_near_misses_are_scattered_not_clustered_at_scale():
    """At N=300 the five competitors must be spread across the catalog, not
    parked beside the correct tool. If they clustered, a model could settle
    the choice by reading one local block and the task would measure local
    comparison rather than integration across a 61k-token context."""
    for case in GRID:
        if case["n_tools"] != 300 or case["ambiguity"] != "adversarial":
            continue
        names = catalog_names(case["id"])
        fam = BY_INTENT[case["intent"]]
        idx = sorted(names.index(nm["tool"]["name"]) for nm in fam["near_misses"])
        # Span at least a third of the catalog. The observed minimum is 147
        # (case_30); 100 is the guarantee, not a description of the data.
        assert max(idx) - min(idx) > 100, f"{case['id']}: near-misses clustered in {idx}"
        correct = names.index(fam["correct_tool"]["name"])
        assert any(abs(i - correct) > 75 for i in idx), \
            f"{case['id']}: every near-miss sits near the correct tool"


def test_filler_sets_are_nested_across_n():
    """Growing the catalog must mean 'the same tools plus more', not 'a
    different catalog'. Otherwise an N effect could be a content effect."""
    for fam in FAMILIES:
        intent = fam["intent"]
        small = next(c for c in GRID if c["intent"] == intent and c["n_tools"] == 60 and c["ambiguity"] == "adversarial")
        big = next(c for c in GRID if c["intent"] == intent and c["n_tools"] == 300 and c["ambiguity"] == "adversarial" and c["position"] == "mid")
        assert set(catalog_names(small["id"])) < set(catalog_names(big["id"])), intent


def test_build_is_deterministic():
    """Same inputs must give the same catalogs on any machine -- seeds are
    sha256-derived, not PYTHONHASHSEED-dependent."""
    case = GRID[5]
    first, _ = compose_catalog(case, FAMILIES, FILLER)
    second, _ = compose_catalog(case, FAMILIES, FILLER)
    assert [t["name"] for t in first] == [t["name"] for t in second]
    assert [t["name"] for t in first] == catalog_names(case["id"])


def test_stable_seed_is_not_python_hash():
    assert stable_seed("a", 1) == stable_seed("a", 1)
    assert stable_seed("a", 1) != stable_seed("a", 2)


# --- fairness / authoring ----------------------------------------------------

def test_every_near_miss_records_why_it_is_wrong():
    for fam in FAMILIES:
        assert len(fam["near_misses"]) == 5
        for nm in fam["near_misses"]:
            assert nm["disqualifier"].strip(), f"{fam['intent']}/{nm['tool']['name']}"


def test_expected_args_are_all_required_by_the_correct_tool():
    """Scoring an argument the schema never demanded would be unfair, not hard."""
    for fam in FAMILIES:
        required = set(fam["correct_tool"]["parameters"]["required"])
        assert set(fam["expected_args"]) <= required, fam["intent"]


def test_query_does_not_contain_the_correct_tool_name():
    """A query that lexically spells out its answer measures lookup, not
    discrimination -- that is precisely what made v1 flat."""
    for fam in FAMILIES:
        q = fam["query"].lower().replace(" ", "_")
        assert fam["correct_tool"]["name"].lower() not in q, fam["intent"]


def test_clean_companions_never_come_from_their_own_family():
    for fi, picks in CLEAN_COMPANIONS.items():
        assert len(set(picks)) == 5
        for (src_fi, src_ni) in picks:
            assert src_fi != fi
            assert 0 <= src_ni < 5


def test_filler_pool_is_disjoint_from_family_answer_space():
    family_names = {f["correct_tool"]["name"] for f in FAMILIES}
    for f in FAMILIES:
        family_names |= {nm["tool"]["name"] for nm in f["near_misses"]}
    filler_names = {t["name"] for t in FILLER}
    assert not (family_names & filler_names)
    for name in filler_names:
        for bad in FORBIDDEN_IN_FILLER:
            assert bad not in name, f"{name} contains {bad}"


def test_filler_schemas_are_verbose_enough_to_be_realistic():
    """Terse toy schemas would make N=300 an ~18k-token prompt, nowhere near
    the regime this task claims to probe."""
    lengths = [len(json.dumps(t)) for t in FILLER]
    assert min(lengths) > 350, "some filler schema is too thin to be plausible"
    assert sum(lengths) / len(lengths) > 550


def test_largest_catalog_is_a_genuine_long_context_load():
    big = next(c for c in GRID if c["n_tools"] == 300)
    chars = len((HERE / "inputs" / big["id"] / "prompt.txt").read_text())
    assert chars > 150_000, "N=300 prompt should be ~50k+ tokens"
