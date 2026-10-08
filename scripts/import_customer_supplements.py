"""Add complete customer, debt and account exports to an existing serving DB."""

import sqlite3

from housing_app.settings import Settings
from housing_app.source_data import load_customer_supplements


def import_supplements():
    profiles, debts, accounts = load_customer_supplements()
    frames = {
        "customer_profiles": profiles,
        "customer_debt_summary": debts,
        "accounts": accounts,
    }
    with sqlite3.connect(Settings().database_path, timeout=30) as db:
        existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "customers" not in existing:
            raise ValueError("Build the existing serving database before importing supplements")
        purchaser_ids = {row[0] for row in db.execute("SELECT customer_id FROM customers")}
        if not purchaser_ids <= set(profiles.customer_id):
            raise ValueError("Existing customers missing from supplied profiles")
        for name, frame in frames.items():
            frame.to_sql(name + "_stage", db, if_exists="replace", index=False, chunksize=1000)
        try:
            db.execute("BEGIN")
            for name in frames:
                db.execute(f"DROP TABLE IF EXISTS {name}")
                db.execute(f"ALTER TABLE {name}_stage RENAME TO {name}")
            db.execute("CREATE UNIQUE INDEX idx_profiles_customer ON customer_profiles(customer_id)")
            db.execute("CREATE UNIQUE INDEX idx_debts_customer ON customer_debt_summary(customer_id)")
            db.execute("CREATE INDEX idx_accounts_customer ON accounts(customer_id)")
            db.commit()
        except Exception:
            db.rollback()
            raise
    return {name: len(frame) for name, frame in frames.items()}


if __name__ == "__main__":
    print(import_supplements())
