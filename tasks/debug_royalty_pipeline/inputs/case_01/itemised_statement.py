"""Itemised statement — per-transaction detail via SQL over multiple tables.

Reads: catalog.csv, suppliers.csv (JOIN target for catalog side only),
       transactions.csv, promotions.csv, product_discounts.csv
Runs a multi-CTE SQL query and prints one row per transaction.

Data flow (relevant to how supplier_name and sku are resolved):
- The catalog+suppliers JOIN is available in the CTEs but is used ONLY for
  royalty term lookup on retail channel transactions.
- The transaction's own baked `supplier_name` field is what's displayed in
  the itemised output -- NOT the resolved name from the catalog+suppliers
  JOIN.
- The transaction's own baked `sku` field is what's displayed for SKU.
"""
import csv
import sqlite3
from pathlib import Path


CATALOG_SCHEMA = """
CREATE TABLE catalog (
    product_id TEXT,
    sku TEXT,
    product_name TEXT,
    supplier_id TEXT,
    royalty_pct REAL,
    royalty_fixed_usd REAL,
    effective_from TEXT
)"""

SUPPLIERS_SCHEMA = """
CREATE TABLE suppliers (
    supplier_id TEXT,
    supplier_name TEXT,
    supplier_currency TEXT
)"""

TXN_SCHEMA = """
CREATE TABLE transactions (
    transaction_id TEXT,
    product_id TEXT,
    channel TEXT,
    sku TEXT,
    supplier_name TEXT,
    sale_date TEXT,
    revenue_gross_usd REAL,
    transaction_fee_usd REAL,
    affiliate_commission_usd REAL,
    status TEXT,
    promo_id TEXT,
    bundle_name TEXT,
    royalty_pct REAL,
    royalty_fixed_usd REAL
)"""

PROMOTIONS_SCHEMA = """
CREATE TABLE promotions (
    promo_id TEXT,
    promo_name TEXT,
    start_date TEXT,
    end_date TEXT,
    discount_pct REAL
)"""

DISCOUNTS_SCHEMA = """
CREATE TABLE product_discounts (
    product_id TEXT,
    discount_pct REAL,
    valid_from TEXT,
    valid_until TEXT
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


def init_db(here: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(CATALOG_SCHEMA)
    conn.execute(SUPPLIERS_SCHEMA)
    conn.execute(TXN_SCHEMA)
    conn.execute(PROMOTIONS_SCHEMA)
    conn.execute(DISCOUNTS_SCHEMA)

    for r in load_csv(here / "catalog.csv"):
        conn.execute(
            "INSERT INTO catalog VALUES (?,?,?,?,?,?,?)",
            (r["product_id"], r["sku"], r["product_name"], r["supplier_id"],
             to_num(r.get("royalty_pct")), to_num(r.get("royalty_fixed_usd")),
             r["effective_from"]),
        )
    for r in load_csv(here / "suppliers.csv"):
        conn.execute(
            "INSERT INTO suppliers VALUES (?,?,?)",
            (r["supplier_id"], r["supplier_name"], r.get("supplier_currency", "USD")),
        )
    for r in load_csv(here / "transactions.csv"):
        conn.execute(
            "INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["transaction_id"], r["product_id"], r["channel"], r["sku"],
             r["supplier_name"], r["sale_date"], to_num(r.get("revenue_gross_usd")),
             to_num(r.get("transaction_fee_usd")), to_num(r.get("affiliate_commission_usd")),
             r.get("status", "COMPLETE"), r.get("promo_id", ""), r.get("bundle_name", ""),
             to_num(r.get("royalty_pct")), to_num(r.get("royalty_fixed_usd"))),
        )
    for r in load_csv(here / "promotions.csv"):
        conn.execute(
            "INSERT INTO promotions VALUES (?,?,?,?,?)",
            (r["promo_id"], r["promo_name"], r["start_date"], r["end_date"],
             to_num(r.get("discount_pct"))),
        )
    for r in load_csv(here / "product_discounts.csv"):
        conn.execute(
            "INSERT INTO product_discounts VALUES (?,?,?,?)",
            (r["product_id"], to_num(r.get("discount_pct")), r["valid_from"], r["valid_until"]),
        )
    conn.commit()
    return conn


ITEMISED_STATEMENT_SQL = """
WITH catalog_versioned AS (
    SELECT
        c.product_id,
        c.sku AS catalog_sku,
        c.product_name,
        c.supplier_id AS catalog_supplier_id,
        s.supplier_name AS resolved_supplier_name,
        c.royalty_pct AS catalog_royalty_pct,
        c.royalty_fixed_usd AS catalog_royalty_fixed_usd,
        c.effective_from AS catalog_effective_from,
        ROW_NUMBER() OVER (
            PARTITION BY c.product_id
            ORDER BY c.effective_from DESC
        ) AS row_recency
    FROM catalog c
    JOIN suppliers s ON c.supplier_id = s.supplier_id
),
active_catalog AS (
    SELECT * FROM catalog_versioned WHERE row_recency = 1
),
per_txn AS (
    SELECT
        t.transaction_id,
        t.sale_date,
        t.sku AS display_sku,
        t.channel,
        t.supplier_name AS display_supplier_name,
        t.revenue_gross_usd,
        COALESCE(t.transaction_fee_usd, 0) AS transaction_fee_usd,
        COALESCE(t.affiliate_commission_usd, 0) AS affiliate_commission_usd,
        t.status,
        t.promo_id,
        t.bundle_name,
        t.royalty_pct AS baked_royalty_pct,
        t.royalty_fixed_usd AS baked_royalty_fixed_usd,
        ac.catalog_royalty_pct,
        ac.catalog_royalty_fixed_usd,
        pr.promo_name,
        pd.discount_pct AS product_discount_pct
    FROM transactions t
    LEFT JOIN active_catalog ac
        ON t.product_id = ac.product_id
        AND ac.catalog_effective_from <= t.sale_date
    LEFT JOIN promotions pr
        ON t.promo_id = pr.promo_id
        AND t.sale_date BETWEEN pr.start_date AND pr.end_date
    LEFT JOIN product_discounts pd
        ON t.product_id = pd.product_id
        AND t.sale_date BETWEEN pd.valid_from AND pd.valid_until
    WHERE t.status = 'COMPLETE'
)
SELECT
    transaction_id,
    sale_date,
    display_sku AS sku,
    channel,
    display_supplier_name AS supplier_name,
    ROUND(revenue_gross_usd, 2) AS revenue_gross_usd,
    ROUND((transaction_fee_usd + affiliate_commission_usd), 2) AS deductions_usd,
    ROUND(
        CASE
            WHEN channel = 'b2b' AND baked_royalty_fixed_usd IS NOT NULL
                THEN baked_royalty_fixed_usd
            WHEN channel = 'b2b' AND baked_royalty_pct IS NOT NULL
                THEN revenue_gross_usd * baked_royalty_pct
            WHEN catalog_royalty_fixed_usd IS NOT NULL
                THEN catalog_royalty_fixed_usd
            WHEN catalog_royalty_pct IS NOT NULL
                THEN revenue_gross_usd * catalog_royalty_pct
            ELSE 0
        END,
        2
    ) AS royalty_amount_usd,
    CASE
        WHEN bundle_name IS NOT NULL AND bundle_name != '' THEN 'Bundle'
        WHEN promo_name IS NOT NULL AND promo_name != '' THEN 'Promo'
        ELSE ''
    END AS promo_flag,
    COALESCE(bundle_name, promo_name, '') AS bundle_or_promo_name
FROM per_txn
ORDER BY sale_date, transaction_id;
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
