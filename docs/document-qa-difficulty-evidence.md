# What makes a document-QA question hard

Evidence collected while raising the difficulty of `pdf_mixed_scan`, whose top
solution had reached 20/20. The question was where to spend the authoring
effort. The literature answers it more cleanly than intuition does, and it
contradicts the obvious move.

Everything below is quoted from the papers themselves, with the model each
number belongs to. Numbers copied out of secondary summaries were discarded.

## The headline: difficulty is perception and absence, not arithmetic

MMLongBench-Doc hand-classified 72 of GPT-4o's errors:

| Error type | Share |
|---|---|
| Hallucinated evidence | 33% |
| Perceptual error | 28% |
| Irrelevant answer | 11% |
| Extractor error | 10% |
| Incomplete evidence (cross-page) | 10% |
| **Reasoning error** | **5%** |
| Knowledge lacking | 3% |

Making a question require more arithmetic attacks the 5%. Two thirds of the
failures are the model inventing evidence or misreading what is in front of
it — which is a property of *what you ask it to find*, not of *what you ask it
to compute*.

## Levers that work, ranked by measured effect

### 1. Ask for something that is not in the document

The single largest gap in the literature. MMLongBench-Doc makes 223 of 1,091
questions (22.5%) unanswerable on purpose, to catch hallucination:

| Model | Single-page | Cross-page | **Unanswerable** |
|---|---|---|---|
| GPT-4o | 54.5 | 41.5 | **20.2** |
| GPT-4V | 36.4 | 27.0 | 31.2 |
| Claude-3 Opus | 25.6 | 13.8 | **7.6** |
| Gemini-1.5-Pro | 21.1 | 11.1 | **69.2** |

Two things to take from this. First, for the aggressive-answering families the
unanswerable column is catastrophic — GPT-4o loses 34 points against its own
single-page score, Claude-3 Opus loses 18 of its 25. The paper names the
mechanism: "GPT-4o and Claude-3 Opus adopt more aggressive strategies and
usually tend to provide some answers." Second, Gemini-1.5-Pro's 69.2 is not
skill, it is a refusal habit — the same habit costs it everywhere else.

So unanswerable questions measure answer *policy* as much as reading. They only
work inside a set that also punishes refusing an answerable question. Score
both directions or you are paying models to say "I don't know."

### 2. Aggregate over a group; don't look up a cell

FinSheet-Bench (March 2026) is the most useful table for this, because it holds
the document constant and varies only the operation, on frontier models:

| Category | Complexity | All 10 models | Top 3 |
|---|---|---|---|
| Simple lookup | Low | 89.1% | 93.6% |
| List extraction | Medium | 85.5% | 93.3% |
| Filtering | Medium | 70.9% | 84.1% |
| Sorting | High | 37.5% | 79.2% |
| Aggregation | High | 53.7% | 76.2% |
| **Counting** | Medium | 41.7% | **66.7%** |
| **Complex aggregation** | Very high | 19.6% | **33.3%** |

Top 3 = Gemini 3.1 Pro, GPT-5.2 with reasoning, Claude Opus 4.6 with thinking.
"Complex aggregation" means something like *median net debt/EBITDA across all
funds* — a group statistic over a set the model has to assemble first.

A lookup question and a complex-aggregation question on the same table are 60
points apart for the best models available. Nothing else in this note comes
close to that spread.

### 3. Counting is not a lookup

41.7% pooled, 66.7% for the top three — worse than sorting, worse than
aggregation, on questions the benchmark itself classifies as only *medium*
complexity. The paper's explanation is that counting requires finding the
boundaries of the set first, and boundary detection is where it breaks.

### 4. Ranking by magnitude, not membership

Sorting scores 37.5% pooled while list extraction scores 85.5% on the same
data. The authors put it plainly: models "can identify what is in a list but
struggle with ordering by magnitude."

### 5. Spread the evidence across pages

Every model in MMLongBench-Doc scores lower on cross-page than on single-page
questions — GPT-4o 41.5 vs 54.5, and the ordering holds for all 24 systems
evaluated. Incomplete evidence gathering is separately visible as 10% of its
errors.

### 6. Make the table bigger, not the formula longer

FinSheet-Bench's largest file (152 companies, 8 funds) averages **48.6%**
across all models against **86.2%** on the easiest one. Same question
categories; only the amount of material changed.

MMLongBench-Doc measures the same thing from the other side. Given only the
oracle evidence pages instead of the whole document, Gemini-1.5-Pro and
InternLM-XC2-4KHD gain more than 20 absolute points (up to 30 on single-page
questions); GPT-4o gains about 10. Long context is a difficulty axis in itself,
independent of the question.

### 7. If the pipeline goes through OCR, noise cascades

OHR-Bench (ICCV 2025) separates semantic noise from formatting noise and finds
that even the best OCR solutions lose about 14 F1 overall once the pipeline is
end-to-end. Worth knowing, but it is a property of the *pipeline* under test,
not of the question — it hits OCR-based solutions and leaves vision-model ones
alone, so it compresses a leaderboard rather than raising its ceiling.

## What does not discriminate at the top

**Which modality holds the evidence.** GPT-4o on MMLongBench-Doc, by evidence
source: text 46.3, layout 46.0, chart 45.3, table 50.0, figure 44.1 — a
six-point band, and tables are its *best* source. Weaker models do show the
expected chart penalty (Mixtral-8x22B: text 34.2, chart 19.5), which is where
the widely-repeated "charts are hardest" claim comes from. It is a statement
about 2024 open models, not about frontier ones. Moving a question into a chart
or a table will not lower a frontier ceiling.

**More reasoning steps.** 5% of errors. Adding a fourth arithmetic operation to
a three-operation question is close to free for the model and expensive for the
author.

**The benchmark's own ceiling.** MMLongBench-Doc's human experts score 65.8
accuracy / 66.0 F1. A task can be too hard to be informative; if humans are at
66 the instrument is measuring its own ambiguity as much as the model.

## Rejected during collection

- *Your Vision-Language Model Can't Even Count to 20* (arXiv 2510.04401) is
  about counting geometric shapes in synthetic images. It supports "VLMs cannot
  count" in general, but nothing about counting rows in a table, and the
  abstract reports no per-model numbers. FinSheet-Bench's 66.7% carries that
  claim properly.
- "Borderless tables produce 2x more hallucinations" appears in several
  round-up posts with no traceable source. Dropped.
- MMTabReal's per-error-type percentages are measured on GPT-4o-mini and
  Qwen2.5-VL. Its headline — 20–40% drops relative to existing benchmarks on
  real-world multimodal tables — stands; the error breakdown does not transfer
  to frontier models.

## Rules we took away

1. **Ask for what is absent.** Score abstention explicitly, and keep answerable
   twins in the set so refusing never pays.
2. **Prefer a group statistic to a cell.** Median, ratio of ratios, share of a
   subset the model must assemble — not one more division.
3. **Count and rank.** Both are documented weak spots and both are cheap to
   author and to grade.
4. **Spread evidence across pages, not across steps.**
5. **Scale the material, not the formula.**
6. **Do not rely on modality alone** — putting a figure in a scan buys nothing
   against a vision model that renders every page anyway.

## Sources

| Source | Venue | Used for |
|---|---|---|
| [MMLongBench-Doc](https://mayubo2333.github.io/MMLongBench-Doc/) ([paper](https://proceedings.neurips.cc/paper_files/paper/2024/file/ae0e43289bffea0c1fa34633fc608e92-Paper-Datasets_and_Benchmarks_Track.pdf)) | NeurIPS 2024 D&B | Error taxonomy, unanswerable/cross-page/evidence-source tables, oracle-page comparison, human baseline |
| [FinSheet-Bench](https://arxiv.org/pdf/2603.07316) | arXiv, March 2026 | Accuracy by question category on frontier models; file-complexity effect |
| [OHR-Bench / OCR Hinders RAG](https://arxiv.org/html/2412.02592v4) | ICCV 2025 | OCR noise cascading into end-to-end accuracy |
| [MMTabReal](https://arxiv.org/pdf/2505.21771) | arXiv 2025 | Headline drop on real-world multimodal tables |
| [DocMath-Eval](https://docmath-eval.github.io/) | ACL 2024 | Evidence-retrieval ceiling; unit-transformation and domain-convention error classes |
| [TableBench](https://arxiv.org/abs/2408.09174) | AAAI 2025 | Category structure for numerical-reasoning table QA |

## What happened when we tested these levers

Six probe questions on `pdf_mixed_scan`, one per lever, three repeats each,
against the pipeline that already scored 20/20 (pdf-inspector-routed, Claude
Sonnet 5, whole document per call, scan pages rendered at 150 dpi). $1.37.

**18 of 18 correct.** Not one lever survived:

| Probe | Lever | Result |
|---|---|---|
| Median Federal Reserve notes, net across the 12 Districts | Complex aggregation | 3/3 — sorted all twelve, returned 123,028.5 exactly |
| Positive interdistrict settlement balances | Counting + detached signs | 3/3 — listed all twelve with correct signs, answered 4 |
| Third-largest District by total liabilities and capital | Ranking | 3/3 — Richmond, 516,387 |
| New York's Treasuries maturing within 15 days | Not derivable | 3/3 — refused, and explained that table 2 is System-wide while table 6 lumps Treasuries in with repos and loans |
| Chicago's earnings remittances a year earlier | Not derivable | 3/3 — refused, named the missing column |
| Rank three Federal Reserve note conventions across three tables | Cross-page, both layers | 3/3 — correct order and spread |

The two not-derivable probes are the interesting failure of the literature to
transfer. MMLongBench-Doc has Claude-3 Opus at **7.6** on unanswerable
questions against 25.6 on single-page ones — the sharpest instrument in the
whole survey, aimed squarely at this model family. Sonnet 5 abstained cleanly
six times out of six, and in one answer volunteered the System-wide 2.5%
figure *while explaining why it cannot be applied to New York*. Two years of
model progress had closed the gap the benchmark was built to expose.

### What the negative result actually says

The lever we did not have was the one FinSheet-Bench and MMLongBench both
point at, and it is not a question property at all:

- FinSheet-Bench: largest file 48.6%, easiest file 86.2% — **same categories,
  more material**.
- MMLongBench-Doc: feeding only the oracle evidence pages instead of the whole
  document is worth more than 20 absolute points — **same questions, less
  material**.

Our document is 11 pages holding one table 12 columns wide. On material that
small a frontier VLM is not perception-limited, so operation-difficulty has
nothing to bite on. Counting is hard at 152 companies across 8 funds; it is not
hard at 12 Districts you can see at once.

**The transferable lesson: check where your instrument sits on the scale axis
before you spend effort on the question axis.** Everything in the ranked list
above is real, and none of it applies below some threshold of material. Six
questions and $1.37 established that; eight hand-authored cases would have
established the same thing for a great deal more work.

## Round two: scaling the material also failed

The negative result above pointed at scale, so we built the scaled version:
eight consecutive weekly H.4.1 releases concatenated into one 89-page PDF (41
text pages, 48 scanned), and asked four questions that only work if you can
tell the weeks apart. Near-identical pages, and figures that move less than
1.5% from week to week. 174,505 input tokens per call, $0.53 a call, $4.24 for
the round.

**8 of 8 correct.**

| Probe | Result |
|---|---|
| Lowest system Deposits across the eight weeks | 2/2 — all eight values listed correctly, answered Aug 19, 4,123,512 |
| How many weeks below a threshold | 2/2 — answered 2, and correctly excluded the week that equals the threshold |
| Median of notes outstanding across eight weeks | 2/2 — 2,827,381.5, with the sort shown |
| Look up one figure in one named week | 2/2 — 959,405, from the release that carries an extra notice page and is shifted one page from all the others |

Two rounds, 26 of 26. On this genre of document a frontier vision model at 150
dpi is not perception-limited, not aggregation-limited, and not
disambiguation-limited at 175k tokens.

### Where that leaves the scale lever

FinSheet-Bench's collapse to 48.6% happens on one spreadsheet with 152
companies across 8 funds. Eight weeks of H.4.1 is not that; it is eight copies
of a small table. Reaching FinSheet's regime here would mean 30–50 releases,
which is past the context window — and past the window the failure stops being
"answers wrong" and becomes "the request errors". That is a real and
interesting task (it forces a retrieval architecture instead of
whole-document prompting, and DocMath-Eval's finding that under 70% of gold
evidence is retrieved in the top 10 says retrieval is where the difficulty
moved), but it is a different instrument, not a harder version of this one.

### The one axis never tested

Both rounds used clean synthetic rasters — pages rendered at 200 dpi from a
digital original, which is the best-case image a scan can be. Perception is 28%
of frontier errors in MMLongBench-Doc's taxonomy, and it is the only lever
these probes never touched, because our scan has none of what makes a real
scan hard: skew, sensor noise, JPEG ringing, threshold artefacts, bleed-through.

That is worth stating as a general lesson. **"It is an image" is not a
difficulty axis. "It is a bad image" might be** — and if you build a synthetic
scan you have quietly opted out of the entire perception axis while believing
you were testing it.

## Choosing the document

Two rounds of probes established that our questions were not the problem. The
next question is which documents are hard in the first place — and the
literature is unusually direct about it, because several benchmarks report
accuracy per document type on the same systems.

### Difficulty is concentrated in document type, not spread evenly

RealDocBench evaluates nine parsing systems on 1,356 field-level questions
across four regulated domains, and the per-domain table is the clearest
statement of the point:

| Domain | Best system | Weakest | Spread among strong systems |
|---|---|---|---|
| Mortgage (clean fillable forms) | 97.5% | 71.6% | ~5 points — "nearly saturated" |
| Supply chain | 97.6% | 77.0% | moderate |
| Finance | 92.7% | 68.4% | **~10 points — most discriminative** |
| Medical/healthcare | 89.8% | 46.9% | **hardest domain outright** |

Per-field accuracy, full bank. The paper's own summary: "difficulty is
concentrated, not uniform: medical documents and finance forms are where
systems diverge, while clean mortgage forms are nearly saturated."

What makes medical hardest is named explicitly — **handwritten case-report
forms, autopsy reports, and consent forms with checkbox grids**. Not length,
not layout complexity in the abstract.

### The answer must not be printed anywhere as a numeral

This is the sharpest property, and the easiest to overlook when picking a
document. On *clean, undegraded* charts, frontier models sit at ChatGPT-4o
70%, Claude Sonnet 4 76%, Gemini 2.5 Pro 88% — a chart question is unsaturated
before you do anything to it, because the value has to be estimated from
geometry rather than read. Under blur it collapses further (Claude Sonnet 4 to
45% under motion blur, 51% under defocus), and the models stay confident
throughout, "generating answers even when the charts were indistinguishable to
humans."

A statistical table prints every number it contains. A chart does not. That
difference is worth more than any question design applied to the table.

### Length matters, but only in image form

Document Haystack plants key–value needles in documents of 5 to 200 pages:
VLMs exceed **90%** retrieving from 200 pages of *text*, drop about **30
points** when the same documents arrive as *images*, and fall to about **40%**
when the needle combines text and image. Length alone is not the axis; length
in image form is.

### Capture degradation separates weak systems, not strong ones

DocPTBench compares digital-born documents against photographs of the same
documents: average parsing edit distance rises **18%** for general MLLMs and
**25%** for specialised document-parsing models. But the per-model detail
matters more than the average — GOT-OCR deteriorates from 49.3 to 90.1 edit
distance, Dolphin from 20.5 to 57.5, Qwen2.5-VL-72B loses 20.1 points,
Kimi-VL 33.1, while **Gemini 2.5 Pro loses 3.4**.

So degrading an image is a strong lever against OCR pipelines and a weak one
against a frontier vision model. If the goal is to lower a leaderboard's
ceiling, this axis widens the bottom of the table instead.

### A checklist for picking the document

Ranked by how much they cost a frontier model, not a weak parser:

1. **Is any answer un-printed?** Charts, plots, maps, schematics, floor plans —
   values that exist only as geometry. Unsaturated at 70–88% before any trick.
2. **Is any of it handwritten?** Case-report forms, annotations, signatures,
   filled-in paper forms. The hardest RealDocBench domain is hardest for this.
3. **Does it need domain convention to read correctly?** Finance is the most
   discriminative domain in RealDocBench, and DocMath-Eval names unit
   transformation and domain-specific conventions as a top error class.
4. **Are there structurally absent fields?** Blanks that must be reported as
   empty, checkbox states, key–value pairs with no value.
5. **Is it long *and* image-only?** Worth 30 points, but only past ~100 pages,
   and it competes with the context window.
6. **Is the capture degraded?** Real effect, wrong target — it separates
   parsers from each other, not the top model from the field.

And the anti-pattern, which is what we built: **a clean, digital-born,
fully-printed statistical table.** Every number present as a numeral, every
page geometrically perfect, one domain convention, no blanks, no handwriting,
88 pages at most. Saturated by construction, and no amount of question design
moves it.

## Decision log

What this evidence changed, in order:

1. **Abandoned "harder questions on the same document."** Two probe rounds,
   26/26 correct, $5.61. Counting, medians, ranking, cross-page, unanswerable,
   week-disambiguation across 89 pages — none of it bit.
2. **Abandoned "make the scan realistic."** Proposed after round two on the
   grounds that perception was the one untested axis, then withdrawn on
   DocPTBench's per-model numbers: photographic degradation costs specialised
   parsers 25% and Gemini 2.5 Pro 3.4 points. It widens the bottom of a
   leaderboard rather than lowering its top, and it would have cost the OCR
   solutions their 0.90 while leaving the ceiling where it was.
3. **Changed the document instead.** `pdf_mixed_scan` is being replaced rather
   than patched. Its premise — half the pages carry no text layer — turned out
   to be a statement about the *pipeline*, not about the *content*: every
   figure it asks for is still printed as a numeral on the page, so any pipeline
   that reaches the pixels reads it. The successor targets values that are not
   printed anywhere in any text form.

The general lesson worth keeping: **"the text layer is missing" is a property
of the file; "the number was never written down" is a property of the
document.** Only the second one survives a model that can see.

## Round three: charts break it

Same pipeline, same repeats, a different document. Six pages of the Federal
Reserve's July 2026 Monetary Policy Report — the Summary of Economic
Projections figures — rasterised so the vector paths are gone and every value
exists only as pixels. 16.5k input tokens per call, $0.68 for the round.

**3 of 12 correct.**

| Probe | Gold | Three answers |
|---|---|---|
| Dots at 3.625% in the 2026 column of the dot plot | 8 | 9 / 9 / 8 |
| Median of the 2028 column | 3.375 | 3.375 / 3.375 / 3.5 |
| Bar height, 3.5–3.6 bin, 2026 panel of figure 3.C | 9 | 10 / 10 / 10 |
| Participants in the 2027 panel of figure 3.C | 18 | 19 / 19 / 19 |

Two failure modes, both worth naming.

**Off-by-one against the gridline.** The histogram draws a line every 2
participants, so an odd bar ends between two lines. All three runs said 10 for
a bar of 9. This is estimation from geometry, and it is stable in its
wrongness — not noise, a bias.

**A prior overriding the page.** Nobody counted the 2027 bars. All three
answers asserted 19 "because that is how many FOMC participants there are",
and the third one invented a 1.7–1.8 bin holding one participant to make the
total come out right. The chart shows 18. This is MMLongBench-Doc's largest
error class — hallucinated evidence, 33% — reached not by hiding the evidence
but by putting a widely-known prior in conflict with it.

The gold was checked twice over: measured from the pre-rasterisation vector
geometry (bar heights are exact integer multiples of 4.12pt; dots land on
eighth-point levels) and counted again by eye at 8x. Two independent figures
agree that 18 participants submitted, 17 of them for 2028.

### A note on who reads charts worse

While authoring these questions, our own eye-read of the 2027 panel was
1/4/5/4/1; the geometry says 2/5/6/4/1. **The author misread a bar chart too.**
That is the argument for deriving chart gold from vector geometry rather than
by eye — and it inverts the rule the table-based task used, where gold had to
be read by eye precisely *because* a parser could extract it. When the value
is not text, measuring the geometry is not extraction, it is measurement, and
the eye is the thing that needs checking.

## Where it landed

The successor task, `pdf_chart_reading`, is 22 questions about rasterised vector
charts in one Federal Reserve Summary of Economic Projections. The pipeline
that scored 20/20 on the printed-number task scores **14/22** on it, with four
of the eight failures not answers at all — the model spent its whole output
budget reasoning about how many dots were in a row and returned nothing.

Three rounds of probing, $9.24 in total, to arrive at a one-line rule:

> Ask for a number that was never written down.
