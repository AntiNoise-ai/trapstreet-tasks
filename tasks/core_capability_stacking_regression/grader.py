"""Overall grader for core_capability_stacking_regression.

Standard aggregation (mean score, n_passed, latency, cost) plus the three
things this task specifically needs, all computed from a SINGLE run because
stacking is a case dimension rather than a solution variant:

1. Accuracy by stack_level x overlap_class -- the degradation surface.
2. The pre-registered primary test: per scenario, the mean of (low - high)
   across L1-L3, tested by exact sign-flip permutation. The L3-only sign test
   is still reported, as a secondary -- it drops exact ties, and F1 scores tie
   constantly against a model near ceiling.
3. The separately-registered L4 bulk probe: the same overlap contrast carried
   out with ~100 distant fillers added to BOTH arms, so a flat result cannot be
   waved away with "26 skills is not a stack".
4. The pre-registered curve-shape call: linear vs inflection, on the high arm,
   read off L0-L3 only -- L4 moves bulk rather than overlap.

And the quarantine that keeps this task from publishing a false positive.
The high-overlap arm at L3 carries the largest prompt, so provider errors and
context overflow concentrate exactly where the hypothesis predicts
degradation. The headline `score` still counts them 0.0 -- excluding them
would let a solution game the board by erroring on cases it finds hard -- but
`n_solution_error`, `score_excluding_solution_errors` and
`solution_errors_by_stack_level` sit next to the number they would corrupt,
and any degradation claim is checked against them first.
"""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

PASS_THRESHOLD = 0.5

# L0-L3 is the overlap ladder: count is held equal between the arms and only
# the competitors grow. L4 adds ~100 distant filler skills to BOTH arms, so it
# raises bulk without touching the overlap contrast. It therefore answers a
# different question -- "does the overlap effect survive at a catalog size
# anyone would call a stack?" -- and is kept out of the dose curve, because a
# level that moves bulk rather than overlap would put a bulk effect inside the
# inflection call.
CURVE_LEVELS = ["L0", "L1", "L2", "L3"]
LEVEL_ORDER = CURVE_LEVELS + ["L4"]

# Levels entering the primary statistic. L0 is the shared baseline (identical
# in both arms, so it contributes a guaranteed zero difference) and L4 is the
# separately-registered bulk probe.
PRIMARY_LEVELS = ["L1", "L2", "L3"]

# Pre-registered before the first run: ONLY these difficulty tiers count toward
# the primary overlap test. The `easy` tier states its disqualifying constraint
# in the request text, so it is a floor check -- if it degrades, the task broke
# rather than overlap biting -- and the `edge` tier tests failure shapes rather
# than the main effect. Fixing the membership here, in code, is what stops the
# tempting move of running all twelve scenarios and then reporting whichever
# subset happened to separate.
PRIMARY_TIERS = ("medium", "hard")

# Pre-registered before the first run. A curve is called non-linear only if its
# largest single-level drop clears BOTH an absolute floor and a relative test
# against the other drops; without a definition fixed in advance, every noisy
# curve has a biggest drop somewhere and "inflection" is unfalsifiable.
INFLECTION_MIN_DROP = 0.10
INFLECTION_RATIO = 2.0


def sign_test_p(n_favour: int, n_discordant: int) -> float:
    """One-sided exact sign test: P(X >= n_favour), X ~ Binom(n_discordant, 0.5)."""
    if n_discordant == 0:
        return 1.0
    tail = sum(math.comb(n_discordant, i) for i in range(n_favour, n_discordant + 1))
    return tail / (2 ** n_discordant)


def permutation_p(diffs: list[float]) -> float:
    """One-sided exact sign-flip permutation test on paired differences.

    THE PRIMARY STATISTIC. Each scenario contributes one difference, the mean
    of (low - high) across the primary levels, so a positive value means the
    high-overlap arm scored worse. Under the null the sign of each scenario's
    difference is symmetric, so enumerating all 2^n sign assignments gives an
    exact p with no distributional assumption.

    Why not the L3-only sign test: that test conditions on discordant pairs, so
    exact ties are simply dropped, and F1 scores tie constantly against a model
    near ceiling. At n=9 a single tie plus a single wrong-direction pair takes
    it past 0.05 whatever the effect size. Averaging three levels of continuous
    F1 makes exact zeroes rare and uses the whole treatment ladder rather than
    its last rung. The sign test is still reported, as a secondary.
    """
    n = len(diffs)
    if n == 0:
        return 1.0
    if n > 20:  # 2^20 enumerations; far above any real scenario count here
        raise ValueError(f"exact permutation over {n} scenarios is too large")
    observed = sum(diffs)
    at_least_as_extreme = 0
    for mask in range(2 ** n):
        total = sum(d if (mask >> i) & 1 else -d for i, d in enumerate(diffs))
        if total >= observed:
            at_least_as_extreme += 1
    return at_least_as_extreme / (2 ** n)


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def main() -> None:
    cases = json.loads(os.environ["TRAPTASK_MANIFEST"])

    scored = [c for c in cases if c.get("metrics") and c["metrics"].get("score") is not None]
    skipped = [c for c in cases if not c.get("metrics") or c["metrics"].get("score") is None]

    accuracy = mean([c["metrics"]["score"] for c in scored])

    def cell(c: dict) -> tuple[str, str]:
        m = c["metrics"]
        return m.get("stack_level"), m.get("overlap_class")

    # --- degradation surface -------------------------------------------------
    by_level: defaultdict[str, list[float]] = defaultdict(list)
    by_arm: defaultdict[str, list[float]] = defaultdict(list)
    by_cell: defaultdict[str, list[float]] = defaultdict(list)
    by_dose: defaultdict[int, list[float]] = defaultdict(list)
    dose_by_cell: defaultdict[str, set[int]] = defaultdict(set)
    by_difficulty: defaultdict[str, list[float]] = defaultdict(list)
    # (scenario, level, arm) -> score, for the paired tests
    paired: dict[tuple[str, str, str], float] = {}
    difficulty_of: dict[str, str] = {}

    for c in scored:
        m = c["metrics"]
        lvl, arm = cell(c)
        if m.get("scenario") and m.get("difficulty"):
            difficulty_of[m["scenario"]] = m["difficulty"]
        if m.get("difficulty"):
            by_difficulty[m["difficulty"]].append(m["score"])
        if lvl:
            by_level[lvl].append(m["score"])
        if arm:
            by_arm[arm].append(m["score"])
        if lvl and arm:
            by_cell[f"{lvl}/{arm}"].append(m["score"])
        dose = m.get("n_competitors")
        if dose is not None and arm == "high":
            by_dose[dose].append(m["score"])
            if lvl:
                dose_by_cell[f"{lvl}/{arm}"].add(dose)
        if m.get("scenario") and lvl and arm:
            paired[(m["scenario"], lvl, arm)] = m["score"]

    # L0 is shared between the arms, so it reads as the baseline for both.
    def arm_curve(arm: str, tiers: tuple[str, ...] | None = None) -> dict[str, float | None]:
        out: dict[str, float | None] = {}
        for lvl in LEVEL_ORDER:
            key = "none" if lvl == "L0" else arm
            vals = [
                v for (s, l, a), v in paired.items()
                if l == lvl and a == key
                and (tiers is None or difficulty_of.get(s) in tiers)
            ]
            out[lvl] = round(mean(vals), 4) if vals else None
        return out

    # The headline curve is read off the pre-registered tiers only. Averaging
    # the easy tier in would flatten it -- those scenarios are expected to sit
    # at ceiling in both arms by design, and a curve diluted with them can look
    # linear purely from the mix rather than from the overlap dose.
    high_curve = arm_curve("high", PRIMARY_TIERS)
    low_curve = arm_curve("low", PRIMARY_TIERS)
    high_curve_all, low_curve_all = arm_curve("high"), arm_curve("low")
    curves_by_tier = {
        tier: arm_curve("high", (tier,))
        for tier in sorted(by_difficulty)
    }

    # --- primary test: overlap at matched L3, paired by scenario -------------
    # Restricted to the pre-registered tiers; every other scenario is reported
    # as a diagnostic and cannot enter the number that gets quoted.
    all_scenarios = sorted({s for (s, _, _) in paired})
    scenarios = [s for s in all_scenarios if difficulty_of.get(s) in PRIMARY_TIERS]
    excluded = [s for s in all_scenarios if s not in scenarios]
    n_favour = n_against = n_tied = 0
    for s in scenarios:
        hi, lo = paired.get((s, "L3", "high")), paired.get((s, "L3", "low"))
        if hi is None or lo is None:
            continue
        if hi < lo:
            n_favour += 1          # high overlap scored worse: the hypothesis
        elif hi > lo:
            n_against += 1
        else:
            n_tied += 1
    n_discordant = n_favour + n_against

    # --- PRIMARY: paired sign-flip permutation over the overlap ladder -------
    per_scenario_diff: dict[str, float] = {}
    for s in scenarios:
        diffs_this = []
        for lvl in PRIMARY_LEVELS:
            hi, lo = paired.get((s, lvl, "high")), paired.get((s, lvl, "low"))
            if hi is not None and lo is not None:
                diffs_this.append(lo - hi)
        if len(diffs_this) == len(PRIMARY_LEVELS):
            per_scenario_diff[s] = round(mean(diffs_this), 6)

    diffs = list(per_scenario_diff.values())
    primary_p = permutation_p(diffs) if diffs else 1.0

    # --- SECONDARY: does the overlap effect survive at bulk? ----------------
    # L4 adds the same ~100 distant fillers to both arms, so this is the same
    # overlap contrast carried out at a catalog size that cannot be dismissed
    # as "26 skills is not a stack".
    l4_diffs = []
    for s in scenarios:
        hi, lo = paired.get((s, "L4", "high")), paired.get((s, "L4", "low"))
        if hi is not None and lo is not None:
            l4_diffs.append(lo - hi)
    bulk_probe = {
        "n_scenarios": len(l4_diffs),
        "mean_low_minus_high": round(mean(l4_diffs), 4) if l4_diffs else None,
        "permutation_p": round(permutation_p(l4_diffs), 4) if l4_diffs else None,
        "note": "L4 raises bulk in BOTH arms; registered separately so it cannot "
                "enter the overlap-dose curve or the primary statistic",
    }

    # --- curve shape on the high arm ----------------------------------------
    curve_shape, drops = "insufficient_data", []
    levels_present = [l for l in CURVE_LEVELS if high_curve.get(l) is not None]
    if len(levels_present) == len(CURVE_LEVELS):
        drops = [
            round(high_curve[a] - high_curve[b], 4)
            for a, b in zip(CURVE_LEVELS, CURVE_LEVELS[1:])
        ]
        max_drop = max(drops)
        idx = drops.index(max_drop)
        others = [d for i, d in enumerate(drops) if i != idx]
        if max_drop < INFLECTION_MIN_DROP:
            curve_shape = "flat"
        elif max_drop > INFLECTION_RATIO * max(mean(others), 0.0):
            curve_shape = f"inflection@{CURVE_LEVELS[idx + 1]}"
        else:
            curve_shape = "linear"

    # --- solution-error quarantine ------------------------------------------
    errs = [c for c in scored if c["metrics"].get("failure_reason") == "solution_error"]
    clean = [c for c in scored if c["metrics"].get("failure_reason") != "solution_error"]
    errs_by_level: Counter[str] = Counter(
        c["metrics"].get("stack_level") for c in errs if c["metrics"].get("stack_level")
    )

    # Which wording actually bled. If only `blunt` ever fires, the effect is
    # about forceful phrasing; if `subtle` fires too, it is about the presence
    # of standing guidance at all -- a much broader claim.
    bled_strengths: Counter[str] = Counter()
    for c in scored:
        for st in c["metrics"].get("bled_strengths") or []:
            bled_strengths[st] += 1

    # Which specific skill displaced which. This is the aggregation a merge
    # decision needs -- "does installing B cost us A" is a question about a
    # pair -- and it exists only for substitutions, since nothing is displaced
    # when the workflow completed and merely gained surplus calls.
    by_skill_pair: Counter[str] = Counter()
    for c in scored:
        for pair in c["metrics"].get("interfering_pairs") or []:
            by_skill_pair[f"{pair[0]} <- {pair[1]}"] += 1

    by_failure_reason = Counter(
        c["metrics"].get("failure_reason") for c in scored if c["metrics"].get("failure_reason")
    )

    durations = [c.get("duration", 0.0) for c in cases if c.get("duration") is not None]
    if durations:
        ds = sorted(durations)
        latency_ms_median = round(ds[len(ds) // 2] * 1000, 1)
        latency_ms_p95 = round(ds[int(0.95 * len(ds))] * 1000, 1) if len(ds) > 1 else latency_ms_median
        latency_ms_total = round(sum(ds) * 1000, 1)
    else:
        latency_ms_median = latency_ms_p95 = latency_ms_total = 0.0

    case_costs = [
        c["cost"]["cost_usd"]
        for c in cases
        if isinstance(c.get("cost"), dict) and c["cost"].get("cost_usd") is not None
    ]
    cost_usd_total = round(sum(case_costs), 4) if case_costs else None

    # The four numbers a reader should see first, lifted out of the nested
    # objects they also live in. The platform's run page renders a nested value
    # as `[object Object]`, so anything that only exists inside `primary_test`
    # or `by_overlap_class` is invisible there. These are duplicates, not a
    # second source of truth -- the nested versions stay authoritative for
    # anything consuming this programmatically.
    arm_high = round(mean(by_arm["high"]), 4) if by_arm.get("high") else None
    arm_low = round(mean(by_arm["low"]), 4) if by_arm.get("low") else None
    arm_gap = round(arm_low - arm_high, 4) if arm_high is not None and arm_low is not None else None

    print(json.dumps({
        "passed": bool(scored) and accuracy >= PASS_THRESHOLD,
        "score": round(accuracy, 3),
        "n_passed": sum(1 for c in scored if c["metrics"]["score"] == 1.0),
        "n_total": len(cases),
        "n_scored": len(scored),
        "n_skipped_no_gold": len(skipped),
        "threshold": PASS_THRESHOLD,

        # Flat duplicates so the run page can show them -- see above.
        "primary_p": round(primary_p, 4),
        "arm_gap": arm_gap,
        "high_overlap_score": arm_high,
        "low_overlap_score": arm_low,

        "completion_mean": round(mean([c["metrics"].get("completion", 0.0) for c in scored]), 4),
        "correctness_mean": round(mean([c["metrics"].get("correctness", 0.0) for c in scored]), 4),

        "by_stack_level": {k: round(mean(v), 4) for k, v in sorted(by_level.items())},
        "by_overlap_class": {k: round(mean(v), 4) for k, v in sorted(by_arm.items())},
        "by_cell": {k: round(mean(v), 4) for k, v in sorted(by_cell.items())},
        "by_difficulty": {k: round(mean(v), 4) for k, v in sorted(by_difficulty.items())},
        "primary_tiers": list(PRIMARY_TIERS),

        # Pre-registered tiers only -- this is the curve the shape call is made
        # from. The all-tier version sits beside it so the dilution is visible
        # rather than hidden.
        "curve_high_overlap": high_curve,
        "curve_low_overlap": low_curve,
        "curve_high_overlap_all_tiers": high_curve_all,
        "curve_low_overlap_all_tiers": low_curve_all,
        "curve_high_by_difficulty": curves_by_tier,

        # The L-axis counts PACKS added, which is not the same as how much
        # overlap a given scenario is actually under -- a pack is a fixed set
        # of skills and not every skill in it competes with every scenario.
        # Dose is the honest x-axis for the mechanism; the level is the honest
        # x-axis for the intervention. Both are reported.
        "by_competitor_dose": {
            str(d): round(mean(v), 4) for d, v in sorted(by_dose.items())
        },
        "dose_by_cell": {k: sorted(v) for k, v in sorted(dose_by_cell.items())},

        "primary_test": {
            "statistic": "mean(low - high) per scenario over L1-L3, sign-flip permutation",
            "n_scenarios": len(diffs),
            "mean_diff": round(mean(diffs), 4) if diffs else None,
            "permutation_p": round(primary_p, 4),
            "per_scenario_diff": per_scenario_diff,
            "note": "positive mean_diff means the high-overlap arm scored worse",
        },
        "bulk_probe_L4": bulk_probe,

        "secondary_sign_test_L3": {
            "n_scenarios": len(scenarios),
            "n_favouring_hypothesis": n_favour,
            "n_against": n_against,
            "n_tied": n_tied,
            "sign_test_p": round(sign_test_p(n_favour, n_discordant), 4),
            "n_discordant": n_discordant,
            "excluded_scenarios": excluded,
            "note": (
                "one-sided exact sign test on discordant pairs from the pre-registered "
                "tiers only; ties are dropped, not counted as support, and 5 discordant "
                "pairs are the minimum that can reach p<0.05"
            ),
        },
        "curve_shape": curve_shape,
        "curve_high_drops": drops,

        "by_failure_reason": dict(by_failure_reason),
        "bled_by_instruction_strength": dict(bled_strengths),
        "by_skill_pair": dict(by_skill_pair.most_common()),
        "n_failures_without_a_pair": sum(
            1 for c in scored
            if c["metrics"].get("score", 1.0) < 1.0
            and not c["metrics"].get("interfering_pairs")
        ),
        "n_solution_error": len(errs),
        "score_excluding_solution_errors": round(mean([c["metrics"]["score"] for c in clean]), 4),
        "solution_errors_by_stack_level": dict(errs_by_level),

        "latency_ms_median": latency_ms_median,
        "latency_ms_p95": latency_ms_p95,
        "latency_ms_total": latency_ms_total,
        "cost_usd_total": cost_usd_total,
    }))


if __name__ == "__main__":
    main()
