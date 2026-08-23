# pdf_chart_reading — the number was never written down

## What it measures

Whether a document pipeline can answer questions whose answers exist only as
geometry: the height of a bar against a gridline, the number of dots in a row.

The document is one Federal Reserve *Summary of Economic Projections*, the
material released after the June 2026 FOMC meeting. Pages 1, 2, 16 and 17 — the
release note, table 1, table 2 and the notes — are the original pages with
their text layer. Pages 3 to 15, every figure page, are images. Twenty-two
questions ask for figures that appear in no table and in no sentence:

> In figure 3.C, how many participants' June projections for 2026 fall in the
> 3.5–3.6 percent range?

> In figure 2, how many distinct rate levels are occupied by at least one dot
> in the longer-run column?

A parser that reaches every pixel still has to read the chart.

## Why it is built this way

This task replaces `pdf_mixed_scan`, whose premise was that half its pages
carried no text layer. That premise turned out to describe the *file* rather
than the *content*: every figure it asked for was still printed as a numeral,
so any pipeline that reached the pixels read it off the page. Three rounds of
probing against the pipeline that had scored 20/20 there — harder questions,
then eight releases and 89 pages, then charts — came back 18/18, 8/8, and
**3/12**. Only the last one is a task.

Two failure modes showed up in that third round and both are built into this
case set. The histograms draw a gridline every 2 participants, so a bar of odd
height ends between two lines and has to be interpolated: a bar of 9 was read
as 10 in three runs out of three. And asked how many participants a panel
holds, no run counted the bars — all three answered 19, because that is how
many people sit on the FOMC. Eighteen submitted in June. One run invented a
bin to make its total come out right.

The charts are vector paths in the original release. A parser cannot read a
data point out of them, but `page.get_drawings()` can measure every bar exactly,
which would make a geometry-reading solution correct by construction.
Rasterising the figure pages removes that shortcut and leaves the value as
pixels. This is disclosed in [ATTRIBUTION.md](ATTRIBUTION.md) with the code.

## Gold provenance

Counts are measured from the pre-rasterisation vector geometry by
`extract_gold.py`: a bar's height is an integer multiple of one participant's
height, a dot's centre lands on an eighth-point level. Three checks stand
behind every figure:

- every panel sums to the participant count the release states in words —
  eighteen in June, one of them without a 2028 projection;
- figure 2 and figure 3.E encode the same variable in two different chart
  types, and they agree bin for bin across all four panels;
- the counts were verified by eye at 8×.

Reading gold by eye alone was tried first and failed: one panel came out
1/4/5/4/1 against a true 2/5/6/4/1. That is the reverse of the rule the
previous task needed, where gold had to be read by eye precisely because a
parser could extract it. When the value is not text, measuring the geometry is
measurement rather than extraction, and the eye is the party that needs
checking.

`gold_geometry.json` is the measurement; `author_cases.py` writes the questions
around it, so no count is ever transcribed by hand.

The text pages were audited against the case set and answer none of it. Table 1
reports medians, central tendencies and ranges, never a count of participants;
the only counts stated in words anywhere in the document are the totals who
submitted, and no case answers with one of those. One case is deliberately
built on the gap: table 1 gives the longer-run PCE range as 2.0, while figure
3.C puts all eighteen in the bin labelled 1.9-2.0. A pipeline reading only the
text answers 2.0 and is wrong.

## Scoring

Deterministic, no LLM judge. A case scores 1.0 only if every matcher passes.

Every answer here is a small integer — a number of participants, of ranges, of
levels. That makes listing a whole distribution a winning move by accident, and
it makes "the last number wins" fail on any trailing aside. So each question
ends with:

> End your reply with a line of the form `ANSWER: <value>`.

and the judge grades that line. **A reply without one scores zero**, whatever
it says. The lenient reading this replaces took the last number in a short
reply, which silently picks 6 out of "the bar reaches 9, up from 6 in March".
The report distinguishes the two ways a reply can commit to nothing — no
ANSWER line, or no reply at all, which is what happens when a model spends its
whole output budget counting dots.

A committed answer may be spelled out (`ANSWER: nine`), and may carry the
sentence around it (`ANSWER: the 3.5-3.6 bar holds 9 participants`) — bin
labels, figure references and years are stripped before the figure is read.

Hedging fails, except on the one case where the document genuinely cannot
answer, where hedging is required *and* must name why.

## Known limitations

- **The Federal Reserve publishes the same numbers as text.** Accessible
  versions of the SEP figures list per-bin participant counts on
  federalreserve.gov. A solution with network access that identifies the
  release can look up the answers. Nothing in this task prevents that, and the
  same exposure existed in the task it replaces. It is stated here rather than
  hoped away.
- **One document, one committee.** Twenty-two questions about a single
  release's figures. What generalises is the construction, not the score.
- **Reading a chart is estimation.** A bar of 9 and a bar of 10 differ by four
  points of height. The task is deliberately at that resolution; the gold is
  exact, the reading is not, and that gap is the thing being measured.
- **Format is part of the score.** The answer contract is stated in every
  question and in this file. A model that ignores it loses the case.

## Rebuild

```bash
python3 build_document.py sep_original.pdf sep_charts.pdf
python3 extract_gold.py sep_original.pdf gold_geometry.json
python3 author_cases.py gold_geometry.json gold.cases.json
python3 build_cases.py
python3 -m pytest tests/ -q
```

`inputs/` and `expected/` are generated. Edit `author_cases.py`, not them.
