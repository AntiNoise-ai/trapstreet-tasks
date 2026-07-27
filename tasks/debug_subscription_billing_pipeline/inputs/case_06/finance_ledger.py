"""Finance ledger -- reconciliation report Finance runs against invoice_detail.

Reads: invoices.csv, subscriptions.csv, customers.csv, regions.csv

The pretax subtotal ALWAYS comes from the invoice's own BAKED columns
(base + addon - discount, all baked). Tax is COALESCE(baked_tax_usd, LIVE
recompute): if the invoice has a baked tax figure, trust it; only when
baked_tax_usd is blank does this report fall back to a LIVE lookup
(invoice -> subscription -> customer -> region -> tax_rate_pct) to fill
the gap. This means a baked tax correction on one invoice is picked up
here automatically (same source column as invoice_detail), while a
missing/never-baked tax figure gets computed fresh from current customer
region.
"""
import csv
from pathlib import Path


def load_csv(path):
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def to_num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def index_by(rows, key):
    return {r[key]: r for r in rows}


def main():
    here = Path(__file__).parent
    invoices = load_csv(here / "invoices.csv")
    subscriptions = index_by(load_csv(here / "subscriptions.csv"), "subscription_id")
    customers = index_by(load_csv(here / "customers.csv"), "customer_id")
    regions = index_by(load_csv(here / "regions.csv"), "region_id")

    rows = []
    for inv in invoices:
        base = to_num(inv.get("baked_base_price_usd")) or 0.0
        addon_total = to_num(inv.get("baked_addon_total_usd")) or 0.0
        discount = to_num(inv.get("baked_discount_applied_usd")) or 0.0
        pretax = base + addon_total - discount

        tax = to_num(inv.get("baked_tax_usd"))
        if tax is None:
            sub = subscriptions.get(inv.get("subscription_id"), {})
            customer = customers.get(sub.get("customer_id"), {})
            region = regions.get(customer.get("region_id"), {})
            tax_rate = to_num(region.get("tax_rate_pct")) or 0.0
            tax = pretax * tax_rate / 100.0

        total = pretax + tax

        rows.append({
            "invoice_id": inv["invoice_id"],
            "subscription_id": inv.get("subscription_id", ""),
            "period": inv.get("period", ""),
            "pretax_subtotal_usd": f"{pretax:.2f}",
            "tax_usd": f"{tax:.2f}",
            "total_usd": f"{total:.2f}",
        })

    rows.sort(key=lambda r: (r["period"], r["invoice_id"]))
    cols = ["invoice_id", "subscription_id", "period",
            "pretax_subtotal_usd", "tax_usd", "total_usd"]
    print(",".join(cols))
    for r in rows:
        print(",".join(str(r[c]) for c in cols))


if __name__ == "__main__":
    main()
