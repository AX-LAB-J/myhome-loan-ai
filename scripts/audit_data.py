"""Validate purchaser and complete customer CSVs and record their provenance."""

import hashlib
import json
from pathlib import Path

import numpy as np

from housing_app.source_data import (
    load_sources,
    load_detail_sources,
    load_customer_supplements,
    DATA_DIR,
)

BASE = Path(__file__).resolve().parents[1]
RAW = DATA_DIR


def audit():
    homes, loans = load_sources()
    customers, details = load_detail_sources(homes)
    profiles, debts, accounts = load_customer_supplements()
    files = {}
    for name, frame in (
        ("home_purchases", homes),
        ("loans_raw", loans),
        ("customers_preprocessed", customers),
        ("real_estate_detail_preprocessed", details),
        ("customer_financial_profiles", profiles),
        ("customer_debt_summary", debts),
        ("accounts", accounts),
    ):
        path = RAW / f"{name}.csv"
        files[name] = {
            "rows": len(frame),
            "columns": list(frame.columns),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "missing": {key: int(value) for key, value in frame.isna().sum().items() if value},
        }
    checks = {
        "home_ids_unique": not homes.real_asset_id.duplicated().any(),
        "customer_ids_unique": not homes.customer_id.duplicated().any(),
        "loan_ids_unique": not loans.loan_id.duplicated().any(),
        "loan_customers_present": set(loans.customer_id) <= set(homes.customer_id),
        "customer_details_join": len(customers) == len(homes),
        "all_customer_profiles_join": set(customers.customer_id) <= set(profiles.customer_id),
        "all_debts_join": set(debts.customer_id) == set(profiles.customer_id),
        "all_accounts_join": set(accounts.customer_id) == set(profiles.customer_id),
        "real_estate_details_join": len(details) == len(homes),
        "reference_trade_ids_present": bool(details.reference_trade_id.notna().all()),
        "prices_positive": bool((homes.purchase_reference_price > 0).all()),
        "area_positive": bool((homes.exclusive_area_m2 > 0).all()),
        "model_inputs_finite": bool(
            np.isfinite(
                homes[
                    [
                        "purchase_price_est",
                        "exclusive_area_m2",
                        "household_annual_income",
                        "financial_assets_estimated",
                        "avg_monthly_consumption",
                        "age_at_purchase",
                    ]
                ].to_numpy(float)
            ).all()
        ),
    }
    linked = (
        loans[loans.housing_purchase_linked == 1].groupby("customer_id").original_principal.sum()
    )
    checks["purchase_loans_reconcile"] = bool(
        np.allclose(
            homes.total_loan_principal.fillna(0), homes.customer_id.map(linked).fillna(0), atol=0.1
        )
    )
    result = {
        "source_kind": "supplied_csv",
        "files": files,
        "checks": checks,
        "eligible_inference_reference_rows": int(
            (
                (homes.purchase_year >= 2022)
                & (homes.under20_at_purchase == 0)
                & (homes.own_funds_est > 0)
            ).sum()
        ),
        "model_retrained": False,
        "limitations": [
            "Home purchases cover only the purchaser subset; complete profiles include non-owners.",
            "Non-purchaser monthly consumption is a budget, not observed spending.",
            "Non-purchaser region is a province; district and target home are search defaults.",
            "The saved model was trained before this CSV import and was not retrained.",
            "Reference purchases are not current listings or loan approvals.",
        ],
    }
    (BASE / "reports" / "data_audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (BASE / "reports" / "data_audit.md").write_text(
        "# CSV audit\n\n"
        + "\n".join(f"- {key}: {value}" for key, value in checks.items())
        + "\n\n"
        + "\n".join(result["limitations"]),
        encoding="utf-8",
    )
    if not all(checks.values()):
        raise ValueError(f"Supplied CSV audit failed: {checks}")
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False))
