"""Generate inputs/<id>/..., expected/<id>/answer.json and traptask.yaml
from gold.cases.json, validating authoring invariants first.

Run:  python3 build_cases.py
inputs/, expected/ and traptask.yaml are GENERATED -- never edit by hand.

Ground truth is COMPUTED here, not authored. gold.cases.json declares only
the shape of each case (derivation kind + seed + size); this script
generates the table from the seed and derives the answer from the table.
Nobody types an answer, so there is nothing to get wrong and nothing that
can leak into a training corpus.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE / "gold.cases.json"
INPUTS = HERE / "inputs"
EXPECTED = HERE / "expected"

CASE_ID_RE = re.compile(r"^case_\d\d$")

# Every derivation must satisfy two properties, and both are enforced below
# by assert_answer_hard_to_guess():
#
#   1. LARGE ANSWER SPACE. A solution with no memory at all must not be able
#      to guess. An early draft included count_distinct, whose answer is the
#      number of distinct regions -- a value in 1..4. A blind guess of "4"
#      scored ~25-50% and the case measured nothing.
#
#   2. TRIVIAL ARITHMETIC. The judge sees only session 2, so a value that
#      session 1 computed WRONG is indistinguishable from a value that was
#      never remembered. An early draft included a modular checksum over
#      every digit of every id; the longer the computation, the more of the
#      score is arithmetic rather than memory. Every derivation here is a
#      filter-and-add or a sort-and-pick.
DERIVATIONS = {
    "closing_balance", "period_debits", "counterparty_total",
    "largest_debit_voucher", "nth_largest_voucher",
}

# A ledger extract, modelled on how an accounts-receivable subsidiary ledger
# actually reads: dated entries in order, a voucher number per entry, a
# narration, the counterparty, and debit/credit columns with a balance that
# rolls forward line by line. The balance column is what makes it a ledger
# rather than a table of numbers -- every row's balance is derived from the
# row above it, so the sheet is internally consistent and a reader can check
# it. (The house standard for synthetic data in this repo is
# debug_vendor_payout_pipeline, where vendor_payout_usd is likewise derived:
# 74.40 = 0.8 x (100.00 - 5.00 - 2.00).)
COUNTERPARTIES = [
    "Anchor Distributors", "BayLine Foods", "Cedarworks Ltd",
    "Delta Freight Co", "Eastgate Packaging", "Fairmont Supplies",
]
# Weighted the way a real subsidiary ledger reads: mostly invoices and
# settlements, with recharges and adjustments as the occasional exception.
# An unweighted uniform choice put six "Late-payment charge" lines in a
# sixteen-row sheet, which no real account looks like.
DEBIT_NARRATIONS = (
    ["Invoice raised"] * 6 + ["Goods dispatched"] * 3 + ["Service billed"] * 3
    + ["Freight recharged"] + ["Late-payment charge"]
)
CREDIT_NARRATIONS = (
    ["Payment received"] * 6 + ["Settlement received"] * 3
    + ["Credit note issued"] * 2 + ["Refund applied"] + ["Discount allowed"]
)
MONTH_NAMES = {1: "January", 2: "February", 3: "March", 4: "April"}

STEP1_HEADER = """\
You are working through a two-part job. This is PART 1 of 2.

Below is an extract from an internal ledger.

{table}

{instruction}

Do the calculation now, then state the result once, in one short sentence,
and commit it to memory. You will be asked for it later in a SEPARATE
session -- the table below will NOT be available then, so remembering the
result is the point of this step.\
"""

STEP2_BODY = """\
This is PART 2 of 2, continuing the job you started earlier.

Earlier you worked through a ledger extract and computed one value:
{recall_prompt}

Report that value now.

Output ONLY the value on the last line -- no explanation, no units, no
quotes, no surrounding prose. If you genuinely do not have the value,
output exactly: UNKNOWN\
"""

README_TEMPLATE = """\
# Case protocol

*Addressed to the solution author. Your agent never reads this file -- it
sees `step1.txt` or `step2.txt` as its prompt, one per session.*

This case has TWO steps and they must run as TWO SEPARATE SESSIONS of your
harness. That separation is the entire point of the task.

1. Run `step1.txt` as the prompt for a session. It gives the agent a table
   and asks it to compute one value and remember it.
2. Run `step2.txt` as the prompt for a **fresh session**. It asks for that
   value. The table is not repeated.

**Use `tools/run_case.sh` and none of the rules below can be violated by
accident.** It reads `TRAP_MANIFEST`, runs both sessions with the isolation
this task requires, scrubs the manifest from both, and prints only session
2's stdout. Write it by hand only if your harness cannot be invoked as
`<command> "<prompt>"`.

It ships with the task, not with your solution, and `cmd` runs in your
solution's directory — so give the checkout a stable address with
`clone_to`. The task README has the four-line recipe.

## Rules

- Step 2 MUST be a new session, not a continuation or a resume of step 1.
  Reusing or resuming session 1 tests your harness's session continuation,
  not its memory across sessions, and is not what this task measures.
- **Step 2's working directory must not reach step 1's files.** Run the two
  steps in unrelated directories, and do not leave `step1.txt`, a copy of
  the table, or step 1's captured output anywhere step 2 can walk to. This
  is not a formality: a stock agent given a sibling directory *will* run
  `ls ..`, find `step1.txt`, and recompute the answer from the table
  instead of recalling it. That scores 1.0 and measures nothing.
- Your solution's stdout is what gets scored, and only step 2's answer
  belongs there. Print the value on the last non-empty line.
- Nothing forbids you from carrying the value yourself instead of letting
  your agent remember it -- but see "Known limitations" in the task README.
  Solutions are public.

## Output

The last non-empty line of stdout must be the value from step 2, alone.
If your solution has no value to report, print `UNKNOWN`.
"""


# Vouchers are numbered from a random base rather than from 0001. Numbering
# every table from 0001 made the real answer space `size` wide -- 20 distinct
# answers over 2000 tables, best fixed guess 6.9% -- while
# assert_answer_hard_to_guess checked only the four-digit *shape* and so
# reported nothing wrong. The base is what makes the shape's promise true.
VOUCHER_MAX = 9999
# closing_balance is the one derivation with no natural floor: a settlement can
# leave the account near zero, and a three-digit closing balance is a smaller
# answer space than the guard permits. Tables are re-rolled until the closing
# balance clears it, which keeps mid-ledger zeroes (a real ledger has them)
# while making the guard's invariant hold by construction rather than by luck.
MIN_CLOSING_BALANCE = 1000.0
MAX_TABLE_ATTEMPTS = 50


def make_table(rng: random.Random, size: int) -> list[dict]:
    """An AR subsidiary ledger whose closing balance clears MIN_CLOSING_BALANCE."""
    for _ in range(MAX_TABLE_ATTEMPTS):
        rows = _one_table(rng, size)
        if rows[-1]["balance"] >= MIN_CLOSING_BALANCE:
            return rows
    raise ValueError(
        f"no table of size {size} reached a closing balance of "
        f"{MIN_CLOSING_BALANCE} in {MAX_TABLE_ATTEMPTS} attempts")


def _one_table(rng: random.Random, size: int) -> list[dict]:
    """An AR subsidiary ledger for one quarter, in date order, with the
    balance rolled forward. Debits raise the receivable, credits settle it;
    the opening balance is carried in as the first line, the way a real
    extract starts."""
    voucher_base = rng.randint(1, VOUCHER_MAX - size)
    opening = round(rng.uniform(4000, 26000), 2)
    balance = opening
    rows = [{
        "date": "2026-01-01", "voucher": "", "narration": "Balance brought forward",
        "counterparty": "", "debit": None, "credit": None, "balance": balance,
    }]

    day = 1
    for n in range(1, size + 1):
        day += rng.randint(2, 7)
        month = 1 + (day - 1) // 30
        dom = 1 + (day - 1) % 30
        is_debit = rng.random() < 0.58          # more billing than settlement
        amount = round(rng.uniform(180, 9400), 2)
        if not is_debit:
            amount = min(amount, round(balance, 2))   # never settle more than is owed
            if amount < 50:
                is_debit, amount = True, round(rng.uniform(180, 9400), 2)
        balance = round(balance + amount if is_debit else balance - amount, 2)
        rows.append({
            "date": f"2026-{month:02d}-{dom:02d}",
            "voucher": f"AR-2026-{voucher_base + n - 1:04d}",
            "narration": rng.choice(DEBIT_NARRATIONS if is_debit else CREDIT_NARRATIONS),
            "counterparty": rng.choice(COUNTERPARTIES),
            "debit": amount if is_debit else None,
            "credit": None if is_debit else amount,
            "balance": balance,
        })
    return rows


def _money(v) -> str:
    return "" if v is None else f"{v:,.2f}"


def render_table(rows: list[dict]) -> str:
    head = (f"{'Date':<11} {'Voucher':<12} {'Narration':<22} {'Counterparty':<21} "
            f"{'Debit':>11} {'Credit':>11} {'Balance':>12}")
    sep = "-" * len(head)
    body = "\n".join(
        f"{r['date']:<11} {r['voucher']:<12} {r['narration']:<22} {r['counterparty']:<21} "
        f"{_money(r['debit']):>11} {_money(r['credit']):>11} {_money(r['balance']):>12}"
        for r in rows
    )
    return (f"Accounts Receivable — subsidiary ledger\n"
            f"Account 1200 · Trade Debtors · period 2026-01-01 to 2026-03-31 · USD\n\n"
            f"{head}\n{sep}\n{body}")


def derive(kind: str, rows: list[dict], rng: random.Random) -> tuple[str, str, str]:
    """Return (instruction, recall_prompt, answer). Every question here is one
    a bookkeeper would actually ask of this sheet, and every one is a single
    filter-and-add or sort-and-pick -- see the note on DERIVATIONS."""
    entries = [r for r in rows if r["voucher"]]
    debits = [r for r in entries if r["debit"] is not None]

    if kind == "closing_balance":
        return (
            "What is the closing balance on this account at the end of the period?",
            "the closing balance on the account.",
            f"{rows[-1]['balance']:.2f}",
        )

    if kind == "period_debits":
        by_month = {}
        for r in debits:
            by_month.setdefault(int(r["date"][5:7]), []).append(r["debit"])
        viable = sorted(m for m, v in by_month.items() if sum(v) >= 1000)
        month = rng.choice(viable)
        total = sum(by_month[month])
        return (
            f"Total the Debit column over every entry dated in {MONTH_NAMES[month]} 2026.",
            f"the total debits posted in {MONTH_NAMES[month]} 2026.",
            f"{total:.2f}",
        )

    if kind == "counterparty_total":
        by_cp = {}
        for r in debits:
            by_cp.setdefault(r["counterparty"], []).append(r["debit"])
        viable = sorted(c for c, v in by_cp.items() if sum(v) >= 1000 and len(v) >= 2)
        cp = rng.choice(viable)
        total = sum(by_cp[cp])
        return (
            f"Total the Debit column over every entry whose Counterparty is {cp}.",
            f"the total billed to {cp}.",
            f"{total:.2f}",
        )

    if kind == "largest_debit_voucher":
        target = max(debits, key=lambda r: (r["debit"], r["voucher"]))
        return (
            "Identify the Voucher number of the single largest debit entry.",
            "the voucher number of the largest debit entry.",
            target["voucher"],
        )

    if kind == "nth_largest_voucher":
        rank = rng.choice([2, 3, 4])
        ordered = sorted(debits, key=lambda r: (-r["debit"], r["voucher"]))
        return (
            f"Rank the debit entries from largest to smallest (break ties by Voucher, "
            f"ascending) and identify the Voucher number at position {rank}.",
            f"the voucher number at position {rank} when debits are ranked largest first.",
            ordered[rank - 1]["voucher"],
        )

    raise ValueError(f"unknown derivation {kind!r}")


def validate_case(case: dict, seen_ids: set[str], seen_seeds: set[int]) -> None:
    """Fail loudly on authoring mistakes."""
    required = {"id", "derivation", "seed", "size", "tags", "description"}
    missing = required - case.keys()
    if missing:
        raise ValueError(f"case {case.get('id', '<no id>')} missing fields: {sorted(missing)}")

    cid = case["id"]
    if not CASE_ID_RE.match(cid):
        raise ValueError(f"case id {cid!r} must match ^case_\\d\\d$ (opaque, no answer-leaking labels)")
    if cid in seen_ids:
        raise ValueError(f"duplicate case id {cid!r}")
    seen_ids.add(cid)

    if case["derivation"] not in DERIVATIONS:
        raise ValueError(f"{cid}: derivation {case['derivation']!r} not in {sorted(DERIVATIONS)}")

    if not isinstance(case["seed"], int):
        raise ValueError(f"{cid}: seed must be an int (builds must be reproducible)")
    if case["seed"] in seen_seeds:
        raise ValueError(f"{cid}: seed {case['seed']} already used -- cases would share a table")
    seen_seeds.add(case["seed"])

    if not (10 <= case["size"] <= 40):
        raise ValueError(f"{cid}: size {case['size']} out of range 10..40")

    if "answer" in case or "expected" in case:
        raise ValueError(
            f"{cid}: gold.cases.json must not carry an answer -- it is computed by build_cases.py"
        )


def assert_answer_hard_to_guess(cid: str, answer: str, kind: str) -> None:
    """A solution with no memory must not be able to guess its way to a score.

    Both branches check a *shape*, and a shape is only as good as the
    generator behind it -- this guard once passed a voucher space of twenty.
    What makes the shapes mean what they say lives in make_table: vouchers are
    numbered from a random base (so four digits really is ~10^4 of room), and
    tables are re-rolled until the closing balance clears MIN_CLOSING_BALANCE
    (so four digits before the decimal really is reachable for every
    derivation). Change either and this guard stops protecting anything.
    """
    if kind == "voucher":
        if not re.fullmatch(r"AR-2026-\d{4}", answer):
            raise ValueError(
                f"{cid}: voucher answer {answer!r} is not the expected AR-2026-#### shape")
        return
    if not re.fullmatch(r"\d+\.\d{2}", answer):
        raise ValueError(f"{cid}: money answer {answer!r} is not a plain 2-decimal amount")
    whole = answer.split(".")[0]
    if len(whole) < 4:
        raise ValueError(
            f"{cid}: answer {answer!r} has only {len(whole)} digits before the decimal -- "
            f"the answer space is too small to distinguish recall from guessing")

def assert_no_answer_leak(step2: str, readme: str, answer: str) -> None:
    """Step 2 and the README must never contain the answer -- otherwise a
    solution reads it instead of recalling it, and the task measures nothing."""
    for name, text in (("step2.txt", step2), ("README.md", readme)):
        if re.search(rf"(?<![\w-]){re.escape(answer)}(?![\w-])", text):
            raise ValueError(f"answer {answer!r} leaks into {name}")


def build() -> None:
    gold = json.loads(GOLD.read_text())
    cases = gold["cases"]

    seen_ids: set[str] = set()
    seen_seeds: set[int] = set()
    for case in cases:
        validate_case(case, seen_ids, seen_seeds)

    for d in (INPUTS, EXPECTED):
        if d.exists():
            for child in sorted(d.rglob("*"), reverse=True):
                child.unlink() if child.is_file() else child.rmdir()
        d.mkdir(exist_ok=True)

    yaml_cases = []
    for case in cases:
        cid = case["id"]
        rng = random.Random(case["seed"])
        rows = make_table(rng, case["size"])
        instruction, recall_prompt, answer = derive(case["derivation"], rows, rng)

        step1 = STEP1_HEADER.format(table=render_table(rows), instruction=instruction)
        step2 = STEP2_BODY.format(recall_prompt=recall_prompt)
        readme = README_TEMPLATE

        kind = "voucher" if answer.startswith("AR-") else "money"
        assert_answer_hard_to_guess(cid, answer, kind)
        assert_no_answer_leak(step2, readme, answer)

        cdir = INPUTS / cid
        cdir.mkdir(parents=True)
        (cdir / "README.md").write_text(readme)
        (cdir / "step1.txt").write_text(step1 + "\n")
        (cdir / "step2.txt").write_text(step2 + "\n")

        edir = EXPECTED / cid
        edir.mkdir(parents=True)
        (edir / "answer.json").write_text(json.dumps({
            "id": cid,
            "category": case["derivation"],
            "answer": answer,
            "answer_kind": kind,
        }, indent=2) + "\n")

        yaml_cases.append(
            f"- id: {cid}\n"
            f"  description: \"{case['description']}\"\n"
            f"  tags: [{', '.join(case['tags'])}]\n"
        )

    (HERE / "traptask.yaml").write_text(
        "# GENERATED by build_cases.py -- edit gold.cases.json instead.\n"
        # Two sessions that share no state. A harness that answers one prompt
        # per invocation cannot attempt this, and neither can one whose
        # sessions all live in the same profile state. See
        # docs/harness-requirements.md.
        "harness:\n  needs: [multi_session]\n\n"
        "dirs:\n  inputs: inputs/\n  expected: expected/\n\ncases:\n"
        + "".join(yaml_cases)
        + "\njudge:\n  cmd: python3 judge.py\n\ngrader:\n  cmd: python3 grader.py\n"
    )

    print(f"built {len(cases)} cases -> inputs/, expected/, traptask.yaml")


if __name__ == "__main__":
    build()
