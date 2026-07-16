"""Itemised statement report — per-transaction detail with sku + publisher.

Reads: catalog.csv, enterprise_deals.csv, publishers.csv, transactions.csv
Output: prints one row per transaction with sku, publisher_name, royalty amount.

Lookup rules (same as publisher_statement.py):
- For enterprise-channel transactions, if the product exists in
  enterprise_deals.csv, use that row's terms (sku, publisher_id, royalty).
- Otherwise, look up terms from catalog.csv, picking the row with the
  largest `effective_from` <= transaction sale_date for the product.
- Publisher name resolved via publisher_id -> publishers.csv.
- SKU comes from the same lookup row (catalog or enterprise_deals).
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


def resolve(txn, catalog_by_pid, enterprise_by_pid):
    """Return (sku, publisher_id, royalty_pct, royalty_fixed_usd)."""
    pid = txn["product_id"]
    if txn["channel"] == "enterprise" and pid in enterprise_by_pid:
        row = enterprise_by_pid[pid]
        return row["sku"], row["publisher_id"], to_float(row["royalty_pct"]), to_float(row["royalty_fixed_usd"])
    candidates = [r for r in catalog_by_pid.get(pid, []) if r["effective_from"] <= txn["sale_date"]]
    if not candidates:
        return None, None, None, None
    row = max(candidates, key=lambda r: r["effective_from"])
    return row["sku"], row["publisher_id"], to_float(row["royalty_pct"]), to_float(row["royalty_fixed_usd"])


def compute_royalty(revenue, pct, fixed):
    if fixed is not None:
        return fixed
    if pct is not None:
        return revenue * pct
    return 0.0


def main():
    here = Path(__file__).parent
    catalog = load_csv(here / "catalog.csv")
    enterprise = load_csv(here / "enterprise_deals.csv")
    publishers = load_csv(here / "publishers.csv")
    transactions = load_csv(here / "transactions.csv")

    catalog_by_pid = defaultdict(list)
    for r in catalog:
        catalog_by_pid[r["product_id"]].append(r)
    enterprise_by_pid = {r["product_id"]: r for r in enterprise}
    publisher_name_by_id = {r["publisher_id"]: r["publisher_name"] for r in publishers}

    print("transaction_id,sale_date,sku,channel,publisher_name,revenue_usd,royalty_usd")
    for txn in sorted(transactions, key=lambda t: (t["sale_date"], t["transaction_id"])):
        sku, pub_id, pct, fixed = resolve(txn, catalog_by_pid, enterprise_by_pid)
        pub_name = publisher_name_by_id.get(pub_id, pub_id or "")
        revenue = float(txn["revenue_usd"])
        royalty = compute_royalty(revenue, pct, fixed)
        print(f'{txn["transaction_id"]},{txn["sale_date"]},{sku or ""},{txn["channel"]},"{pub_name}",{revenue:.2f},{royalty:.2f}')


if __name__ == "__main__":
    main()
