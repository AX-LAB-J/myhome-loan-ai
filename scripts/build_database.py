"""Build the serving database from purchaser and complete customer CSVs."""

import json
import os
import sqlite3
import time
from contextlib import closing

from housing_app.source_data import (
    load_sources,
    load_detail_sources,
    load_customer_supplements,
    serving_frames,
)
from scripts.audit_data import audit, BASE


def build():
    audit()
    homes, loans = load_sources()
    customer_source, detail_source = load_detail_sources(homes)
    profiles, debts, accounts = load_customer_supplements()
    if not set(customer_source.customer_id) <= set(profiles.customer_id):
        raise ValueError("Existing home purchasers missing from complete customer profiles")
    housing, trades, customers = serving_frames(homes, loans, customer_source, detail_source)
    details = detail_source.merge(
        housing[["real_asset_id", "address", "sido", "sigungu", "complex_id"]],
        on="real_asset_id",
        validate="one_to_one",
    )
    path = BASE / "data" / "housing.sqlite"
    pending = path.with_suffix(".pending.sqlite")
    pending.unlink(missing_ok=True)
    try:
        with closing(sqlite3.connect(pending)) as db:
            homes.to_sql("home_purchases", db, index=False, chunksize=1000)
            loans.to_sql("loans_raw", db, index=False, chunksize=1000)
            customers.to_sql("customers", db, index=False, chunksize=1000)
            profiles.to_sql("customer_profiles", db, index=False, chunksize=1000)
            debts.to_sql("customer_debt_summary", db, index=False, chunksize=1000)
            accounts.to_sql("accounts", db, index=False, chunksize=1000)
            details.to_sql("real_estate_detail", db, index=False, chunksize=1000)
            housing.to_sql("housing_customers", db, index=False, chunksize=1000)
            trades.to_sql("apartment_trades", db, index=False, chunksize=1000)
            for table in ("housing_customers", "apartment_trades"):
                db.execute(f"CREATE INDEX idx_{table}_region ON {table}(sido,sigungu)")
                db.execute(f"CREATE INDEX idx_{table}_complex ON {table}(complex_id)")
            db.execute("CREATE INDEX idx_loans_customer ON loans_raw(customer_id)")
            db.execute("CREATE INDEX idx_housing_customer ON housing_customers(customer_id)")
            db.execute("CREATE INDEX idx_detail_customer ON real_estate_detail(customer_id)")
            db.execute("CREATE INDEX idx_customers_customer ON customers(customer_id)")
            db.execute(
                "CREATE UNIQUE INDEX idx_profiles_customer ON customer_profiles(customer_id)"
            )
            db.execute(
                "CREATE UNIQUE INDEX idx_debts_customer ON customer_debt_summary(customer_id)"
            )
            db.execute("CREATE INDEX idx_accounts_customer ON accounts(customer_id)")
            db.execute(
                "CREATE TABLE geocode_cache(address TEXT PRIMARY KEY, latitude REAL, longitude REAL, matched_address TEXT, checked_at TEXT)"
            )
            if path.exists():
                with closing(sqlite3.connect(path)) as old:
                    cached = old.execute(
                        "SELECT address,latitude,longitude,matched_address,checked_at FROM geocode_cache"
                    ).fetchall()
                    db.executemany("INSERT INTO geocode_cache VALUES(?,?,?,?,?)", cached)
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert abs(housing.all_balance.sum() - loans.outstanding_balance.sum()) < 0.01
            db.commit()
        for attempt in range(10):
            try:
                os.replace(pending, path)
                break
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(0.5)
    finally:
        if pending.exists():
            pending.unlink()
    result = {
        "customers": len(housing),
        "customer_details": len(customers),
        "all_customer_profiles": len(profiles),
        "accounts": len(accounts),
        "real_estate_details": len(details),
        "loans": len(loans),
        "unique_reference_trades": len(trades),
        "complexes": housing.complex_id.nunique(),
        "original": housing.all_original.sum(),
        "balance": housing.all_balance.sum(),
        "model_retrained": False,
    }
    (BASE / "reports" / "database_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(result)


if __name__ == "__main__":
    build()
