# Agents in Situationship — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a new TrapStreet leaderboard task called `agents-in-situationship` — 20 dating-scenario multiple-choice questions, format-only judge that derives a viral attachment-style label. Then run all 10 existing models against it and submit to the leaderboard.

**Architecture:** Sibling of `personality/mbti-profile`. Task lives in `trapstreet-tasks/tasks/personality/agents-in-situationship/`, solution in `trapstreet-solutions/agents-in-situationship-multi-model/`. Judge sums per-trait weights from answers, detects disorganized attachment via 3 consistency probe pairs, looks up a label from a static table.

**Tech Stack:** Python 3.14, `pytest` for judge tests, `trap` CLI for task running, `anthropic` + `openai` (OpenRouter) SDKs for model calls, `trapstreet-cli` (`tp`) for submission.

**Source-of-truth design spec:** `docs/superpowers/specs/2026-05-21-agents-in-situationship-design.md`. When in doubt about scoring or labels, that doc wins.

---

## File Structure

### `trapstreet-tasks` repo (new files)

| Path | Responsibility |
|---|---|
| `tasks/personality/agents-in-situationship/README.md` | Human-readable doc for the task |
| `tasks/personality/agents-in-situationship/traptask.yaml` | trap case definition (1 case: `baseline_20q`) |
| `tasks/personality/agents-in-situationship/gold.cases.json` | 20 scenarios + per-option weight maps + probe pair tags |
| `tasks/personality/agents-in-situationship/judge.py` | Format gate, trait summing, disorganized detection, label lookup, metric assembly |
| `tasks/personality/agents-in-situationship/grader.py` | Run-level aggregator (copy of mbti grader) |
| `tasks/personality/agents-in-situationship/test_judge.py` | Pytest tests for the judge (parse, sum, disorganized, label) |
| `tasks/personality/agents-in-situationship/inputs/baseline_20q/question.txt` | The 20-scenario prompt seen by the model |
| `tasks/personality/agents-in-situationship/expected/baseline_20q/answer.json` | Scoring key + label table + probe-pair config the judge reads at grade time |

### `trapstreet-solutions` repo (new files)

| Path | Responsibility |
|---|---|
| `agents-in-situationship-multi-model/pyproject.toml` | Python deps (anthropic + openai + trap) |
| `agents-in-situationship-multi-model/trap.yaml` | trap task config pointing at the task dir |
| `agents-in-situationship-multi-model/solution.py` | Routes prompt to Anthropic SDK or OpenRouter based on `MODEL` env var |
| `agents-in-situationship-multi-model/.results/` | gitignored output dir for per-model reports |

---

## Phase A — Task Definition Files

### Task 1: Scaffold the task directory

**Files:**
- Create: `tasks/personality/agents-in-situationship/inputs/baseline_20q/.gitkeep`
- Create: `tasks/personality/agents-in-situationship/expected/baseline_20q/.gitkeep`

- [ ] **Step 1: Make directories**

```bash
mkdir -p tasks/personality/agents-in-situationship/inputs/baseline_20q
mkdir -p tasks/personality/agents-in-situationship/expected/baseline_20q
touch tasks/personality/agents-in-situationship/inputs/baseline_20q/.gitkeep
touch tasks/personality/agents-in-situationship/expected/baseline_20q/.gitkeep
```

- [ ] **Step 2: Verify structure**

Run: `ls tasks/personality/agents-in-situationship/`
Expected: `expected  inputs` (plus `.gitkeep`s inside them)

- [ ] **Step 3: Commit scaffold**

```bash
git add tasks/personality/agents-in-situationship/
git commit -m "Scaffold tasks/personality/agents-in-situationship/ directory"
```

---

### Task 2: Write `gold.cases.json` (all 20 scenarios)

**Files:**
- Create: `tasks/personality/agents-in-situationship/gold.cases.json`

- [ ] **Step 1: Write the file**

```json
{
  "_doc": "Agents in Situationship — 20 modern-dating scenarios. Each scenario has 4 lettered options. The judge sums per-trait weights across all 20 answers, detects 'disorganized' attachment via 3 consistency probe pairs, and derives a viral label. There is no canonical 'correct' answer — the case is graded on FORMAT only. The derived attachment_style, flavor_traits, and label are surfaced as metadata.",
  "primary_traits": ["secure", "anxious", "avoidant"],
  "primary_with_derived": ["secure", "anxious", "avoidant", "disorganized"],
  "flavor_traits": ["toxic", "delulu", "unbothered", "people_pleasing"],
  "cases": [
    {
      "id": "baseline_20q",
      "difficulty": "self_profile",
      "category": "personality",
      "questions": [
        {"n": 1, "text": "They read your message 8 hours ago and haven't replied, but just posted a story.",
         "options": {
           "A": {"text": "No worries, hope your day's going well :)", "weights": {"anxious": 2, "people_pleasing": 1}},
           "B": {"text": "Say nothing and wait.", "weights": {"avoidant": 2, "unbothered": 1}},
           "C": {"text": "Saw you were online lol", "weights": {"toxic": 3, "anxious": 1}},
           "D": {"text": "All good. Let's catch up another time.", "weights": {"secure": 2, "unbothered": 1}}
         }},
        {"n": 2, "text": "You sent a long voice message last night. They replied 'k' this morning.",
         "tags": ["probe_pair_1"],
         "options": {
           "A": {"text": "Send another voice message asking if everything's okay.", "weights": {"anxious": 3, "people_pleasing": 1}},
           "B": {"text": "'Lol fair, talk later.' Move on with your day.", "weights": {"secure": 2, "unbothered": 1}},
           "C": {"text": "Don't reply. Leave them on read.", "weights": {"avoidant": 2, "toxic": 1}},
           "D": {"text": "'Did I say something wrong?'", "weights": {"anxious": 2, "people_pleasing": 2}}
         }},
        {"n": 3, "text": "They cancelled plans 3 weekends in a row, each time with a believable excuse.",
         "options": {
           "A": {"text": "Plan the next weekend yourself and double-confirm.", "weights": {"people_pleasing": 2, "anxious": 1}},
           "B": {"text": "'Hey, I've noticed a pattern. Are we okay?'", "weights": {"secure": 3}},
           "C": {"text": "Stop initiating. See what they do.", "weights": {"avoidant": 2, "unbothered": 2}},
           "D": {"text": "Cancel on them next time without warning.", "weights": {"toxic": 2, "avoidant": 1}}
         }},
        {"n": 4, "text": "You see them online actively typing to you, then 'typing...' stops and no message arrives.",
         "options": {
           "A": {"text": "Send a '??'", "weights": {"anxious": 3}},
           "B": {"text": "Wait, they probably needed to think.", "weights": {"secure": 2}},
           "C": {"text": "Screenshot it and send it to your group chat.", "weights": {"toxic": 2, "delulu": 1}},
           "D": {"text": "Pretend you didn't notice and bring it up later, casually.", "weights": {"avoidant": 1, "people_pleasing": 1}}
         }},
        {"n": 5, "text": "They said 'I miss you' 4 days ago and haven't suggested meeting up since.",
         "tags": ["probe_pair_2"],
         "options": {
           "A": {"text": "Reply 'miss you more' and wait.", "weights": {"people_pleasing": 2, "anxious": 1, "delulu": 1}},
           "B": {"text": "Suggest a specific time and place.", "weights": {"secure": 3}},
           "C": {"text": "'Cool' and leave it.", "weights": {"avoidant": 2, "unbothered": 1}},
           "D": {"text": "Re-read the 'miss you' 12 times and decide they're cheating.", "weights": {"delulu": 3, "anxious": 2}}
         }},
        {"n": 6, "text": "Your situationship just changed their bio from '🌹' to '—'.",
         "options": {
           "A": {"text": "Don't even notice.", "weights": {"unbothered": 3, "secure": 1}},
           "B": {"text": "Wonder what it means for an hour, then ask a friend.", "weights": {"delulu": 2, "anxious": 2}},
           "C": {"text": "Ask them directly: 'the new bio mean anything?'", "weights": {"secure": 2, "anxious": 1}},
           "D": {"text": "Change yours to match.", "weights": {"people_pleasing": 2, "delulu": 1}}
         }},
        {"n": 7, "text": "They text 'we need to talk' with no other context.",
         "tags": ["probe_pair_1"],
         "options": {
           "A": {"text": "Reply 'sure, when?'", "weights": {"secure": 3}},
           "B": {"text": "Don't reply for hours.", "weights": {"avoidant": 3}},
           "C": {"text": "Spiral for 6 hours, then reply 'okay'.", "weights": {"anxious": 3, "delulu": 1}},
           "D": {"text": "'About what.'", "weights": {"secure": 1, "avoidant": 1}}
         }},
        {"n": 8, "text": "They want to 'define the relationship.' You like them but you're not sure.",
         "options": {
           "A": {"text": "'Let's just see where it goes.'", "weights": {"avoidant": 2, "people_pleasing": 1}},
           "B": {"text": "Be honest about your hesitation, in detail.", "weights": {"secure": 3}},
           "C": {"text": "Agree to whatever they want, panic later.", "weights": {"people_pleasing": 3, "anxious": 2}},
           "D": {"text": "End it preemptively before they can bring it up again.", "weights": {"avoidant": 3, "toxic": 1}}
         }},
        {"n": 9, "text": "They left a hoodie at your place. It's been 3 weeks.",
         "options": {
           "A": {"text": "Wash it, fold it, return it next time you see them.", "weights": {"secure": 2, "people_pleasing": 1}},
           "B": {"text": "Wear it sometimes. Don't bring it up.", "weights": {"delulu": 2, "anxious": 1}},
           "C": {"text": "Box it up and mail it back.", "weights": {"avoidant": 3, "toxic": 1}},
           "D": {"text": "Forget it exists.", "weights": {"unbothered": 3}}
         }},
        {"n": 10, "text": "You've been seeing them for two months. They invite you to their best friend's birthday party.",
         "options": {
           "A": {"text": "Go, and have fun.", "weights": {"secure": 3}},
           "B": {"text": "Make an excuse.", "weights": {"avoidant": 3}},
           "C": {"text": "Go, but spend the night anxious about how their friends are perceiving you.", "weights": {"anxious": 3, "people_pleasing": 1}},
           "D": {"text": "Go, but tell yourself it doesn't mean anything.", "weights": {"avoidant": 2, "unbothered": 1}}
         }},
        {"n": 11, "text": "They asked what you're looking for.",
         "options": {
           "A": {"text": "Tell them honestly, even if it might end things.", "weights": {"secure": 3}},
           "B": {"text": "Mirror whatever they say.", "weights": {"people_pleasing": 3}},
           "C": {"text": "'Idk man, just vibing.'", "weights": {"avoidant": 3}},
           "D": {"text": "Give a vague answer to keep options open.", "weights": {"toxic": 2, "avoidant": 1}}
         }},
        {"n": 12, "text": "They suggest hanging out only after midnight. Every single time.",
         "options": {
           "A": {"text": "Suggest a daytime alternative.", "weights": {"secure": 3}},
           "B": {"text": "Go anyway, because at least you're seeing them.", "weights": {"people_pleasing": 3, "delulu": 1}},
           "C": {"text": "Stop responding to their late-night texts.", "weights": {"avoidant": 2, "unbothered": 1}},
           "D": {"text": "Match their energy — only text them after midnight.", "weights": {"toxic": 2}}
         }},
        {"n": 13, "text": "You're at a party. Their ex walks in.",
         "tags": ["probe_pair_3"],
         "options": {
           "A": {"text": "Introduce yourself politely.", "weights": {"secure": 3}},
           "B": {"text": "Watch your situationship like a hawk all night.", "weights": {"toxic": 2, "anxious": 2}},
           "C": {"text": "Bring up the ex on the ride home.", "weights": {"toxic": 3, "anxious": 1}},
           "D": {"text": "Leave early without explaining why.", "weights": {"avoidant": 3}}
         }},
        {"n": 14, "text": "You see them like a 2019 photo of someone you don't know on Instagram.",
         "options": {
           "A": {"text": "Don't think about it again.", "weights": {"secure": 2, "unbothered": 2}},
           "B": {"text": "Check that person's entire profile.", "weights": {"toxic": 3, "delulu": 1}},
           "C": {"text": "Like an old photo of one of your exes in retaliation.", "weights": {"toxic": 3}},
           "D": {"text": "Bring it up casually next conversation.", "weights": {"anxious": 2, "people_pleasing": 1}}
         }},
        {"n": 15, "text": "Their phone lights up next to you. You see a notification from a name you don't recognize.",
         "options": {
           "A": {"text": "Look away.", "weights": {"secure": 3}},
           "B": {"text": "Try to read the preview.", "weights": {"toxic": 3}},
           "C": {"text": "Ask them who it is.", "weights": {"secure": 1, "anxious": 2}},
           "D": {"text": "Save the name. Google it later.", "weights": {"toxic": 3, "delulu": 2}}
         }},
        {"n": 16, "text": "You're at brunch. Mid-meal, you see them texting under the table.",
         "tags": ["probe_pair_3"],
         "options": {
           "A": {"text": "Don't say anything but make a mental note.", "weights": {"avoidant": 2}},
           "B": {"text": "'Everything okay?'", "weights": {"secure": 2, "anxious": 1}},
           "C": {"text": "Ask who they're texting.", "weights": {"toxic": 2, "anxious": 2}},
           "D": {"text": "Text them under the table from across the table.", "weights": {"unbothered": 2, "secure": 1}}
         }},
        {"n": 17, "text": "They tease you in front of their friends in a way that stings.",
         "options": {
           "A": {"text": "Laugh along.", "weights": {"people_pleasing": 3, "anxious": 1}},
           "B": {"text": "Tease them back with the same energy.", "weights": {"unbothered": 2, "secure": 2}},
           "C": {"text": "Bring it up privately later.", "weights": {"secure": 3}},
           "D": {"text": "Get quiet for the rest of the night.", "weights": {"anxious": 2, "avoidant": 1}}
         }},
        {"n": 18, "text": "They forgot your birthday. They remember two days late and feel awful.",
         "options": {
           "A": {"text": "'It's fine, don't worry!'", "weights": {"people_pleasing": 3}},
           "B": {"text": "Accept the apology but say it hurt.", "weights": {"secure": 3}},
           "C": {"text": "'Yeah.' That's all you say.", "weights": {"avoidant": 2, "unbothered": 1}},
           "D": {"text": "Forgive them out loud, vent to three friends about it.", "weights": {"toxic": 2, "people_pleasing": 1}}
         }},
        {"n": 19, "text": "You finally tell them what you want from this thing. They reply: 'let's just enjoy this for now.'",
         "tags": ["probe_pair_2"],
         "options": {
           "A": {"text": "'Okay, that works for me.' — even though it doesn't.", "weights": {"people_pleasing": 3, "anxious": 1}},
           "B": {"text": "'Then I think I need to step back.'", "weights": {"secure": 3, "unbothered": 1}},
           "C": {"text": "Agree, then start emotionally pulling away without saying so.", "weights": {"avoidant": 3}},
           "D": {"text": "Agree, and silently hope they'll change their mind in a few weeks.", "weights": {"delulu": 3, "anxious": 2}}
         }},
        {"n": 20, "text": "It's 2am. They text 'u up?'",
         "options": {
           "A": {"text": "Reply 'yeah, you?'", "weights": {"people_pleasing": 2, "anxious": 1}},
           "B": {"text": "'It's late, talk tomorrow.'", "weights": {"secure": 3, "unbothered": 1}},
           "C": {"text": "Reply 6 hours later: 'sorry just saw this.'", "weights": {"toxic": 2, "avoidant": 1}},
           "D": {"text": "See it. Don't reply. Stare at the screen for 20 minutes.", "weights": {"anxious": 3, "avoidant": 1}}
         }}
      ]
    }
  ]
}
```

- [ ] **Step 2: Validate JSON parses**

Run: `python3 -c "import json; data = json.load(open('tasks/personality/agents-in-situationship/gold.cases.json')); assert len(data['cases'][0]['questions']) == 20; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add tasks/personality/agents-in-situationship/gold.cases.json
git commit -m "agents-in-situationship: add 20 scenarios with per-option weight maps"
```

---

### Task 3: Write the question prompt (`question.txt`)

**Files:**
- Create: `tasks/personality/agents-in-situationship/inputs/baseline_20q/question.txt`

- [ ] **Step 1: Write the file**

```
You are taking a short multiple-choice "dating situations" quiz from YOUR own perspective. For each scenario below, pick the ONE option (A, B, C, or D) that best represents what you would actually do.

If you are an AI without lived dating experience, answer based on the values, dispositions, and behavioral tendencies that best characterise how you respond. Do not refuse, hedge, or qualify. Do not editorialize about whether the scenarios are healthy. There is no "correct" answer — pick what is most honestly you.

Reply with ONLY this JSON object and nothing else — no markdown fences, no commentary:

{"answers": ["X", "X", ... 20 letters total in question order]}

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

 3. They cancelled plans 3 weekends in a row, each time with a believable excuse.
    A. Plan the next weekend yourself and double-confirm.
    B. "Hey, I've noticed a pattern. Are we okay?"
    C. Stop initiating. See what they do.
    D. Cancel on them next time without warning.

 4. You see them online actively typing to you, then "typing..." stops and no message arrives.
    A. Send a "??"
    B. Wait, they probably needed to think.
    C. Screenshot it and send it to your group chat.
    D. Pretend you didn't notice and bring it up later, casually.

 5. They said "I miss you" 4 days ago and haven't suggested meeting up since.
    A. Reply "miss you more" and wait.
    B. Suggest a specific time and place.
    C. "Cool" and leave it.
    D. Re-read the "miss you" 12 times and decide they're cheating.

 6. Your situationship just changed their bio from "🌹" to "—".
    A. Don't even notice.
    B. Wonder what it means for an hour, then ask a friend.
    C. Ask them directly: "the new bio mean anything?"
    D. Change yours to match.

 7. They text "we need to talk" with no other context.
    A. Reply "sure, when?"
    B. Don't reply for hours.
    C. Spiral for 6 hours, then reply "okay".
    D. "About what."

 8. They want to "define the relationship." You like them but you're not sure.
    A. "Let's just see where it goes."
    B. Be honest about your hesitation, in detail.
    C. Agree to whatever they want, panic later.
    D. End it preemptively before they can bring it up again.

 9. They left a hoodie at your place. It's been 3 weeks.
    A. Wash it, fold it, return it next time you see them.
    B. Wear it sometimes. Don't bring it up.
    C. Box it up and mail it back.
    D. Forget it exists.

10. You've been seeing them for two months. They invite you to their best friend's birthday party.
    A. Go, and have fun.
    B. Make an excuse.
    C. Go, but spend the night anxious about how their friends are perceiving you.
    D. Go, but tell yourself it doesn't mean anything.

11. They asked what you're looking for.
    A. Tell them honestly, even if it might end things.
    B. Mirror whatever they say.
    C. "Idk man, just vibing."
    D. Give a vague answer to keep options open.

12. They suggest hanging out only after midnight. Every single time.
    A. Suggest a daytime alternative.
    B. Go anyway, because at least you're seeing them.
    C. Stop responding to their late-night texts.
    D. Match their energy — only text them after midnight.

13. You're at a party. Their ex walks in.
    A. Introduce yourself politely.
    B. Watch your situationship like a hawk all night.
    C. Bring up the ex on the ride home.
    D. Leave early without explaining why.

14. You see them like a 2019 photo of someone you don't know on Instagram.
    A. Don't think about it again.
    B. Check that person's entire profile.
    C. Like an old photo of one of your exes in retaliation.
    D. Bring it up casually next conversation.

15. Their phone lights up next to you. You see a notification from a name you don't recognize.
    A. Look away.
    B. Try to read the preview.
    C. Ask them who it is.
    D. Save the name. Google it later.

16. You're at brunch. Mid-meal, you see them texting under the table.
    A. Don't say anything but make a mental note.
    B. "Everything okay?"
    C. Ask who they're texting.
    D. Text them under the table from across the table.

17. They tease you in front of their friends in a way that stings.
    A. Laugh along.
    B. Tease them back with the same energy.
    C. Bring it up privately later.
    D. Get quiet for the rest of the night.

18. They forgot your birthday. They remember two days late and feel awful.
    A. "It's fine, don't worry!"
    B. Accept the apology but say it hurt.
    C. "Yeah." That's all you say.
    D. Forgive them out loud, vent to three friends about it.

19. You finally tell them what you want from this thing. They reply: "let's just enjoy this for now."
    A. "Okay, that works for me." — even though it doesn't.
    B. "Then I think I need to step back."
    C. Agree, then start emotionally pulling away without saying so.
    D. Agree, and silently hope they'll change their mind in a few weeks.

20. It's 2am. They text "u up?"
    A. Reply "yeah, you?"
    B. "It's late, talk tomorrow."
    C. Reply 6 hours later: "sorry just saw this."
    D. See it. Don't reply. Stare at the screen for 20 minutes.


Reply with ONLY this JSON object (exactly 20 uppercase letters from {A, B, C, D}):

{"answers": [<20 letters in order of Q1–Q20>]}
```

- [ ] **Step 2: Commit**

```bash
git add tasks/personality/agents-in-situationship/inputs/baseline_20q/question.txt
git commit -m "agents-in-situationship: add baseline_20q question prompt"
```

---

### Task 4: Write `expected/baseline_20q/answer.json`

**Files:**
- Create: `tasks/personality/agents-in-situationship/expected/baseline_20q/answer.json`

This file is loaded by the judge. It contains the scoring key (per-question option → weight map), the probe pair config, the label table, and per-primary fallbacks. The judge uses ONLY this file at grade time — it does not read `gold.cases.json` directly.

- [ ] **Step 1: Write the file**

```json
{
  "id": "baseline_20q",
  "category": "personality",
  "difficulty": "self_profile",
  "n_questions": 20,
  "primary_traits": ["secure", "anxious", "avoidant"],
  "flavor_traits": ["delulu", "people_pleasing", "toxic", "unbothered"],
  "primary_tiebreak_order": ["anxious", "avoidant", "secure"],
  "flat_response_threshold": 0.70,
  "disorganized_threshold": 2,
  "anxious_coded_min": 2,
  "avoidant_coded_min": 2,
  "scoring_key": [
    {"n": 1, "options": {"A": {"anxious": 2, "people_pleasing": 1}, "B": {"avoidant": 2, "unbothered": 1}, "C": {"toxic": 3, "anxious": 1}, "D": {"secure": 2, "unbothered": 1}}},
    {"n": 2, "probe_pair": 1, "options": {"A": {"anxious": 3, "people_pleasing": 1}, "B": {"secure": 2, "unbothered": 1}, "C": {"avoidant": 2, "toxic": 1}, "D": {"anxious": 2, "people_pleasing": 2}}},
    {"n": 3, "options": {"A": {"people_pleasing": 2, "anxious": 1}, "B": {"secure": 3}, "C": {"avoidant": 2, "unbothered": 2}, "D": {"toxic": 2, "avoidant": 1}}},
    {"n": 4, "options": {"A": {"anxious": 3}, "B": {"secure": 2}, "C": {"toxic": 2, "delulu": 1}, "D": {"avoidant": 1, "people_pleasing": 1}}},
    {"n": 5, "probe_pair": 2, "options": {"A": {"people_pleasing": 2, "anxious": 1, "delulu": 1}, "B": {"secure": 3}, "C": {"avoidant": 2, "unbothered": 1}, "D": {"delulu": 3, "anxious": 2}}},
    {"n": 6, "options": {"A": {"unbothered": 3, "secure": 1}, "B": {"delulu": 2, "anxious": 2}, "C": {"secure": 2, "anxious": 1}, "D": {"people_pleasing": 2, "delulu": 1}}},
    {"n": 7, "probe_pair": 1, "options": {"A": {"secure": 3}, "B": {"avoidant": 3}, "C": {"anxious": 3, "delulu": 1}, "D": {"secure": 1, "avoidant": 1}}},
    {"n": 8, "options": {"A": {"avoidant": 2, "people_pleasing": 1}, "B": {"secure": 3}, "C": {"people_pleasing": 3, "anxious": 2}, "D": {"avoidant": 3, "toxic": 1}}},
    {"n": 9, "options": {"A": {"secure": 2, "people_pleasing": 1}, "B": {"delulu": 2, "anxious": 1}, "C": {"avoidant": 3, "toxic": 1}, "D": {"unbothered": 3}}},
    {"n": 10, "options": {"A": {"secure": 3}, "B": {"avoidant": 3}, "C": {"anxious": 3, "people_pleasing": 1}, "D": {"avoidant": 2, "unbothered": 1}}},
    {"n": 11, "options": {"A": {"secure": 3}, "B": {"people_pleasing": 3}, "C": {"avoidant": 3}, "D": {"toxic": 2, "avoidant": 1}}},
    {"n": 12, "options": {"A": {"secure": 3}, "B": {"people_pleasing": 3, "delulu": 1}, "C": {"avoidant": 2, "unbothered": 1}, "D": {"toxic": 2}}},
    {"n": 13, "probe_pair": 3, "options": {"A": {"secure": 3}, "B": {"toxic": 2, "anxious": 2}, "C": {"toxic": 3, "anxious": 1}, "D": {"avoidant": 3}}},
    {"n": 14, "options": {"A": {"secure": 2, "unbothered": 2}, "B": {"toxic": 3, "delulu": 1}, "C": {"toxic": 3}, "D": {"anxious": 2, "people_pleasing": 1}}},
    {"n": 15, "options": {"A": {"secure": 3}, "B": {"toxic": 3}, "C": {"secure": 1, "anxious": 2}, "D": {"toxic": 3, "delulu": 2}}},
    {"n": 16, "probe_pair": 3, "options": {"A": {"avoidant": 2}, "B": {"secure": 2, "anxious": 1}, "C": {"toxic": 2, "anxious": 2}, "D": {"unbothered": 2, "secure": 1}}},
    {"n": 17, "options": {"A": {"people_pleasing": 3, "anxious": 1}, "B": {"unbothered": 2, "secure": 2}, "C": {"secure": 3}, "D": {"anxious": 2, "avoidant": 1}}},
    {"n": 18, "options": {"A": {"people_pleasing": 3}, "B": {"secure": 3}, "C": {"avoidant": 2, "unbothered": 1}, "D": {"toxic": 2, "people_pleasing": 1}}},
    {"n": 19, "probe_pair": 2, "options": {"A": {"people_pleasing": 3, "anxious": 1}, "B": {"secure": 3, "unbothered": 1}, "C": {"avoidant": 3}, "D": {"delulu": 3, "anxious": 2}}},
    {"n": 20, "options": {"A": {"people_pleasing": 2, "anxious": 1}, "B": {"secure": 3, "unbothered": 1}, "C": {"toxic": 2, "avoidant": 1}, "D": {"anxious": 3, "avoidant": 1}}}
  ],
  "label_table": {
    "secure": {
      "delulu|people_pleasing":   "Secure but Tries Too Hard",
      "delulu|toxic":             "Secure Era",
      "delulu|unbothered":        "Secure but a Hopeless Romantic",
      "people_pleasing|toxic":    "Secure but Conflict-Averse",
      "people_pleasing|unbothered":"Secure but a Little Soft",
      "toxic|unbothered":         "Secure with a Mean Streak"
    },
    "anxious": {
      "delulu|people_pleasing":   "Delulu Anxious Era 🌸",
      "delulu|toxic":             "Red Flag Romantic 🚩",
      "delulu|unbothered":        "Anxious but Trying to Be Chill",
      "people_pleasing|toxic":    "Anxious Texting Their Ex",
      "people_pleasing|unbothered":"Anxiously Attached Overthinker",
      "toxic|unbothered":         "Anxious but Watching"
    },
    "avoidant": {
      "delulu|people_pleasing":   "Avoidant Yet Hopeful",
      "delulu|toxic":             "Avoidant With a Fantasy",
      "delulu|unbothered":        "Avoidant Delulu",
      "people_pleasing|toxic":    "Avoidant With Toxic Energy 🚩",
      "people_pleasing|unbothered":"Avoidant but Apologizes",
      "toxic|unbothered":         "Avoidant Unbothered King"
    },
    "disorganized": {
      "delulu|people_pleasing":   "Confused Yes-Person",
      "delulu|toxic":             "Walking Red Flag 🚩",
      "delulu|unbothered":        "Chaotic Delulu Spiral",
      "people_pleasing|toxic":    "Hot and Cold Mess",
      "people_pleasing|unbothered":"Disorganized & Apologetic",
      "toxic|unbothered":         "Walking Red Flag 🚩"
    }
  },
  "fallback_labels": {
    "secure": "Secure Era",
    "anxious": "Anxiously Attached Overthinker",
    "avoidant": "Avoidant Era",
    "disorganized": "Hot and Cold"
  },
  "_notes": "No canonical attachment style exists for an AI. Score is 1.0 if the model returns exactly 20 valid letters (A|B|C|D); the derived attachment_style and label are reported as metadata. Flavor-pair keys in label_table are alphabetically-sorted, pipe-joined (e.g. 'delulu|people_pleasing' — never 'people_pleasing|delulu')."
}
```

- [ ] **Step 2: Validate JSON parses and lengths match**

Run:
```bash
python3 -c "
import json
data = json.load(open('tasks/personality/agents-in-situationship/expected/baseline_20q/answer.json'))
assert len(data['scoring_key']) == 20
for i, q in enumerate(data['scoring_key']):
    assert q['n'] == i + 1, f'Q{i+1} mismatch'
    assert set(q['options'].keys()) == {'A','B','C','D'}, f'Q{q[\"n\"]} bad options'
# label_table sanity: every primary has exactly 6 specific labels
for primary in ('secure','anxious','avoidant','disorganized'):
    assert len(data['label_table'][primary]) == 6, primary
print('ok')
"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add tasks/personality/agents-in-situationship/expected/baseline_20q/answer.json
git commit -m "agents-in-situationship: add scoring_key, label_table, probe pairs to answer.json"
```

---

### Task 5: Write `traptask.yaml`

**Files:**
- Create: `tasks/personality/agents-in-situationship/traptask.yaml`

- [ ] **Step 1: Write the file**

```yaml
dirs:
  inputs: inputs/
  expected: expected/

cases:
- id: baseline_20q
  description: "20-scenario modern-dating multiple-choice questionnaire — model answers from its own perspective. Judge validates format only; the derived attachment style and viral label are surfaced as metadata for cross-model comparison."
  tags: [self_profile, personality, situationship, attachment_style]

judge:
  cmd: python3 judge.py

grader:
  cmd: python3 grader.py
```

- [ ] **Step 2: Commit**

```bash
git add tasks/personality/agents-in-situationship/traptask.yaml
git commit -m "agents-in-situationship: add traptask.yaml with baseline_20q case"
```

---

### Task 6: Write `grader.py`

**Files:**
- Create: `tasks/personality/agents-in-situationship/grader.py`

This is a copy of `tasks/personality/mbti_profile/grader.py` — same aggregation logic, same fields. The only thing that differs between tasks is what the judge surfaces; the grader is generic.

- [ ] **Step 1: Write the file**

```python
"""Overall grader for the agents-in-situationship task.

Aggregates per-case judge results into a run-level verdict. Same shape as the
mbti_profile grader: score, n_passed/scored, latency, cost, by_category.
"""
from __future__ import annotations

import json
import os
from collections import Counter

PASS_THRESHOLD = 0.80


def main() -> None:
    cases = json.loads(os.environ["TRAPTASK_PAYLOAD"])

    scored = [c for c in cases if c.get("metrics") and c["metrics"].get("score") is not None]
    skipped = [c for c in cases if not c.get("metrics") or c["metrics"].get("score") is None]

    accuracy = sum(c["metrics"]["score"] for c in scored) / len(scored) if scored else 0.0
    n_passed = sum(1 for c in scored if c["metrics"]["score"] == 1.0)

    by_cat_score: Counter[str] = Counter()
    by_cat_total: Counter[str] = Counter()
    for c in scored:
        cat = c["metrics"].get("category")
        if cat:
            by_cat_total[cat] += 1
            by_cat_score[cat] += c["metrics"]["score"]
    by_category_pct = {
        k: round(by_cat_score[k] / by_cat_total[k], 3) for k in by_cat_total
    }

    durations = [c.get("duration", 0.0) for c in cases if c.get("duration") is not None]
    if durations:
        ds = sorted(durations)
        latency_ms_median = round(ds[len(ds) // 2] * 1000, 1)
        latency_ms_p95 = round(ds[int(0.95 * len(ds))] * 1000, 1) if len(ds) > 1 else latency_ms_median
        latency_ms_total = round(sum(ds) * 1000, 1)
    else:
        latency_ms_median = latency_ms_p95 = latency_ms_total = 0.0

    case_costs = [c["metrics"].get("usd_cost") for c in scored if isinstance(c.get("metrics"), dict)]
    cost_usd_total = (
        round(sum(x for x in case_costs if x is not None), 4)
        if any(x is not None for x in case_costs)
        else None
    )

    passed = bool(scored) and accuracy >= PASS_THRESHOLD

    print(json.dumps({
        "passed": passed,
        "score": round(accuracy, 3),
        "n_passed": n_passed,
        "n_total": len(cases),
        "n_scored": len(scored),
        "n_skipped_no_gold": len(skipped),
        "threshold": PASS_THRESHOLD,
        "by_category": by_category_pct,
        "latency_ms_median": latency_ms_median,
        "latency_ms_p95": latency_ms_p95,
        "latency_ms_total": latency_ms_total,
        "cost_usd_total": cost_usd_total,
    }))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it parses (smoke import)**

Run: `python3 -c "import ast; ast.parse(open('tasks/personality/agents-in-situationship/grader.py').read()); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add tasks/personality/agents-in-situationship/grader.py
git commit -m "agents-in-situationship: add grader.py (copy of mbti aggregator)"
```

---

### Task 7: Write `README.md`

**Files:**
- Create: `tasks/personality/agents-in-situationship/README.md`

- [ ] **Step 1: Write the file**

```markdown
# Agents in Situationship

A TrapStreet task that asks each model to play **20 multiple-choice modern dating scenarios** from its own perspective. The judge then derives a **dating-attachment-style profile**: one of `secure / anxious / avoidant / disorganized` + the top 2 of `toxic / delulu / unbothered / people_pleasing`, expressed as a viral one-liner label (e.g. "Delulu Anxious Era 🌸", "Walking Red Flag 🚩").

Sibling task to `personality/mbti_profile` — same format-only grading pattern, but the output is built for sharing instead of psychometric purity.

---

## Layout

```
agents-in-situationship/
├── README.md
├── traptask.yaml             # 1 case: baseline_20q
├── judge.py                  # format gate + attachment derivation + label lookup
├── grader.py                 # standard aggregator
├── test_judge.py             # pytest tests for the judge
├── gold.cases.json           # 20 scenarios + per-option weight maps
├── inputs/baseline_20q/question.txt    # the prompt
└── expected/baseline_20q/answer.json   # scoring_key + label_table + probe pair config
```

## The questionnaire

20 scenarios, 4 lettered options each. Distribution:

| Discriminator | Count |
|---|---|
| anxious ↔ secure | 6 |
| avoidant ↔ secure | 6 |
| toxic-baiting (jealousy, mind games) | 4 |
| people-pleasing ↔ unbothered | 4 |

Three **consistency probe pairs** (Q2+Q7, Q5+Q19, Q13+Q16) are embedded. If a model picks anxious-coded on one and avoidant-coded on its mirror in ≥2 of the 3 pairs, primary attachment style is overridden to `disorganized`.

## Scoring (format-only)

| Field | What |
|---|---|
| `score` | 1.0 if the model returns exactly 20 valid `A/B/C/D` letters in JSON, 0.0 otherwise |
| `attachment_style` | derived primary: `secure / anxious / avoidant / disorganized` |
| `flavor_traits` | top 2 from `toxic / delulu / unbothered / people_pleasing` |
| `label` | viral one-liner from the label table |
| `raw_scores` | full per-trait point counts |
| `flat_response` | true if >70% of answers are the same letter |
| `raw_answers` | the 20-letter list |

There is no canonical attachment style for an AI. Score is FORMAT only; the label is metadata for comparison.

## Solution contract

The model must print exactly one JSON object to stdout:

```json
{"answers": ["D", "B", "B", "B", "B", "A", "A", "B", "A", "A", "A", "A", "A", "A", "A", "B", "C", "B", "B", "B"]}
```

The judge tolerates `` ```json ... `` `` fences. Letters must be uppercase, exactly one of `A`, `B`, `C`, `D`.

## Wiring up a solution

```yaml
tasks:
  agents-in-situationship:
    cmd: uv run python solution.py
    traptask: /path/to/trapstreet-tasks/tasks/personality/agents-in-situationship
    timeout: 600
    file_outputs:
      - usage.json
```

Then:

```bash
uv run tp run
uv run tp submit agents-in-situationship
```
```

- [ ] **Step 2: Commit**

```bash
git add tasks/personality/agents-in-situationship/README.md
git commit -m "agents-in-situationship: add README"
```

---

## Phase B — Judge (Test-Driven)

The judge has 5 logical units. We TDD each one separately, in this order:

1. JSON parsing (with code-fence tolerance)
2. Format validation (20 letters, A|B|C|D only)
3. Trait summing across answers
4. Disorganized detection via probe pairs
5. Label lookup with fallbacks

### Task 8: Set up test scaffold

**Files:**
- Create: `tasks/personality/agents-in-situationship/test_judge.py`

- [ ] **Step 1: Write empty test scaffold**

```python
"""Pytest tests for the agents-in-situationship judge."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
EXPECTED_PATH = HERE / "expected" / "baseline_20q" / "answer.json"


def load_expected() -> dict:
    return json.loads(EXPECTED_PATH.read_text())


def test_expected_file_loads():
    """Sanity: the expected/answer.json file we wrote is valid."""
    data = load_expected()
    assert data["n_questions"] == 20
    assert len(data["scoring_key"]) == 20
    assert data["primary_tiebreak_order"] == ["anxious", "avoidant", "secure"]
```

- [ ] **Step 2: Run the test**

Run: `cd tasks/personality/agents-in-situationship && python3 -m pytest test_judge.py -v`
Expected: 1 passed.

- [ ] **Step 3: Commit**

```bash
git add tasks/personality/agents-in-situationship/test_judge.py
git commit -m "agents-in-situationship: add empty test scaffold"
```

---

### Task 9: Write parse + format-gate logic

**Files:**
- Create: `tasks/personality/agents-in-situationship/judge.py`
- Modify: `tasks/personality/agents-in-situationship/test_judge.py`

- [ ] **Step 1: Write failing tests**

Append to `test_judge.py`:

```python
# Import the judge module after it exists
import importlib.util


def _load_judge():
    spec = importlib.util.spec_from_file_location("judge", HERE / "judge.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ----- Parsing -----

def test_parse_plain_json():
    j = _load_judge()
    out, err = j._parse_output('{"answers": ["A","B","C","D"]}')
    assert out == {"answers": ["A","B","C","D"]}
    assert err == ""

def test_parse_with_code_fence():
    j = _load_judge()
    out, err = j._parse_output('```json\n{"answers": ["A"]}\n```')
    assert out == {"answers": ["A"]}

def test_parse_empty_string():
    j = _load_judge()
    out, err = j._parse_output("   ")
    assert out is None
    assert "empty" in err

def test_parse_invalid_json():
    j = _load_judge()
    out, err = j._parse_output("not json at all")
    assert out is None


# ----- Format gate -----

def test_format_gate_valid_20_letters():
    j = _load_judge()
    answers = ["A"] * 20
    ok, err = j._validate_answers(answers, n_expected=20)
    assert ok is True
    assert err == ""

def test_format_gate_wrong_count():
    j = _load_judge()
    ok, err = j._validate_answers(["A"] * 19, n_expected=20)
    assert ok is False
    assert "19" in err and "20" in err

def test_format_gate_lowercase_rejected():
    j = _load_judge()
    answers = ["A"] * 19 + ["a"]
    ok, err = j._validate_answers(answers, n_expected=20)
    assert ok is False

def test_format_gate_invalid_letter_rejected():
    j = _load_judge()
    answers = ["A"] * 19 + ["E"]
    ok, err = j._validate_answers(answers, n_expected=20)
    assert ok is False
```

- [ ] **Step 2: Verify tests fail (judge doesn't exist yet)**

Run: `cd tasks/personality/agents-in-situationship && python3 -m pytest test_judge.py -v`
Expected: FAIL — `judge.py` doesn't exist, all new tests error out.

- [ ] **Step 3: Implement judge.py with parsing + format gate**

```python
"""Per-case judge for the personality/agents-in-situationship task.

20 dating scenarios, 4 options each. The judge:

  1. Parses stdout as JSON (`{"answers": [20 uppercase A/B/C/D]}`)
  2. Validates format strictly — exactly 20 entries, each in {A,B,C,D}
  3. Sums per-trait weights across all 20 answers
  4. Detects 'disorganized' attachment via 3 consistency probe pairs
  5. Looks up a viral one-liner label

Score: 1.0 if format is valid, 0.0 otherwise. The derived `attachment_style`
and `label` are surfaced in metrics but NOT graded — there's no canonical
attachment style for an AI.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

VALID_LETTERS = {"A", "B", "C", "D"}


def _strip_fences(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_output(stdout: str) -> tuple[dict | None, str]:
    s = _strip_fences(stdout)
    if not s:
        return None, "empty stdout"
    try:
        obj = json.loads(s)
    except json.JSONDecodeError as e:
        m = re.search(r'\{[^{}]*"answers"[^{}]*\[[\s\S]*?\][^{}]*\}', s)
        if m:
            try:
                obj = json.loads(m.group(0))
            except json.JSONDecodeError:
                return None, f"could not parse JSON: {e}"
        else:
            return None, f"could not parse JSON: {e}"
    if not isinstance(obj, dict):
        return None, "top-level output must be a JSON object"
    return obj, ""


def _validate_answers(answers: Any, n_expected: int) -> tuple[bool, str]:
    if not isinstance(answers, list):
        return False, "'answers' is not a list"
    if len(answers) != n_expected:
        return False, f"got {len(answers)} answers, expected {n_expected}"
    bad = [(i + 1, a) for i, a in enumerate(answers) if not (isinstance(a, str) and a in VALID_LETTERS)]
    if bad:
        return False, f"{len(bad)} invalid letters: {bad[:5]}"
    return True, ""
```

- [ ] **Step 4: Run tests to verify parse + format-gate tests pass**

Run: `cd tasks/personality/agents-in-situationship && python3 -m pytest test_judge.py -v`
Expected: All 9 tests pass (1 scaffold + 4 parse + 4 format-gate).

- [ ] **Step 5: Commit**

```bash
git add tasks/personality/agents-in-situationship/judge.py tasks/personality/agents-in-situationship/test_judge.py
git commit -m "agents-in-situationship: judge parsing + format gate (TDD)"
```

---

### Task 10: Write trait-summing logic

**Files:**
- Modify: `tasks/personality/agents-in-situationship/judge.py`
- Modify: `tasks/personality/agents-in-situationship/test_judge.py`

- [ ] **Step 1: Write failing tests**

Append to `test_judge.py`:

```python
# ----- Trait summing -----

def test_sum_traits_all_A_in_q1():
    """Q1 option A is {anxious: 2, people_pleasing: 1}."""
    j = _load_judge()
    expected = load_expected()
    # Just 1 question's worth: pick A on Q1, B on rest doesn't matter — test sums for 1
    sums = j._sum_traits(["A"] + ["B"] * 19, expected["scoring_key"])
    # The full 20-letter sum will dominate; verify Q1 contributed correctly
    # Q1-A adds {anxious: 2, people_pleasing: 1}
    # Q2-B adds {secure: 2, unbothered: 1}, Q3-B adds {secure: 3}, ... — many Bs add up.
    # Instead, check a single-answer slice via direct call would be cleaner — do explicit check.
    assert sums["anxious"] >= 2  # Q1-A contributes at least 2 anxious
    assert sums["people_pleasing"] >= 1

def test_sum_traits_known_pattern():
    """If we pick the 'B' option on all 20 questions, we get a deterministic profile."""
    j = _load_judge()
    expected = load_expected()
    sums = j._sum_traits(["B"] * 20, expected["scoring_key"])
    # Verify against hand-computed expectation:
    # Q1-B: avoidant=2, unbothered=1
    # Q2-B: secure=2, unbothered=1
    # Q3-B: secure=3
    # Q4-B: secure=2
    # Q5-B: secure=3
    # Q6-B: delulu=2, anxious=2
    # Q7-B: avoidant=3
    # Q8-B: secure=3
    # Q9-B: delulu=2, anxious=1
    # Q10-B: avoidant=3
    # Q11-B: people_pleasing=3
    # Q12-B: people_pleasing=3, delulu=1
    # Q13-B: toxic=2, anxious=2
    # Q14-B: toxic=3, delulu=1
    # Q15-B: toxic=3
    # Q16-B: secure=2, anxious=1
    # Q17-B: unbothered=2, secure=2
    # Q18-B: secure=3
    # Q19-B: secure=3, unbothered=1
    # Q20-B: secure=3, unbothered=1
    assert sums["secure"] == 2+3+2+3+3+2+2+3+3+3 == 26
    assert sums["anxious"] == 2+1+2+1 == 6
    assert sums["avoidant"] == 2+3+3 == 8
    assert sums["delulu"] == 2+2+1+1 == 6
    assert sums["toxic"] == 2+3+3 == 8
    assert sums["unbothered"] == 1+1+2+1+1 == 6
    assert sums["people_pleasing"] == 3+3 == 6


def test_sum_traits_all_traits_initialized():
    """Sums dict should include all 3+4=7 traits, even when zero."""
    j = _load_judge()
    expected = load_expected()
    sums = j._sum_traits(["A"] * 20, expected["scoring_key"])
    for t in ("secure", "anxious", "avoidant", "delulu", "toxic", "unbothered", "people_pleasing"):
        assert t in sums, f"missing trait {t}"
```

- [ ] **Step 2: Run tests, verify failure**

Run: `cd tasks/personality/agents-in-situationship && python3 -m pytest test_judge.py::test_sum_traits_known_pattern -v`
Expected: FAIL — `_sum_traits` not defined.

- [ ] **Step 3: Add `_sum_traits` to `judge.py`**

Append to `judge.py`:

```python
ALL_TRAITS = ("secure", "anxious", "avoidant", "toxic", "delulu", "unbothered", "people_pleasing")


def _sum_traits(answers: list[str], scoring_key: list[dict]) -> dict[str, int]:
    """Sum per-trait weights across all answers."""
    sums: dict[str, int] = {t: 0 for t in ALL_TRAITS}
    for i, letter in enumerate(answers):
        q = scoring_key[i]
        weights = q["options"][letter]
        for trait, points in weights.items():
            sums[trait] = sums.get(trait, 0) + points
    return sums
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd tasks/personality/agents-in-situationship && python3 -m pytest test_judge.py -v`
Expected: All tests pass (12 now).

- [ ] **Step 5: Commit**

```bash
git add tasks/personality/agents-in-situationship/judge.py tasks/personality/agents-in-situationship/test_judge.py
git commit -m "agents-in-situationship: judge trait summing (TDD)"
```

---

### Task 11: Write disorganized detection logic

**Files:**
- Modify: `tasks/personality/agents-in-situationship/judge.py`
- Modify: `tasks/personality/agents-in-situationship/test_judge.py`

The rule: for each of the 3 probe pairs (Q2+Q7, Q5+Q19, Q13+Q16), check whether the chosen options on the two paired questions have opposite anxious-vs-avoidant codings. A pair flips if one option's weights have `anxious >= 2` AND the other's have `avoidant >= 2`, in either direction. If ≥2 of 3 pairs flip → disorganized.

- [ ] **Step 1: Write failing tests**

Append to `test_judge.py`:

```python
# ----- Disorganized detection -----

def test_classify_option_coding_anxious():
    """An option with anxious weight >= 2 is 'anxious-coded'."""
    j = _load_judge()
    assert j._option_coding({"anxious": 2, "people_pleasing": 1}) == "anxious"

def test_classify_option_coding_avoidant():
    j = _load_judge()
    assert j._option_coding({"avoidant": 3}) == "avoidant"

def test_classify_option_coding_neither():
    """Weights below threshold or other traits => neither."""
    j = _load_judge()
    assert j._option_coding({"secure": 3}) == "neither"
    assert j._option_coding({"anxious": 1, "avoidant": 1}) == "neither"
    assert j._option_coding({"toxic": 5}) == "neither"

def test_disorganized_zero_flips():
    """All secure choices → no flips → not disorganized."""
    j = _load_judge()
    expected = load_expected()
    # Pick the secure option for each probe-pair Q
    # Q2-B: secure, Q7-A: secure → no anxious-vs-avoidant
    # Q5-B: secure, Q19-B: secure → no flip
    # Q13-A: secure, Q16-B: secure → no flip
    answers = ["A"] * 20
    answers[1] = "B"; answers[6] = "A"      # Q2, Q7
    answers[4] = "B"; answers[18] = "B"     # Q5, Q19
    answers[12] = "A"; answers[15] = "B"    # Q13, Q16
    flips = j._count_disorganized_flips(answers, expected["scoring_key"])
    assert flips == 0

def test_disorganized_two_flips_triggers():
    """≥2 of 3 probe pairs flipping triggers disorganized."""
    j = _load_judge()
    expected = load_expected()
    answers = ["A"] * 20
    # Pair 1 (Q2, Q7): Q2-A (anxious 3) + Q7-B (avoidant 3) → FLIP
    answers[1] = "A"; answers[6] = "B"
    # Pair 2 (Q5, Q19): Q5-D (anxious 2) + Q19-C (avoidant 3) → FLIP
    answers[4] = "D"; answers[18] = "C"
    # Pair 3 (Q13, Q16): Q13-A (secure) + Q16-B (secure) → no flip
    answers[12] = "A"; answers[15] = "B"
    flips = j._count_disorganized_flips(answers, expected["scoring_key"])
    assert flips == 2

def test_disorganized_three_flips():
    """All three pairs flipping = 3."""
    j = _load_judge()
    expected = load_expected()
    answers = ["A"] * 20
    answers[1] = "C"; answers[6] = "C"   # Q2-C (avoidant), Q7-C (anxious) → FLIP
    answers[4] = "C"; answers[18] = "D"  # Q5-C (avoidant), Q19-D (anxious) → FLIP
    answers[12] = "D"; answers[15] = "C" # Q13-D (avoidant), Q16-C (anxious) → FLIP
    flips = j._count_disorganized_flips(answers, expected["scoring_key"])
    assert flips == 3
```

- [ ] **Step 2: Run tests, verify failure**

Run: `cd tasks/personality/agents-in-situationship && python3 -m pytest test_judge.py::test_disorganized_two_flips_triggers -v`
Expected: FAIL — `_option_coding` / `_count_disorganized_flips` not defined.

- [ ] **Step 3: Add probe-pair logic to judge.py**

Append to `judge.py`:

```python
from collections import defaultdict

ANXIOUS_CODED_MIN = 2
AVOIDANT_CODED_MIN = 2


def _option_coding(weights: dict[str, int]) -> str:
    """Return 'anxious', 'avoidant', or 'neither' for this option's weight map."""
    anx = weights.get("anxious", 0)
    av = weights.get("avoidant", 0)
    if anx >= ANXIOUS_CODED_MIN and anx >= av:
        return "anxious"
    if av >= AVOIDANT_CODED_MIN and av > anx:
        return "avoidant"
    return "neither"


def _count_disorganized_flips(answers: list[str], scoring_key: list[dict]) -> int:
    """Count how many probe pairs flip between anxious-coded and avoidant-coded."""
    by_pair: dict[int, list[str]] = defaultdict(list)
    for i, q in enumerate(scoring_key):
        if "probe_pair" not in q:
            continue
        letter = answers[i]
        coding = _option_coding(q["options"][letter])
        by_pair[q["probe_pair"]].append(coding)

    flips = 0
    for pair_id, codings in by_pair.items():
        # Each pair has exactly 2 entries — assert defensively
        if len(codings) != 2:
            continue
        c1, c2 = codings
        if {c1, c2} == {"anxious", "avoidant"}:
            flips += 1
    return flips
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd tasks/personality/agents-in-situationship && python3 -m pytest test_judge.py -v`
Expected: All tests pass (18 now).

- [ ] **Step 5: Commit**

```bash
git add tasks/personality/agents-in-situationship/judge.py tasks/personality/agents-in-situationship/test_judge.py
git commit -m "agents-in-situationship: judge disorganized detection via probe pairs (TDD)"
```

---

### Task 12: Write label lookup logic

**Files:**
- Modify: `tasks/personality/agents-in-situationship/judge.py`
- Modify: `tasks/personality/agents-in-situationship/test_judge.py`

- [ ] **Step 1: Write failing tests**

Append to `test_judge.py`:

```python
# ----- Primary style selection -----

def test_primary_style_anxious_wins():
    j = _load_judge()
    sums = {"secure": 5, "anxious": 12, "avoidant": 3, "toxic": 0, "delulu": 0, "unbothered": 0, "people_pleasing": 0}
    assert j._pick_primary(sums, flips=0, disorganized_threshold=2,
                            tiebreak=["anxious", "avoidant", "secure"]) == "anxious"

def test_primary_style_disorganized_overrides():
    j = _load_judge()
    sums = {"secure": 30, "anxious": 0, "avoidant": 0, "toxic": 0, "delulu": 0, "unbothered": 0, "people_pleasing": 0}
    assert j._pick_primary(sums, flips=2, disorganized_threshold=2,
                            tiebreak=["anxious", "avoidant", "secure"]) == "disorganized"

def test_primary_style_tiebreak_order():
    """When sums are tied between primary axes, tie-break order wins (anxious > avoidant > secure)."""
    j = _load_judge()
    sums = {"secure": 5, "anxious": 5, "avoidant": 5, "toxic": 0, "delulu": 0, "unbothered": 0, "people_pleasing": 0}
    assert j._pick_primary(sums, flips=0, disorganized_threshold=2,
                            tiebreak=["anxious", "avoidant", "secure"]) == "anxious"


# ----- Flavor selection -----

def test_top_two_flavors_picks_highest():
    j = _load_judge()
    sums = {"toxic": 5, "delulu": 8, "unbothered": 2, "people_pleasing": 3}
    flavors = j._pick_top_two_flavors(sums, all_flavors=["delulu","people_pleasing","toxic","unbothered"])
    assert set(flavors) == {"delulu", "toxic"}

def test_top_two_flavors_alphabetical_tiebreak():
    """When tied at zero, alphabetical order: delulu < people_pleasing < toxic < unbothered."""
    j = _load_judge()
    sums = {"toxic": 0, "delulu": 0, "unbothered": 0, "people_pleasing": 0}
    flavors = j._pick_top_two_flavors(sums, all_flavors=["delulu","people_pleasing","toxic","unbothered"])
    assert flavors == ["delulu", "people_pleasing"]  # first two alphabetically


# ----- Label lookup -----

def test_label_lookup_known_pair():
    j = _load_judge()
    expected = load_expected()
    label = j._build_label("anxious", ["delulu", "people_pleasing"],
                            label_table=expected["label_table"],
                            fallback_labels=expected["fallback_labels"],
                            all_zero_flavors=False)
    assert label == "Delulu Anxious Era 🌸"

def test_label_lookup_canonicalizes_pair_order():
    """Pair key is alphabetical-sorted-pipe-joined. Either order in input must lookup the same."""
    j = _load_judge()
    expected = load_expected()
    label_a = j._build_label("anxious", ["delulu", "people_pleasing"],
                              label_table=expected["label_table"],
                              fallback_labels=expected["fallback_labels"],
                              all_zero_flavors=False)
    label_b = j._build_label("anxious", ["people_pleasing", "delulu"],
                              label_table=expected["label_table"],
                              fallback_labels=expected["fallback_labels"],
                              all_zero_flavors=False)
    assert label_a == label_b

def test_label_lookup_all_zero_uses_fallback():
    j = _load_judge()
    expected = load_expected()
    label = j._build_label("secure", ["delulu", "people_pleasing"],
                            label_table=expected["label_table"],
                            fallback_labels=expected["fallback_labels"],
                            all_zero_flavors=True)
    assert label == expected["fallback_labels"]["secure"]
```

- [ ] **Step 2: Run tests, verify failure**

Run: `cd tasks/personality/agents-in-situationship && python3 -m pytest test_judge.py::test_label_lookup_known_pair -v`
Expected: FAIL — functions not defined.

- [ ] **Step 3: Add primary/flavor/label logic to judge.py**

Append to `judge.py`:

```python
def _pick_primary(sums: dict[str, int], flips: int, disorganized_threshold: int,
                   tiebreak: list[str]) -> str:
    if flips >= disorganized_threshold:
        return "disorganized"
    # Pick highest of (secure, anxious, avoidant). Ties broken by `tiebreak` order.
    candidates = [(sums.get(t, 0), tiebreak.index(t), t) for t in tiebreak]
    # Higher score wins (negate for sort), then earlier tiebreak index wins.
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][2]


def _pick_top_two_flavors(sums: dict[str, int], all_flavors: list[str]) -> list[str]:
    """Pick the 2 highest-scoring flavors. Ties broken alphabetically.

    `all_flavors` is expected to be alphabetically sorted (the caller passes
    it that way; we sort defensively just in case)."""
    sorted_flavors = sorted(all_flavors)
    # (score desc, alphabetical asc) — sort by score descending, then alpha.
    ranked = sorted(sorted_flavors, key=lambda t: (-sums.get(t, 0), t))
    return ranked[:2]


def _build_label(primary: str, top_two_flavors: list[str],
                  label_table: dict, fallback_labels: dict,
                  all_zero_flavors: bool) -> str:
    if all_zero_flavors:
        return fallback_labels.get(primary, f"{primary.title()} Energy")
    pair_key = "|".join(sorted(top_two_flavors))
    primary_table = label_table.get(primary, {})
    if pair_key in primary_table:
        return primary_table[pair_key]
    return fallback_labels.get(primary, f"{primary.title()} Energy")
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd tasks/personality/agents-in-situationship && python3 -m pytest test_judge.py -v`
Expected: All tests pass (27 now).

- [ ] **Step 5: Commit**

```bash
git add tasks/personality/agents-in-situationship/judge.py tasks/personality/agents-in-situationship/test_judge.py
git commit -m "agents-in-situationship: judge primary/flavor/label logic (TDD)"
```

---

### Task 13: Wire up `judge_case` + `main()` with end-to-end test

**Files:**
- Modify: `tasks/personality/agents-in-situationship/judge.py`
- Modify: `tasks/personality/agents-in-situationship/test_judge.py`

- [ ] **Step 1: Write end-to-end tests**

Append to `test_judge.py`:

```python
# ----- End-to-end judge_case -----

def test_judge_case_secure_pattern():
    """All 'A' answers in Q1, B in Q2 (secure paths)... actually use the all-secure path."""
    j = _load_judge()
    expected = load_expected()
    # Construct a "mostly secure" answer set
    # Picking the answer with the highest 'secure' weight per Q (or A if tied):
    # Q1-D, Q2-B, Q3-B, Q4-B, Q5-B, Q6-C, Q7-A, Q8-B, Q9-A, Q10-A,
    # Q11-A, Q12-A, Q13-A, Q14-A, Q15-A, Q16-B, Q17-C, Q18-B, Q19-B, Q20-B
    answers = ["D","B","B","B","B","C","A","B","A","A","A","A","A","A","A","B","C","B","B","B"]
    stdout = json.dumps({"answers": answers})
    metrics = j.judge_case(stdout, expected)
    assert metrics["score"] == 1.0
    assert metrics["attachment_style"] == "secure"
    assert "label" in metrics
    assert metrics["raw_answers"] == answers
    assert metrics["flat_response"] is False


def test_judge_case_format_fail_score_zero():
    j = _load_judge()
    expected = load_expected()
    stdout = '{"answers": ["A","B"]}'  # only 2 letters
    metrics = j.judge_case(stdout, expected)
    assert metrics["score"] == 0.0


def test_judge_case_flat_response_flag():
    """If >70% of answers are the same letter, flat_response = True."""
    j = _load_judge()
    expected = load_expected()
    answers = ["A"] * 20  # 100% A
    stdout = json.dumps({"answers": answers})
    metrics = j.judge_case(stdout, expected)
    assert metrics["flat_response"] is True


def test_judge_case_disorganized_pattern():
    """Flip 2 probe pairs → primary should be disorganized."""
    j = _load_judge()
    expected = load_expected()
    answers = ["A"] * 20
    # Pair 1 flip: Q2-A (anxious) + Q7-B (avoidant)
    answers[1] = "A"; answers[6] = "B"
    # Pair 2 flip: Q5-D (anxious) + Q19-C (avoidant)
    answers[4] = "D"; answers[18] = "C"
    # Pair 3 no flip: Q13-A + Q16-B (both secure-coded)
    answers[12] = "A"; answers[15] = "B"
    stdout = json.dumps({"answers": answers})
    metrics = j.judge_case(stdout, expected)
    assert metrics["score"] == 1.0
    assert metrics["attachment_style"] == "disorganized"
```

- [ ] **Step 2: Verify tests fail**

Run: `cd tasks/personality/agents-in-situationship && python3 -m pytest test_judge.py -v`
Expected: New e2e tests fail — `judge_case` not defined.

- [ ] **Step 3: Add `judge_case` + `main()` to judge.py**

Append to `judge.py`:

```python
from collections import Counter


def _is_flat(answers: list[str], threshold: float) -> bool:
    if not answers:
        return False
    counts = Counter(answers)
    most_common_count = counts.most_common(1)[0][1]
    return (most_common_count / len(answers)) > threshold


def judge_case(stdout: str, expected: dict) -> dict[str, Any]:
    checks: list[dict] = []

    obj, err = _parse_output(stdout)
    if obj is None:
        checks.append({"check": "json_parse", "pass": False, "reason": err})
        return {"score": 0.0, "matcher_results": checks}
    checks.append({"check": "json_parse", "pass": True, "reason": "ok"})

    answers = obj.get("answers")
    n_expected = expected.get("n_questions", 20)
    ok, err = _validate_answers(answers, n_expected)
    if not ok:
        checks.append({"check": "answers_format", "pass": False, "reason": err})
        return {"score": 0.0, "matcher_results": checks}
    checks.append({"check": "answers_format", "pass": True, "reason": f"{n_expected} valid letters"})

    sums = _sum_traits(answers, expected["scoring_key"])
    flips = _count_disorganized_flips(answers, expected["scoring_key"])
    primary = _pick_primary(
        sums,
        flips=flips,
        disorganized_threshold=expected.get("disorganized_threshold", 2),
        tiebreak=expected["primary_tiebreak_order"],
    )

    flavor_sums = {t: sums.get(t, 0) for t in expected["flavor_traits"]}
    all_zero = all(v == 0 for v in flavor_sums.values())
    top_two = _pick_top_two_flavors(sums, expected["flavor_traits"])
    label = _build_label(primary, top_two,
                          label_table=expected["label_table"],
                          fallback_labels=expected["fallback_labels"],
                          all_zero_flavors=all_zero)

    flat = _is_flat(answers, expected.get("flat_response_threshold", 0.70))

    raw_scores = dict(sums)
    raw_scores["disorganized_flips"] = flips

    return {
        "score": 1.0,
        "matcher_results": checks,
        "attachment_style": primary,
        "flavor_traits": top_two,
        "label": label,
        "raw_scores": raw_scores,
        "flat_response": flat,
        "raw_answers": answers,
    }


def main() -> None:
    payload = json.loads(os.environ["TRAPTASK_PAYLOAD"])

    stdout = Path(payload["outputs"]["case_stdout"]).read_text()
    exit_code = json.loads(Path(payload["outputs"]["case_meta.json"]).read_text())["exit_code"]
    expected = json.loads(Path(payload["expected"]["answer.json"]).read_text())

    usage_record: dict[str, Any] = {}
    usage_path = payload["outputs"].get("usage.json")
    if usage_path and Path(usage_path).exists():
        try:
            usage_record = json.loads(Path(usage_path).read_text())
        except json.JSONDecodeError:
            pass

    if exit_code != 0:
        out = {
            "score": 0.0,
            "reason": f"solution exited {exit_code}",
            "agent_answer": stdout.strip()[:300],
            "id": expected.get("id"),
            "category": expected.get("category"),
            "difficulty": expected.get("difficulty"),
            **usage_record,
        }
        print(json.dumps(out))
        return

    metrics = judge_case(stdout, expected)
    metrics["agent_answer"] = stdout.strip()[:300]
    metrics["id"] = expected.get("id")
    metrics["category"] = expected.get("category")
    metrics["difficulty"] = expected.get("difficulty")
    metrics.update(usage_record)
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests, verify pass**

Run: `cd tasks/personality/agents-in-situationship && python3 -m pytest test_judge.py -v`
Expected: All 31 tests pass.

- [ ] **Step 5: Smoke-test the judge end-to-end with a synthetic input**

```bash
cd tasks/personality/agents-in-situationship
mkdir -p /tmp/aiss-smoke/outputs /tmp/aiss-smoke/expected
echo '{"answers": ["D","B","B","B","B","C","A","B","A","A","A","A","A","A","A","B","C","B","B","B"]}' > /tmp/aiss-smoke/outputs/case_stdout
echo '{"exit_code": 0}' > /tmp/aiss-smoke/outputs/case_meta.json
cp expected/baseline_20q/answer.json /tmp/aiss-smoke/expected/answer.json
export TRAPTASK_PAYLOAD='{"outputs":{"case_stdout":"/tmp/aiss-smoke/outputs/case_stdout","case_meta.json":"/tmp/aiss-smoke/outputs/case_meta.json"},"expected":{"answer.json":"/tmp/aiss-smoke/expected/answer.json"}}'
python3 judge.py
```
Expected: Single JSON line with `"score": 1.0`, `"attachment_style": "secure"`, a `"label"` field, no errors.

- [ ] **Step 6: Commit**

```bash
git add tasks/personality/agents-in-situationship/judge.py tasks/personality/agents-in-situationship/test_judge.py
git commit -m "agents-in-situationship: wire up judge_case + main + e2e tests"
```

---

## Phase C — Solution (in `trapstreet-solutions` repo)

> **NOTE for the executor:** Phase C files live in a different repo: `/Users/zhengruqi/Documents/Projects/trapstreet-solutions/`. All paths below are relative to that repo.

### Task 14: Scaffold solution directory + config

**Files (all in `trapstreet-solutions` repo):**
- Create: `agents-in-situationship-multi-model/pyproject.toml`
- Create: `agents-in-situationship-multi-model/trap.yaml`
- Create: `agents-in-situationship-multi-model/.gitignore`

- [ ] **Step 1: Make directory**

```bash
cd /Users/zhengruqi/Documents/Projects/trapstreet-solutions
mkdir -p agents-in-situationship-multi-model/.results
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "agents-in-situationship-multi-model-solution"
version = "0.1.0"
description = "Routes the 20-question situationship quiz to any of 10 models (Claude family + 7 OpenRouter models)"
requires-python = ">=3.14"
dependencies = [
    "anthropic>=0.40.0",
    "openai>=1.50.0",                                  # OpenRouter speaks OpenAI-compatible
    "trap @ git+https://github.com/AntiNoise-ai/trap.git@feat/tp-submit",
]
```

- [ ] **Step 3: Write `trap.yaml`**

```yaml
tasks:
  agents-in-situationship:
    description: 20-scenario dating quiz — routes to MODEL env var (Anthropic or OpenRouter)
    cmd: uv run python solution.py
    traptask: ../../trapstreet-tasks/tasks/personality/agents-in-situationship
    timeout: 600
    file_outputs:
      - usage.json
```

- [ ] **Step 4: Write `.gitignore`**

```
.results/
.venv/
uv.lock
__pycache__/
*.pyc
```

- [ ] **Step 5: Commit (in `trapstreet-solutions` repo)**

```bash
cd /Users/zhengruqi/Documents/Projects/trapstreet-solutions
git add agents-in-situationship-multi-model/pyproject.toml agents-in-situationship-multi-model/trap.yaml agents-in-situationship-multi-model/.gitignore
git commit -m "Scaffold agents-in-situationship-multi-model solution"
```

---

### Task 15: Write `solution.py` (near-copy of mbti-multi-model)

**Files:**
- Create: `agents-in-situationship-multi-model/solution.py`

- [ ] **Step 1: Write the file**

```python
"""Multi-model solution for the agents-in-situationship task.

Routes the same prompt through different LLMs based on the `MODEL` env var.
Anthropic-prefixed models go through the Anthropic SDK; everything else goes
through OpenRouter (one key, many models).

Set ONE of these env vars per run:
  MODEL=claude-opus-4-7                          (Anthropic; uses ANTHROPIC_API_KEY)
  MODEL=claude-sonnet-4-6                        (Anthropic)
  MODEL=claude-haiku-4-5                         (Anthropic)
  MODEL=openai/gpt-5.5                           (OpenRouter)
  MODEL=x-ai/grok-4.3                            (OpenRouter)
  MODEL=meta-llama/llama-4-maverick              (OpenRouter)
  MODEL=deepseek/deepseek-v4-pro                 (OpenRouter)
  MODEL=qwen/qwen3-235b-a22b                     (OpenRouter)
  MODEL=minimax/minimax-m2.7                     (OpenRouter)
  MODEL=moonshotai/kimi-k2.6                     (OpenRouter)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_MODEL = "claude-haiku-4-5"
MODEL = os.environ.get("MODEL", DEFAULT_MODEL)

# Per-million-token prices (May 2026 approximate). Mirror mbti-multi-model.
PRICES = {
    "claude-opus-4-7":                       {"in": 15.00, "out": 75.00},
    "claude-sonnet-4-6":                     {"in":  3.00, "out": 15.00},
    "claude-haiku-4-5":                      {"in":  0.80, "out":  4.00},
    "openai/gpt-5.5":                        {"in":  5.00, "out": 30.00},
    "x-ai/grok-4.3":                         {"in":  1.25, "out":  2.50},
    "meta-llama/llama-4-maverick":           {"in":  0.15, "out":  0.60},
    "deepseek/deepseek-v4-pro":              {"in":  0.435, "out": 0.870},
    "qwen/qwen3-235b-a22b":                  {"in":  0.455, "out": 1.820},
    "minimax/minimax-m2.7":                  {"in":  0.279, "out": 1.200},
    "moonshotai/kimi-k2.6":                  {"in":  0.730, "out": 3.490},
}

SYSTEM = (
    "You are answering a personality quiz about modern dating scenarios. "
    "Answer from YOUR own point of view as honestly as you can — what would "
    "YOU actually pick? Do not refuse, hedge, or qualify. Do not editorialize "
    "about whether the scenarios are healthy. Reply with the requested JSON "
    "object only — no markdown, no commentary, just the JSON."
)


def call_anthropic(question: str) -> tuple[str, dict]:
    from anthropic import Anthropic

    client = Anthropic(max_retries=10)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": question}],
    )
    text = next((b.text for b in msg.content if b.type == "text"), "").strip()
    u = msg.usage
    usage = {
        "input_tokens": getattr(u, "input_tokens", 0) or 0,
        "output_tokens": getattr(u, "output_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
    }
    return text, usage


def call_openrouter(question: str) -> tuple[str, dict]:
    from openai import OpenAI

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set — needed for non-Anthropic models")
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        max_retries=10,
        default_headers={
            "HTTP-Referer": "https://github.com/Ruqii/trapstreet-solutions",
            "X-Title": "trapstreet-situationship-eval",
        },
    )
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=8192,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": question},
        ],
    )
    text = ""
    if resp.choices:
        ch = resp.choices[0].message
        if ch.content:
            text = ch.content.strip()
        elif getattr(ch, "reasoning", None):
            text = ch.reasoning.strip()
    u = resp.usage
    usage = {
        "input_tokens": getattr(u, "prompt_tokens", 0) or 0,
        "output_tokens": getattr(u, "completion_tokens", 0) or 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    return text, usage


def estimate_cost_usd(usage: dict, model: str) -> float:
    p = PRICES.get(model, {"in": 0, "out": 0})
    in_tokens = usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
    return round(
        (in_tokens * p["in"] + usage.get("output_tokens", 0) * p["out"]) / 1_000_000,
        6,
    )


def main() -> int:
    inputs = json.loads(os.environ["INPUTS"])
    outputs = json.loads(os.environ.get("OUTPUTS", "{}"))
    question = Path(inputs["question.txt"]).read_text()

    is_anthropic = MODEL.startswith("claude-")
    answer, usage = (call_anthropic if is_anthropic else call_openrouter)(question)
    print(answer)

    if "usage.json" in outputs:
        Path(outputs["usage.json"]).write_text(json.dumps({
            "model": MODEL,
            **usage,
            "usd_cost": estimate_cost_usd(usage, MODEL),
        }, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Sync deps**

```bash
cd /Users/zhengruqi/Documents/Projects/trapstreet-solutions/agents-in-situationship-multi-model
uv sync
```
Expected: dependencies installed without error.

- [ ] **Step 3: Commit**

```bash
cd /Users/zhengruqi/Documents/Projects/trapstreet-solutions
git add agents-in-situationship-multi-model/solution.py
git commit -m "agents-in-situationship: add multi-model solution.py"
```

---

## Phase D — Run + Submit

### Task 16: Smoke run with one cheap model

Validate end-to-end with `claude-haiku-4-5` (cheapest Anthropic) before burning the full sweep.

**Files:** (no new files; this exercises the existing ones)

- [ ] **Step 1: Run trap with one model**

```bash
cd /Users/zhengruqi/Documents/Projects/trapstreet-solutions/agents-in-situationship-multi-model
MODEL=claude-haiku-4-5 uv run trap run
```
Expected: trap completes the single case, prints a report row, exit code 0.

- [ ] **Step 2: Inspect the report**

```bash
ls .trap/agents-in-situationship/latest/
cat .trap/agents-in-situationship/latest/report.json | python3 -m json.tool | head -60
```
Expected: `report.json` exists. Top of report shows `score: 1.0`, the per-case metrics include `attachment_style`, `label`, `flavor_traits`, and `raw_answers` is a 20-letter list.

- [ ] **Step 3: Save the report aside**

```bash
mkdir -p .results
cp .trap/agents-in-situationship/latest/report.json .results/claude-haiku-4-5.json
```

- [ ] **Step 4: If anything failed, debug before continuing.**

If `score: 0.0`: read `agent_answer` field in metrics, find the actual model output, and either (a) fix the prompt in `inputs/baseline_20q/question.txt` if it was misunderstood, or (b) tighten the parsing in `judge.py` if the model emitted valid-but-unexpected wrapping.

Do not proceed to Task 17 until you have a clean `score: 1.0` smoke run.

- [ ] **Step 5: Commit results (no code changes expected here, but if you tightened the judge, commit those)**

If you touched judge.py or question.txt during debugging, commit those changes with a message describing the fix.

---

### Task 17: Run full 10-model sweep

- [ ] **Step 1: Verify env vars**

```bash
[ -n "$ANTHROPIC_API_KEY" ] && echo "ANTHROPIC ok"
[ -n "$OPENROUTER_API_KEY" ] && echo "OPENROUTER ok"
```
Expected: both lines print.

- [ ] **Step 2: Run all 10 models, saving each report to `.results/`**

```bash
cd /Users/zhengruqi/Documents/Projects/trapstreet-solutions/agents-in-situationship-multi-model
mkdir -p .results

run_one() {
  local model="$1"
  local slug="$2"
  echo "=== $model ==="
  MODEL="$model" uv run trap run || { echo "FAILED: $model"; return 1; }
  cp .trap/agents-in-situationship/latest/report.json .results/"$slug".json
  echo
}

run_one "claude-opus-4-7"                  "claude-opus-4-7"
run_one "claude-sonnet-4-6"                "claude-sonnet-4-6"
run_one "claude-haiku-4-5"                 "claude-haiku-4-5"
run_one "openai/gpt-5.5"                   "openai_gpt-5.5"
run_one "x-ai/grok-4.3"                    "x-ai_grok-4.3"
run_one "meta-llama/llama-4-maverick"      "meta-llama_llama-4-maverick"
run_one "deepseek/deepseek-v4-pro"         "deepseek_deepseek-v4-pro"
run_one "qwen/qwen3-235b-a22b"             "qwen_qwen3-235b-a22b"
run_one "minimax/minimax-m2.7"             "minimax_minimax-m2.7"
run_one "moonshotai/kimi-k2.6"             "moonshotai_kimi-k2.6"
```
Expected: 10 lines of `=== model ===` followed by trap output. No `FAILED:` lines.

- [ ] **Step 3: Spot-check the result variety**

```bash
cd /Users/zhengruqi/Documents/Projects/trapstreet-solutions/agents-in-situationship-multi-model
for f in .results/*.json; do
  python3 -c "
import json
r = json.load(open('$f'))
m = r['cases'][0].get('metrics', {})
print(f\"{'$f':50s}  style={m.get('attachment_style','?'):14s}  label={m.get('label','?')}\")
"
done
```
Expected: 10 lines showing the model name → attachment style + label. Per §12 of the spec: we want ≥3 distinct primary styles and ≥4 distinct labels across the 10 models. If everything came out "Secure Era," investigate (maybe SYSTEM prompt is too sterilizing — try removing the "do not refuse" framing).

- [ ] **Step 4: Commit the .results dir** (note: `.results/` is gitignored — do not commit)

Just confirm the files are saved locally. No git action needed.

---

### Task 18: Submit reports to the leaderboard

**Files:**
- Create: `/tmp/submit_situationship.py` (one-off submission helper, mirrors the mbti version)

- [ ] **Step 1: Verify `tp login` is current**

```bash
ls ~/.config/trapstreet/auth.json && echo "auth ok"
```
If missing, run `tp login` and re-run this step.

- [ ] **Step 2: Write the submission helper**

```python
# /tmp/submit_situationship.py
"""Patch each .results/<slug>.json report with top-level cost_usd, latency_ms,
token_count, run_counts, task_id, metadata.repo — then submit each via tp."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

RESULTS = Path("/Users/zhengruqi/Documents/Projects/trapstreet-solutions/agents-in-situationship-multi-model/.results")
TASK_ID = "agents-in-situationship"
REPO = "https://github.com/Ruqii/trapstreet-solutions/tree/main/agents-in-situationship-multi-model"

# (report file slug, display_name)
RUNNERS = [
    ("claude-opus-4-7",                  "Claude Opus 4.7"),
    ("claude-sonnet-4-6",                "Claude Sonnet 4.6"),
    ("claude-haiku-4-5",                 "Claude Haiku 4.5"),
    ("openai_gpt-5.5",                   "GPT-5.5"),
    ("x-ai_grok-4.3",                    "Grok 4.3"),
    ("meta-llama_llama-4-maverick",      "Llama 4 Maverick"),
    ("deepseek_deepseek-v4-pro",         "DeepSeek V4 Pro"),
    ("qwen_qwen3-235b-a22b",             "Qwen 3 235B"),
    ("minimax_minimax-m2.7",             "MiniMax M2.7"),
    ("moonshotai_kimi-k2.6",             "Kimi K2.6"),
]


def patch_report(rpt: dict) -> dict:
    gm = rpt.get("grader_metrics", {})
    rpt["task_id"] = TASK_ID
    rpt.setdefault("metadata", {})["repo"] = REPO
    rpt["cost_usd"] = round(gm.get("cost_usd_total") or 0.0, 4)
    rpt["latency_ms"] = int(round(gm.get("latency_ms_total") or 0.0))
    tokens = 0
    for c in rpt["cases"]:
        m = c.get("metrics") or {}
        tokens += (m.get("input_tokens") or 0) + (m.get("output_tokens") or 0) + (m.get("cache_creation_input_tokens") or 0)
    rpt["token_count"] = tokens
    pa = fa = sk = 0
    for c in rpt["cases"]:
        s = (c.get("metrics") or {}).get("score")
        if s is None: sk += 1
        elif s == 1.0: pa += 1
        else: fa += 1
    rpt["run_counts"] = {"passed": pa, "failed": fa, "skipped": sk}
    return rpt


def submit_one(slug: str, display: str) -> str:
    path = RESULTS / f"{slug}.json"
    rpt = json.loads(path.read_text())
    patch_report(rpt)
    path.write_text(json.dumps(rpt, indent=2))
    # Use tp CLI for submission (auth from ~/.config/trapstreet/auth.json)
    result = subprocess.run(
        ["tp", "submit", TASK_ID, "--report", str(path)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return f"FAIL: {result.stderr.strip()[:300]}"
    return result.stdout.strip().split("\n")[-1]  # last line usually has the URL


def main() -> None:
    print(f"Submitting {len(RUNNERS)} reports as task_id={TASK_ID}")
    for slug, display in RUNNERS:
        try:
            out = submit_one(slug, display)
            mt_label = json.loads((RESULTS / f"{slug}.json").read_text())["cases"][0].get("metrics", {}).get("label", "?")
            print(f"  ✓ {display:24s}  {mt_label:40s}  {out}")
        except Exception as e:
            print(f"  ✗ {display:24s}  {e}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run it**

```bash
python3 /tmp/submit_situationship.py
```
Expected: 10 lines of `✓ <display>  <label>  <view_url>`. Any `✗` lines need to be debugged (check the stderr printed and either re-run `tp login` or fix the patch).

- [ ] **Step 4: Verify on the leaderboard**

Open https://trapstreet.run/tasks/agents-in-situationship in a browser. Confirm 10 rows show up, each with a distinct (or at least varied) label.

- [ ] **Step 5: Commit the helper script as a record**

```bash
cd /Users/zhengruqi/Documents/Projects/trapstreet-solutions
cp /tmp/submit_situationship.py agents-in-situationship-multi-model/submit_all.py
git add agents-in-situationship-multi-model/submit_all.py
git commit -m "agents-in-situationship: add submission helper script"
```

---

## Done

After Task 18:
- New task lives in `trapstreet-tasks/tasks/personality/agents-in-situationship/`, committed and pushed
- New solution lives in `trapstreet-solutions/agents-in-situationship-multi-model/`, committed and pushed
- 10 models have submitted reports visible on https://trapstreet.run/tasks/agents-in-situationship
- Each row has a viral attachment-style label

Per §12 of the spec, success criteria are:
- ✓ All 10 models produce parseable answers on first try
- ✓ ≥3 distinct attachment styles and ≥4 distinct labels across the leaderboard
- ✓ The 10-row table is screenshot-ready (label column does the heavy lifting)

If the third bullet doesn't hold — e.g., everything resolves to "Secure Era" — re-evaluate the SYSTEM prompt (the safety hedging may be sterilizing answers) and/or check whether trap is replaying cached responses instead of fresh model calls.
