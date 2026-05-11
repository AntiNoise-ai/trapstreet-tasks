# Case 5 — Live Demo Flow

A roughly 7–9 minute live demo built around FinanceBench. Designed for a mixed-audience speaker event where the goal is **visible divergence between agents** — not "watch them all succeed." Numbers are unambiguous, the failure modes are theatrical (wrong dollar amount, wrong fiscal year, wrong unit), and the question setup ("read this 10-K and tell me X") needs zero domain background to follow.

This is the stronger stage pick versus CUAD in 2026 because frontier models still meaningfully fail at numerical reasoning over long financial documents, while clause extraction has largely been solved.

---

## The narrative arc

| Beat | Time | Purpose |
|------|------|---------|
| 1. Hook | 45–60s | Set the question the audience already cares about |
| 2. Setup | 60–90s | Project the 10-K, frame the question |
| 3. The race | 2–3 min | Run 6 agents head-to-head |
| 4. The reveal | 60s | Score against the gold answer, find the line in the 10-K |
| 5. The aggregate | 90s | Pre-recorded scoreboard across 30+ questions |
| 6. The close | 45–60s | Generalize to "trading agents" / "research agents" |

**Total stage time: ~8 minutes.** Add ~1 min cushion for transitions.

---

## 1. The hook (45–60s)

> "There are 50+ AI trading agents on the market today. They all claim to be best. None have published a head-to-head benchmark.
>
> Today we test step 1: *can they correctly read an earnings report?*"

This is the original framing in the project's design doc, and FinanceBench is the case it was written for. Audience members in finance, investing, or product strategy all care about this question.

---

## 2. The setup (60–90s)

Project the 10-K on screen. Show the table of contents. Explain that today's question requires reading **a specific section** to find the answer.

### Recommended 10-K: Amazon FY2022 (10-K filed January 2023)

Why Amazon:
- Universally recognized — no explanation needed
- **Multi-segment reporting** (AWS, North America, International, Advertising) — segment confusion is a real failure mode for current models
- Theatrical numbers ($514B revenue, $80B AWS revenue, ~$11B negative free cash flow)
- The 10-K is dense (~100 pages), with cash flow + income statement + segment reporting all required for different questions

### Recommended lead question

> **"What was Amazon's free cash flow in fiscal year 2022?"**

Why this question:
- **Gold answer is `($11,569M)` — i.e., NEGATIVE.** Amazon's free cash flow flipped negative in FY2022, which is itself surprising news to many audience members. The reveal has news value, not just trivia value.
- Requires the model to identify the right cash flow definition (operating cash flow minus capex), which models often confuse.
- Requires the model to handle the **negative sign** correctly — a common silent failure.
- Pulls from the cash flow statement, which has clean line items easy to point to on stage.

### Common failure modes you'll see live

| Failure | What the model returns | Why it matters |
|---|---|---|
| **Wrong fiscal year** | $25,924M (FY2021 figure) | Same metric, wrong year — column-confusion |
| **Wrong metric** | $46,752M (operating cash flow, not free cash flow) | Subtle — operating CF is on the same statement |
| **Missed the negative** | $11,569M (correct magnitude, wrong sign) | Catastrophic in a real investing context |
| **Wrong unit** | $11.5T or $11,569 | Reporting in billions vs millions vs raw |
| **Hallucinated number** | Any number not in the 10-K | Worst case — model confabulates |
| **Refusal / hedge** | "I cannot determine this from the document" | Common for safety-tuned products on financial questions |

### Backup question and 10-K

If Amazon FY2022 produces uniform answers across agents in pre-test, fall back to:

| Company | Question | Gold | Why it's interesting |
|---|---|---|---|
| **3M FY2018** | "What was 3M's FY2018 capital expenditure (USD millions)?" | $1,577M | Already documented in the case README; clean cash flow statement |
| **Boeing FY2022** | "What was Boeing's net loss in FY2022?" | $5,053M | 737 MAX charges; multiple sources of loss |
| **Pfizer FY2022** | "What was Pfizer's COVID-19 vaccine revenue in FY2022?" | $37,806M (Comirnaty) | Audience knows the storyline; segment isolation is hard |
| **Tesla FY2022** | "What was Tesla's automotive gross margin in FY2022?" | 28.5% | Requires computing from automotive revenue + COGS |

The Tesla and Boeing questions force calculation, not just extraction — that's where 2026 frontier models still diverge most.

---

## 3. The race (2–3 min)

Run the same `(question, 10-K PDF)` through 6 agents simultaneously, in a 2×3 grid on screen.

For each agent, show:
1. **The number it returns** — large, central
2. **The cited line** — what part of the 10-K it claims to be quoting (if anything)
3. **Latency** — how long the response took

### Recommended lineup

#### Tier A — finance-specialized AI products

The category whose marketing is being tested. Most are gated; line up POC accounts a few weeks out.

- **AlphaSense AI** — institutional research; has API access through enterprise sales
- **Hebbia** — financial research over documents; enterprise API
- **Brightwave** — institutional finance research
- **FinChat** — consumer-facing finance AI
- **Patronus AI** — they own FinanceBench, would be a credibility play to include if accessible
- **BloombergGPT** — gated heavily; likely not accessible for live demo, useful if it is

#### Tier B — frontier general-purpose LLMs

The baselines that often *beat* Tier A on document Q&A. Easy to script live.

- **Claude 4.7 Opus (1M context)** — can hold a full 10-K in one shot
- **GPT-5** with file-read tool
- **Gemini 3 Pro** — long-context strong, often best on numerical reasoning

#### Tier C — naive baselines (the floor)

- **Vanilla RAG over the PDF** — chunk + embed + top-k + answer. Shows what the obvious pipeline gets you.
- **Single-page extraction** — feed the model just the page containing the answer. Measures pure reading vs. retrieval.

### Practical 6-pane lineup for the live race

Top row (Tier B — frontier general): **Claude 4.7**, **GPT-5**, **Gemini 3 Pro**
Bottom row (Tier A + baseline): **AlphaSense (or any accessible Tier A)**, **FinChat**, **RAG baseline**

If Tier A access falls through entirely, replace with pre-recorded panes labeled "RECORDED" and use 1–2 additional frontier models (Grok-3, DeepSeek V4) to fill out the grid.

---

## 4. The reveal (60s)

Flip to the gold answer overlay. **Open the 10-K to the cash flow statement page**, highlight the operating-cash-flow row and the capex row, do the subtraction live on screen.

Score each agent:
- ✅ Correct number, correct sign
- 🟡 Right magnitude, wrong sign or wrong period
- ❌ Wrong number entirely
- ⚠️ Refused / hedged

The visceral moment: an agent that confidently said "$25,924M positive free cash flow" when the actual answer was a $11.6B *loss* — and you have the page open to prove it.

---

## 5. The aggregate (90s)

Pre-recorded. Run the full lineup against 30+ questions across the 32 companies in FinanceBench's open-source split. Show:

```
Agent          | Correct  | Off by year | Wrong metric | Hallucinated | Refused | Avg latency
───────────────┼──────────┼─────────────┼──────────────┼──────────────┼─────────┼────────────
Claude 4.7     |  22/30   |     3/30    |     2/30     |     1/30     |   2/30  |   12s
GPT-5          |  19/30   |     4/30    |     3/30     |     2/30     |   2/30  |   18s
Gemini 3 Pro   |  21/30   |     3/30    |     2/30     |     0/30     |   4/30  |   14s
AlphaSense     |  17/30   |     5/30    |     3/30     |     1/30     |   4/30  |   22s
FinChat        |  12/30   |     6/30    |     5/30     |     3/30     |   4/30  |   31s
RAG baseline   |   9/30   |     7/30    |     8/30     |     2/30     |   4/30  |    8s
```

Numbers above are illustrative — populate from the actual pre-event run.

The mic-drop framing: **"The product *built specifically for this task* is worse than the general-purpose model. The 30+ percentage points are real money in a real workflow."**

---

## 6. The close (45–60s)

> "If the AI agents marketed *specifically for finance* can't reliably read an earnings report, what does that say about the trading agents built on top of them? About the research agents? About every product that claims to read documents and reason about numbers?
>
> TrapStreet evaluates the *steps*, not the marketing."

Bridge to other cases on the platform (CUAD for legal, Article Summarization for news, Everyday Q&A for trivia) as the same pattern applied to other categories.

---

## Pre-event checklist

- [ ] Lock the agent lineup; secure API/POC access for each Tier A product (3+ weeks lead time recommended)
- [ ] Run the **full 150-question FinanceBench open-source split** through all candidate agents — at least 1 week before event
- [ ] Pick the live-race question based on which one produces the **most divergent** agent outputs (not the hardest one)
- [ ] Pick 30 questions for the aggregate scoreboard, weighted toward calculation-required questions
- [ ] Pre-run all agents on those 30 questions; capture exact outputs, citations, and latencies
- [ ] Pre-record any agent that can't run programmatically; label clearly with "RECORDED" badge
- [ ] Build the side-by-side display (6 panes, gold-answer overlay)
- [ ] Build the aggregate scoreboard slide with **real** numbers
- [ ] Have a fallback recording of the entire demo in case live API access fails on event day
- [ ] Prepare the 10-K PDF with bookmarks to relevant sections (cash flow statement, segment reporting, MD&A)

---

## Eval rubric for grading

For each `(agent, question)` pair:

| Outcome | Definition | Score |
|---|---|---|
| Exact | Number matches gold within 1% (handles rounding) | 1.0 |
| Right metric, wrong period | Correct line item but wrong fiscal year | 0.0 (track separately) |
| Right metric, wrong unit | Correct figure, off by 1000× | 0.0 (track separately) |
| Wrong sign | Correct magnitude, opposite sign (positive vs negative cash flow) | 0.0 (track separately) |
| Wrong metric | Returned a different number from the same statement | 0.0 |
| Hallucinated | Number not in the 10-K | 0.0 (track separately) |
| Refusal / hedge | "Cannot determine" when answer is plainly extractable | 0.0 (track separately) |

Track **hallucination rate**, **wrong-period rate**, and **refusal rate** as separate headline numbers — those tell different stories about each agent's failure profile and are more interesting than a single accuracy number.

### Numerical equivalence

Normalize before comparison:
- Strip currency symbols (`$`, `USD`)
- Strip thousand separators (`,`)
- Convert units (`$11.6B` → `11600`, `$11,569 million` → `11569`)
- Allow ±1% tolerance for rounding (the gold answers are often stated to thousands)
- Match sign explicitly — `(11569)` and `-11569` and `$11.6B negative` are equivalent

Reference implementation lives in the FinanceBench paper (Patronus AI) and their grading script on GitHub.
