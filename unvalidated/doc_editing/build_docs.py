"""Source-of-truth generator for the doc_editing task.

Each case ships a structured input document and asks the agent to perform a
structure-changing edit while preserving ALL content. The gold record set is
derived from the same source data, so the judge can measure exact retention.

DELEGATE-52 finding adopted here: frontier models silently drop/alter records
over structural edits. These cases make that measurable and deterministic.

Run:  python3 build_docs.py
Emits per case: inputs/<id>/{question.txt, <doc>}  +  expected/<id>/answer.json
plus traptask.yaml and gold.cases.json.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
META = []


def _in(cid: str) -> Path:
    p = HERE / "inputs" / cid
    p.mkdir(parents=True, exist_ok=True)
    return p


def _emit(cid, category, difficulty, question, gold, match_mode, numeric_keys, note):
    (HERE / "expected" / cid).mkdir(parents=True, exist_ok=True)
    ans = {"id": cid, "category": category, "difficulty": difficulty,
           "match_mode": match_mode, "numeric_keys": numeric_keys,
           "gold": gold, "_notes": note}
    (HERE / "expected" / cid / "answer.json").write_text(json.dumps(ans, indent=2, ensure_ascii=False) + "\n")
    (HERE / "inputs" / cid / "question.txt").write_text(question.strip() + "\n")
    META.append({"id": cid, "category": category, "difficulty": difficulty,
                 "n_records": len(gold), "match_mode": match_mode, "notes": note})


def case_ledger_reformat():
    cid = "ledger_csv_to_json"
    # Trap rows (dropping/dedup/tidying bait) interleaved with filler so the doc
    # is long enough that single-shot preservation is non-trivial.
    special = [
        {"date": "2026-01-05", "description": "Coffee, tea & snacks", "amount": "-18.50"},   # comma in field
        {"date": "2026-01-07", "description": "Café Münchner catering", "amount": "-120.00"},  # unicode
        {"date": "2026-01-09", "description": "Invoice #1001", "amount": "2500.00"},
        {"date": "2026-01-09", "description": "Invoice #1002", "amount": "2500.00"},          # near-dup (same amount)
        {"date": "2026-01-11", "description": "", "amount": "-9.99"},                         # empty field
        {"date": "2026-01-12", "description": "Refund — partial", "amount": "33.33"},         # em dash
    ]
    vendors = ["Office supplies", "Travel reimbursement", "Cloud hosting", "Legal fees",
               "Marketing spend", "Hardware", "Stationery", "Training", "Subscriptions",
               "Maintenance", "Utilities", "Consulting", "Shipping", "Insurance",
               "Bank charges", "Software license"]
    rows = [{"date": "2026-01-03", "description": "Office supplies", "amount": "-42.10"}]
    day = 13
    for i, v in enumerate(vendors):
        rows.append({"date": f"2026-01-{day:02d}", "description": v, "amount": f"{(i + 1) * 17.5 - 50:.2f}"})
        day += 1
        if i in (1, 4, 7, 10, 13):  # sprinkle the trap rows through the file
            rows.append(special.pop(0))
    rows.extend(special)  # any remaining trap rows
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["date", "description", "amount"])
    w.writeheader()
    w.writerows(rows)
    (_in(cid) / "data.csv").write_text(buf.getvalue(), encoding="utf-8")
    _emit(cid, "reformat", "medium", """
data.csv is a ledger. Convert it to a JSON array of objects, one object per data
row, with keys "date", "description", and "amount".

Preserve EVERY row and EVERY value exactly:
- do not skip rows with blank fields
- do not merge or de-duplicate rows that look similar
- do not translate, re-spell, or "tidy" any text (keep accents, punctuation, symbols)
- keep amounts exactly as written

Output ONLY the JSON array.
""", rows, "multiset", ["amount"],
    "23 rows incl. comma-in-field, unicode, em dash, empty description, and a near-duplicate pair. "
    "Baits dedup/drop/tidy across a long doc.")


def case_sort_preserve():
    cid = "transactions_sort"
    # 18 transactions, distinct dates (so the sort is unambiguous), shuffled by
    # construction. Includes dedup/drop bait: repeated amounts, a 0.00, a negative.
    amounts = ["12.50", "88.00", "5.00", "12.50", "240.00", "0.00", "12.50", "-30.00",
               "19.99", "7.00", "240.00", "63.40", "1.00", "500.00", "0.00", "44.44",
               "-12.50", "99.00"]
    days = [11, 2, 19, 5, 15, 8, 22, 28, 3, 26, 14, 9, 30, 1, 17, 24, 6, 20]  # all distinct
    src = [{"id": f"T-{i+1:02d}", "date": f"2026-03-{days[i]:02d}", "amount": amounts[i]}
           for i in range(len(amounts))]
    lines = ["id | date | amount"] + [f'{r["id"]} | {r["date"]} | {r["amount"]}' for r in src]
    (_in(cid) / "data.txt").write_text("\n".join(lines) + "\n")
    gold = sorted(src, key=lambda r: r["date"])
    _emit(cid, "sort", "medium", """
data.txt lists transactions (pipe-separated), one per line, in random order.

Sort the transactions by "date" in ascending order and output them as a JSON
array of objects with keys "id", "date", "amount" — one object per transaction.

Keep ALL transactions. Do not drop, merge, or de-duplicate any row, even if two
rows share the same amount or an amount is 0 or negative. Output ONLY the JSON array.
""", gold, "ordered", ["amount"],
    "18 rows; repeated amount 12.50, one is 0.00, one negative. Tests sort while preserving "
    "every record (drop/dedup bait).")


def case_uniform_edit():
    cid = "apply_surcharge"
    # Clean multiples so x1.05 lands on exact cents (no rounding disputes).
    names = ["Desk", "Chair", "Lamp", "Monitor", "Cable", "Stand", "Keyboard", "Mouse",
             "Webcam", "Dock", "Riser", "Pad", "Hub", "Arm", "Tray", "Filter"]
    items = [{"item": n, "price": f"{20 * (i + 1)}.00"} for i, n in enumerate(names)]
    lines = ["item | price"] + [f'{r["item"]} | {r["price"]}' for r in items]
    (_in(cid) / "data.txt").write_text("\n".join(lines) + "\n")
    gold = [{"item": r["item"], "new_price": f'{float(r["price"]) * 1.05:.2f}'} for r in items]
    _emit(cid, "edit", "hard", """
data.txt lists products (pipe-separated), one per line, with a price.

Add a 5% surcharge to EVERY product's price. Output a JSON array of objects with
keys "item" and "new_price" (the price after the 5% surcharge, as a number with
two decimals), one object per product, in the SAME order as the input.

Apply the surcharge to every single product — do not skip any. Output ONLY the JSON array.
""", gold, "ordered", ["new_price"],
    "16 items, uniform +5% edit. Tests multi-edit consistency: every row must be edited "
    "correctly with none skipped or left unedited.")


def case_long_retention():
    cid = "config_long_retention"
    # 30 key=value lines. Long enough to bait truncation; a couple of value traps.
    pairs = []
    words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf",
             "hotel", "india", "juliet", "kilo", "lima", "mike", "november",
             "oscar", "papa", "quebec", "romeo", "sierra", "tango", "uniform",
             "victor", "whiskey", "xray", "yankee", "zulu"]
    for i in range(1, 49):  # 48 feature keys -> long enough to bait truncation
        wd = words[(i - 1) % len(words)]
        pairs.append((f"feature_{i:02d}", f"{wd}-{i:02d}"))
    # value traps:
    pairs.append(("db_url", "postgres://host:5432/db?ssl=true"))  # value contains '=' and ':'
    pairs.append(("retry_enabled", "false"))                      # must stay string "false", not bool
    pairs.append(("max_retries", "007"))                          # leading zeros must survive
    pairs.append(("empty_note", ""))                              # empty value must survive
    text = "\n".join(f"{k}={v}" for k, v in pairs) + "\n"
    (_in(cid) / "config.txt").write_text(text)
    gold = {k: v for k, v in pairs}
    _emit(cid, "retention", "hard", """
config.txt is a configuration file with one "key=value" pair per line.

Convert it to a single JSON object mapping each key to its value.

Preserve EVERY line and value exactly as a string:
- split each line on the FIRST "=" only (values may themselves contain "=")
- keep values verbatim as strings — do not convert "false" to a boolean, do not
  drop leading zeros, do not omit empty values
- include every key; do not truncate the list

Output ONLY the JSON object.
""", gold, "dict", [],
    "52 keys incl. a value containing '=' and ':', a string 'false', leading-zero '007', and an "
    "empty value. Long list baits truncation; traps bait type-coercion and bad splitting.")


def main():
    case_ledger_reformat()
    case_sort_preserve()
    case_uniform_edit()
    case_long_retention()

    lines = ["dirs:", "  inputs: inputs/", "  expected: expected/", "", "cases:"]
    for m in META:
        desc = m["notes"].replace('"', "'")
        lines += [f"- id: {m['id']}", f'  description: "{desc}"', "  tags:",
                  f"  - {m['category']}", f"  - {m['difficulty']}", ""]
    lines += ["judge:", "  cmd: python3 judge.py", "", "grader:", "  cmd: python3 grader.py", ""]
    (HERE / "traptask.yaml").write_text("\n".join(lines))
    (HERE / "gold.cases.json").write_text(json.dumps(META, indent=2) + "\n")
    print(f"generated {len(META)} doc_editing cases into {HERE}")


if __name__ == "__main__":
    main()
