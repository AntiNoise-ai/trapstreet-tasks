# Product Matching — SKU Disambiguation

A trap-compatible task that asks an agent to decide whether two product names
refer to the **same product**, **different SKUs of the same product line**, or
**genuinely different products**. The eval surfaces a specific failure mode
LLMs are bad at: distinguishing *variant* from *different*.

The classic trap: **"Apple AirPods Pro 2nd Gen"** vs **"AirPods Pro Gen 2 USB-C"**.
Strong models reflexively say "same" (they're both AirPods Pro 2nd Gen).
Strict graders say "different" (different SKUs). The correct answer is
**variant** — same generation, different connector refresh that Apple still
markets as one product family.

The eval is **pure-rule-based**: judge does a strict 3-way verdict string match.
No LLM-judge. No prompt-engineering loophole.

---

## Layout

```
sku_disambiguation/
├── README.md
├── traptask.yaml             # case list + judge/grader cmds
├── judge.py                  # strict verdict-match (with markdown-fence + embedded-JSON fallback)
├── grader.py                 # aggregator (score, latency, cost, by-category)
├── gold.cases.json           # source-of-truth case data
├── inputs/
│   └── {case_id}/
│       └── question.txt      # the product comparison prompt
└── expected/
    └── {case_id}/
        └── answer.json       # gold verdict + product strings + notes
```

## The verdict vocabulary

Exactly three values are accepted:

| Verdict | Meaning | Examples |
|---|---|---|
| `same` | Both names refer to the IDENTICAL product. A consumer asking for either receives the exact same item. | Tylenol vs Acetaminophen · iPhone 15 vs Apple iPhone 15 · iPad (10th gen) vs iPad 10 |
| `variant` | Same product LINE but different SKUs that a consumer chooses between. One name may be more specific than the other. | AirPods Pro 2nd Gen vs AirPods Pro Gen 2 USB-C · MacBook Air M2 13" vs 15" · Tesla Model 3 Long Range vs Performance |
| `different` | Different products entirely (different lines, distinct products in the same family, or unrelated). | iPad Pro vs iPad Air · Galaxy S24 vs S24 Ultra · iPhone 15 vs iPhone 15 Pro |

Any other verdict (`yes`, `no`, `maybe`, `unknown`, etc.) fails the
`verdict_in_vocab` check → score 0.

## Cases (v0 — 12 cases)

| id | gold | difficulty | what it tests |
|---|---|---|---|
| `airpods_pro_lightning_vs_usbc` | `variant` | expert | The headline trap — same gen, USB-C refresh |
| `macbook_air_m2_13_vs_15` | `variant` | hard | Size variants |
| `tesla_model3_trim` | `variant` | hard | Trim variants (Long Range vs Performance) |
| `tylenol_vs_acetaminophen` | `same` | easy | Brand vs generic |
| `coke_classic_naming` | `same` | easy | Colloquial vs official |
| `photoshop_cc_abbreviation` | `same` | easy | Abbreviation expansion |
| `iphone_15_brand_prefix` | `same` | easy | Brand prefix toggle |
| `ipad_pro_vs_air` | `different` | medium | Different product lines, same screen size |
| `galaxy_s24_vs_ultra` | `different` | medium | Distinct products in same family |
| `airpods_pro_vs_max` | `different` | easy | Completely different product types |
| `iphone_15_vs_15_pro` | `different` | medium | Same family, different products |
| `ipad_10th_gen_naming` | `same` | medium | Naming-convention difference |

Verdict distribution: 4 same · 3 variant · 5 different — agents that always
guess one verdict cap out at 5/12 = 41.7%.

## Solution contract

Each solution must:

1. Read `INPUTS` env var (JSON dict mapping `filename → absolute path`).
2. Read `INPUTS["question.txt"]` — the comparison prompt with Product A and Product B.
3. Print exactly one JSON object to **stdout**:

   ```json
   {"verdict": "variant", "reasoning": "USB-C is the Sept 2023 connector refresh of the AirPods Pro 2nd generation"}
   ```

The judge tolerates markdown code-fence wrappers (`` ```json ... ``` ``) and
extracts the first `{"verdict": ...}` substring even if the model wraps it in
prose. But plain JSON is the canonical format.

## What the judge checks

| # | Check | How |
|---|---|---|
| 1 | stdout parses as a JSON object | `json.loads` (fence stripping + regex fallback) |
| 2 | `verdict` field present and is a string | type check |
| 3 | `verdict` ∈ `{"same", "variant", "different"}` | set membership |
| 4 | `verdict` matches gold | case-insensitive exact match |

All four pass → score 1.0. Any one fails → score 0.0. `reasoning` is captured
in the report but never graded — keeping that out of scoring is what stops
this from becoming an LLM-judge task in disguise.

## Why this discriminates

| Model failure mode | What happens |
|---|---|
| Defaults to "yes/no" thinking → answers `same` for any pair sharing words | misses all `variant` cases (3/12) |
| Conservative → answers `different` for anything with ANY string difference | misses all `same` cases (4/12 down) |
| Doesn't know the `variant` concept at all | best case 9/12 = 75% (gets `same` + `different`) |
| Strong, with product knowledge + nuance | 11–12/12 |

Real-world cost narrative: misclassifying these in a product-catalogue or
e-commerce dedup pipeline ships duplicate listings (treating variants as
different) or merges distinct products (treating different as same). Both
break commerce.

## Wiring up a solution

```yaml
tasks:
  product-matching:
    cmd: uv run python solution.py
    traptask: /path/to/trapstreet-tasks/tasks/product_matching/sku_disambiguation
    timeout: 60
    file_outputs:
      - usage.json
```

Then:

```bash
uv run tp run                          # all 12 cases
uv run tp run -t expert                # just the AirPods trap
uv run tp submit product-matching      # upload to trapstreet.run
```
