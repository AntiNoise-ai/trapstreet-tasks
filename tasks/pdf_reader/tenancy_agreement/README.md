# Tenancy Agreement — PDF Reader

A trap-compatible eval that asks an agent to read a real UK Assured Shorthold Tenancy (AST) PDF and answer 19 questions about it. The questions cover rent figures, dates, clauses, deposit handling, and two multi-step scenarios that require reading the agreement and doing arithmetic.

## What this task tests

**Can the model read a real-world contract PDF and answer questions about it accurately, without hedging or hallucinating?**

Every question has a single right answer that's literally in the document — a number, a date, a yes/no, an Act of Parliament, or a calculation derived from clauses in Section 6. The judge is harsh: agents that hedge ("I cannot determine from the document…"), skip parts of multi-part questions, or use the wrong format fail the case outright. No partial credit.

The 19 cases break down as:

| Category | Count | Example |
|---|---|---|
| `money` | 6 | Monthly rent in year 2; total rent over fixed term |
| `dates` | 1 | Tenancy start date (DD/MM/YYYY) |
| `clauses` | 8 | Break clause present? Deposit scheme name? Governing Act? |
| `deposit` | 1 | What happens if a deposit dispute remains unresolved? |
| `scenario` | 1 | Early surrender 22 months in: compute the total cost owed |
| `scenario_reasoning` | 1 | If replacement tenant pays higher rent, does the original tenant benefit? |

## Input

Per case the agent receives:
- `INPUTS["question.txt"]` — a single-line natural-language question
- `INPUTS["document.pdf"]` — the AST PDF (~1.8 MB, identical across all 19 cases)

## Expected output

A plain answer printed to **stdout**. Plain text or `{"answer": "..."}` JSON — both work. The agent must:
- Commit to a single answer (no "it depends", no "as an AI…")
- Match the requested format when one is specified (`DD/MM/YYYY`, `yes/no`, `'N/A' if not specified`, etc.)
- For multi-part questions, answer all parts — one-word answers that skip the explanation are rejected
- For scenario questions, show the calculation **and** give the final number

The judge scores each case 1.0 (pass) or 0.0 (fail). A run passes if ≥80% of scored cases pass.

## Purpose

This eval exists to answer a practical question: **which model can read a contract PDF reliably, and among the ones that can, which is the cheapest?**

Contract review is a real-world task where accuracy is non-negotiable but cost adds up fast — you're paying per page, per document, per tenant. A model that's 95% accurate at 1/10 the price of a frontier model is the better business choice. This task surfaces exactly that trade-off: the leaderboard reports both the score and the cost per run, so you can pick the cheapest model that still clears the accuracy bar you need.

If two models score identically, the cheaper one wins.
