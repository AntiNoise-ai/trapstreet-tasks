"""Itemised statement — per-transaction detail with sku + supplier via SQL.

Reads: catalog.csv, transactions.csv (retail), b2b_details.csv (B2B).
Displays sku and supplier_name FROM the transaction's own baked fields
(no lookup) for BOTH retail and b2b.
"""
import csv
import sqlite3
from pathlib import Path


CATALOG_SCHEMA = """
CREATE TABLE catalog (
    product_id TEXT, sku TEXT, product_name TEXT, supplier_id TEXT,
    royalty_pct REAL, royalty_fixed_usd REAL, effective_from TEXT
)"""

SUPPLIERS_SCHEMA = """
CREATE TABLE suppliers (
    supplier_id TEXT, supplier_name TEXT, supplier_currency TEXT
)"""

TXN_SCHEMA = """
CREATE TABLE transactions (
    transaction_id TEXT, product_id TEXT, sku TEXT, supplier_name TEXT,
    sale_date TEXT, revenue_gross_usd REAL, royalty_amount_usd REAL,
    transaction_fee_usd REAL, affiliate_commission_usd REAL,
    status TEXT, promo_id TEXT, bundle_name TEXT
)"""

B2B_SCHEMA = """
CREATE TABLE b2b_details (
    b2b_txn_id TEXT, product_id TEXT, sku TEXT, supplier_name TEXT,
    sale_date TEXT, unit_count INTEGER, unit_price_usd REAL,
    revenue_gross_usd REAL, royalty_pct REAL, royalty_fixed_usd REAL,
    status TEXT
)"""

PROMOTIONS_SCHEMA = """
CREATE TABLE promotions (
    promo_id TEXT, promo_name TEXT, start_date TEXT, end_date TEXT, discount_pct REAL
)"""

DISCOUNTS_SCHEMA = """
CREATE TABLE product_discounts (
    product_id TEXT, discount_pct REAL, valid_from TEXT, valid_until TEXT
)"""


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


def to_int(v):
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def init_db(here: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(CATALOG_SCHEMA)
    conn.execute(SUPPLIERS_SCHEMA)
    conn.execute(TXN_SCHEMA)
    conn.execute(B2B_SCHEMA)
    conn.execute(PROMOTIONS_SCHEMA)
    conn.execute(DISCOUNTS_SCHEMA)

    for r in load_csv(here / "catalog.csv"):
        conn.execute("INSERT INTO catalog VALUES (?,?,?,?,?,?,?)", (
            r["product_id"], r["sku"], r["product_name"], r["supplier_id"],
            to_num(r.get("royalty_pct")), to_num(r.get("royalty_fixed_usd")),
            r["effective_from"]))
    for r in load_csv(here / "suppliers.csv"):
        conn.execute("INSERT INTO suppliers VALUES (?,?,?)", (
            r["supplier_id"], r["supplier_name"], r.get("supplier_currency", "USD")))
    for r in load_csv(here / "transactions.csv"):
        conn.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            r["transaction_id"], r["product_id"], r["sku"], r["supplier_name"],
            r["sale_date"], to_num(r.get("revenue_gross_usd")),
            to_num(r.get("royalty_amount_usd")),
            to_num(r.get("transaction_fee_usd")), to_num(r.get("affiliate_commission_usd")),
            r.get("status", "COMPLETE"), r.get("promo_id", ""), r.get("bundle_name", "")))
    for r in load_csv(here / "b2b_details.csv"):
        conn.execute("INSERT INTO b2b_details VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            r["b2b_txn_id"], r["product_id"], r["sku"], r["supplier_name"],
            r["sale_date"], to_int(r.get("unit_count")), to_num(r.get("unit_price_usd")),
            to_num(r.get("revenue_gross_usd")),
            to_num(r.get("royalty_pct")), to_num(r.get("royalty_fixed_usd")),
            r.get("status", "COMPLETE")))
    for r in load_csv(here / "promotions.csv"):
        conn.execute("INSERT INTO promotions VALUES (?,?,?,?,?)", (
            r["promo_id"], r["promo_name"], r["start_date"], r["end_date"],
            to_num(r.get("discount_pct"))))
    for r in load_csv(here / "product_discounts.csv"):
        conn.execute("INSERT INTO product_discounts VALUES (?,?,?,?)", (
            r["product_id"], to_num(r.get("discount_pct")),
            r["valid_from"], r["valid_until"]))
    conn.commit()
    return conn


ITEMISED_STATEMENT_SQL = """
WITH catalog_versioned AS (
    SELECT c.product_id, c.sku AS catalog_sku, c.supplier_id AS catalog_supplier_id,
           c.royalty_pct AS catalog_royalty_pct, c.royalty_fixed_usd AS catalog_royalty_fixed_usd,
           c.effective_from AS catalog_effective_from,
           ROW_NUMBER() OVER (PARTITION BY c.product_id ORDER BY c.effective_from DESC) AS row_recency
    FROM catalog c
),
active_catalog AS (
    SELECT * FROM catalog_versioned WHERE row_recency = 1
),
retail_lines AS (
    SELECT
        t.transaction_id AS txn_ref,
        t.sale_date,
        t.sku AS display_sku,
        'retail' AS channel,
        t.supplier_name AS display_supplier_name,
        1 AS units,
        t.revenue_gross_usd,
        (COALESCE(t.transaction_fee_usd, 0) + COALESCE(t.affiliate_commission_usd, 0)) AS deductions_usd,
        COALESCE(
            t.royalty_amount_usd,
            CASE
                WHEN ac.catalog_royalty_fixed_usd IS NOT NULL THEN ac.catalog_royalty_fixed_usd
                WHEN ac.catalog_royalty_pct IS NOT NULL THEN
                    (t.revenue_gross_usd
                     - COALESCE(t.transaction_fee_usd, 0)
                     - COALESCE(t.affiliate_commission_usd, 0)
                    ) * ac.catalog_royalty_pct
                ELSE 0
            END
        ) AS royalty_amount_usd
    FROM transactions t
    LEFT JOIN active_catalog ac
        ON t.product_id = ac.product_id
        AND ac.catalog_effective_from <= t.sale_date
    WHERE t.status = 'COMPLETE'
),
b2b_lines AS (
    SELECT
        b.b2b_txn_id AS txn_ref,
        b.sale_date,
        b.sku AS display_sku,
        'b2b' AS channel,
        b.supplier_name AS display_supplier_name,
        b.unit_count AS units,
        b.revenue_gross_usd,
        0.0 AS deductions_usd,
        CASE
            WHEN b.royalty_fixed_usd IS NOT NULL THEN b.royalty_fixed_usd * b.unit_count
            WHEN b.royalty_pct IS NOT NULL THEN b.revenue_gross_usd * b.royalty_pct
            ELSE 0
        END AS royalty_amount_usd
    FROM b2b_details b
    WHERE b.status = 'COMPLETE'
),
unioned AS (
    SELECT * FROM retail_lines UNION ALL SELECT * FROM b2b_lines
)
SELECT
    txn_ref,
    sale_date,
    display_sku AS sku,
    channel,
    display_supplier_name AS supplier_name,
    units,
    ROUND(revenue_gross_usd, 2) AS revenue_gross_usd,
    ROUND(deductions_usd, 2) AS deductions_usd,
    ROUND(royalty_amount_usd, 2) AS royalty_amount_usd
FROM unioned
ORDER BY sale_date, txn_ref;
"""


def main():
    here = Path(__file__).parent
    conn = init_db(here)
    cursor = conn.execute(ITEMISED_STATEMENT_SQL)
    columns = [d[0] for d in cursor.description]
    print(",".join(columns))
    for row in cursor.fetchall():
        vals = []
        for c in columns:
            v = row[c]
            if isinstance(v, float):
                vals.append(f"{v:.2f}")
            elif v is None:
                vals.append("")
            elif isinstance(v, str) and "," in v:
                vals.append(f'"{v}"')
            else:
                vals.append(str(v))
        print(",".join(vals))
    conn.close()


if __name__ == "__main__":
    main()
