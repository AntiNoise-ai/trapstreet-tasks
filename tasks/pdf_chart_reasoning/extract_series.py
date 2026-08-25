"""Measure the diffusion-index series of figures 4.D and 4.E.

Unlike the distribution figures, these carry values that appear in no table in
the release -- the only place the numbers exist is the drawing. Gold therefore
comes from the marker coordinates in the pre-rasterisation vector paths.

Dates are recovered from structure rather than from fitting the year labels,
which a stray label off the axis was enough to skew by two years. The markers
sit at 75 x positions with one double-width gap; 75 points plus that gap is 76
quarterly slots, which is 19.00 years exactly, and anchoring the last slot at
the June 2026 SEP puts the first at October 2007 -- when the SEP began -- and
the gap at March 2020, which the figure's own note says is excluded.

    python3 extract_series.py sep_original.pdf series_gold.json
"""
import json
import sys
from collections import defaultdict

import numpy as np
import pymupdf

MARK_RGB = (0.03, 0.48, 0.68)
LAST_SLOT = (2026, 6)              # the SEP this release accompanies
SKIPPED = (2020, 3)                # stated in the note to figure 4.D
PANELS_4D = ["change in real GDP", "unemployment rate", "PCE inflation",
             "core PCE inflation"]


def _quarterly_dates(n_points: int) -> list[tuple[int, int]]:
    """Slot dates, newest last, with the skipped SEP left out."""
    months, y, m = [], *LAST_SLOT
    while len(months) < n_points + 1:
        months.append((y, m))
        m -= 3
        if m < 1:
            m += 12
            y -= 1
    months.reverse()
    if SKIPPED in months:
        months.remove(SKIPPED)
    return months[-n_points:]


def series(page) -> dict[str, list[tuple[str, float]]]:
    marks = [it["rect"] for it in page.get_drawings()
             if it.get("fill")
             and tuple(round(c, 2) for c in it["fill"]) == MARK_RGB
             and 2 < it["rect"].width < 12]

    # Each x position carries exactly one marker per panel, and the panels do
    # not overlap vertically, so sorting a column top to bottom assigns them.
    # Grouping by a y modulus instead put 135 points in one panel of 4.E and 27
    # in another; the 75-point invariant caught it.
    by_x = defaultdict(list)
    for m in marks:
        by_x[round((m.x0 + m.x1) / 2, 1)].append(m)
    n_panels = max(len(v) for v in by_x.values())

    # Each panel's own -1.00 .. 1.00 axis, taken from the ticks nearest it.
    ticks = []
    for w in page.get_text("words"):
        t = w[4].replace("−", "-")
        try:
            v = float(t)
        except ValueError:
            continue
        if "." in t and -1.001 <= v <= 1.001 and w[0] > 500:
            ticks.append(((w[1] + w[3]) / 2, v))

    columns = defaultdict(list)
    for x in sorted(by_x):
        for i, m in enumerate(sorted(by_x[x], key=lambda r: r.y0)):
            columns[i].append((x, (m.y0 + m.y1) / 2))

    out = {}
    for i in sorted(columns):
        pts = columns[i]
        lo = min(y for _, y in pts) - 60
        hi = max(y for _, y in pts) + 60
        cal = sorted(t for t in ticks if lo <= t[0] <= hi)
        if len(cal) < 3:
            continue
        slope, icept = np.polyfit([a for a, _ in cal], [b for _, b in cal], 1)
        dates = _quarterly_dates(len(pts))
        name = PANELS_4D[i] if i < len(PANELS_4D) else f"panel {i}"
        out[name] = [(f"{y}-{m:02d}", round(slope * py + icept, 4))
                     for (y, m), (_, py) in zip(dates, pts)]
    return out


def main(src: str, dst: str) -> None:
    doc = pymupdf.open(src)
    gold = {}
    for i, page in enumerate(doc, start=1):
        t = page.get_text()
        for fig in ("4.D", "4.E"):
            if f"Figure {fig}." in t:
                gold[f"figure_{fig}"] = series(page)

    problems = []
    for fig, panels in gold.items():
        for name, pts in panels.items():
            if len(pts) != 75:
                problems.append(f"{fig} {name}: {len(pts)} points, expected 75")
            # The index is (higher - lower) / total, so every value is a
            # multiple of 1/N for a participant count N in the high teens.
            best = min(range(15, 21),
                       key=lambda N: np.median([abs(v * N - round(v * N)) for _, v in pts]))
            dev = float(np.median([abs(v * best - round(v * best)) for _, v in pts]))
            if dev > 0.25:
                problems.append(f"{fig} {name}: values are not multiples of 1/N "
                                f"(best N={best}, median deviation {dev:.3f})")
    if problems:
        raise SystemExit("invariant failed:\n  " + "\n  ".join(problems))

    json.dump(gold, open(dst, "w"), indent=2)
    print(f"{dst}: {len(gold)} figures, "
          f"{sum(len(p) for p in gold.values())} series of 75 quarterly points")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
