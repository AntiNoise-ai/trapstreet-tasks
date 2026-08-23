"""Write gold.cases.json. Questions are hand-written; every answer is taken
from gold_geometry.json, so no figure is ever transcribed by hand.

    python3 author_cases.py gold_geometry.json gold.cases.json
"""
import json
import sys

G = json.load(open(sys.argv[1]))
CONTRACT = "End your reply with a line of the form `ANSWER: <value>`."


def n(fig, panel, bin_):
    return G[fig][panel][bin_]


def total(fig, panel, pred):
    return sum(c for b, c in G[fig][panel].items() if pred(b))


def count_case(cid, fig, panel, bin_, question, why, difficulty="medium"):
    value = n(fig, panel, bin_)
    return {
        "id": cid, "figure": fig, "panel": panel, "type": "bin_count",
        "difficulty": difficulty, "question": question + " " + CONTRACT,
        "answer": str(value), "_why": why,
        "matchers": [{"kind": "committed_value", "value": value, "tolerance": 0},
                     {"kind": "no_hedge"}],
    }


def value_case(cid, fig, panel, value, question, why, type_, difficulty="hard", extra=None,
               compound=False):
    kind = "committed_has_value" if compound else "committed_value"
    m = [{"kind": kind, "value": value, "tolerance": 0}, {"kind": "no_hedge"}]
    return {"id": cid, "figure": fig, "panel": panel, "type": type_,
            "difficulty": difficulty, "question": question + " " + CONTRACT,
            "answer": str(value), "_why": why, "matchers": m + (extra or [])}


ODD = ("The gridlines are drawn every 2 participants, so a bar of odd height ends "
       "between two of them and has to be interpolated. Sonnet 5 read a bar of 9 as "
       "10 in all three probe runs.")
PRIOR = ("Eighteen participants submitted in June and the release says so in a footnote "
         "to table 1. A model answering from what it knows about the FOMC says 19.")

cases = [
    count_case("case_01", "figure_3.C", "2026", "3.5-3.6",
               'In figure 3.C, "Distribution of participants\' projections for PCE inflation", '
               "how many participants' June projections for 2026 fall in the 3.5-3.6 percent range?",
               ODD, "hard"),
    count_case("case_02", "figure_3.C", "2027", "2.3-2.4",
               "In figure 3.C, how many participants' June projections for 2027 fall in the "
               "2.3-2.4 percent range?",
               "The tallest bar in a panel where four of the five bars are within two of each other."),
    count_case("case_03", "figure_3.A", "2026", "2.2-2.3",
               'In figure 3.A, "Distribution of participants\' projections for the change in real '
               'GDP", how many participants project 2026 growth in the 2.2-2.3 percent range?',
               ODD, "hard"),
    count_case("case_04", "figure_3.A", "longer run", "2.0-2.1",
               "In figure 3.A, how many participants put their longer-run projection for the change "
               "in real GDP in the 2.0-2.1 percent range?",
               "Two-thirds of the panel in one bar, which invites rounding to the participant count."),
    count_case("case_05", "figure_3.B", "2026", "4.2-4.3",
               'In figure 3.B, "Distribution of participants\' projections for the unemployment '
               'rate", how many participants project a 2026 unemployment rate of 4.2-4.3 percent?',
               ODD + " This bar is 13, the tallest in the figure.", "hard"),
    count_case("case_06", "figure_3.B", "2028", "4.2-4.3",
               "In figure 3.B, how many participants project a 2028 unemployment rate in the "
               "4.2-4.3 percent range?",
               "An even bar, sitting exactly on a gridline -- the control for the odd-bar cases."),
    count_case("case_07", "figure_3.D", "2026", "3.3-3.4",
               'In figure 3.D, "Distribution of participants\' projections for core PCE inflation", '
               "how many participants project 2026 core inflation in the 3.3-3.4 percent range?",
               "Even bar in a panel whose other bars are 1, 3 and 4."),
    count_case("case_08", "figure_3.E", "2026", "3.63-3.87",
               'In figure 3.E, "Distribution of participants\' judgments of the midpoint of the '
               'appropriate target range for the federal funds rate", how many participants place '
               "the end-2026 midpoint in the 3.63-3.87 percent range?",
               ODD + " Figure 2 encodes the same eight participants as dots at 3.625.", "hard"),
    count_case("case_09", "figure_3.A", "2027", "2.2-2.3",
               "In figure 3.A, how many participants project 2027 GDP growth in the 2.2-2.3 percent "
               "range?", ODD, "hard"),
    count_case("case_10", "figure_3.C", "2028", "1.9-2.0",
               "In figure 3.C, how many participants project 2028 PCE inflation in the 1.9-2.0 "
               "percent range?",
               "Twelve of seventeen in one bar; the panel total is 17, not 18, and the release "
               "explains why in a footnote."),

    value_case("case_11", "figure_2", "2026", G["figure_2"]["2026"]["3.625"],
               'In figure 2, "FOMC participants\' assessments of appropriate monetary policy", how '
               "many participants judge the appropriate midpoint of the target range at the end of "
               "2026 to be 3.625 percent?",
               "Counting a dense row of dots. Two of three probe runs answered 9.",
               "dot_count"),
    value_case("case_12", "figure_2", "2027", G["figure_2"]["2027"]["3.875"],
               "In figure 2, how many participants judge the appropriate midpoint at the end of "
               "2027 to be 3.875 percent?",
               "The modal row of a column spread across seven levels.", "dot_count", "medium"),
    value_case("case_13", "figure_2", "longer run", G["figure_2"]["longer run"]["3.000"],
               "In figure 2, how many participants put their longer-run value for the federal funds "
               "rate at 3.0 percent?",
               "The longer-run column uses levels the other columns do not, including whole and "
               "eighth-point values.", "dot_count"),
    value_case("case_14", "figure_2", "longer run", len(G["figure_2"]["longer run"]),
               "In figure 2, how many distinct rate levels are occupied by at least one dot in the "
               "longer-run column?",
               "Requires reading the whole column, not one row of it. Nine levels hold dots.",
               "dot_structure"),
    value_case("case_15", "figure_2", "2028",
               G["figure_2"]["2028"]["3.125"] + G["figure_2"]["2028"]["2.875"],
               "In figure 2, how many participants judge the appropriate midpoint at the end of "
               "2028 to be 3.125 percent or lower?",
               "Two rows summed, with the boundary level included.", "dot_aggregate"),

    value_case("case_16", "figure_3.E", "2027",
               total("figure_3.E", "2027", lambda b: float(b.split("-")[0]) >= 3.88),
               "In figure 3.E, how many participants place the end-2027 midpoint of the appropriate "
               "target range at 3.88 percent or higher?",
               "Three bins summed at the sparse end of the panel.", "bin_aggregate"),
    value_case("case_17", "figure_3.A", "2028",
               total("figure_3.A", "2028", lambda b: float(b.split("-")[1]) < 2.2),
               "In figure 3.A, how many participants project 2028 GDP growth below 2.2 percent?",
               "Two bins summed, one of them the shortest bar in the panel.", "bin_aggregate",
               "medium"),
    value_case("case_18", "figure_3.C", "2028",
               total("figure_3.C", "2028", lambda b: float(b.split("-")[0]) > 2.0),
               "In figure 3.C, how many participants project 2028 PCE inflation above 2.0 percent?",
               "The complement of the tall bar; answering by subtraction needs the panel total, "
               "which is 17 here rather than 18.", "bin_aggregate"),
    value_case("case_19", "figure_3.B", "longer run",
               sum(1 for c in G["figure_3.B"]["longer run"].values() if c >= 2),
               "In figure 3.B, how many separate percent ranges hold two or more participants in "
               "the longer-run panel?",
               "A count of bars meeting a threshold rather than a count of participants.",
               "bin_structure"),
    value_case("case_20", "figure_3.D", "2028", G["figure_3.D"]["2028"]["1.9-2.0"],
               "In figure 3.D, two percent ranges are tied for the most participants in the 2028 "
               "panel. Name both ranges and give the number of participants in each.",
               "A tie between two bars of equal height, which is only visible if both are read.",
               "bin_structure", compound=True, extra=[
                   {"kind": "regex_required", "pattern": r"1\.9\s*[-‐-―]\s*2\.0"},
                   {"kind": "regex_required", "pattern": r"2\.1\s*[-‐-―]\s*2\.2"}]),
]

cases.append({
    "id": "case_21", "figure": "figure_3.C", "panel": "longer run", "type": "bin_structure",
    "difficulty": "medium",
    "question": "In figure 3.C, every participant's longer-run projection for PCE inflation falls "
                "in a single percent range. Which range is it? " + CONTRACT,
    "answer": list(G["figure_3.C"]["longer run"])[0],
    "_why": "A one-bar panel: the answer is the label, and the bar's height is the entire "
            "participant count. " + PRIOR,
    "matchers": [{"kind": "committed_regex", "pattern": r"1\.9\s*[-‐-―]\s*2\.0"},
                 {"kind": "no_hedge"}],
})

cases.append({
    "id": "case_22", "figure": "figure_2", "panel": "2026", "type": "not_derivable",
    "difficulty": "hard",
    "question": "In figure 2, which FOMC participant placed the single highest dot for the end of "
                "2026? " + CONTRACT,
    "answer": "Not derivable -- the projections are anonymous.",
    "_why": "The dots carry no identity, and the release states the projections are submitted "
            "without attribution. A model that names the Chair or any governor has invented it.",
    "matchers": [{"kind": "not_derivable",
                  "pattern": r"anonym|not identif|does not identif|no names?\b|not attribut|"
                             r"unattributed|cannot be determined|cannot be identified|"
                             r"not possible to (?:say|tell|determine|identify)"}],
})

out = {
    "document": "sep_charts.pdf",
    "_source": {
        "title": "Summary of Economic Projections",
        "issuer": "Board of Governors of the Federal Reserve System",
        "release": "June 17, 2026 (FOMC meeting of June 16-17, 2026)",
        "downloaded_from": "https://www.federalreserve.gov/monetarypolicy/files/"
                           "fomcprojtabl20260617.pdf",
        "_licence": "A work of the United States federal government. Not subject to copyright "
                    "in the US; freely redistributable.",
    },
    "_construction": "sep_charts.pdf is the released SEP with pages 3-15 -- every figure page -- "
                     "replaced by 200 dpi JPEG images of themselves. Pages 1, 2, 16 and 17 (the "
                     "release note, table 1, table 2 and the notes) are byte-for-byte the "
                     "original. Nothing is added, removed or reordered. The charts are vector "
                     "paths in the original, which a parser cannot read a data point out of but "
                     "CAN measure exactly with page.get_drawings(); rasterising removes that "
                     "shortcut, leaving the value as pixels only. See build_document.py.",
    "_gold_provenance": "Every count is measured from the pre-rasterisation vector geometry by "
                        "extract_gold.py: a bar's height is an integer multiple of one "
                        "participant, a dot's centre lands on an eighth-point level. Three "
                        "independent checks: every panel sums to the participant count the "
                        "release states in words (eighteen in June, one without a 2028 "
                        "projection); figure 2 and figure 3.E encode the same variable and agree "
                        "bin for bin across all four panels; and the counts were verified by eye "
                        "at 8x. Reading gold by eye alone was tried and failed -- one panel came "
                        "out 1/4/5/4/1 against a true 2/5/6/4/1.",
    "_answer_contract": "Every question asks for a line of the form `ANSWER: <value>`. Counts here "
                        "are small integers, so an answer that lists a whole distribution would "
                        "otherwise contain the right number by accident; the contract is what "
                        "makes the grading exact instead of positional.",
    "cases": cases,
}
json.dump(out, open(sys.argv[2], "w"), indent=2, ensure_ascii=False)
print(f"{sys.argv[2]}: {len(cases)} cases")
