# Case 19 — Live Demo Flow

A roughly 7–8 minute live demo built around BFCL. Designed for the "one-person company / autonomous agent" speaker-event narrative: every product on Twitter and GitHub claims to handle full workflows, **nobody has measured which steps actually work.** This case tests the foundational step every agent depends on — calling the right function with the right arguments.

The demo lands because the failure modes are visible in plain text: an agent that confidently calls a fabricated function, picks the wrong tool, or invents an argument value is the cleanest possible "this would be a real-money mistake in production" moment.

---

## The narrative arc

| Beat | Time | Purpose |
|------|------|---------|
| 1. Hook | 45–60s | Set the question — "do these autonomous agents actually use tools right?" |
| 2. Setup | 60–90s | Project the input: user query + function schema |
| 3. The race | 2–3 min | Run 6 agents head-to-head |
| 4. The reveal | 60s | Score against gold |
| 5. The aggregate | 90s | Pre-recorded scoreboard across 50+ questions |
| 6. The close | 45–60s | Generalize to all "autonomous agent" claims |

**Total: ~8 minutes.**

---

## 1. The hook (45–60s)

> "Every week there's a new GitHub repo claiming an AI agent that runs your entire business. Customer support. Sales. Bookkeeping. Marketing. Some are getting venture funding. None of them have published a head-to-head benchmark of the one thing every workflow depends on:
>
> *Did the agent call the right tool, with the right arguments?*"

This is the question the audience already cares about whether or not they realize it. Every "autonomous agent" pitch is built on top of function calling. If that fails, everything downstream is theater.

---

## 2. The setup (60–90s)

Project a single BFCL row on screen, formatted clearly. Two halves:

**Left pane — what the agent sees:**

```
USER: I just got off a plane. Send my partner a text saying I landed safely
       and tell my assistant to clear my calendar for the rest of the day.

AVAILABLE FUNCTIONS:
  send_text(recipient, message)
  update_calendar(action, date_range)
  book_flight(...)
  search_hotels(...)
```

**Right pane — empty agent response slots, six of them.**

Walk the audience through:
- "The agent has four functions available."
- "It needs to call `send_text` once and `update_calendar` once."
- "Both calls need the right arguments — the right recipient, the right action, the right date range."
- "Watch what each agent actually does."

### Recommended demo categories (lead with one, fall back to others)

| Category | Why it bites in 2026 | What audience sees |
|----------|----------------------|--------------------|
| **`irrelevance`** | Models still call functions when they shouldn't ("hi, how are you?" → calls `book_flight`) | Agent confidently makes a fabricated booking. Visceral. |
| **`parallel`** | Multiple calls required in one turn — models miss one, hallucinate another | Side-by-side: gold needs 2 calls, agent makes 1 or 4 |
| **`multi_turn_miss_func`** | The required function isn't in the schema; agent should refuse, but often fabricates one | Agent invents a function name that doesn't exist |
| **`multi_turn_miss_param`** | User omitted a required argument; agent should ask, but often guesses | Agent fills in a fake email, fake date, fake amount |

Lead pick: **`multi_turn_miss_param`**. The failure mode (agent fabricates an argument value) is the clearest "this is a production lawsuit" moment for a non-technical audience.

---

## 3. The race (2–3 min)

Run the same `(user query, function schema)` through 6 agents, side-by-side.

For each agent, show:
1. **Function name called** — green if right, red if wrong, yellow if hallucinated/invented
2. **Argument values** — green if right, red if wrong, yellow if fabricated
3. **Latency**

### Recommended lineup

#### Tier A — agent products (the cohort the narrative is about)

The "one-person company" frameworks and products. Most have public APIs or scriptable interfaces.

- **AutoGen** (Microsoft) — multi-agent conversation framework
- **CrewAI** — role-based agents
- **LangChain agents** — most-used framework, easy to script
- **Devin / Manus / OpenHands**-class products — autonomous developer/worker agents
- **One specific "one-person company" product** — pick whatever's gone viral on Twitter that month

#### Tier B — frontier general LLMs with native function calling

The baselines that often beat Tier A on tool-use tasks. Direct API calls.

- **Claude Opus 4.1 / Claude 4.7 Opus** — strong native tool use
- **GPT-5** — native tool use
- **Gemini 3 Pro** — native tool use

#### Tier C — open-source baseline

- **Llama 3.1 405B** — currently #1 on BFCL leaderboard at 88.5%; a strong open baseline

### Practical 6-pane lineup

Top row: **Claude 4.7**, **GPT-5**, **Gemini 3 Pro** (Tier B — frontier general)
Bottom row: **AutoGen**, **CrewAI**, **Llama 3.1 405B** (Tier A products + open baseline)

If a Tier A product can't run live, replace with a pre-recorded pane labeled "RECORDED."

---

## 4. The reveal (60s)

Flip to the gold answer. Show the accepted function calls and accepted argument values. Score each agent live:

- ✅ Right function, right args
- 🟡 Right function, wrong args (e.g., wrong recipient)
- ❌ Wrong function (called `update_calendar` when should have been `send_text`)
- 🚫 Refused / missed call entirely
- ⚠️ **Hallucinated function** (called something that doesn't exist in the schema) — the worst failure

The visceral moment: an agent that called `book_flight(destination="Tokyo", date="2026-05-09")` when the user just said "hi how are you," or fabricated a recipient email like `partner@example.com` when the user never gave one.

---

## 5. The aggregate (90s)

Pre-recorded. Run the full lineup against 50+ questions across `multi_turn_*`, `irrelevance`, and `parallel`. Show:

```
Agent          | Right call | Wrong arg | Wrong func | Hallucinated | Refused | Avg latency
───────────────┼────────────┼───────────┼────────────┼──────────────┼─────────┼────────────
Llama 3.1 405B |   42/50    |   3/50    |    2/50    |    1/50      |   2/50  |   2.1s
Claude 4.7     |   38/50    |   5/50    |    3/50    |    1/50      |   3/50  |   1.8s
Gemini 3 Pro   |   36/50    |   5/50    |    4/50    |    2/50      |   3/50  |   2.4s
GPT-5          |   31/50    |   8/50    |    5/50    |    3/50      |   3/50  |   2.0s
AutoGen        |   24/50    |   9/50    |    8/50    |    5/50      |   4/50  |   4.2s
CrewAI         |   19/50    |  11/50    |   10/50    |    7/50      |   3/50  |   5.1s
```

Numbers above are illustrative — populate from the actual pre-event run using the official BFCL evaluator.

The mic-drop framing: **"The 'autonomous agent' frameworks are dramatically worse than the underlying frontier models they're built on. They are layering bugs on top of capability."**

---

## 6. The close (45–60s)

> "Every workflow these agents claim to automate — the customer email, the booking, the report, the trade — runs through this one step. We measured it. The products marketed as 'agents' are not as good at it as the raw models they're wrappers around.
>
> TrapStreet evaluates the steps, not the marketing."

Bridge to other cases (FinanceBench for finance, CUAD for legal, BrowseComp for research) as the same pattern across other agent categories.

---

## Pre-event checklist

- [ ] Pick the category for the live race (default: `multi_turn_miss_param`)
- [ ] Pull 5 candidate rows from that category; pre-test against all 6 agents to find one with **maximum divergence** (ideally: 2 agents right, 2 wrong-arg, 2 hallucinated)
- [ ] Pull 50 rows for the aggregate scoreboard (mix of `multi_turn_*` + `irrelevance` + `parallel`)
- [ ] Run the official BFCL evaluator on those 50 rows for all 6 agents; capture exact outputs
- [ ] Lock Tier A access; pre-record any agent that can't run programmatically
- [ ] Build the 6-pane side-by-side display with color-coded function-call and argument cells
- [ ] Build the gold-answer overlay with the exact accepted call(s) and accepted argument values
- [ ] Have a fallback recording of the entire demo

---

## Eval rubric for grading

For each `(agent, row)` pair:

| Outcome | Definition | Score |
|---|---|---|
| Right call | Function name matches gold AND every required arg matches an accepted value | 1.0 |
| Wrong arg | Function name correct, ≥1 arg outside accepted values | 0.0 (track separately) |
| Wrong function | Called a different function than gold | 0.0 (track separately) |
| Hallucinated function | Called a function name not in the schema | 0.0 (track separately) |
| Refused | Returned natural language instead of a call when one was required | 0.0 (track separately) |
| Correct refusal | Returned natural language when gold is "no call" (`irrelevance` rows) | 1.0 |

### Headline metrics (3 separate numbers, not one average)

1. **Right-call rate** on `multi_turn_*` — capability ceiling on the realistic case
2. **Hallucinated-function rate** across all categories — the "production lawsuit" metric
3. **Correct-refusal rate** on `irrelevance` — the "decide when not to act" metric

Reporting all three together is more honest than averaging them. An agent that's 95% right but hallucinates a function 5% of the time is not 90% reliable — it's *unusable* in any workflow that touches money or external systems.
