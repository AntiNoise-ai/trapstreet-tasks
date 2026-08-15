"""Generate inputs/<id>/... , expected/<id>/answer.json and traptask.yaml.

Run:  python3 build_cases.py

WHY THIS TASK EXISTS, given that ledger_audit already asks similar questions
of a similar ledger:

ledger_audit is single-shot. One prompt, one fully-visible sheet, one answer:
intrinsic horizon H* ~ 1, compositional depth s ~ 1. Eight calibration rounds
raised the arithmetic difficulty every way we could think of -- multi-rule
settlement, an induced rather than stated policy, a mid-period policy change,
out-of-order vouchers, shortcut-proof aggregates -- and a bare harness scored
8, 8, 10, 9, 8, 9, 10 out of 10. Repeated trials showed the spread was mostly
run-to-run noise: the design changes had almost no measurable effect.

The published work on where agents actually break says why. Failure
concentrates in long-horizon, compositionally deep settings: performance
degrades non-linearly in the number of nested sub-goals, with a sharp knee,
and planning failures dominate because they arise early and propagate. Making
a single step harder to compute is the flat part of that curve.

So this task keeps the same domain and the same deterministic scoring and
moves the two axes that matter:

  H*  -- the figures are spread over a year of monthly ledgers plus a policy
         memo, a counterparty master and a document index; references resolve
         only through the index; two files in the directory are decoys.
  s   -- one month's file is short: entries were posted late and booked in a
         supplement. Nothing announces this. It is visible only by tying each
         month's closing balance to the next month's opening, and everything
         downstream of the gap is wrong if it is missed.

Both are parameters (MONTHS, DECOYS, and whether a gap is planted), so the
task has calibration knobs rather than a redesign per attempt.
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE / "gold.cases.json"
INPUTS = HERE / "inputs"
EXPECTED = HERE / "expected"

CASE_ID_RE = re.compile(r"^case_\d\d$")
PERIOD_START = datetime.date(2026, 1, 1)
MIN_DISCRIMINATING = 2

# How many post-changeover rows the memo must work through where a Reference
# was NOT honoured. One is not enough and the first calibration run proved it:
# the harness noticed that its induced policy matched 14 of 15 memo rows,
# reported the ratio honestly, and treated the odd row as a keying error
# rather than a change of regime -- which, on a single example, is a
# defensible reading. A task that is hard because the evidence is too thin to
# support the intended inference is measuring luck, not capability.
MIN_CHANGE_EVIDENCE = 3
CHANGEOVER = "2026-03-15"
SHORTCUT_TOLERANCE = 25.00

COUNTERPARTIES = [
    ("C-ANCH", "Anchor Distributors"),
    ("C-BAYL", "BayLine Foods"),
    ("C-CEDA", "Cedarworks Ltd"),
    ("C-DELT", "Delta Freight Co"),
    ("C-EAST", "Eastgate Packaging"),
    ("C-FAIR", "Fairmont Supplies"),
]
DEBIT_NARRATIONS = (["Invoice raised"] * 6 + ["Goods dispatched"] * 3
                    + ["Service billed"] * 3 + ["Freight recharged"] + ["Late-payment charge"])
CREDIT_NARRATIONS = (["Payment received"] * 6 + ["Settlement received"] * 3
                     + ["Credit note issued"] * 2 + ["Refund applied"] + ["Discount allowed"])


# --------------------------------------------------------------------------
# settlement (identical model to ledger_audit -- see its README)

def apply_credit(open_list: list[list], amount: float, ref: str,
                 honour_reference: bool = True) -> tuple[float, list[tuple[str, float]]]:
    remaining, applied = amount, []
    if ref and honour_reference:
        for item in open_list:
            if item[0] == ref and item[2] > 0.005:
                take = min(item[2], remaining)
                item[2] = round(item[2] - take, 2)
                remaining = round(remaining - take, 2)
                applied.append((item[0], round(take, 2)))
                break
    for item in sorted(open_list, key=lambda i: (i[1], i[0])):
        if remaining <= 0.005:
            break
        if item[2] <= 0.005:
            continue
        take = min(item[2], remaining)
        item[2] = round(item[2] - take, 2)
        remaining = round(remaining - take, 2)
        applied.append((item[0], round(take, 2)))
    return round(remaining, 2), applied


def settle(entries: list[dict], merge_renamed: bool = True
           ) -> tuple[dict[str, tuple[str, float]], float]:
    open_inv: dict[str, list[list]] = {}
    unapplied = 0.0
    for r in sorted(entries, key=lambda x: (x["date"], x["voucher"])):
        cp = canonical(r["cp_code"]) if merge_renamed else r["cp_code"]
        if r["debit"] is not None:
            open_inv.setdefault(cp, []).append([r["voucher"], r["date"], r["debit"]])
        else:
            left, _ = apply_credit(open_inv.setdefault(cp, []), r["credit"],
                                   r["reference_voucher"], r["date"] < CHANGEOVER)
            unapplied = round(unapplied + left, 2)
    out = {}
    for es in open_inv.values():
        for voucher, date, residual in es:
            if residual > 0.005:
                out[voucher] = (date, residual)
    return out, round(unapplied, 2)


# --------------------------------------------------------------------------
# generation

def make_entries(rng: random.Random, months: int, per_month: int) -> list[dict]:
    entries: list[dict] = []
    open_inv: dict[str, list[list]] = {}
    n = 0
    for month in range(1, months + 1):
        days = (datetime.date(2026, month % 12 + 1, 1) - datetime.date(2026, month, 1)).days \
            if month < 12 else 31
        for offset in sorted(rng.choices(range(1, days + 1), k=per_month)):
            n += 1
            date = datetime.date(2026, month, offset).isoformat()
            code, _ = rng.choice(COUNTERPARTIES)
            voucher = f"AR-{n:05d}"
            outstanding = [i for i in open_inv.get(code, []) if i[2] > 0.005]
            if rng.random() < 0.60 or not outstanding:
                amount = round(rng.uniform(180, 9400), 2)
                open_inv.setdefault(code, []).append([voucher, date, amount])
                entries.append({"date": date, "voucher": voucher, "cp_code": code,
                                "narration": rng.choice(DEBIT_NARRATIONS),
                                "debit": amount, "credit": None,
                                "reference_voucher": "", "discriminating": False,
                                "shows_change": False})
                continue
            narration = rng.choice(CREDIT_NARRATIONS)
            cap = round(sum(i[2] for i in outstanding), 2)
            amount = round(min(rng.uniform(180, 9400),
                               cap * (1.1 if rng.random() < 1 / 8 else 1.0)), 2)
            if amount < 50:
                amount = round(rng.uniform(180, 9400), 2)
                open_inv.setdefault(code, []).append([voucher, date, amount])
                entries.append({"date": date, "voucher": voucher, "cp_code": code,
                                "narration": rng.choice(DEBIT_NARRATIONS),
                                "debit": amount, "credit": None,
                                "reference_voucher": "", "discriminating": False,
                                "shows_change": False})
                continue
            cites = narration == "Credit note issued" or rng.random() < 0.55
            ref = ""
            if cites:
                settled = [v for v, *_ in [(i[0],) for i in open_inv.get(code, [])]
                           if all(i[0] != v or i[2] <= 0.005 for i in open_inv[code])]
                ref = (rng.choice(settled) if settled and rng.random() < 1 / 4
                       else rng.choice(outstanding)[0])
            live = [i for i in outstanding if i[2] > 0.005]
            oldest = min(live, key=lambda i: (i[1], i[0]), default=None)
            ref_differs = bool(ref) and oldest is not None and ref != oldest[0] and any(
                i[0] == ref and i[2] > 0.005 for i in outstanding)
            apply_credit(open_inv[code], amount, ref, date < CHANGEOVER)
            entries.append({"date": date, "voucher": voucher, "cp_code": code,
                            "narration": narration, "debit": None, "credit": amount,
                            "reference_voucher": ref,
                            "discriminating": ref_differs and date < CHANGEOVER,
                            "shows_change": ref_differs and date >= CHANGEOVER})
    return entries


def mark_demonstration(cid: str, entries: list[dict]) -> None:
    """Flag the leading credits the policy memo works through. Same contract as
    ledger_audit: enough to induce the policy, the change, and nothing
    unexplained left in the region the solver has to do."""
    credits = [r for r in entries if r["credit"] is not None]
    seen, disc = set(), 0
    for r in credits:
        applied_refs = r["reference_voucher"]
        seen.add("fifo" if not applied_refs else "referenced")
        r["demonstrated"] = True
        disc += 1 if r["discriminating"] else 0
        narr = {x["narration"] for x in credits if x.get("demonstrated") and x["discriminating"]}
        if (seen >= {"fifo", "referenced"} and disc >= MIN_DISCRIMINATING and len(narr) >= 2
                and sum(1 for x in credits
                        if x.get("demonstrated") and x["shows_change"]) >= MIN_CHANGE_EVIDENCE):
            break
    else:
        raise ValueError(f"{cid}: memo cannot demonstrate the policy and show its change at least {MIN_CHANGE_EVIDENCE} times")
    if sum(1 for r in credits if r.get("demonstrated")) > len(credits) * 0.55:
        raise ValueError(f"{cid}: memo would work through too much of the year")


def _money(v) -> str:
    return "" if v is None else f"{v:,.2f}"


def render_month(entries: list[dict], month: int, opening: float,
                 doc_of: dict[str, str], title_suffix: str = "") -> str:
    head = (f"{'Date':<11} {'Voucher':<11} {'Ref doc':<11} {'Narration':<20} "
            f"{'Cust':<8} {'Debit':>11} {'Credit':>11} {'Balance':>12}")
    bal = opening
    body = [f"{'':<11} {'':<11} {'':<11} {'Opening balance':<20} {'':<8} "
            f"{'':>11} {'':>11} {opening:>12,.2f}"]
    for r in entries:
        bal = round(bal + (r["debit"] or 0) - (r["credit"] or 0), 2)
        body.append(
            f"{r['date']:<11} {r['voucher']:<11} "
            f"{doc_of.get(r['reference_voucher'], ''):<11} {r['narration']:<20} "
            f"{r['cp_code']:<8} {_money(r['debit']):>11} {_money(r['credit']):>11} "
            f"{bal:>12,.2f}")
    body.append(f"{'':<11} {'':<11} {'':<11} {'Closing balance':<20} {'':<8} "
                f"{'':>11} {'':>11} {bal:>12,.2f}")
    return (f"Accounts Receivable — Account 1200 Trade Debtors — 2026-{month:02d}{title_suffix}\n"
            "Amounts in USD. 'Ref doc' is the document the customer's remittance advice or "
            "credit note cites; resolve it through index/documents.csv.\n"
            "'Cust' is a counterparty code; see masters/counterparties.csv.\n\n"
            f"{head}\n{'-' * len(head)}\n" + "\n".join(body) + "\n")


# --------------------------------------------------------------------------
# the surrounding documents

RENAMED_FROM, RENAMED_TO, RENAME_DATE = "C-CEDW", "C-CEDA", "2026-05-01"


def canonical(code: str) -> str:
    return RENAMED_TO if code == RENAMED_FROM else code


def apply_rename(entries: list[dict]) -> None:
    """One counterparty changed code mid-year. The ledgers show whichever code
    was in force; the master file records the succession. Settlement never
    crosses counterparties -- but these two codes are one counterparty, and a
    solver that does not read the master will split them."""
    for r in entries:
        if r["cp_code"] == RENAMED_TO and r["date"] < RENAME_DATE:
            r["cp_code"] = RENAMED_FROM


def write_masters(path: Path) -> None:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["code", "name", "status", "note"])
    for code, name in COUNTERPARTIES:
        if code == RENAMED_TO:
            w.writerow([RENAMED_FROM, name, "superseded",
                        f"re-coded to {RENAMED_TO} with effect from {RENAME_DATE}; "
                        f"same legal entity, same account"])
            w.writerow([code, name, "active", f"formerly {RENAMED_FROM}"])
        else:
            w.writerow([code, name, "active", ""])
    path.write_text(buf.getvalue())


def write_index(path: Path, doc_of: dict[str, str]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["document_id", "voucher", "document_type"])
    for voucher, doc in sorted(doc_of.items(), key=lambda kv: kv[1]):
        w.writerow([doc, voucher, "invoice"])
    path.write_text(buf.getvalue())


def render_memo(entries: list[dict], doc_of: dict[str, str]) -> str:
    """The worked allocation schedule. Everything the solver needs to induce
    the policy is here and nowhere else; the policy itself is never stated."""
    open_inv: dict[str, list[list]] = {}
    lines = []
    for r in sorted(entries, key=lambda x: (x["date"], x["voucher"])):
        cp = canonical(r["cp_code"])
        if r["debit"] is not None:
            open_inv.setdefault(cp, []).append([r["voucher"], r["date"], r["debit"]])
            continue
        left, applied = apply_credit(open_inv.setdefault(cp, []), r["credit"],
                                     r["reference_voucher"], r["date"] < CHANGEOVER)
        if not r.get("demonstrated"):
            continue
        parts = "  ".join(f"{v} {a:,.2f}" for v, a in applied)
        if left > 0.005:
            parts = (parts + "  " if parts else "") + f"(unapplied {left:,.2f})"
        cited = doc_of.get(r["reference_voucher"], "")
        lines.append(f"{r['date']:<11} {r['voucher']:<11} {cited:<11} {r['credit']:>11,.2f}   {parts}")
    last = max((r["date"] for r in entries if r.get("demonstrated")), default="")
    return ("Allocation memo — Accounts Receivable\n\n"
            "Cash and credit notes are allocated to open invoices under the allocation "
            "policy in force. The schedule below records how each receipt was allocated. "
            "It has been worked through to " + last + " and stops there; the remainder of "
            "the year has not yet been allocated.\n\n"
            "Cash received in excess of what the customer owed at that moment is parked as "
            "unapplied. This account does not carry unapplied cash forward against invoices "
            "raised later.\n\n"
            f"{'Date':<11} {'Voucher':<11} {'Ref doc':<11} {'Amount':>11}   Allocated to\n"
            f"{'-' * 100}\n" + "\n".join(lines) + "\n")


README = """\
# Year-end receivables

Close out the Accounts Receivable ledger for 2026 and answer the question below.

## What is here

- `ledgers/` — the monthly ledger extracts for account 1200
- `policy/allocation-memo.md` — how receipts have been allocated so far
- `masters/counterparties.csv` — the customer master
- `index/documents.csv` — resolves the `Ref doc` column to a voucher

Not everything in `ledgers/` belongs to this year's account 1200 close. Check
what you are reading before you use it.

## Question

{question}

## Output

Print the answer on its own line, prefixed exactly like this:

    ANSWER: 12345.67

A plain amount, no currency symbol and no thousands separators. You may write
whatever else you like before or after that line; only the `ANSWER:` line is
read.
"""


# --------------------------------------------------------------------------
# the gap, the decoys, the question

def split_months(entries: list[dict]) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for r in entries:
        out.setdefault(int(r["date"][5:7]), []).append(r)
    return out


def choose_gap(rng: random.Random, by_month: dict[int, list[dict]], months: int) -> int:
    """Which month gets short-shipped. Never the first or last: the gap has to
    be findable by tying one month's closing to the next month's opening, and
    the last month has no successor."""
    return rng.choice(range(3, months - 1))


def ask(kind: str, entries: list[dict], rng: random.Random) -> tuple[str, str]:
    open_res, _ = settle(entries)
    if kind == "aged_open_after":
        cutoff = sorted({d for d, _ in open_res.values()})[len(open_res) // 3]
        total = sum(res for d, res in open_res.values() if d >= cutoff)
        return (f"How much was still owed at the end of the year on invoices billed on or "
                f"after {cutoff}?", f"{round(total, 2):.2f}")
    if kind == "open_total_cp":
        by_cp: dict[str, float] = {}
        cp_of = {r["voucher"]: canonical(r["cp_code"]) for r in entries}
        for v, (_, res) in open_res.items():
            by_cp[cp_of[v]] = round(by_cp.get(cp_of[v], 0.0) + res, 2)
        code = rng.choice(sorted(c for c, t in by_cp.items() if t >= 1000))
        name = dict(COUNTERPARTIES)[code]
        return (f"How much did {name} still owe at the end of the year?",
                f"{by_cp[code]:.2f}")
    if kind == "settled_total":
        settled = sum(r["debit"] for r in entries
                      if r["debit"] is not None and r["voucher"] not in open_res)
        return ("How much of everything billed during the year had been settled in full by "
                "the end of it?", f"{round(settled, 2):.2f}")
    raise ValueError(f"unknown question kind {kind!r}")


def _residual_distance(a: dict, b: dict) -> float:
    """Total absolute difference between two allocations, invoice by invoice.

    Comparing the TOTALS instead would miss almost everything: total open is
    SUM(debits) - SUM(credits) + unapplied, so any error that merely moves
    money between invoices leaves the total untouched. That identity already
    hid one defect in ledger_audit; per-invoice comparison is what actually
    detects that a mistake matters.
    """
    keys = set(a) | set(b)
    return round(sum(abs(a.get(k, (None, 0.0))[1] - b.get(k, (None, 0.0))[1]) for k in keys), 2)


def assert_sound(cid: str, entries: list[dict], gap_entries: list[dict],
                 decoy_entries: list[dict], answer: str) -> None:
    """Every mechanism this task relies on must actually change the answer, and
    the answer must not be reachable by a shortcut."""
    truth, _ = settle(entries)

    checks = {
        "missing the supplement": settle([r for r in entries if r not in gap_entries])[0],
        "folding in the decoy year": settle(entries + decoy_entries)[0],
        "splitting the re-coded customer": settle(entries, merge_renamed=False)[0],
    }
    for name, alt in checks.items():
        if _residual_distance(truth, alt) < 100.0:
            raise ValueError(f"{cid}: {name} barely changes the allocation "
                             f"(distance {_residual_distance(truth, alt)}) -- the mistake "
                             f"would be undetectable, so the mechanism is decoration")

    value = float(answer)
    debits = round(sum(r["debit"] for r in entries if r["debit"] is not None), 2)
    credits = round(sum(r["credit"] for r in entries if r["credit"] is not None), 2)
    for name, sc in {"total debits": debits, "total credits": credits,
                     "debits minus credits": round(debits - credits, 2)}.items():
        if abs(value - sc) < SHORTCUT_TOLERANCE:
            raise ValueError(f"{cid}: answer is within {SHORTCUT_TOLERANCE} of '{name}'")
    if len(answer.split(".")[0]) < 4:
        raise ValueError(f"{cid}: answer {answer} too small to be unguessable")


# --------------------------------------------------------------------------
# build

def validate_case(case: dict, seen: set[str], seeds: set[int]) -> None:
    required = {"id", "question", "seed", "months", "per_month", "tags", "description"}
    missing = required - case.keys()
    if missing:
        raise ValueError(f"case {case.get('id')} missing {sorted(missing)}")
    if not CASE_ID_RE.match(case["id"]):
        raise ValueError(f"case id {case['id']!r} must be opaque (case_NN)")
    if case["id"] in seen:
        raise ValueError(f"duplicate id {case['id']}")
    seen.add(case["id"])
    if case["seed"] in seeds:
        raise ValueError(f"{case['id']}: seed reused")
    seeds.add(case["seed"])
    if not (6 <= case["months"] <= 12):
        raise ValueError(f"{case['id']}: months out of range 6..12")
    if "answer" in case:
        raise ValueError(f"{case['id']}: gold.cases.json must not carry an answer")


def build() -> None:
    cases = json.loads(GOLD.read_text())["cases"]
    seen: set[str] = set()
    seeds: set[int] = set()
    for c in cases:
        validate_case(c, seen, seeds)

    for d in (INPUTS, EXPECTED):
        if d.exists():
            for child in sorted(d.rglob("*"), reverse=True):
                child.unlink() if child.is_file() else child.rmdir()
        d.mkdir(exist_ok=True)

    yaml_cases = []
    for case in cases:
        cid, rng = case["id"], random.Random(case["seed"])
        months, per_month = case["months"], case["per_month"]

        entries = make_entries(rng, months, per_month)
        apply_rename(entries)
        mark_demonstration(cid, entries)
        doc_of = {r["voucher"]: f"DOC-{rng.randint(10000, 99999)}"
                  for r in entries if r["debit"] is not None}

        by_month = split_months(entries)
        gap_month = choose_gap(rng, by_month, months)
        gap_entries = by_month[gap_month][-max(3, per_month // 4):]

        # a decoy year that would fold in cleanly if mistaken for this one
        decoy_entries = make_entries(random.Random(case["seed"] + 7), 2, per_month)
        for r in decoy_entries:
            r["date"] = r["date"].replace("2026", "2025")
            r["voucher"] = r["voucher"].replace("AR-", "AR-9")

        question, answer = ask(case["question"], entries, rng)
        assert_sound(cid, entries, gap_entries, decoy_entries, answer)

        cdir = INPUTS / cid
        (cdir / "ledgers").mkdir(parents=True)
        (cdir / "policy").mkdir()
        (cdir / "masters").mkdir()
        (cdir / "index").mkdir()

        opening = 0.0
        for month in range(1, months + 1):
            shown = [r for r in by_month[month] if r not in gap_entries]
            (cdir / "ledgers" / f"2026-{month:02d}.txt").write_text(
                render_month(shown, month, opening, doc_of))
            opening = round(opening + sum((r["debit"] or 0) - (r["credit"] or 0)
                                          for r in by_month[month]), 2)
        (cdir / "ledgers" / f"2026-{gap_month:02d}-supplement.txt").write_text(
            "Late-posted entries for 2026-%02d, booked after that month's extract was taken.\n"
            "These entries are part of account 1200 and of the 2026 close.\n\n" % gap_month
            + render_month(gap_entries, gap_month, 0.0, doc_of, " supplement"))
        (cdir / "ledgers" / "2025-12.txt").write_text(
            render_month(decoy_entries[:per_month], 12, 0.0, doc_of, " (prior year)")
            .replace("2026-12", "2025-12"))

        (cdir / "policy" / "allocation-memo.md").write_text(render_memo(entries, doc_of))
        write_masters(cdir / "masters" / "counterparties.csv")
        write_index(cdir / "index" / "documents.csv", doc_of)
        (cdir / "README.md").write_text(README.format(question=question))

        edir = EXPECTED / cid
        edir.mkdir(parents=True)
        (edir / "answer.json").write_text(json.dumps({
            "id": cid, "question_kind": case["question"], "answer": answer,
            "answer_kind": "money", "months": months,
            "gap_month": gap_month, "gap_entries": len(gap_entries),
        }, indent=2) + "\n")

        yaml_cases.append(f"- id: {cid}\n  description: \"{case['description']}\"\n"
                          f"  tags: [{', '.join(case['tags'])}]\n")

    (HERE / "traptask.yaml").write_text(
        "# GENERATED by build_cases.py -- edit gold.cases.json instead.\n"
        "dirs:\n  inputs: inputs/\n  expected: expected/\n\ncases:\n"
        + "".join(yaml_cases) + "\njudge:\n  cmd: python3 judge.py\n"
        "\ngrader:\n  cmd: python3 grader.py\n")
    print(f"built {len(cases)} cases")


if __name__ == "__main__":
    build()
