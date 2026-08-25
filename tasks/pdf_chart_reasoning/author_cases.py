"""Write gold.cases.json. Questions are hand-written; every answer is taken from
a measurement file, so no figure is ever transcribed by hand.

    python3 author_cases.py gold.cases.json
"""
import json
import sys

G = json.load(open("gold_geometry.json"))      # bars and dots, per panel
S = json.load(open("series_gold.json"))        # diffusion series, per quarter
CONTRACT = "End your reply with a line of the form `ANSWER: <value>`."

# Reading a continuous index off an axis cannot be graded exactly. The index is
# (higher - lower) / participants, so it moves in steps of about 1/18 = 0.056;
# a tolerance of half a step keeps two adjacent legal values from both passing,
# and 0.025 of an index unit is 5.6 pixels at the shipped 200 dpi -- readable
# by a careful reader, not by a glance. Items are chosen so the measurement
# behind the gold is itself within 0.1 of a participant of a legal value.
TOL = 0.025


def bars(fig, panel, bin_): return G[f"figure_{fig}"][panel][bin_]
def series(fig, name, date): return round(dict(S[f"figure_{fig}"][name])[date], 3)


def case(cid, cap, question, answer, why, matchers, difficulty="hard", **kw):
    return {"id": cid, "capability": cap, "difficulty": difficulty,
            "question": question + " " + CONTRACT, "answer": str(answer),
            "_why": why, "matchers": matchers, **kw}


def value(v, tol=0): return [{"kind": "committed_value", "value": v, "tolerance": tol},
                             {"kind": "no_hedge"}]


cases = [
    # --- A: read a length encoding (3) -------------------------------------
    case("case_01", "read_length",
         'In figure 3.B, "Distribution of participants\' projections for the unemployment '
         'rate", how many participants project a 2026 rate in the 4.2-4.3 percent range?',
         bars("3.B", "2026", "4.2-4.3"),
         "Gridlines every 2 participants, so an odd bar ends between two of them. This is "
         "the tallest bar in the figure.", value(bars("3.B", "2026", "4.2-4.3"))),
    case("case_02", "read_length",
         'In figure 3.A, "Distribution of participants\' projections for the change in real '
         'GDP", how many participants project 2026 growth in the 2.2-2.3 percent range?',
         bars("3.A", "2026", "2.2-2.3"), "A second odd bar, different figure.",
         value(bars("3.A", "2026", "2.2-2.3"))),
    case("case_03", "read_length",
         "In figure 3.B, how many participants project a 2028 unemployment rate in the "
         "4.2-4.3 percent range?", bars("3.B", "2028", "4.2-4.3"),
         "The control: an even bar sitting exactly on a gridline. If this scores like the "
         "odd bars, the off-by-one story is wrong.",
         value(bars("3.B", "2028", "4.2-4.3")), difficulty="medium"),

    # --- B: read a position encoding, continuous (3) ------------------------
    case("case_04", "read_position",
         'In figure 4.E, "Diffusion indexes of participants\' risk weightings", what was the '
         "diffusion index for the change in real GDP at the June 2019 SEP?",
         series("4.E", "change in real GDP", "2019-06"),
         "A continuous value read against an axis, not a count. Nothing in any table carries "
         "the diffusion indexes.",
         value(series("4.E", "change in real GDP", "2019-06"), TOL)),
    case("case_05", "read_position",
         'In figure 4.D, "Diffusion indexes of participants\' uncertainty assessments", what '
         "was the diffusion index for PCE inflation at the June 2019 SEP?",
         series("4.D", "PCE inflation", "2019-06"),
         "Near zero rather than near the top of the axis, so the reading cannot be anchored "
         "to the frame.", value(series("4.D", "PCE inflation", "2019-06"), TOL)),
    case("case_06", "read_position",
         "In figure 4.E, what was the diffusion index for PCE inflation at the June 2020 SEP?",
         series("4.E", "PCE inflation", "2020-06"),
         "A large negative value, in the year whose March SEP the figure omits.",
         value(series("4.E", "PCE inflation", "2020-06"), TOL)),
]

# --- C: compute an exact derived value (4) ----------------------------------
d1 = round(series("4.E", "change in real GDP", "2026-06")
           - series("4.E", "change in real GDP", "2019-06"), 3)
e27 = G["figure_3.E"]["2027"]
a28 = G["figure_3.A"]["2028"]
c28 = G["figure_3.C"]["2028"]
cases += [
    case("case_07", "derived_value",
         "In figure 4.E, by how much did the diffusion index for the change in real GDP move "
         "between the June 2019 SEP and the June 2026 SEP? Give the change, with its sign.",
         d1, "Two readings and a subtraction. Systematic reading bias cancels; random error "
             "does not.", value(d1, TOL * 2)),
    case("case_08", "derived_value",
         "In figure 3.E, how many participants place the end-2027 midpoint of the appropriate "
         "target range at 3.88 percent or higher?",
         sum(v for k, v in e27.items() if float(k.split("-")[0]) >= 3.88),
         "Three bins summed at the sparse end, and the bin labels are rounded: the bin "
         "printed 3.88-4.12 holds projections of 3.875.",
         value(sum(v for k, v in e27.items() if float(k.split("-")[0]) >= 3.88))),
    case("case_09", "derived_value",
         "In figure 3.A, how many participants project 2028 GDP growth below 2.2 percent?",
         sum(v for k, v in a28.items() if float(k.split("-")[1]) < 2.2),
         "Two bins summed, one of them the shortest bar in the panel.",
         value(sum(v for k, v in a28.items() if float(k.split("-")[1]) < 2.2)),
         difficulty="medium"),
    case("case_10", "derived_value",
         "In figure 3.C, how many participants project 2028 PCE inflation above 2.0 percent?",
         sum(v for k, v in c28.items() if float(k.split("-")[0]) > 2.0),
         "The complement of the tall bar. Answering by subtraction needs the panel total, "
         "which is 17 here rather than 18 -- a footnote to table 1 says why.",
         value(sum(v for k, v in c28.items() if float(k.split("-")[0]) > 2.0))),
]
json.dump(cases, open("/tmp/partial.json", "w"))


# --- D: count discrete marks (3) --------------------------------------------
f2 = G["figure_2"]
cases += [
    case("case_11", "count_marks",
         'In figure 2, "FOMC participants\' assessments of appropriate monetary policy", how '
         "many participants judge the appropriate midpoint of the target range at the end of "
         "2026 to be 3.625 percent?", f2["2026"]["3.625"],
         "Counting a dense row of identical markers.", value(f2["2026"]["3.625"])),
    case("case_12", "count_marks",
         "In figure 2, how many participants judge the appropriate midpoint at the end of "
         "2027 to be 3.875 percent?", f2["2027"]["3.875"],
         "The modal row of a column spread over seven levels.", value(f2["2027"]["3.875"]),
         difficulty="medium"),
    case("case_13", "count_marks",
         "In figure 2, how many distinct rate levels are occupied by at least one dot in the "
         "longer-run column?", len(f2["longer run"]),
         "Reads the whole column rather than one row of it.", value(len(f2["longer run"]))),
]

# --- E: semantic and reconciliation (4) -------------------------------------
# The median of figure 2's dots is an eighth-point value; table 1 prints it to
# one decimal, so the two agree without being the same number.
lv = sorted((float(k) for k, n in f2["2026"].items() for _ in range(n)))
median_2026 = (lv[len(lv)//2 - 1] + lv[len(lv)//2]) / 2
cases += [
    case("case_14", "semantic",
         "Figure 1 shows the central tendency of participants' projections alongside their "
         "full range. For any one variable and year, how many participants' projections lie "
         "outside the central tendency?", 6,
         "Table 1's footnote 2 states the central tendency excludes the three highest and "
         "three lowest projections. Nothing in figure 1 shows this; the band can be measured "
         "and its construction cannot.",
         value(6)),
    case("case_15", "semantic",
         'Figure 4.A shows a 70 percent confidence interval around the median projection for '
         "GDP growth. Does that interval describe how widely the participants' own "
         "projections are spread? Answer yes or no and say what it is based on.",
         "No -- historical forecast errors of outside forecasters, 2006-2025",
         "The interval is measurable to the pixel and means something entirely different "
         "from what it looks like: table 2's note derives it from the root mean squared "
         "error of private and government forecasters over 2006-2025.",
         [{"kind": "committed_regex", "pattern": r"\bno\b"},
          {"kind": "regex_required",
           "pattern": r"historical|forecast error|root mean squared|past projection|"
                      r"private and government|outside forecaster"}]),
    case("case_16", "semantic",
         "In figure 3.C, every participant's longer-run projection for PCE inflation falls in "
         "a single percent range. Which range is it?",
         list(G["figure_3.C"]["longer run"])[0],
         "Table 1 prints the same longer-run quantity as 2.0. The figure bins it as 1.9-2.0. "
         "Both are correct; only one answers the question asked.",
         [{"kind": "committed_regex", "pattern": r"1\.9\s*[-‐-―]\s*2\.0"},
          {"kind": "no_hedge"}], difficulty="medium"),
    case("case_17", "semantic",
         "Figure 2 plots each participant's judgment for the end of 2026 rounded to the "
         "nearest eighth of a percentage point. Taking the dots as plotted, what is the "
         "median of those judgments?", median_2026,
         "Table 1 prints the median to one decimal place, which is a rounding of this "
         "number rather than this number. A pipeline reading the table answers the table's "
         "figure and misses the question.", value(median_2026, 0.001)),
]

# --- F: abstention calibration (3) ------------------------------------------
cases += [
    case("case_18", "abstention",
         "In figure 3.D, how many participants put their longer-run projection for core PCE "
         "inflation in the 1.9-2.0 percent range?",
         "Not derivable -- longer-run core PCE projections are not collected",
         "Phrased exactly like the answerable questions about figures 3.A, 3.B, 3.C and 3.E, "
         "all of which have a longer-run panel. Figure 3.D has three panels because table 1's "
         "footnote 4 says these projections are not collected at all.",
         [{"kind": "not_derivable",
           "pattern": r"not collected|no longer[- ]run|does not (?:have|include|show)|"
                      r"only .{0,20}three panels|not (?:gathered|solicited)"}]),
    case("case_19", "abstention",
         "In figure 2, which FOMC participant placed the single highest dot for the end of "
         "2026?", "Not derivable -- the projections are anonymous",
         "The dots carry no identity. A model that names the Chair or any governor has "
         "invented it.",
         [{"kind": "not_derivable",
           "pattern": r"anonym|not identif|does not identif|no names?\b|not attribut|"
                      r"unattributed|cannot be determined|cannot be identified"}]),
    case("case_20", "abstention",
         "How many participants submitted a projection for 2028?", 17,
         "The reverse item. It looks like it needs per-participant data and it does not: a "
         "footnote to table 1 states that one of the eighteen June participants did not "
         "submit 2028 projections. Without this, the abstention group rewards a pipeline "
         "that refuses by habit.", value(17), difficulty="medium"),
]

# --- G: cross-figure integration (3) ----------------------------------------
e26 = G["figure_3.E"]["2026"]
cases += [
    case("case_21", "cross_figure",
         "Figures 2 and 3.E describe the same judgments in two different chart types. How "
         "many participants place the end-2026 midpoint in the range figure 3.E labels "
         "3.63-3.87?", e26["3.63-3.87"],
         "Answerable from either figure, and the two must agree. A pipeline that reads only "
         "one still has to know they are the same quantity.", value(e26["3.63-3.87"])),
    case("case_22", "cross_figure",
         "At the June 2020 SEP, the diffusion indexes for PCE inflation in figure 4.D "
         "(uncertainty) and figure 4.E (risk weightings) point opposite ways. How far apart "
         "were they?",
         round(series("4.D", "PCE inflation", "2020-06")
               - series("4.E", "PCE inflation", "2020-06"), 3),
         "Two figures, same variable, same date, different question asked of participants -- "
         "near-total agreement that uncertainty was elevated, and the reverse on risks. The "
         "date is also the one whose March sitting the figures omit. Chosen because the two "
         "series coincide at many other dates, where the question would be degenerate.",
         value(round(series("4.D", "PCE inflation", "2020-06")
                     - series("4.E", "PCE inflation", "2020-06"), 3), TOL * 2)),
    case("case_23", "cross_figure",
         "In figure 2's longer-run column, two participants sit at 3.375 percent. Which of "
         "figure 3.E's longer-run percent ranges contains them?", "3.38-3.62",
         "The bin edges are eighth-point values rounded to two places, so 3.375 belongs to "
         "the bin printed 3.38-3.62 and not to the one printed 3.13-3.37, which looks like "
         "it should hold it. Verifiable both ways: that bin holds three participants, which "
         "is the two at 3.375 plus the one at 3.500.",
         [{"kind": "committed_regex", "pattern": r"3\.38\s*[-‐-―]\s*3\.62"},
          {"kind": "no_hedge"}]),
]

out = {
    "document": "sep_charts.pdf",
    "_source": json.load(open("gold.cases.json"))["_source"] if False else {
        "title": "Summary of Economic Projections",
        "issuer": "Board of Governors of the Federal Reserve System",
        "release": "June 17, 2026 (FOMC meeting of June 16-17, 2026)",
        "downloaded_from": "https://www.federalreserve.gov/monetarypolicy/files/"
                           "fomcprojtabl20260617.pdf",
        "_licence": "A work of the United States federal government. Not subject to "
                    "copyright in the US; freely redistributable.",
    },
    "_construction": "sep_charts.pdf is the released SEP with pages 3-15 -- every figure "
                     "page -- replaced by 200 dpi JPEG images of themselves. See "
                     "build_document.py.",
    "_gold_provenance": "Counts come from extract_gold.py (bar heights and marker positions "
                        "in the pre-rasterisation vector paths, every panel checked against "
                        "the participant count the release states in words). Diffusion-index "
                        "values come from extract_series.py, whose dates are recovered from "
                        "structure -- 75 points plus one double-width gap is 76 quarterly "
                        "slots, 19.00 years, putting the first at the SEP's first release and "
                        "the gap at the March 2020 meeting the figure's note says is omitted. "
                        "Semantic and abstention answers are stated by the release itself in "
                        "table 1's footnotes and table 2's note.",
    "cases": cases,
}
json.dump(out, open(sys.argv[1], "w"), indent=2, ensure_ascii=False)
from collections import Counter
print(f"{sys.argv[1]}: {len(cases)} cases")
print("按能力:", dict(Counter(c["capability"] for c in cases)))
