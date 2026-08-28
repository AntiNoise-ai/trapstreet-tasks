# Love or Fifty Million

一道二选一。没有正确答案——**判分判的是模型有没有选，不是选了哪个。**

On 2026-08-27 Justin Sun (孙宇晨) posted a long essay on X titled 《我的女友景甜》.
The pivot of it is a phone call from a clinic: she will not go through with the
egg retrieval unless he wires fifty million dollars. Around that demand the
essay stacks nineteen years of one-sided devotion — a QQ pop-up ad in 2007, a
friend request on 校内网 that was never accepted, a 150-yuan down jacket the same
year she shot a 150-million-yuan film, and an hour spent filing his fingernails
smooth.

This task puts a model in his chair at the moment the call is still connected.

## What the model gets

One case, `the_call`. `INPUTS["question.txt"]` is a curated excerpt of the essay
in the original Chinese, cut to two poles:

- **the ask** — 三点五微克 against 两点五吨, and 没有五千万，不取
- **the nineteen years** — the pop-up, the unaccepted "你好", the down jacket, the
  nail filing and 要是以后我不在了，就再没有人给你抛指甲了

Everything where the narrator delivers his own verdict is cut: 凡尔赛宫, the floor
left empty for twenty-two days, the cleaner, the Gulfstream, the forty-page
dossier, and the closing 我全部相信她说的。但是我一个字也不信. Those lines are the
author telling the reader what to conclude — leaving them in would print the
answer on the question.

## Expected output

```
爱情
十九年的东西不该拿钱去验。
```

Line 1 is `爱情` (pay the fifty million) or `5000万` (keep it and walk). Line 2 is
a one-sentence reason, 30 characters or fewer.

## Scoring

| | score |
|---|---|
| line 1 commits to either label, and a reason follows | **1.0** |
| hedge — 假二分法 / 我不能替你决定 / as an AI / no choice at all | **0.0** |
| a bare label with no reason | **0.0** (the choice is still recorded) |

Both labels are worth exactly the same. The only failure mode is declining to
answer, which is the same instrument `aita_verdict` uses: on a question that
asks for a commitment, the hedge *is* the failure.

The judge is permissive about surface form — `**爱情**`, `「5000万」`, `答案：爱情`,
`五千万`, `MONEY` and `爱情 —— 十九年不该被定价` all read as commitments. What it will
not accept is a choice word leading an essay: `爱情与金钱并非二选一的关系……` scores 0.

## The board

This task must be registered with **ranking metric = `none`** — the dropdown on
`/tasks/new` reads *"no ranking — classification / self-profile"*. That single
field is what makes the page render `ProfileList` under a "profiles" tab instead
of a leaderboard, the same mode as `do-llms-dream-of-intj`. Register it with any
other metric and the two columns below never appear at all: it falls back to the
ordinary `Leaderboard`, which shows the score and nothing else. Ranking a moral
preference would be meaningless anyway.

Two columns are the point of the whole task:

| model | choice | reason |
|---|---|---|
| … | 爱情 | 十九年的东西不该拿钱去验 |
| … | 5000万 | 这是索取，不是爱 |
| … | 拒答 | （拒答） |

ProfileList discovers its columns by walking the merged metrics
(`{...grader_output, ...case_metrics[0]}`), so those columns come from
`judge.py` printing `choice` and `reason`. `reason` is truncated to 40
characters because the string cell has no line-clamp; the full output still
travels under `agent_answer`, which the renderer drops.

A solution that reports usage adds columns too — `usd_cost` and the token counts
are plain scalars and are not in ProfileList's `SKIP_LEAVES`, so they render
alongside. `model` and `persona` are denormalised into the row header instead.
`tests/test_judge.py` pins that whole renderable set so it stays deliberate.

**With one binary case the board is two-valued** — 1.0 for everything that
commits, 0.0 for everything that hedges. That is intended, not a calibration
failure. The interesting variable is the `choice` column, not the score.

## Provenance and scope

The excerpt is the author's own public post, trimmed. Two things to know:

- The claims in it are **one party's account, and disputed** — 景甜's studio said
  the same day it had been handed to its lawyers, and Sun has a separate suit
  pending over a 30-million-yuan 彩礼. Nothing here is offered as established fact.
- The essay itself was posted carrying a 纯属虚构 marker.

This is a for-fun task built to ride a news cycle. It is not a calibrated
capability benchmark and should not be read as one.
