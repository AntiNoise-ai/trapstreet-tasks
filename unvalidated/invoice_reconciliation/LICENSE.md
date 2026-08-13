# Data License & Attribution

## Source

The two data files in this task (`customer_invoice.xlsx` + `internal_transactions.csv`) are derived from **anonymized real B2B transactional data** contributed by the project owner from her own work. Released publicly after the anonymization process described below and a manual content-review pass.

### What was done to anonymize

A two-step anonymization pipeline was run against the raw data (kept private, never committed):

1. **`anonymize_take_two.py`** — replaced every sensitive value while preserving structure:
   - Real customer / vendor / retailer / partner names → fictional ones
   - Real product names → fictional product names (consistent across rows)
   - Real SKU codes → synthetic codes that preserve the SKU pattern
   - Real UUIDs / order references → deterministic hashes (preserving the `-1` retry pattern)
   - Numeric values perturbed by a single multiplier (so absolute values are scrambled but row-to-row relationships are intact)
   - Dates shifted by a fixed offset (so chronological gaps are preserved)

2. **`rename_columns.py`** — re-themed column names from publisher-specific terminology to generic B2B vocabulary, dropped unused columns, renamed sheet + file.

A `mapping_report.json` exists in the contributor's local environment as audit/reverse-lookup but is NEVER committed.

### Residual disclosure note

Even with the anonymization above, the SHAPE of the data (row counts, country mix, currency profile, time range) is real. The contributor has reviewed the released files and signed off that no business-sensitive patterns leak through. Forkers using this data for their own evals do not need to do additional anonymization — but should attribute via this LICENSE file.

### Sampling for this task

From the full anonymized dataset (~6,000 rows), a **500-row deterministic subset** (seed=42) was sampled, preserving:
- All 6 rows with the `-1` retry suffix pattern (rare but interesting for reconciliation cases)
- The base counterparts of those `-1` rows where they exist
- Random sample of the remainder

A matched ~492-row CSV subset (487 joining + 5 CSV-only orphans) was constructed alongside.

## Important note for contributors / forkers

If you're contributing similar tasks to TrapStreet using your own real B2B data, **run a comparable two-step anonymization** and surface the same legal / commercial review caveats here before any public commit.
