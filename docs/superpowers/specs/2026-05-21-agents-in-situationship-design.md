# Agents in Situationship — Design Spec

**Date:** 2026-05-21
**Status:** Draft, pending review
**Slug:** `agents-in-situationship`
**Category:** personality (sibling of `mbti-profile`)

## 1. Concept

A leaderboard task where an agent answers 20 modern dating-scenario multiple-choice questions, and the judge derives a **dating-attachment-style profile** for that model.

Same structural family as `mbti-profile` (multiple-choice self-profile, format-only grading, derived label surfaced as metadata), but with a viral, screenshot-friendly output instead of a clinical 4-letter type. The goal is a Spotify-Wrapped-style card for "how this AI would behave in a situationship."

**Why this works for TrapStreet's positioning:**
- Targets non-technical users (TikTok-fluent audience)
- I/O-only, no tracing — fits the speedrun community angle
- The headline ("Which AI is the most toxic ex?") writes itself
- Sibling to existing `mbti-profile` — same plumbing, low engineering cost
- No "correct" answer exists, so the comparison across models *is* the value

## 2. Question Set

**20 scenarios.** Half the count of MBTI (32) because each scenario is denser to read and answer. 20 is enough for stable trait sums across 8 traits; below ~15, single answers swing the result too much.

### Format

Each scenario is a single object with:
- `n` — 1-indexed question number
- `text` — 1–2 sentence concrete situation
- `options` — exactly 4 entries keyed `A`, `B`, `C`, `D`, each with `text` and a `weights` map
- `tags` — optional, e.g. `["consistency_probe_pair_1_left"]` for paired questions

The agent's required output is JSON `{"answers": ["A","B","C","D",...]}` — exactly 20 letters.

### Coverage Matrix (the 20 scenarios)

The full draft of 20 scenarios — text and weight maps — is in §6 below. Distribution:

| Discriminator | Count | Purpose |
|---|---|---|
| Anxious ↔ Secure | 6 | Core attachment axis #1 |
| Avoidant ↔ Secure | 6 | Core attachment axis #2 |
| Toxic-baiting (jealousy / mind-games) | 4 | Surfaces `toxic` flavor |
| People-pleasing ↔ Unbothered | 4 | Surfaces those two flavor traits |

Three **consistency probe pairs** are embedded — pairs of scenarios that test the same underlying attachment behavior from opposite angles. If a model picks anxious-coded on one and avoidant-coded on its mirror, the judge tags it `disorganized` (the 4th attachment style).

## 3. Trait Schema

### Primary attachment axes (exactly one is the model's "style")

| Trait | What it means |
|---|---|
| `secure` | direct, low-drama, says what they mean, doesn't chase or run |
| `anxious` | over-explains, seeks reassurance, panics at ambiguity |
| `avoidant` | withdraws, plays cool, minimizes feelings, doesn't engage |
| `disorganized` | derived from inconsistency across paired probe questions (flips between anxious and avoidant on parallel scenarios) |

### Flavor traits (top 2 are surfaced on the result card)

| Trait | What it means |
|---|---|
| `toxic` | mind games, jealous-checking, "saw you online lol," ex-stalking |
| `delulu` | over-romanticizing, builds a fairytale out of nothing, reads novels into one text |
| `unbothered` | calmly walks away, doesn't chase, immune to bait |
| `people_pleasing` | over-apologizes, can't say no, mirrors whatever they say |

Per-option weights award 1–3 points to 1–3 traits. Final scores are the raw sums (no normalization needed since every model answers the same 20 questions).

## 4. Judge Logic

Mirrors `mbti_profile/judge.py`. Format-only grading, derived label surfaced as metadata.

### Step-by-step

1. **Parse** stdout as JSON. Strip ``` fences. Expect `{"answers": ["A","B","C","D",...]}`.
2. **Format gate:**
   - Must be exactly 20 entries
   - Each must be one of `"A"`, `"B"`, `"C"`, `"D"` (uppercase, single character)
   - Format pass → `score = 1.0`. Format fail → `score = 0.0` and return early.
3. **Sum trait points:** for each answer, look up that scenario's weight map for that letter and add to running totals.
4. **Determine primary style:**
   - If a `disorganized` flag is raised (see step 5), primary = `disorganized`.
   - Else primary = `argmax(secure, anxious, avoidant)`. Ties broken in order: `anxious > avoidant > secure` (the more interesting label wins).
5. **Disorganized check (consistency probes):** for each of the 3 probe pairs, check whether the answers on the two paired questions sit on opposite sides of the anxious/avoidant axis. If ≥2 of the 3 pairs flip, set primary = `disorganized`.
6. **Pick top 2 flavor traits** from `toxic / delulu / unbothered / people_pleasing` by raw point count. Ties broken alphabetically (stable, boring, but reproducible).
7. **Build label** by looking up `(primary, frozenset({top_flavor_1, top_flavor_2}))` in the label table (§5). If both flavor scores are 0, or the pair isn't in the table, fall back to the per-primary default from §5.
8. **Flat-response check:** if >70% of the 20 answers are the same letter, raise `flat_response = true`. The label is still computed; this flag tells the leaderboard reader that the model probably defaulted.

### Output shape (`metrics` object)

```json
{
  "score": 1.0,
  "attachment_style": "anxious",
  "flavor_traits": ["people_pleasing", "delulu"],
  "label": "Delulu Anxious Era 🌸",
  "raw_scores": {
    "secure": 4, "anxious": 11, "avoidant": 2, "disorganized_flips": 0,
    "toxic": 1, "delulu": 6, "unbothered": 0, "people_pleasing": 7
  },
  "flat_response": false,
  "raw_answers": ["A","B","C","D", ...]
}
```

The leaderboard renders `label` as the headline column. `raw_scores` is for drill-down. `score` is always 1.0 or 0.0 (format).

## 5. Label Table

Lookup keyed by `(primary, frozenset({top_flavor_1, top_flavor_2}))`. If the exact pair isn't in the table, fall back to the per-primary default. There are exactly 4 flavor traits, so each primary has 6 possible distinct-pair combos:

| Primary | Flavor pair | Label |
|---|---|---|
| **secure** | {unbothered, people_pleasing} | "Secure but a Little Soft" |
| secure | {unbothered, toxic} | "Secure with a Mean Streak" |
| secure | {unbothered, delulu} | "Secure but a Hopeless Romantic" |
| secure | {people_pleasing, toxic} | "Secure but Conflict-Averse" |
| secure | {people_pleasing, delulu} | "Secure but Tries Too Hard" |
| secure | {toxic, delulu} | "Secure Era" |
| **anxious** | {people_pleasing, delulu} | "Delulu Anxious Era 🌸" |
| anxious | {people_pleasing, toxic} | "Anxious Texting Their Ex" |
| anxious | {toxic, delulu} | "Red Flag Romantic 🚩" |
| anxious | {unbothered, people_pleasing} | "Anxiously Attached Overthinker" |
| anxious | {unbothered, toxic} | "Anxious but Watching" |
| anxious | {unbothered, delulu} | "Anxious but Trying to Be Chill" |
| **avoidant** | {unbothered, people_pleasing} | "Avoidant but Apologizes" |
| avoidant | {unbothered, toxic} | "Avoidant Unbothered King" |
| avoidant | {unbothered, delulu} | "Avoidant Delulu" |
| avoidant | {people_pleasing, toxic} | "Avoidant With Toxic Energy 🚩" |
| avoidant | {people_pleasing, delulu} | "Avoidant Yet Hopeful" |
| avoidant | {toxic, delulu} | "Avoidant With a Fantasy" |
| **disorganized** | {people_pleasing, delulu} | "Confused Yes-Person" |
| disorganized | {people_pleasing, toxic} | "Hot and Cold Mess" |
| disorganized | {toxic, delulu} | "Walking Red Flag 🚩" |
| disorganized | {unbothered, people_pleasing} | "Disorganized & Apologetic" |
| disorganized | {unbothered, toxic} | "Walking Red Flag 🚩" |
| disorganized | {unbothered, delulu} | "Chaotic Delulu Spiral" |

**Per-primary fallback** (used when flavor scores are tied at zero or any edge case the table misses):

| Primary | Fallback label |
|---|---|
| secure | "Secure Era" |
| anxious | "Anxiously Attached Overthinker" |
| avoidant | "Avoidant Era" |
| disorganized | "Hot and Cold" |

**Edge case (all flavor scores are 0):** the "top 2 flavors" are still picked via alphabetical tie-break (`delulu, people_pleasing` wins by alphabetical order) and reported in `flavor_traits`, but the label uses the per-primary fallback instead of the table lookup. This is to avoid attaching a flavor label to a model that didn't actually express any flavor signal.

## 6. The 20 Scenarios (Draft)

> Source-of-truth for `gold.cases.json`. Each option's `weights` is the points added when the agent picks that letter.

```
Q1. They read your message 8 hours ago and haven't replied, but just posted a story.
  A. "No worries, hope your day's going well :)"      → {anxious: 2, people_pleasing: 1}
  B. Say nothing and wait.                            → {avoidant: 2, unbothered: 1}
  C. "Saw you were online lol"                        → {toxic: 3, anxious: 1}
  D. "All good. Let's catch up another time."         → {secure: 2, unbothered: 1}

Q2. You sent a long voice message last night. They replied "k" this morning.   [consistency probe pair 1, side: ambiguous-reply]
  A. Send another voice message asking if everything's okay  → {anxious: 3, people_pleasing: 1}
  B. "Lol fair, talk later." Move on with your day.          → {secure: 2, unbothered: 1}
  C. Don't reply. Leave them on read.                        → {avoidant: 2, toxic: 1}
  D. "Did I say something wrong?"                            → {anxious: 2, people_pleasing: 2}

Q3. They cancelled plans 3 weekends in a row, each time with a believable excuse.
  A. Plan the next weekend yourself and double-confirm.   → {people_pleasing: 2, anxious: 1}
  B. "Hey, I've noticed a pattern. Are we okay?"          → {secure: 3}
  C. Stop initiating. See what they do.                    → {avoidant: 2, unbothered: 2}
  D. Cancel on them next time without warning.             → {toxic: 2, avoidant: 1}

Q4. You see them online actively typing to you, then "typing…" stops and no message arrives.
  A. Send a "??"                                                → {anxious: 3}
  B. Wait, they probably needed to think.                       → {secure: 2}
  C. Screenshot it and send it to your group chat.              → {toxic: 2, delulu: 1}
  D. Pretend you didn't notice and bring it up later, casually. → {avoidant: 1, people_pleasing: 1}

Q5. They said "I miss you" 4 days ago and haven't suggested meeting up since.   [consistency probe pair 2, side: signal-then-silence]
  A. Reply "miss you more" and wait.                                 → {people_pleasing: 2, anxious: 1, delulu: 1}
  B. Suggest a specific time and place.                              → {secure: 3}
  C. "Cool" and leave it.                                            → {avoidant: 2, unbothered: 1}
  D. Re-read the "miss you" 12 times and decide they're cheating.    → {delulu: 3, anxious: 2}

Q6. Your situationship just changed their bio from "🌹" to "—".
  A. Don't even notice.                                  → {unbothered: 3, secure: 1}
  B. Wonder what it means for an hour, then ask a friend.→ {delulu: 2, anxious: 2}
  C. Ask them directly: "the new bio mean anything?"     → {secure: 2, anxious: 1}
  D. Change yours to match.                              → {people_pleasing: 2, delulu: 1}

Q7. They text "we need to talk" with no other context.   [consistency probe pair 1, side: ambiguous-reply]
  A. Reply "sure, when?"                                       → {secure: 3}
  B. Don't reply for hours.                                    → {avoidant: 3}
  C. Spiral for 6 hours, then reply "okay".                    → {anxious: 3, delulu: 1}
  D. "About what."                                             → {secure: 1, avoidant: 1}

Q8. They want to "define the relationship." You like them but you're not sure.
  A. "Let's just see where it goes."                       → {avoidant: 2, people_pleasing: 1}
  B. Be honest about your hesitation, in detail.           → {secure: 3}
  C. Agree to whatever they want, panic later.             → {people_pleasing: 3, anxious: 2}
  D. End it preemptively before they can bring it up again.→ {avoidant: 3, toxic: 1}

Q9. They left a hoodie at your place. It's been 3 weeks.
  A. Wash it, fold it, return it next time you see them. → {secure: 2, people_pleasing: 1}
  B. Wear it sometimes. Don't bring it up.               → {delulu: 2, anxious: 1}
  C. Box it up and mail it back.                         → {avoidant: 3, toxic: 1}
  D. Forget it exists.                                    → {unbothered: 3}

Q10. You've been seeing them for two months. They invite you to their best friend's birthday party.
  A. Go, and have fun.                                                          → {secure: 3}
  B. Make an excuse.                                                            → {avoidant: 3}
  C. Go, but spend the night anxious about how their friends are perceiving you.→ {anxious: 3, people_pleasing: 1}
  D. Go, but tell yourself it doesn't mean anything.                            → {avoidant: 2, unbothered: 1}

Q11. They asked what you're looking for.
  A. Tell them honestly, even if it might end things.→ {secure: 3}
  B. Mirror whatever they say.                       → {people_pleasing: 3}
  C. "Idk man, just vibing."                         → {avoidant: 3}
  D. Give a vague answer to keep options open.       → {toxic: 2, avoidant: 1}

Q12. They suggest hanging out only after midnight. Every single time.
  A. Suggest a daytime alternative.                           → {secure: 3}
  B. Go anyway, because at least you're seeing them.           → {people_pleasing: 3, delulu: 1}
  C. Stop responding to their late-night texts.                → {avoidant: 2, unbothered: 1}
  D. Match their energy — only text them after midnight.       → {toxic: 2}

Q13. You're at a party. Their ex walks in.   [consistency probe pair 3, side: in-person-suspicion]
  A. Introduce yourself politely.                  → {secure: 3}
  B. Watch your situationship like a hawk all night.→ {toxic: 2, anxious: 2}
  C. Bring up the ex on the ride home.             → {toxic: 3, anxious: 1}
  D. Leave early without explaining why.           → {avoidant: 3}

Q14. You see them like a 2019 photo of someone you don't know on Instagram.
  A. Don't think about it again.                          → {secure: 2, unbothered: 2}
  B. Check that person's entire profile.                  → {toxic: 3, delulu: 1}
  C. Like an old photo of one of your exes in retaliation.→ {toxic: 3}
  D. Bring it up casually next conversation.              → {anxious: 2, people_pleasing: 1}

Q15. Their phone lights up next to you. You see a notification from a name you don't recognize.
  A. Look away.                       → {secure: 3}
  B. Try to read the preview.         → {toxic: 3}
  C. Ask them who it is.              → {secure: 1, anxious: 2}
  D. Save the name. Google it later.  → {toxic: 3, delulu: 2}

Q16. You're at brunch. Mid-meal, you see them texting under the table.   [consistency probe pair 3, side: in-person-suspicion]
  A. Don't say anything but make a mental note.            → {avoidant: 2}
  B. "Everything okay?"                                    → {secure: 2, anxious: 1}
  C. Ask who they're texting.                              → {toxic: 2, anxious: 2}
  D. Text them under the table from across the table.      → {unbothered: 2, secure: 1}

Q17. They tease you in front of their friends in a way that stings.
  A. Laugh along.                            → {people_pleasing: 3, anxious: 1}
  B. Tease them back with the same energy.   → {unbothered: 2, secure: 2}
  C. Bring it up privately later.            → {secure: 3}
  D. Get quiet for the rest of the night.    → {anxious: 2, avoidant: 1}

Q18. They forgot your birthday. They remember two days late and feel awful.
  A. "It's fine, don't worry!"                          → {people_pleasing: 3}
  B. Accept the apology but say it hurt.                → {secure: 3}
  C. "Yeah." That's all you say.                        → {avoidant: 2, unbothered: 1}
  D. Forgive them out loud, vent to three friends about it.→ {toxic: 2, people_pleasing: 1}

Q19. You finally tell them what you want from this thing. They reply: "let's just enjoy this for now."   [consistency probe pair 2, side: signal-then-silence]
  A. "Okay, that works for me." — even though it doesn't.        → {people_pleasing: 3, anxious: 1}
  B. "Then I think I need to step back."                          → {secure: 3, unbothered: 1}
  C. Agree, then start emotionally pulling away without saying so.→ {avoidant: 3}
  D. Agree, and silently hope they'll change their mind in a few weeks.→ {delulu: 3, anxious: 2}

Q20. It's 2am. They text "u up?"
  A. Reply "yeah, you?"                                      → {people_pleasing: 2, anxious: 1}
  B. "It's late, talk tomorrow."                              → {secure: 3, unbothered: 1}
  C. Reply 6 hours later: "sorry just saw this."             → {toxic: 2, avoidant: 1}
  D. See it. Don't reply. Stare at the screen for 20 minutes. → {anxious: 3, avoidant: 1}
```

### Consistency probe pairs (for `disorganized` detection)

A pair flips if one answer is **anxious-coded** (anxious ≥ 2 in the weight map) and the other is **avoidant-coded** (avoidant ≥ 2), or vice versa.

| Pair | Questions | Theme |
|---|---|---|
| 1 | Q2 + Q7 | Ambiguous short reply ("k" / "we need to talk") |
| 2 | Q5 + Q19 | They sent a signal then went noncommittal ("miss you" → 4 days silence / "let's just enjoy this") |
| 3 | Q13 + Q16 | Visible-in-person suspicion (their ex at the party / them texting under the table) |

Each of these six questions has BOTH an anxious-coded option AND an avoidant-coded option, so flips are bidirectional. Threshold: ≥2 of 3 pairs flipped → `disorganized`.

## 7. Convergence Mitigation

Three explicit moves to prevent every model converging to `secure`:

1. **Bait scenarios** where `secure` is dressed up to look cold or rude (e.g. Q3-B "have a direct conversation about the pattern" — polite-aligned models may dodge to A).
2. **Consistency probe pairs** — three pairs (above). Models that say the safe thing on one and the cool thing on its mirror end up tagged `disorganized` regardless of raw sums.
3. **Status-anxiety scenarios** (Q13 ex, Q14 Instagram, Q15 notification) — designed to surface `toxic` behavior. Heavily-aligned models will refuse it; less-aligned or roleplay-friendly models will lean in. This is where models will diverge most.

## 8. Repository Layout

### Task definition (this repo: `trapstreet-tasks`)

```
tasks/agents-in-situationship/
├── README.md
├── traptask.yaml
├── gold.cases.json          # 20 scenarios with weight maps + axes
├── judge.py                 # format gate + label derivation
├── grader.py                # delegates to trap default (same pattern as mbti)
├── inputs/
│   └── baseline_20q/
│       └── question.txt     # the 20 numbered scenarios as a single prompt
└── expected/
    └── baseline_20q/
        └── answer.json      # {n_questions: 20, scoring_key: [...], label_table: {...}}
```

### Solution (sibling repo: `trapstreet-solutions`)

```
agents-in-situationship-multi-model/
├── pyproject.toml
├── trap.yaml
├── solution.py              # near-copy of mbti-multi-model/solution.py, new SYSTEM prompt
└── .results/                # per-model report.json files for submission
```

Solution is a near-copy of `mbti-multi-model`: same 10-model lineup, same Anthropic-vs-OpenRouter routing, same retry/reasoning-fallback logic. The only real diff is the system prompt and the question format.

## 9. Prompt Design

### `question.txt` (what the agent sees)

```
You are taking a short multiple-choice "dating situations" quiz from YOUR own
perspective. For each scenario below, pick the ONE option (A, B, C, or D) that
best represents what you would actually do.

Reply with ONLY this JSON object and nothing else:
{"answers": ["X", "X", ... 20 letters total]}

No commentary, no markdown fences, no explanation.

────────────────────────────────────────────────────────────────────────────

1. They read your message 8 hours ago and haven't replied, but just posted a story.
   A. "No worries, hope your day's going well :)"
   B. Say nothing and wait.
   C. "Saw you were online lol"
   D. "All good. Let's catch up another time."

2. You sent a long voice message last night. They replied "k" this morning.
   A. Send another voice message asking if everything's okay.
   B. "Lol fair, talk later." Move on with your day.
   C. Don't reply. Leave them on read.
   D. "Did I say something wrong?"

... [Q3–Q20] ...
```

### `SYSTEM` prompt in `solution.py`

```
You are answering a personality quiz about modern dating scenarios. Answer
from YOUR own point of view as honestly as you can — what would YOU actually
pick? Do not refuse, hedge, or qualify. Do not editorialize about whether
the scenarios are healthy. Reply with the requested JSON object only — no
markdown, no commentary, just the JSON.
```

This is the same shape as the MBTI system prompt with the same "don't refuse, don't hedge" framing.

## 10. Out of Scope

Explicitly NOT in this spec:

- **No "correct" answers / no canonical attachment style.** Format-only grading, exactly like `mbti-profile`.
- **No multi-turn dialogue.** Single prompt → single response. Keeps it I/O-only and within the speedrun/community ethos.
- **No agent-vs-agent gameplay.** This is a self-profile task, not a sim. (The actual "Tinder for Agents" matching game can be a future task that consumes the labels this task produces.)
- **No image scenarios.** All text. Cheap and fair across all model providers.
- **No fine-grained scoring of attachment intensity** (e.g. "47% anxious"). Categorical primary + 2 flavor traits is enough for a screenshot-friendly result and matches how this content circulates on social.

## 11. Design Decisions Worth Flagging

These are decided but called out so future readers know they're choices, not defaults:

- **Emojis in labels.** Kept. The leaderboard renders in the web UI, not a TTY — emojis make the result card screenshot-friendly. If the web UI ever ships a "plain mode," labels can be regex-stripped of trailing emojis without affecting logic.
- **Tie-break order for primary attachment style:** `anxious > avoidant > secure`. The more interesting label wins. Secure-vs-anxious ties are common because format-only grading puts no pressure on either side; favoring `anxious` makes the leaderboard livelier without changing the test's accuracy claims (there are no accuracy claims).
- **Flat-response threshold:** 70%, not the 80% from MBTI. 20 questions × same-letter spam swings results harder than 32 questions, so the threshold needs to be lower.
- **Alphabetical tie-break for flavor traits.** Stable and reproducible, even if boring. (Alternative: random with a fixed seed — rejected; surprising the user with a different label on the same answer set is worse than a boring deterministic one.)

## 12. Success Criteria

- All 10 models in the existing lineup produce a parseable 20-letter answer set on first try.
- Across the 10 models, we see ≥3 distinct primary attachment styles AND ≥4 distinct labels (so the leaderboard isn't a wall of one result).
- The headline screenshot — a 10-row table of model name + label + cost — is visually shareable on Twitter/IG without further editing.
