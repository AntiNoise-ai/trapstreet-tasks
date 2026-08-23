"""Measure the SEP figures from the vector paths of the ORIGINAL release.

Gold for this task cannot be read off the shipped document -- that is the point
of the task -- and must not be eyeballed either: the author's own eye-read of
one panel was 1/4/5/4/1 where the geometry says 2/5/6/4/1. So it is measured
here, from the pre-rasterisation paths, and checked against invariants the
release states in its own words: eighteen participants submitted in June, one
of them without a 2028 projection.

    python3 extract_gold.py sep_original.pdf gold_geometry.json
"""
import json
import sys
from collections import defaultdict

import pymupdf

PANELS = ["2026", "2027", "2028", "longer run"]
EXPECTED_TOTALS = {"2026": 18, "2027": 18, "2028": 17, "longer run": 18}


def axis_labels(page, y0, y1):
    words = [w for w in page.get_text("words") if y0 < (w[1] + w[3]) / 2 < y1]
    cols = defaultdict(list)
    for w in words:
        cols[round((w[0] + w[2]) / 2 / 4)].append(w)
    out = []
    for k in sorted(cols):
        ws = sorted(cols[k], key=lambda w: w[1])
        out.append((sum((w[0] + w[2]) / 2 for w in ws) / len(ws),
                    "".join(w[4] for w in ws).replace("−", "-")))
    return out


def histogram(page):
    """Filled bars are the June projections; the March outline is dashed and unfilled."""
    bars = [it["rect"] for it in page.get_drawings()
            if it.get("fill") and it["rect"].width > 8]
    by_base = defaultdict(list)
    for r in bars:
        by_base[round(r.y1, 1)].append(r)

    # A panel draws one rect per bin, empty ones included; the single tall rect
    # sharing a page with them is the panel frame, not a bar.
    by_base = {b: rs for b, rs in by_base.items() if len(rs) >= 5}
    heights = [b - r.y0 for b, rs in by_base.items() for r in rs]
    unit = min(h for h in heights if h > 1.0)          # one participant, page-wide

    panels = []
    for base in sorted(by_base):
        rs = sorted(by_base[base], key=lambda r: r.x0)
        counts = [max(0, round((base - r.y0) / unit)) for r in rs]
        labs = axis_labels(page, base + 2, base + 26)
        bins = {}
        for r, c in zip(rs, counts):
            if not c:
                continue
            xc = (r.x0 + r.x1) / 2
            bins[min(labs, key=lambda L: abs(L[0] - xc))[1]] = c
        panels.append(bins)
    return panels


def dotplot(page):
    dots = [it["rect"] for it in page.get_drawings()
            if 2.0 < it["rect"].width < 4.0 and 2.0 < it["rect"].height < 4.0]
    labs = sorted(((float(w[4]), (w[1] + w[3]) / 2) for w in page.get_text("words")
                   if "." in w[4] and w[4].replace(".", "").isdigit() and w[0] > 480),
                  key=lambda t: t[1])
    (v1, y1), (v2, y2) = labs[0], labs[-1]

    xs = sorted((d.x0 + d.x1) / 2 for d in dots)
    groups, cur = [], [xs[0]]
    for x in xs[1:]:
        if x - cur[-1] < 25:
            cur.append(x)
        else:
            groups.append(cur)
            cur = [x]
    groups.append(cur)

    out = []
    for g in groups:
        lo, hi = min(g) - 1, max(g) + 1
        counts = defaultdict(int)
        for d in dots:
            if lo <= (d.x0 + d.x1) / 2 <= hi:
                rate = v1 + ((d.y0 + d.y1) / 2 - y1) * (v2 - v1) / (y2 - y1)
                counts[f"{round(rate * 8) / 8:.3f}"] += 1
        out.append(dict(sorted(counts.items(), key=lambda kv: -float(kv[0]))))
    return out


def main(src_path: str, out_path: str) -> None:
    doc = pymupdf.open(src_path)
    gold = {}
    for i, page in enumerate(doc, start=1):
        text = page.get_text()
        if "Figure 2." in text:
            gold["figure_2"] = dict(zip(PANELS, dotplot(page)))
        for letter in "ABCDE":
            if f"Figure 3.{letter}." in text:
                panels = histogram(page)
                names = PANELS if len(panels) == 4 else PANELS[:len(panels)]
                gold[f"figure_3.{letter}"] = dict(zip(names, panels))

    problems = []
    for fig, panels in gold.items():
        for name, bins in panels.items():
            total = sum(bins.values())
            if total != EXPECTED_TOTALS[name]:
                problems.append(f"{fig} {name}: total {total}, expected {EXPECTED_TOTALS[name]}")
    if problems:
        raise SystemExit("invariant failed:\n  " + "\n  ".join(problems))

    json.dump(gold, open(out_path, "w"), indent=2, ensure_ascii=False)
    print(f"{out_path}: {len(gold)} figures, every panel sums to the stated participant count")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
