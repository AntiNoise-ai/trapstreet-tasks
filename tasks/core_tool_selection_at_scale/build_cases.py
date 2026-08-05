"""Compose inputs/<id>/prompt.txt and expected/<id>/answer.json from
gold.cases.json + families.json + filler_pool.json.

Run:  python3 build_cases.py
inputs/ and expected/ are GENERATED -- never edit them by hand.

Catalog composition, per case:

    [correct tool] + [5 hand-authored companions] + [N-6 filler tools]

  * adversarial arm -- the companions are the family's OWN five near-misses:
    tools that plausibly match the request and are each disqualified by
    something stated in their own description (see families.json).
  * clean arm -- the companions are five near-misses BORROWED from other,
    semantically distant families. They are equally hand-authored and equally
    verbose, but none of them is a defensible answer to this family's query.

That borrowing is the whole point of the control. If the clean arm were
padded with generated filler only, the correct tool would be the single
hand-written schema in a catalog of templated ones and could be found by
prose style alone -- which would manufacture an ambiguity effect out of an
authoring artifact. Both arms carry exactly six hand-authored schemas; the
only thing that varies is whether the confusable ones are present.

Ordering is a seeded shuffle keyed on (intent, n_tools, ambiguity) and
deliberately NOT on position, so the three position variants of a cell are
byte-identical in content and differ only by one swap. validate_grid()
asserts that.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent

PROMPT_TEMPLATE = """You are an AI agent that selects exactly one tool to call to satisfy a user request.

# Available tools

```json
{tools_json}
```

# User request

{query}

# Your task

Output ONLY a single JSON object of the form:
{{"name": "<tool_name>", "arguments": {{"<arg>": <value>, ...}}}}

Call exactly one tool -- the one that correctly satisfies the request. Output
ONLY the JSON object. No explanation, no markdown fences, no array.
"""

# Fraction of the catalog at which the correct tool sits, per position level.
POSITION_FRACTIONS = {"early": 0.02, "mid": 0.50, "late": 0.98}

# Clean-arm companions: (family_index, near_miss_index) pairs, hand-picked so
# that every borrowed tool comes from a family whose subject matter cannot be
# confused with the borrowing family's query. Deliberately explicit rather
# than a modular-arithmetic rotation -- a rotation put analytics_list_events
# ("list event records over a date range") into the log-reading family's clean
# catalog, which is exactly the kind of accidental distractor that would have
# quietly contaminated the control arm.
CLEAN_COMPANIONS = {
    0: [(2, 0), (3, 4), (5, 3), (7, 4), (1, 4)],  # payments  <- calendar, deploy, chat, storage, traces
    1: [(0, 1), (2, 4), (5, 2), (7, 3), (4, 3)],  # logs      <- payments, scheduling, template, upload, groups
    2: [(0, 2), (1, 1), (3, 3), (6, 4), (7, 4)],  # calendar  <- payments, logs-export, flag, report, archive
    3: [(0, 4), (2, 3), (5, 4), (6, 2), (7, 2)],  # deploy    <- payments, calendar-list, announce, crm, share
    4: [(0, 3), (1, 2), (3, 4), (6, 3), (7, 0)],  # access    <- invoice, log-counts, scale, compare, move
    5: [(0, 0), (1, 3), (2, 1), (4, 4), (7, 4)],  # messaging <- void, metrics, cal-create, perm-list, archive
    6: [(0, 0), (2, 2), (3, 1), (5, 1), (7, 3)],  # analytics <- void, cal-check, cancel-deploy, schedule, upload
    7: [(0, 4), (1, 0), (3, 4), (4, 1), (6, 1)],  # storage   <- cancel-sub, tail, scale, req-access, channels
}

# Filler must never be a defensible answer to any family query. Domains were
# chosen to be disjoint from the eight families' territories; this list
# re-checks that mechanically instead of trusting the choice.
FORBIDDEN_IN_FILLER = [
    "refund", "chargeback", "store_credit", "void_authorization", "subscription",
    "free_slot", "availability", "booking", "calendar",
    "rollback", "deploy_", "feature_flag", "promote_build",
    "grant", "invite", "visibility", "request_access",
    "draft", "send", "announce", "chat_post",
    "count_events", "list_events", "channel_breakdown", "compare_periods",
    "copy_object", "move_object", "shortcut", "share_object", "upload_object",
    "tail_stream", "export_to_bucket", "count_by_level", "query_range", "traces_",
]


def stable_seed(*parts: object) -> int:
    """PYTHONHASHSEED-independent seed so builds are reproducible across
    machines and Python versions."""
    key = "|".join(str(p) for p in parts).encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big")


def load() -> tuple[dict, list[dict], list[dict]]:
    grid = json.loads((HERE / "gold.cases.json").read_text())
    families = json.loads((HERE / "families.json").read_text())["families"]
    filler = json.loads((HERE / "filler_pool.json").read_text())["tools"]
    return grid, families, filler


def validate_sources(families: list[dict], filler: list[dict]) -> None:
    """Fail loudly on authoring mistakes. These invariants are what make the
    instrument fair; a silent break here turns a measured effect into an
    artifact."""
    family_names: set[str] = set()
    for fi, fam in enumerate(families):
        if len(fam["near_misses"]) != 5:
            raise ValueError(f"family {fam['intent']}: expected 5 near-misses, got {len(fam['near_misses'])}")

        correct = fam["correct_tool"]
        names = [correct["name"]] + [nm["tool"]["name"] for nm in fam["near_misses"]]
        if len(names) != len(set(names)):
            raise ValueError(f"family {fam['intent']}: duplicate tool names within the family")
        family_names.update(names)

        # Every expected argument must be one the correct tool actually
        # requires -- otherwise the judge would penalise an omission the
        # schema never asked for, which is unfair rather than hard.
        required = set(correct["parameters"].get("required", []))
        for arg in fam["expected_args"]:
            if arg not in required:
                raise ValueError(
                    f"family {fam['intent']}: expected_args key {arg!r} is not in the correct "
                    f"tool's required list {sorted(required)} -- judge would be scoring an "
                    f"argument the schema never demanded"
                )
            accepted = fam["expected_args"][arg]
            if not isinstance(accepted, list) or not accepted:
                raise ValueError(f"family {fam['intent']}: expected_args[{arg!r}] must be a non-empty list")

        # Every near-miss must record WHY it is wrong. This is the field that
        # makes "hard but fair" auditable rather than asserted.
        for nm in fam["near_misses"]:
            if not nm.get("disqualifier", "").strip():
                raise ValueError(
                    f"family {fam['intent']}: near-miss {nm['tool']['name']} has no disqualifier"
                )

        for (src_fi, src_ni) in CLEAN_COMPANIONS[fi]:
            if src_fi == fi:
                raise ValueError(
                    f"family {fam['intent']}: clean companion borrowed from its own family -- "
                    f"that would put a real distractor in the control arm"
                )
            if not (0 <= src_ni < 5):
                raise ValueError(f"family {fam['intent']}: clean companion index {src_ni} out of range")
        if len(set(CLEAN_COMPANIONS[fi])) != 5:
            raise ValueError(f"family {fam['intent']}: clean companions must be 5 distinct tools")

    filler_names = [t["name"] for t in filler]
    if len(filler_names) != len(set(filler_names)):
        raise ValueError("filler pool contains duplicate tool names")

    clash = family_names & set(filler_names)
    if clash:
        raise ValueError(f"filler pool collides with family tool names: {sorted(clash)}")

    for name in filler_names:
        for bad in FORBIDDEN_IN_FILLER:
            if bad in name:
                raise ValueError(
                    f"filler tool {name!r} contains forbidden token {bad!r} -- it may be a "
                    f"defensible answer to a family query and would contaminate both arms"
                )

    for t in filler:
        if not all(k in t for k in ("name", "description", "parameters")):
            raise ValueError(f"malformed filler schema: {t}")


def compose_catalog(case: dict, families: list[dict], filler: list[dict]) -> tuple[list[dict], int]:
    """Return (catalog, index_of_correct_tool)."""
    fi = next(i for i, f in enumerate(families) if f["intent"] == case["intent"])
    fam = families[fi]
    n = case["n_tools"]

    correct = fam["correct_tool"]

    if case["ambiguity"] == "adversarial":
        companions = [nm["tool"] for nm in fam["near_misses"]]
    else:
        companions = [
            families[src_fi]["near_misses"][src_ni]["tool"]
            for (src_fi, src_ni) in CLEAN_COMPANIONS[fi]
        ]

    n_filler = n - 1 - len(companions)
    if n_filler < 0:
        raise ValueError(f"case {case['id']}: n_tools={n} too small for 6 hand-authored tools")
    if n_filler > len(filler):
        raise ValueError(f"case {case['id']}: needs {n_filler} filler tools, pool has {len(filler)}")

    # One shuffle order per intent, then take a PREFIX. Filler sets are
    # therefore nested across N: going from 60 to 300 tools literally means
    # "the same catalog plus more tools", not "a different catalog".
    pool = list(filler)
    random.Random(stable_seed("filler", case["intent"])).shuffle(pool)
    chosen_filler = pool[:n_filler]

    catalog = [correct] + companions + chosen_filler
    # Seed deliberately excludes position, so all position variants of a cell
    # share one starting order.
    random.Random(stable_seed("order", case["intent"], n, case["ambiguity"])).shuffle(catalog)

    target = round(POSITION_FRACTIONS[case["position"]] * (n - 1))
    cur = next(i for i, t in enumerate(catalog) if t["name"] == correct["name"])
    catalog[cur], catalog[target] = catalog[target], catalog[cur]

    return catalog, target


def validate_case(case: dict, catalog: list[dict], idx: int, fam: dict) -> None:
    n = case["n_tools"]
    if len(catalog) != n:
        raise ValueError(f"case {case['id']}: catalog has {len(catalog)} tools, expected {n}")

    names = [t["name"] for t in catalog]
    if len(names) != len(set(names)):
        dupes = sorted({x for x in names if names.count(x) > 1})
        raise ValueError(f"case {case['id']}: duplicate tool names in catalog: {dupes}")

    correct = fam["correct_tool"]["name"]
    if names.count(correct) != 1:
        raise ValueError(f"case {case['id']}: correct tool appears {names.count(correct)} times")
    if names[idx] != correct:
        raise ValueError(f"case {case['id']}: position control broken -- index {idx} is {names[idx]!r}")

    nm_names = {nm["tool"]["name"] for nm in fam["near_misses"]}
    present = nm_names & set(names)
    if case["ambiguity"] == "adversarial" and present != nm_names:
        raise ValueError(f"case {case['id']}: adversarial arm missing near-misses {sorted(nm_names - present)}")
    if case["ambiguity"] == "clean" and present:
        raise ValueError(f"case {case['id']}: clean arm contaminated with own near-misses {sorted(present)}")


def validate_grid(built: dict[str, tuple[dict, list[dict], int]]) -> None:
    """Position variants of the same cell must contain exactly the same tools.

    v1 asserted that the correct tool sat at the recorded index but never that
    the surrounding catalog was held constant -- so a position effect could
    have been a content effect wearing position's clothes.
    """
    groups: dict[tuple, list[str]] = {}
    for cid, (case, catalog, _) in built.items():
        key = (case["intent"], case["n_tools"], case["ambiguity"])
        groups.setdefault(key, []).append(cid)

    for key, cids in groups.items():
        if len(cids) < 2:
            continue
        ref = {t["name"] for t in built[cids[0]][1]}
        for cid in cids[1:]:
            other = {t["name"] for t in built[cid][1]}
            if other != ref:
                diff = ref ^ other
                raise ValueError(
                    f"cell {key}: position variants {cids} differ in catalog contents "
                    f"({sorted(diff)[:5]}...) -- position is confounded with content"
                )


def build() -> None:
    grid, families, filler = load()
    validate_sources(families, filler)

    by_intent = {f["intent"]: f for f in families}
    built: dict[str, tuple[dict, list[dict], int]] = {}
    seen: set[str] = set()

    for case in grid["cases"]:
        cid = case["id"]
        if cid in seen:
            raise ValueError(f"duplicate case id: {cid}")
        seen.add(cid)

        fam = by_intent[case["intent"]]
        catalog, idx = compose_catalog(case, families, filler)
        validate_case(case, catalog, idx, fam)
        built[cid] = (case, catalog, idx)

    validate_grid(built)

    for cid, (case, catalog, idx) in built.items():
        fam = by_intent[case["intent"]]

        in_dir = HERE / "inputs" / cid
        in_dir.mkdir(parents=True, exist_ok=True)
        (in_dir / "prompt.txt").write_text(PROMPT_TEMPLATE.format(
            tools_json=json.dumps(catalog, indent=2),
            query=fam["query"],
        ))

        exp_dir = HERE / "expected" / cid
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "answer.json").write_text(json.dumps({
            "id": cid,
            "correct_tool_name": fam["correct_tool"]["name"],
            "expected_args": fam["expected_args"],
            "n_tools": case["n_tools"],
            "position": case["position"],
            "position_index": idx,
            "ambiguity": case["ambiguity"],
            "intent": case["intent"],
            "category": case["category"],
            # Recorded so the judge can report WHICH near-miss won when a
            # case fails -- the interesting datum is not "wrong" but "wrong
            # in the specific way the family was built to provoke".
            "near_miss_names": [nm["tool"]["name"] for nm in fam["near_misses"]],
        }, indent=2))

    print(f"Built {len(built)} cases.")


if __name__ == "__main__":
    build()
