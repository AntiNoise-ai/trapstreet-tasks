"""Customer statement -- all-time invoice history re-rendered with
CURRENT add-on names/prices and CURRENT customer region, but the
historical BASE PRICE stays locked at what was actually baked (grandfather
pricing: a plan price hike does not retroactively re-bill old invoices).

Reads: invoices.csv, subscriptions.csv, addons.csv, discount_codes.csv,
       customers.csv, regions.csv

Resolution per invoice:
- base price: BAKED (invoice's own baked_base_price_usd) -- historical lock-in
- add-on names/total: LIVE lookup via subscription.addon_ids -> addons.csv
  (a rename or reprice shows up on EVERY invoice immediately, including old ones)
- discount: LIVE lookup via subscription.discount_code -> discount_codes.csv,
  using whichever of pct-discount or fixed-discount is LARGER for the
  customer (best-of rule, distinct from billing_summary's pct-or-fixed rule)
- tax: LIVE lookup via subscription -> customer -> CURRENT region (a
  customer's region change re-taxes their ENTIRE history when this report
  is regenerated, not just future invoices)
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


def split_ids(s):
    return [x.strip() for x in (s or "").split(";") if x.strip()]


def main():
    here = Path(__file__).parent
    invoices = load_csv(here / "invoices.csv")
    subscriptions = index_by(load_csv(here / "subscriptions.csv"), "subscription_id")
    addons = index_by(load_csv(here / "addons.csv"), "addon_id")
    discount_codes = index_by(load_csv(here / "discount_codes.csv"), "code")
    customers = index_by(load_csv(here / "customers.csv"), "customer_id")
    regions = index_by(load_csv(here / "regions.csv"), "region_id")

    rows = []
    for inv in invoices:
        sub = subscriptions.get(inv.get("subscription_id"), {})
        addon_ids = split_ids(sub.get("addon_ids"))
        live_addon_names = "; ".join(
            addons[aid]["addon_name"] for aid in sorted(addon_ids) if aid in addons
        )
        live_addon_total = sum(
            to_num(addons[aid].get("addon_price_usd")) or 0.0
            for aid in addon_ids if aid in addons
        )

        base = to_num(inv.get("baked_base_price_usd")) or 0.0
        subtotal = base + live_addon_total

        code = (sub.get("discount_code") or "").strip()
        discount = 0.0
        if code and code in discount_codes:
            dc = discount_codes[code]
            pct_discount = (subtotal * to_num(dc.get("discount_pct"))) if to_num(dc.get("discount_pct")) else 0.0
            fixed_discount = to_num(dc.get("discount_fixed_usd")) or 0.0
            discount = max(pct_discount, fixed_discount)

        after_discount = subtotal - discount

        customer = customers.get(sub.get("customer_id"), {})
        region = regions.get(customer.get("region_id"), {})
        tax_rate = to_num(region.get("tax_rate_pct")) or 0.0
        tax = after_discount * tax_rate / 100.0
        total = after_discount + tax

        rows.append({
            "invoice_id": inv["invoice_id"],
            "period": inv.get("period", ""),
            "addon_names": live_addon_names,
            "addon_total_usd": f"{live_addon_total:.2f}",
            "discount_usd": f"{discount:.2f}",
            "tax_usd": f"{tax:.2f}",
            "total_usd": f"{total:.2f}",
        })

    rows.sort(key=lambda r: (r["period"], r["invoice_id"]))
    cols = ["invoice_id", "period", "addon_names", "addon_total_usd",
            "discount_usd", "tax_usd", "total_usd"]
    print(",".join(cols))
    for r in rows:
        vals = [f'"{r[c]}"' if "," in r[c] else r[c] for c in cols]
        print(",".join(vals))


if __name__ == "__main__":
    main()
