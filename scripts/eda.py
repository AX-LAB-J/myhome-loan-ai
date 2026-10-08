"""Exploratory summary for the currently supplied home and loan CSVs."""

import json

from housing_app.source_data import load_sources, serving_frames
from scripts.audit_data import BASE


def run():
    homes, loans = load_sources()
    housing, trades, _ = serving_frames(homes, loans)
    result = {
        "homes": len(homes), "customers": homes.customer_id.nunique(),
        "loans": len(loans), "reference_trades": len(trades),
        "regions": housing.groupby(["sido", "sigungu"]).size().rename("customers").reset_index().to_dict("records"),
        "loan_types": loans.loan_type.value_counts().to_dict(),
        "purchase_years": homes.purchase_year.value_counts().sort_index().to_dict(),
        "mortgage_rate_median": float(homes.mortgage_rate.median()),
        "purchase_price_median": float(homes.purchase_reference_price.median()),
        "financial_assets_median": float(homes.financial_assets_estimated.median()),
    }
    (BASE / "reports" / "eda_current.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in result.items() if key != "regions"}, ensure_ascii=False))


if __name__ == "__main__":
    run()
