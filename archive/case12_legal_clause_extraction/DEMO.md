# Case 12 — Live Demo Flow

A roughly 8-minute live demo built around CUAD. Designed for a mixed-audience speaker event: legal/business/technical attendees can all follow it, the failure mode is visually obvious, and the narrative answers a question the audience already cares about ("which legal AI tool is actually any good?").

---

## The narrative arc

| Beat | Time | Purpose |
|------|------|---------|
| 1. Hook | 60s | Set up the stakes |
| 2. Setup | 90s | Show the contract + pick the clause |
| 3. The race | 3 min | Run multiple agents head-to-head |
| 4. The reveal | 60s | Score against the gold answer |
| 5. The twist | 90s | Aggregate results across more contracts |
| 6. The close | 60s | Generalize to other agent categories |

---

## 1. The hook (60s)

> "There are 20+ legal AI tools on the market — Harvey, Spellbook, Robin AI, CoCounsel, Lexis+ AI, Ironclad AI Assist. They all claim to review contracts. None have published a head-to-head benchmark.
>
> Today we test step 1: *can any of them actually find the clause?*"

Why this works: every audience member has heard at least one of these names. Nobody knows which is best. The question is genuine, not rhetorical.

---

## 2. The setup (90s)

Project a real CUAD contract on screen — pick a 30–50 page commercial agreement (CUAD ships these as PDFs in the [raw dataset](https://huggingface.co/datasets/theatticusproject/cuad)). Show the 41 clause categories from the Atticus rubric on a side panel.

Pick **one** clause for the test. Best demo picks (laziness-prone, audience-relatable):

| Clause | Why it demos well |
|--------|-------------------|
| **Anti-Assignment** | Often buried in boilerplate; relevant to anyone who's done M&A. Models frequently miss it. |
| **Change of Control** | Same dynamic, even higher stakes. Audiences in deal-heavy industries lean in. |
| **Cap on Liability** | Dollar amounts make misreads unambiguous. |
| **Most Favored Nation** | Subtle phrasing; models confidently say "not present" when it is. |
| **Effective Date vs Agreement Date** | Two similar fields → models frequently conflate them. |

Recommended lead: **Anti-Assignment**. The Atticus paper specifically flags it as a category models get wrong, and the failure mode (model returns "no clause found" when one exists) is the cleanest visual reveal.

---

## 3. The race (3 min)

Run the same `(question, contract PDF)` through 4–6 agents simultaneously, side-by-side panes on screen.

For each agent show:
1. **Did it return a span?** Binary. Many will return "no clause found" or refuse.
2. **Is the span the right one?** Visual overlay against the gold span.
3. **How long did it take?** Latency matters in real review work.

**Recommended lineup:**

### Tier A — dedicated legal AI products
The cohort the demo's narrative is built around. Most are gated; line up demo/POC accounts a few weeks before the event.

- **Harvey** — flagship "lawyer agent." Hardest access (sales-led, gated).
- **Spellbook** — contract drafting/review, has Word add-in and API.
- **Robin AI** — contract review specialist with API access.
- **Thomson Reuters CoCounsel** (formerly Casetext) — large-firm staple.
- **Ironclad AI Assist** — embedded in Ironclad CLM.
- **Lexis+ AI / Protégé** — incumbent legal research; contract analysis included.

### Tier B — general-purpose LLM agents
The baselines that often *beat* Tier A on tasks like this. Easy access, cheap to run.

- **Claude 4.7 Opus (1M context)** — long-context PDF read in one shot.
- **GPT-5** with file-read tool.
- **Gemini 3 Pro** — long-context strength.

### Tier C — naive baseline
The floor. Shows what the obvious approach gets you.

- A vanilla RAG-over-PDF pipeline (chunk + embed + top-k + answer).

**Practical lineup for 6 panes (2×3 grid):** Harvey, Spellbook, Robin AI, Claude 4.7, GPT-5, RAG baseline. If any Tier A access falls through, replace with a pre-recorded run and label it as such.

> **Honest caveat:** Tier A API/eval-access policies change. Confirm programmatic access for each before locking the lineup. Anything you can't script live should be pre-recorded with a visible "recorded" badge so the audience trusts what they're seeing.

---

## 4. The reveal (60s)

Flip to the gold answer overlay from `answers.text[0]` and `answers.answer_start[0]`. Highlight the exact span in the contract.

Score live:
- ✅ Found it, exact span
- 🟡 Found something, partial overlap
- ❌ Returned a wrong span
- ⚠️ Said "no clause found" — the laziness failure

The visceral moment: an agent that confidently said "no termination clause in this contract" when the clause is plainly visible on screen.

---

## 5. The twist (90s)

Pre-recorded. Run the same test on 5 more contracts in fast-forward. Show aggregate per agent:

```
Tool         |  Found  |  Correct span  |  Latency
─────────────┼─────────┼────────────────┼─────────
Harvey       |   5/5   |     3/5        |  4.2s
Spellbook    |   4/5   |     2/5        |  6.1s
Robin AI     |   5/5   |     4/5        |  3.8s
Claude 4.7   |   5/5   |     4/5        |  2.1s
GPT-5        |   4/5   |     3/5        |  3.5s
RAG baseline |   3/5   |     1/5        |  1.2s
```

The numbers above are illustrative — populate with actual eval output.

This is where TrapStreet's value lands: not "tool X is bad," but "for the first time you can see which tools actually do the thing they claim to do."

---

## 6. The close (60s)

> "If the legal AI category — billions in funding, the loudest claims — gets a basic clause-extraction task wrong this often, what does that say about the trading agents, the medical agents, the research agents claiming similar capabilities?
>
> TrapStreet evaluates the steps, not the marketing."

Bridge to other cases on the platform (Finance Q&A, Article Summarization, Everyday Q&A) as the same pattern applied to other categories.

---

## Pre-event checklist

- [ ] Lock the agent lineup; secure API access or POC accounts for each
- [ ] Pick 6 contracts from CUAD (1 live + 5 for the twist segment)
- [ ] Pick the lead clause type (default: Anti-Assignment)
- [ ] Pre-run all agents on all 6 contracts; capture outputs and latencies
- [ ] Pre-record any agent that can't run live; label clearly
- [ ] Build the side-by-side display (6 panes, gold-answer overlay)
- [ ] Build the aggregate scoreboard (filled with real numbers from pre-runs)
- [ ] Have a fallback recording of the entire demo in case live access fails

---

## Eval rubric for grading

For each `(agent, row)` pair in the eval:

| Outcome | Definition | Score |
|---------|------------|-------|
| Exact | Predicted span exactly matches a gold span | 1.0 |
| Partial | Token-level F1 ≥ 0.5 against any gold span | F1 score |
| Wrong span | Returned a span; F1 < 0.5 against all gold | 0.0 |
| Lazy miss | Said "no clause found" when gold is non-empty | 0.0 (track separately) |
| Correct null | Said "no clause found" and gold is empty | 1.0 |

Track **lazy-miss rate** as its own headline number — that's the silent failure this case is designed to catch, and it's the most surprising result for the audience.
