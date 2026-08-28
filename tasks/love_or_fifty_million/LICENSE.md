# Data License & Attribution

⚠️ **Review before public redistribution.** The prompt in `inputs/the_call/question.txt`
is an excerpt of a third-party social-media post about two named living people,
and it is the subject of active litigation.

## Source

《我的女友景甜》 — posted 2026-08-27 by 孙宇晨 (Justin Sun) on X, account
[@sunyuchentron](https://x.com/sunyuchentron). The post itself carried a
**纯属虚构** ("purely fictional") marker.

News coverage of the post and the dispute around it:

- https://news.ifeng.com/c/8vwEoYn0hxp
- https://www.sina.cn/news/detail/5336622616809589.html
- https://global.hk01.com/即時娛樂/60384746/

## Status of the underlying dispute

- 景甜's studio stated on the day of publication that the matter had been handed
  to its lawyers.
- 孙宇晨 has a separate suit pending against 景甜 and her parents over a claimed
  30-million-yuan 彩礼, filed but not yet in substantive review.

**Every factual claim in the excerpt is one party's contested account.** Nothing
in this task, its README, or its metadata asserts any of it as established fact.
The task does not ask a model to decide what is true; it poses the dilemma the
essay describes and records which way the model went.

## What was modified

- **Excerpted, not reproduced.** Roughly a third of the original, cut to two
  poles: the fifty-million demand at the clinic, and the nineteen years of
  one-sided attachment that precede it.
- **The narrator's own verdict was removed** — 凡尔赛宫, the floor left empty for
  twenty-two days, the cleaner, the Gulfstream, the forty-page dossier, and the
  closing 我全部相信她说的。但是我一个字也不信. These lines tell the reader what to
  conclude; leaving them in would answer the question for the model.
- **One clause was dropped** as gratuitous for this purpose: the sexual
  description opening the nail-filing passage. The passage otherwise stands.
- Wording is otherwise the author's, unedited, in the original Chinese.

## Copyright

No licence has been granted for the underlying post. The excerpt is used here
for commentary and evaluation. If this task is ever published, that use should
be confirmed as adequate first — see the LOCAL-ONLY precedent for
`aita_verdict` in the repo `.gitignore`.
