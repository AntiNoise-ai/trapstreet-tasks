"""Invoice detail -- the historical record customers see on their invoices.

Reads: invoices.csv ONLY.

Every field is read directly from the invoice's own BAKED columns -- no
lookups against customers/plans/addons/discount_codes/regions. This is
what actually went out to the customer at billing time, so it must NOT
change just because current-state tables (plan prices, addon names,
customer region, discount code definitions) change later. Only editing
a specific invoice row changes what this report shows for that row.
"""
import csv
from pathlib import Path


def load_csv(path):
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def main():
    here = Path(__file__).parent
    invoices = load_csv(here / "invoices.csv")
    invoices.sort(key=lambda r: (r.get("period", ""), r.get("invoice_id", "")))

    cols = ["invoice_id", "period", "baked_customer_name", "baked_plan_name",
            "baked_addon_names", "baked_base_price_usd", "baked_addon_total_usd",
            "baked_discount_applied_usd", "baked_tax_usd", "baked_total_usd", "status"]
    print(",".join(cols))
    for r in invoices:
        vals = [r.get(c, "") for c in cols]
        vals = [f'"{v}"' if "," in v else v for v in vals]
        print(",".join(vals))


if __name__ == "__main__":
    main()
