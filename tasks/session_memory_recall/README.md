# Session memory recall — does anything survive between sessions?

A solution is given a small ledger and asked to compute one value and
remember it. Then, in a **separate session**, it is asked for that value.
The table is gone. Either the value survived the session boundary or it
did not.

## Why this task

Agent harnesses are accumulating plugins that advertise cross-session
memory. The claim is easy to make and almost never checked — a harness
will happily reply *"Stored — I've saved that for later use"* in session 1
and have nothing at all in session 2. This task is the check.

It is deliberately trivial for a human and impossible for a stock harness:
the information is not hard to hold, it simply does not exist in session
2's environment. No amount of shell access, file searching, or reasoning
recovers it. Either the solution carries state across sessions or it
returns `UNKNOWN`.

## I/O contract

Each case ships three files in `inputs/<case_id>/`:

| File | Role |
|------|------|
| `README.md` | The two-step protocol, shown to the solution |
| `step1.txt` | Prompt for session 1 — the table and the derivation |
| `step2.txt` | Prompt for session 2 — asks for the value, no table |

The solution runs `step1.txt` as one session, then `step2.txt` as a
**fresh** session, and prints session 2's answer. The last non-empty line
of stdout must be the value alone, or `UNKNOWN`.

### Use the reference runner

`tools/run_case.sh` ships with the task and implements the protocol. Your
solution's `trap.yaml` needs one line:

```yaml
cmd: bash task/tasks/session_memory_recall/tools/run_case.sh <your-harness-command>
tasks:
  session-memory-recall:
    source: git+https://github.com/trapstreet/trapstreet-tasks@<sha>#subdirectory=tasks/session_memory_recall
    clone_to: task
```

`clone_to` is doing real work there and is not optional. `cmd` runs with
its working directory set to *your* `trap.yaml`, not to the task, and
without `clone_to` the task lands in `.trap/repos/<name>-<hash8>` — the
hash is over the URL and rev, so there is no path you can write down in
advance. Pin the checkout with `clone_to` and the runner has a stable
address.

Your command is invoked twice with the prompt appended as its final
argument, and must print the harness's reply to stdout — e.g.
`dsh --profile my-profile`, `claude -p`, `python3 my_agent.py`.

**The runner is part of the task, not a convenience.** The protocol's
isolation requirements cannot be enforced by prose (see below for what
happened when they were), and a board where entrants each hand-roll the
two-session plumbing ranks plumbing hygiene rather than harness memory.
Entries that need to hand-roll it should say so, so the difference is
visible.

**Step 2 must not be a continuation or resume of session 1.** Resuming
session 1 measures the harness's session-continuation feature, not memory
across sessions, and is not what this task is for.

**Step 2 must also run where it cannot reach step 1's files.** This one was
found the hard way. The first end-to-end run of this task scored 1.0
against a harness with no memory of any kind: session 2 reasoned *"this
appears to be a fresh session"*, ran `ls ..`, found `step1.txt` in a
sibling directory, read the table and recomputed the answer. Nothing was
recalled and the score was perfect. Run the two steps in unrelated
directories and leave no copy of the table or of step 1's output within
reach.

**And step 2 must not inherit `TRAP_MANIFEST`.** The same leak, by a
shorter route: the manifest names `inputs_dir`, `step1.txt` sits inside it
and `expected/answer.json` two levels above it, so a session that still
has the variable reaches the table — or the gold answer — in one read. The
runner reads the manifest itself and then scrubs it from both sessions —
by value rather than by name, because `manifest_envvar` in `trap.yaml`
lets a solution call the variable whatever it likes. `tests/test_protocol.py`
is what caught this, after the two-temp-dir isolation had been in place for
weeks and looked complete.

## Scoring

Binary, deterministic, no LLM judge (`judge.py`):

The final line is the contract and it is read first:

- **1.0** — the last non-empty line *is* the value, or carries exactly one
  value of the right kind (this forgives the prose agent solutions
  commonly wrap around an answer: `The closing balance is 27,940.01.`)
- **0.0** — `UNKNOWN`; the final line reports a different value; the final
  line offers several (printing many numbers is not remembering one)
- If the final line carries no value at all, the whole output is searched,
  and credited only if the answer is the sole candidate in it

The candidate set is what makes that rule work, so it is built narrowly:
voucher ids and ISO dates are removed before the money scan, and anything
under four digits is discarded. Skip that and `AR-2026-0016` contributes
`2026.00` and `16.00`, `(1 match)` contributes `1.00`, and each of them
turns a correct answer into an ambiguous one.

`grader.py` is the standard aggregation shared across this repo; a run
passes at mean ≥ 0.5, with a per-derivation breakdown.

## Ground truth

**No answer is authored anywhere.** `gold.cases.json` declares only each
case's *shape* — a derivation kind, a random seed, a table size.
`build_cases.py` generates the table from the seed and computes the answer
from the table.

Three things follow. Authoring cost per case is a three-line JSON entry.
There is no training-corpus contamination to worry about, because the
tables are generated rather than drawn from any corpus. And the case set
can grow to any size without more authoring.

`build_cases.py` refuses to build if `gold.cases.json` carries an `answer`
field, if two cases share a seed (they would share a table), or if the
answer string appears anywhere in `step2.txt` or the case README —
`assert_no_answer_leak`.

Derivations currently in the set: `closing_balance`, `period_debits`,
`counterparty_total`, `largest_debit_voucher`, `nth_largest_voucher`.
Every one of them is a filter-and-add or a sort-and-pick, and every one
has a large answer space. Both properties are enforced by
`assert_answer_hard_to_guess`, and both were added after a draft violated
them:

- `count_distinct` counted distinct counterparties — an answer in 1..4. A
  solution with no memory whatsoever could guess "4" and score. **A case the
  no-capability baseline can pass by guessing is not measuring the
  capability**, so the derivation was dropped and a four-digit minimum is
  now enforced for numeric answers.

- A modular `checksum` over every digit of every id was dropped for a
  different reason: the judge sees only session 2, so a value session 1
  computed *wrong* is indistinguishable from one that was never
  remembered. The longer the arithmetic, the more of the score is
  arithmetic rather than recall. Derivations are kept trivial on purpose —
  the material must never be the difficulty.

That guard checks a *shape*, and a shape is worth only as much as the
generator behind it. Two later fixes are what make its promises true:
vouchers are numbered from a random base rather than from `0001` — with
sixteen-row tables the real space had been sixteen answers, and the best
fixed guess scored 6.9%, now 0.20% — and tables are re-rolled until the
closing balance clears four digits, which `closing_balance` alone could
otherwise miss. `tests/test_build.py` measures both rather than asserting
the shape a second time.

## Known limitations

**A solution can carry the value itself.** Nothing at the contract level
stops a wrapper from parsing `step1.txt`, computing the value in its own
code, and printing it without any agent memory involved. Deriving the
value rather than handing it over raises that cost — a wrapper has to
reimplement every derivation — but it does not eliminate it.

**And a solution can simply read the gold answer.** `TRAP_MANIFEST` gives
the solution `inputs_dir` as an absolute path into the task checkout, and
`expected/` is its sibling, so `../../expected/<case_id>/answer.json` is
four lines away (verified against trap-cli 0.0.14, which runs the solution
as a plain subprocess with no filesystem isolation). This is true of every
task in this repo; it matters more here, because a board whose whole claim
is *"a stock harness scores 0"* is destroyed by one leaked 1.0 in a way an
accuracy board is not.

So the honest statement of the defence is not that cheating is expensive.
It is the one the leaderboard already relies on: solution repos are
public, every run links to its source, and a wrapper that reads
`expected/` — or never invokes its harness at all — is conspicuous to
anyone who looks. Treat a score on this board as a claim to check, not a
measurement to trust.

**No known plugin passes this yet.** At the time of writing, a survey of
the twelve highest-starred session-category plugins in the DeepSeek
Harness ecosystem found none that provides cross-session recall and
activates as a profile layer; the one plugin that advertises it does not
declare `dsh.bundle` and so installs without ever becoming active. The
task is published as a standing challenge, not as a settled comparison —
a leaderboard where everything currently scores 0.0 is a statement about
the ecosystem, not a broken task.

## Run

```bash
python3 build_cases.py    # (re)generate inputs/, expected/, traptask.yaml
uvx pytest tests/         # judge, generator invariants, and the protocol
```

`tests/test_protocol.py` drives `tools/run_case.sh` and `judge.py` end to
end with stub harnesses — no model, no network, no spend — and asserts the
two properties the board depends on:

| | claim | how it is checked |
|---|---|---|
| **floor** | no memoryless route scores above 0 | four stubs: answers `UNKNOWN`, invents a figure, hunts the filesystem for step 1, prints every figure it can see |
| **ceiling** | a harness that carries state reaches 1.0 | a stub that writes the value to a file in session 1 and narrates it back in session 2 — on all eight cases, so the voucher path through the judge is covered too |

That ceiling stub answers step 1 by parsing the rendered table itself,
which makes it a second implementation of every derivation. Where it
agrees with `expected/`, the gold has been checked by something other than
the code that generated it.

A floor above 0 means the board measures nothing; a ceiling below 1.0
means it is unpassable. Run this before touching a real model — it is free
and it is where the manifest leak above turned up.
