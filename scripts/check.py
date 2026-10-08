"""Read-only readiness check. Never prints configuration values or changes .env."""

import importlib.metadata
import sqlite3
import sys

from housing_app.settings import BASE, Settings
from housing_app.prep import DATA_DIR, MODEL_DIR


def main():
    errors = []
    if sys.version_info[:2] != (3, 12):
        errors.append("Python 3.12 is required for the tested model environment.")
    try:
        settings = Settings()
    except Exception:
        print("FAIL: Invalid configuration. Check variable names/types in .env; values are hidden.")
        return 1
    required = [
        settings.database_path,
        MODEL_DIR / "home_loan_models.joblib",
        DATA_DIR / "home_purchases.csv",
        DATA_DIR / "loans_raw.csv",
        DATA_DIR / "customer_financial_profiles.csv",
        DATA_DIR / "customer_debt_summary.csv",
        DATA_DIR / "accounts.csv",
        BASE / "reports" / "model_evaluation.json",
        BASE / "reports" / "data_audit.json",
        BASE / "frontend" / "dist" / "index.html",
    ]
    for path in required:
        if not path.is_file():
            errors.append("Missing required artifact: " + path.name)
    if settings.database_path.is_file():
        try:
            with sqlite3.connect(
                settings.database_path.resolve().as_uri() + "?mode=ro", uri=True
            ) as db:
                present = {
                    r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
                }
                expected = {"housing_customers", "apartment_trades", "loans_raw", "geocode_cache",
                            "customer_profiles", "customer_debt_summary", "accounts"}
                if not expected <= present:
                    errors.append("Required database tables are missing.")
        except sqlite3.Error:
            errors.append("Database cannot be opened read-only.")
    # Pickled estimators were trained with this version; upgrades require retraining.
    if importlib.metadata.version("scikit-learn") != "1.9.1":
        errors.append("scikit-learn differs from the saved model environment; retrain before use.")
    for error in errors:
        print("FAIL:", error)
    print(
        "OpenAI key:",
        "configured (not authenticated)"
        if settings.openai_api_key.get_secret_value()
        else "not configured",
    )
    print(
        "NAVER keys:",
        "configured (not authenticated)"
        if settings.naver_maps_client_id and settings.naver_maps_client_secret.get_secret_value()
        else "incomplete",
    )
    if not errors:
        print("PASS: Local runtime artifacts ready. No external API requests made.")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
