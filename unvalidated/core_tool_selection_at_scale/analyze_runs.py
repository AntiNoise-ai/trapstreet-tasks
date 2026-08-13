"""Aggregate repeated tp runs into the pre-registered analysis.

Run:  python3 analyze_runs.py <solution-variant-dir> [<dir> ...]

Reads every report.json under each variant's .trap/runs/, reports the MEDIAN
across runs for each marginal together with the min-max range, and applies the
decision rules registered in README.md before any of this was run:

  * catalog-size effect: adversarial N=300 is >=15 points below N=6, ranges
    across runs not overlapping
  * ambiguity effect:    adversarial is >=15 points below clean at matched N,
    ranges not overlapping
  * position effect:     two position levels at N=300 differ by >=15 points,
    ranges not overlapping. The U-shaped-attention hypothesis specifically
    predicts `mid` is WORST -- reported separately, since a position spread in
    the opposite direction falsifies it rather than supporting it.

Median, never a single run: with 8 cases per cell a lucky pass moves a cell by
12.5 points, which is most of a threshold.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


def load_runs(variant_dir: Path) -> list[dict]:
    """Prefer report.rescored.json when present, so every pass is scored by the
    same (final) judge regardless of when it ran."""
    out = []
    for r in sorted(variant_dir.glob(".trap/runs/*/*/*/report.json")):
        rescored = r.parent / "report.rescored.json"
        src = rescored if rescored.exists() else r
        try:
            d = json.loads(src.read_text())
        except json.JSONDecodeError:
            continue
        m = d.get("grader_metrics")
        if m and m.get("n_scored"):
            out.append(m)
    return out


def agg(runs: list[dict], field: str, key: str) -> tuple[float, float, float] | None:
    vals = [r[field][key] for r in runs if field in r and key in r[field]]
    if not vals:
        return None
    return statistics.median(vals), min(vals), max(vals)


def fmt(t: tuple[float, float, float] | None) -> str:
    if t is None:
        return "     --     "
    med, lo, hi = t
    return f"{med*100:5.1f}  [{lo*100:4.1f}-{hi*100:4.1f}]"


def overlap(a: tuple[float, float, float], b: tuple[float, float, float]) -> bool:
    return not (a[2] < b[1] or b[2] < a[1])


def verdict(name: str, hi_side, lo_side, label_hi: str, label_lo: str) -> str:
    """Apply one pre-registered rule. hi_side is the level expected to score
    higher if the effect is real."""
    if hi_side is None or lo_side is None:
        return f"  {name}: insufficient data"
    gap = (hi_side[0] - lo_side[0]) * 100
    sep = not overlap(hi_side, lo_side)
    meets = gap >= 15 and sep
    mark = "EFFECT" if meets else "no effect"
    detail = f"{label_hi} {hi_side[0]*100:.1f} vs {label_lo} {lo_side[0]*100:.1f}, gap {gap:+.1f}pt"
    reason = "" if meets else (
        "  (gap <15pt)" if gap < 15 else "  (ranges overlap across runs)")
    return f"  {name}: {mark} -- {detail}{reason}"


def report(variant_dir: Path) -> None:
    runs = load_runs(variant_dir)
    if not runs:
        print(f"\n{variant_dir.name}: no completed runs found")
        return

    print(f"\n{'='*72}\n{variant_dir.name}   (m={len(runs)} runs)\n{'='*72}")
    if len(runs) < 3:
        print("  !! m<3: the ranges below are degenerate, so the 'ranges do not\n"
              "     overlap' half of every rule passes trivially. Verdicts here are\n"
              "     NOT the pre-registered analysis -- they are a preview. Do not\n"
              "     report them as findings.")

    overall = [r["score"] for r in runs]
    print(f"  overall score        median {statistics.median(overall)*100:.1f}  "
          f"[{min(overall)*100:.1f}-{max(overall)*100:.1f}]")

    errs = [r.get("n_solution_error", 0) for r in runs]
    if any(errs):
        print(f"  !! provider errors   median {statistics.median(errs):.0f} of 64 cases "
              f"-- excluded from effect claims; see solution_errors_by_n_tools")
        for r in runs:
            if r.get("solution_errors_by_n_tools"):
                print(f"     by n_tools: {r['solution_errors_by_n_tools']}")
                break

    print(f"\n  {'marginal':<22}{'median  [min - max]':<22}")
    print(f"  {'-'*22}{'-'*22}")
    for field, keys in (("by_ambiguity", ["clean", "adversarial"]),
                        ("by_n_tools", ["6", "60", "300"]),
                        ("by_position", ["early", "mid", "late"])):
        for k in keys:
            t = agg(runs, field, k)
            print(f"  {field.replace('by_',''):<10}{k:<12}{fmt(t)}")
        print()

    print(f"  {'cell':<22}{'median  [min - max]':<22}")
    print(f"  {'-'*22}{'-'*22}")
    cells = sorted({k for r in runs for k in r.get("by_category", {})})
    for c in cells:
        print(f"  {c:<22}{fmt(agg(runs, 'by_category', c))}")

    print("\n  pre-registered rules:")
    print(verdict("catalog size (adversarial, matched position=mid)",
                  agg(runs, "by_category", "adv_n6_mid"),
                  agg(runs, "by_category", "adv_n300_mid"), "N=6", "N=300"))
    for n in ("6", "60", "300"):
        print(verdict(f"ambiguity at N={n}",
                      agg(runs, "by_category", f"clean_n{n}_mid"),
                      agg(runs, "by_category", f"adv_n{n}_mid"), "clean", "adversarial"))

    pos = {p: agg(runs, "by_category", f"adv_n300_{p}") for p in ("early", "mid", "late")}
    if all(pos.values()):
        best = max(pos, key=lambda p: pos[p][0])
        worst = min(pos, key=lambda p: pos[p][0])
        spread = f"(early {pos['early'][0]*100:.1f}, mid {pos['mid'][0]*100:.1f}, late {pos['late'][0]*100:.1f})"
        if pos[best][0] == pos[worst][0]:
            # All three tied -- naming a "worst" here would invent a ranking
            # out of an exact tie, which is how a flat result gets written up
            # as a trend.
            print(f"  position at N=300: no effect -- all levels tied at "
                  f"{pos[best][0]*100:.1f} {spread}")
            print("  U-shaped-attention prediction (mid worst): NOT SUPPORTED "
                  "-- no position ranking exists to support it")
        else:
            print(verdict("position at N=300", pos[best], pos[worst], best, worst))
            print(f"  U-shaped-attention prediction (mid worst): "
                  f"{'CONSISTENT' if worst == 'mid' else 'NOT SUPPORTED'} "
                  f"-- worst position is {worst!r} {spread}")

    lost: dict[str, int] = {}
    for r in runs:
        for k, v in r.get("lost_to_near_miss", {}).items():
            lost[k] = lost.get(k, 0) + v
    if lost:
        print("\n  lost to near-miss (summed across runs):")
        for k, v in sorted(lost.items(), key=lambda kv: -kv[1]):
            print(f"    {v:>3}x  {k}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    for d in sys.argv[1:]:
        report(Path(d).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
