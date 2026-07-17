"""Itemised statement report — per-transaction detail with sku + supplier.

Reads: catalog.csv, transactions.csv
Output: prints one row per transaction with sku, supplier_name, royalty amount.

Lookup rules:
- Supplier name: read the transaction's supplier_name field DIRECTLY (BAKED
  at time of sale). No lookup through catalog/suppliers.
- SKU: read the transaction's sku field DIRECTLY (BAKED at time of sale).
- Royalty amount:
  - retail channel: computed from catalog's royalty_pct/royalty_fixed_usd
    (looked up via product_id + effective_from routing).
  - b2b channel: computed from the TRANSACTION's own royalty_pct/
    royalty_fixed_usd (BAKED at contract time).
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
    pid = txn["product_id"]
    candidates = [r for r in catalog_by_pid.get(pid, []) if r["effective_from"] <= txn["sale_date"]]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r["effective_from"])


def compute_royalty(revenue, pct, fixed):
    if fixed is not None:
        return fixed
    if pct is not None:
        return revenue * pct
    return 0.0


def main():
    here = Path(__file__).parent
    catalog = load_csv(here / "catalog.csv")
    transactions = load_csv(here / "transactions.csv")

    catalog_by_pid = defaultdict(list)
    for r in catalog:
        catalog_by_pid[r["product_id"]].append(r)

    print("transaction_id,sale_date,sku,channel,supplier_name,revenue_usd,royalty_usd")
    for txn in sorted(transactions, key=lambda t: (t["sale_date"], t["transaction_id"])):
        revenue = float(txn["revenue_usd"])
        # Royalty: retail uses catalog terms, b2b uses baked terms
        if txn["channel"] == "b2b":
            pct = to_float(txn.get("royalty_pct"))
            fixed = to_float(txn.get("royalty_fixed_usd"))
        else:
            cat_row = resolve_catalog(txn, catalog_by_pid)
            if cat_row:
                pct = to_float(cat_row.get("royalty_pct"))
                fixed = to_float(cat_row.get("royalty_fixed_usd"))
            else:
                pct = fixed = None
        royalty = compute_royalty(revenue, pct, fixed)

        # Supplier name + SKU: read BAKED from transaction directly
        print(f'{txn["transaction_id"]},{txn["sale_date"]},{txn["sku"]},{txn["channel"]},"{txn["supplier_name"]}",{revenue:.2f},{royalty:.2f}')


if __name__ == "__main__":
    main()
