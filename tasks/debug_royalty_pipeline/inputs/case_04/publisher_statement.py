"""Publisher statement report — aggregate revenue and royalty by publisher.

Reads: catalog.csv, enterprise_deals.csv, publishers.csv, transactions.csv
Output: prints per-publisher totals (revenue, royalty, transaction count)

Lookup rules:
- For enterprise-channel transactions, if the product exists in
  enterprise_deals.csv, use that row's terms (publisher_id + royalty).
- Otherwise, look up terms from catalog.csv, picking the row with the
  largest `effective_from` <= transaction sale_date for the product.
- Publisher name is resolved via publisher_id -> publishers.csv lookup.
"""
import csv
import sys
from pathlib import Path
from collections import defaultdict


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def to_float(v):
    if v is None or v == "":
        return None
    return float(v)


def resolve_terms(txn, catalog_by_pid, enterprise_by_pid):
    """Return (publisher_id, royalty_pct, royalty_fixed_usd) for a transaction."""
    pid = txn["product_id"]
    if txn["channel"] == "enterprise" and pid in enterprise_by_pid:
        row = enterprise_by_pid[pid]
        return row["publisher_id"], to_float(row["royalty_pct"]), to_float(row["royalty_fixed_usd"])
    # Catalog lookup — pick latest effective_from <= sale_date
    candidates = [r for r in catalog_by_pid.get(pid, []) if r["effective_from"] <= txn["sale_date"]]
    if not candidates:
        return None, None, None
    row = max(candidates, key=lambda r: r["effective_from"])
    return row["publisher_id"], to_float(row["royalty_pct"]), to_float(row["royalty_fixed_usd"])


def compute_royalty(revenue, pct, fixed):
    if fixed is not None:
        return fixed  # per-transaction fixed amount
    if pct is not None:
        return revenue * pct
    return 0.0


def main():
    here = Path(__file__).parent
    catalog = load_csv(here / "catalog.csv")
    enterprise = load_csv(here / "enterprise_deals.csv")
    publishers = load_csv(here / "publishers.csv")
    transactions = load_csv(here / "transactions.csv")

    # Index
    catalog_by_pid = defaultdict(list)
    for r in catalog:
        catalog_by_pid[r["product_id"]].append(r)
    enterprise_by_pid = {r["product_id"]: r for r in enterprise}
    publisher_name_by_id = {r["publisher_id"]: r["publisher_name"] for r in publishers}

    # Aggregate by publisher
    agg = defaultdict(lambda: {"revenue": 0.0, "royalty": 0.0, "txn_count": 0})
    for txn in transactions:
        pub_id, pct, fixed = resolve_terms(txn, catalog_by_pid, enterprise_by_pid)
        if pub_id is None:
            continue
        revenue = float(txn["revenue_usd"])
        royalty = compute_royalty(revenue, pct, fixed)
        pub_name = publisher_name_by_id.get(pub_id, pub_id)
        agg[pub_name]["revenue"] += revenue
        agg[pub_name]["royalty"] += royalty
        agg[pub_name]["txn_count"] += 1

    # Print report
    print("publisher_name,total_revenue_usd,total_royalty_usd,transaction_count")
    for pub_name in sorted(agg):
        d = agg[pub_name]
        print(f'"{pub_name}",{d["revenue"]:.2f},{d["royalty"]:.2f},{d["txn_count"]}')


if __name__ == "__main__":
    main()
