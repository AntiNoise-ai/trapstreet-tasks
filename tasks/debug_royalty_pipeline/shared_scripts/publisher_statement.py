"""Publisher statement report — aggregate revenue and royalty by supplier.

Reads: catalog.csv, suppliers.csv, transactions.csv
Output: prints per-supplier totals (revenue, royalty, transaction count)

Lookup rules:
- Supplier name: for every transaction, look up via
  catalog[product_id] -> suppliers[supplier_id] -> supplier_name.
  (LOOKUP path; the transaction's own supplier_name field is IGNORED.)
- Royalty amount:
  - retail channel: computed from catalog's royalty_pct or royalty_fixed_usd.
  - b2b channel: computed from the TRANSACTION's own royalty_pct or
    royalty_fixed_usd (BAKED at contract time, not looked up from catalog).
- catalog can have multiple rows per product_id with different
  effective_from; scripts pick the row with the largest effective_from
  that is <= the transaction's sale_date.
"""
import csv
from pathlib import Path
from collections import defaultdict


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def to_float(v):
    if v is None or v == "":
        return None
    return float(v)


def resolve_catalog(txn, catalog_by_pid):
    """Return the applicable catalog row for this transaction, or None."""
    pid = txn["product_id"]
    candidates = [r for r in catalog_by_pid.get(pid, []) if r["effective_from"] <= txn["sale_date"]]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r["effective_from"])


def compute_royalty(revenue, pct, fixed):
    if fixed is not None:
        return fixed  # per-transaction fixed amount
    if pct is not None:
        return revenue * pct
    return 0.0


def main():
    here = Path(__file__).parent
    catalog = load_csv(here / "catalog.csv")
    suppliers = load_csv(here / "suppliers.csv")
    transactions = load_csv(here / "transactions.csv")

    catalog_by_pid = defaultdict(list)
    for r in catalog:
        catalog_by_pid[r["product_id"]].append(r)
    supplier_name_by_id = {r["supplier_id"]: r["supplier_name"] for r in suppliers}

    agg = defaultdict(lambda: {"revenue": 0.0, "royalty": 0.0, "txn_count": 0})
    for txn in transactions:
        cat_row = resolve_catalog(txn, catalog_by_pid)
        if not cat_row:
            continue
        # Supplier name via LOOKUP path
        supplier_name = supplier_name_by_id.get(cat_row["supplier_id"], cat_row["supplier_id"])
        revenue = float(txn["revenue_usd"])

        # Royalty computation: retail uses catalog terms, b2b uses baked terms
        if txn["channel"] == "b2b":
            pct = to_float(txn.get("royalty_pct"))
            fixed = to_float(txn.get("royalty_fixed_usd"))
        else:
            pct = to_float(cat_row.get("royalty_pct"))
            fixed = to_float(cat_row.get("royalty_fixed_usd"))
        royalty = compute_royalty(revenue, pct, fixed)

        agg[supplier_name]["revenue"] += revenue
        agg[supplier_name]["royalty"] += royalty
        agg[supplier_name]["txn_count"] += 1

    print("supplier_name,total_revenue_usd,total_royalty_usd,transaction_count")
    for name in sorted(agg):
        d = agg[name]
        print(f'"{name}",{d["revenue"]:.2f},{d["royalty"]:.2f},{d["txn_count"]}')


if __name__ == "__main__":
    main()
