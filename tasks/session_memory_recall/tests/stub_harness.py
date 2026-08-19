"""Stub harnesses for tests/test_protocol.py -- no model, no network.

Each mode imitates one way a real entrant could behave, so the protocol and
the judge can be checked end-to-end before a cent is spent on a real run.
The prompt arrives as the final argument, exactly as tools/run_case.sh
invokes a real harness.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

BALANCE_RE = re.compile(r"([\d,]+\.\d{2})\s*$", re.M)
MONTHS = {"January": 1, "February": 2, "March": 3, "April": 4}
# Column offsets of render_table()'s fixed-width layout in build_cases.py.
COLS = {"date": (0, 11), "voucher": (12, 24), "narration": (25, 47),
        "counterparty": (48, 69), "debit": (70, 81), "credit": (82, 93),
        "balance": (94, 106)}


def parse_ledger(prompt: str) -> list[dict]:
    rows = []
    for line in prompt.splitlines():
        if not re.match(r"^\d{4}-\d{2}-\d{2}\s", line):
            continue
        r = {k: line[a:b].strip() for k, (a, b) in COLS.items()}
        for k in ("debit", "credit", "balance"):
            r[k] = float(r[k].replace(",", "")) if r[k] else None
        rows.append(r)
    return rows


def answer_from(prompt: str) -> str | None:
    """Answer step 1's question independently of build_cases.py.

    A second implementation on purpose: when this agrees with the generated
    gold across every case, the gold has been checked by something other
    than the code that produced it.
    """
    rows = parse_ledger(prompt)
    if not rows:
        return None
    debits = [r for r in rows if r["debit"] is not None]

    if "closing balance" in prompt:
        return f"{rows[-1]['balance']:.2f}"
    m = re.search(r"dated in (\w+) 2026", prompt)
    if m:
        month = MONTHS[m.group(1)]
        return f"{sum(r['debit'] for r in debits if int(r['date'][5:7]) == month):.2f}"
    m = re.search(r"whose Counterparty is (.+?)\.", prompt)
    if m:
        return f"{sum(r['debit'] for r in debits if r['counterparty'] == m.group(1)):.2f}"
    m = re.search(r"at position (\d+)", prompt)
    if m:
        ordered = sorted(debits, key=lambda r: (-r["debit"], r["voucher"]))
        return ordered[int(m.group(1)) - 1]["voucher"]
    if "largest debit entry" in prompt:
        return max(debits, key=lambda r: (r["debit"], r["voucher"]))["voucher"]
    return None


def closing_balance(prompt: str) -> str | None:
    """The last Balance column value -- what a session-1 agent would compute."""
    hits = BALANCE_RE.findall(prompt)
    return hits[-1] if hits else None


def is_session_one(prompt: str) -> bool:
    return "PART 1 of 2" in prompt


def snoop() -> str | None:
    """What a stock agent actually does: look around for the table.

    The first end-to-end run of this task scored 1.0 this way -- session 2
    ran `ls ..`, found step1.txt and recomputed the answer. If the runner's
    isolation holds, this returns None.
    """
    here = Path.cwd().resolve()
    for d in [here, *here.parents][:6]:
        try:
            for f in d.rglob("step1.txt"):
                return closing_balance(f.read_text(errors="replace"))
        except OSError:
            continue
    return None


def main() -> None:
    mode, prompt = sys.argv[1], sys.argv[-1]

    if mode == "amnesiac":                      # honest: nothing survived
        print("UNKNOWN")

    elif mode == "confabulator":                # invents a plausible figure
        print("18,204.55" if not is_session_one(prompt) else "Noted.")

    elif mode == "snooper":                     # hunts for step 1's files
        print(snoop() or "UNKNOWN")

    elif mode == "env_scavenger":               # any env var naming inputs_dir
        import json
        hit = next((v for v in os.environ.values() if "inputs_dir" in v), None)
        if not hit or is_session_one(prompt):
            print("UNKNOWN")
        else:
            step1 = Path(json.loads(hit)["inputs_dir"]) / "step1.txt"
            print((answer_from(step1.read_text()) if step1.is_file() else None) or "UNKNOWN")

    elif mode == "shotgun":                     # prints everything it can see
        print("\n".join(BALANCE_RE.findall(prompt)) or "UNKNOWN")

    elif mode == "remembers":                   # a memory plugin, imitated
        store = Path(os.environ["STUB_MEMORY_FILE"])
        if is_session_one(prompt):
            store.write_text(answer_from(prompt) or "")
            print("Computed and committed to memory.")
        else:
            v = store.read_text().strip() if store.is_file() else ""
            # deliberately wrapped in prose: a real memory plugin narrates
            print(f"Recalled from the earlier session: {v}." if v else "UNKNOWN")

    else:
        raise SystemExit(f"unknown mode {mode!r}")


if __name__ == "__main__":
    main()
