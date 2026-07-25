CREATE TABLE regions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE stores (
    id INTEGER PRIMARY KEY,
    region_id INTEGER NOT NULL,
    legacy_customer_ref INTEGER,  -- old free-text field from a decommissioned system, NOT a real FK: no constraint is declared on it anywhere, and there is no customers table in this schema at all
    name TEXT
);

ALTER TABLE stores
    ADD CONSTRAINT fk_stores_region
    FOREIGN KEY (region_id) REFERENCES regions(id);

CREATE TABLE sales (
    id INTEGER PRIMARY KEY,
    store_id INTEGER NOT NULL REFERENCES stores(id),
    amount NUMERIC
);
