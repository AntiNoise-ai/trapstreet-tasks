"""Billing summary -- LIVE current-state view of what each active
subscription would be billed TODAY.

Reads: customers.csv, subscriptions.csv, plans.csv, tiers.csv, addons.csv,
       discount_codes.csv, regions.csv

Everything here is resolved via LOOKUP against the CURRENT tables (no
invoice history involved). If a plan's price changes, or a customer's
region changes, or an add-on is renamed/repriced, this report reflects
the new value immediately for every active subscription -- it is the
"if we billed today" view, not a historical record.
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
    customers = index_by(load_csv(here / "customers.csv"), "customer_id")
    plans = index_by(load_csv(here / "plans.csv"), "plan_id")
    tiers = index_by(load_csv(here / "tiers.csv"), "tier_id")
    addons = index_by(load_csv(here / "addons.csv"), "addon_id")
    discount_codes = index_by(load_csv(here / "discount_codes.csv"), "code")
    regions = index_by(load_csv(here / "regions.csv"), "region_id")
    subscriptions = load_csv(here / "subscriptions.csv")

    rows = []
    for sub in subscriptions:
        if sub.get("status") != "active":
            continue
        customer = customers.get(sub["customer_id"])
        plan = plans.get(sub["plan_id"])
        if not customer or not plan:
            continue
        tier = tiers.get(plan.get("tier_id"), {})
        region = regions.get(customer.get("region_id"), {})

        base_price = to_num(plan.get("base_price_usd")) or 0.0
        addon_total = 0.0
        for aid in split_ids(sub.get("addon_ids")):
            addon = addons.get(aid)
            if addon:
                addon_total += to_num(addon.get("addon_price_usd")) or 0.0

        subtotal = base_price + addon_total
        discount = 0.0
        code = (sub.get("discount_code") or "").strip()
        if code and code in discount_codes:
            dc = discount_codes[code]
            pct = to_num(dc.get("discount_pct"))
            fixed = to_num(dc.get("discount_fixed_usd"))
            if pct:
                discount = subtotal * pct
            elif fixed:
                discount = fixed

        after_discount = subtotal - discount
        tax_rate = to_num(region.get("tax_rate_pct")) or 0.0
        tax = after_discount * tax_rate / 100.0
        total = after_discount + tax

        rows.append({
            "subscription_id": sub["subscription_id"],
            "customer_name": customer.get("customer_name", ""),
            "plan_name": plan.get("plan_name", ""),
            "tier_name": tier.get("tier_name", ""),
            "region_name": region.get("region_name", ""),
            "base_price_usd": f"{base_price:.2f}",
            "addon_total_usd": f"{addon_total:.2f}",
            "discount_usd": f"{discount:.2f}",
            "tax_usd": f"{tax:.2f}",
            "total_usd": f"{total:.2f}",
        })

    rows.sort(key=lambda r: r["subscription_id"])
    cols = ["subscription_id", "customer_name", "plan_name", "tier_name",
            "region_name", "base_price_usd", "addon_total_usd",
            "discount_usd", "tax_usd", "total_usd"]
    print(",".join(cols))
    for r in rows:
        vals = [f'"{r[c]}"' if "," in r[c] else r[c] for c in cols]
        print(",".join(vals))


if __name__ == "__main__":
    main()
