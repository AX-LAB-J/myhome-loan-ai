"""Adapt the two supplied CSV exports to the app's stable query/model fields."""

import hashlib
import os
from pathlib import Path

import pandas as pd
import numpy as np

from housing_app.regions import normalize_region

DATA_DIR = Path(os.getenv("HOME_LOAN_DATA_DIR", str(Path(__file__).resolve().parents[1] / "data" / "raw")))


def load_customer_supplements():
    """Read the complete customer exports, including customers without a home purchase."""
    profiles = pd.read_csv(DATA_DIR / "customer_financial_profiles.csv", encoding="utf-8-sig", low_memory=False)
    debts = pd.read_csv(DATA_DIR / "customer_debt_summary.csv", encoding="utf-8-sig", low_memory=False)
    accounts = pd.read_csv(DATA_DIR / "accounts.csv", encoding="utf-8-sig", low_memory=False)
    required = (
        (profiles, {"customer_id", "name", "age", "region", "household_size",
                    "household_annual_income", "monthly_consumption_budget", "financial_assets_estimated"}),
        (debts, {"customer_id", "monthly_debt_service", "is_home_owner",
                 "personal_loan_balance", "credit_line_balance", "mortgage_balance"}),
        (accounts, {"account_id", "customer_id", "account_type", "balance"}),
    )
    for frame, columns in required:
        if columns - set(frame):
            raise ValueError(f"Customer supplement missing columns: {sorted(columns - set(frame))}")
        if frame.customer_id.isna().any():
            raise ValueError("Customer supplement has empty customer IDs")
    if profiles.customer_id.duplicated().any() or debts.customer_id.duplicated().any():
        raise ValueError("Customer profiles and debt summaries require unique customer IDs")
    if accounts.account_id.duplicated().any():
        raise ValueError("Account IDs must be unique")
    profile_ids = set(profiles.customer_id)
    if set(debts.customer_id) != profile_ids or set(accounts.customer_id) != profile_ids:
        raise ValueError("Customer supplement IDs differ across profiles, debt and accounts")
    numeric = profiles[["age", "household_annual_income", "monthly_consumption_budget",
                        "financial_assets_estimated"]].to_numpy(float)
    if not np.isfinite(numeric).all() or (numeric[:, 1:] < 0).any():
        raise ValueError("Customer profile financial inputs must be finite and nonnegative")
    if not profiles.name.notna().all() or (profiles.name.astype(str).str.strip() == "").any():
        raise ValueError("Customer names must be present")
    if (debts.monthly_debt_service < 0).any() or (accounts.balance < 0).any():
        raise ValueError("Customer debt payments and account balances must be nonnegative")
    return profiles, debts, accounts


def load_sources():
    homes = pd.read_csv(DATA_DIR / "home_purchases.csv", encoding="utf-8-sig", low_memory=False)
    loans = pd.read_csv(DATA_DIR / "loans_raw.csv", encoding="utf-8-sig", low_memory=False)
    required_home = {
        "real_asset_id", "customer_id", "full_region_name", "sido", "si", "gu", "gun",
        "purchase_reference_price", "purchase_date", "reference_deal_date", "apt_name",
        "exclusive_area_m2", "age", "household_annual_income", "financial_assets_estimated",
        "avg_monthly_consumption", "monthly_debt_service", "purchase_year",
    }
    required_loans = {"loan_id", "customer_id", "original_principal", "outstanding_balance"}
    for label, frame, required in (("home_purchases", homes, required_home), ("loans_raw", loans, required_loans)):
        missing = required - set(frame)
        if missing:
            raise ValueError(f"{label} missing columns: {sorted(missing)}")
    if homes.real_asset_id.duplicated().any() or homes.customer_id.duplicated().any():
        raise ValueError("Home/customer IDs must be unique")
    if loans.loan_id.duplicated().any() or not set(loans.customer_id) <= set(homes.customer_id):
        raise ValueError("Loan IDs must be unique and reference a supplied customer")

    # Province rows use sido+si(+gu/gun); metropolitan rows put the province in si.
    metro = homes.sido.isna()
    region = homes.sido.where(~metro, homes.si)
    district = (
        homes.si.where(~metro, "").fillna("").astype(str)
        + " " + homes.gu.fillna("").astype(str)
        + " " + homes.gun.fillna("").astype(str)
    ).str.strip()
    normalized = [normalize_region(s, d) for s, d in zip(region, district)]
    homes["sido"], homes["sigungu"] = zip(*normalized)
    unknown = homes.sigungu == "확인 불가"
    if unknown.any():
        recovered = [
            normalize_region(s, str(full).split()[1])
            for s, full in zip(homes.loc[unknown, "sido"], homes.loc[unknown, "full_region_name"])
        ]
        homes.loc[unknown, ["sido", "sigungu"]] = recovered
    if (homes.sigungu == "확인 불가").any():
        raise ValueError("Some supplied regions cannot be resolved")
    homes["umd_nm"] = [
        full.removeprefix(f"{province} {district} ").strip()
        for full, province, district in zip(homes.full_region_name, homes.sido, homes.sigungu)
    ]
    # When source names use a legacy province spelling, the final locality is
    # still explicitly present in full_region_name.
    homes.loc[homes.umd_nm == homes.full_region_name, "umd_nm"] = homes.full_region_name.str.split().str[-1]
    homes["purchase_price_est"] = homes.purchase_reference_price
    homes["region_key"] = homes.sido + " " + homes.sigungu
    return homes, loans


def load_detail_sources(homes):
    """Read customer and property exports, rejecting mismatched customer/asset joins."""
    customers = pd.read_csv(DATA_DIR / "customers_preprocessed.csv", encoding="utf-8-sig", low_memory=False)
    details = pd.read_csv(DATA_DIR / "real_estate_detail_preprocessed.csv", encoding="utf-8-sig", low_memory=False)
    required_customers = {"customer_id", "age", "household_annual_income", "financial_assets_estimated",
                          "avg_monthly_consumption", "monthly_debt_service", "is_home_owner", "cf_months"}
    required_details = {"real_asset_id", "customer_id", "reference_trade_id", "apt_name",
                        "exclusive_area_m2", "purchase_reference_price", "reference_deal_date"}
    for label, frame, required in (("customers_preprocessed", customers, required_customers),
                                    ("real_estate_detail_preprocessed", details, required_details)):
        missing = required - set(frame)
        if missing:
            raise ValueError(f"{label} missing columns: {sorted(missing)}")
    if customers.customer_id.duplicated().any() or details.real_asset_id.duplicated().any():
        raise ValueError("Customer and real asset IDs must be unique")
    if set(customers.customer_id) != set(homes.customer_id) or set(details.real_asset_id) != set(homes.real_asset_id):
        raise ValueError("Customer/asset IDs differ from home purchases")
    linked = homes[["real_asset_id", "customer_id", "apt_name", "exclusive_area_m2",
                    "purchase_reference_price", "reference_deal_date"]].merge(
        details[["real_asset_id", "customer_id", "apt_name", "exclusive_area_m2",
                 "purchase_reference_price", "reference_deal_date"]],
        on="real_asset_id", validate="one_to_one", suffixes=("_home", "_detail"))
    for column in ("customer_id", "apt_name", "reference_deal_date"):
        if not linked[column + "_home"].eq(linked[column + "_detail"]).all():
            raise ValueError(f"Real estate detail conflicts on {column}")
    for column in ("exclusive_area_m2", "purchase_reference_price"):
        if not np.allclose(linked[column + "_home"], linked[column + "_detail"], rtol=0, atol=0.01):
            raise ValueError(f"Real estate detail conflicts on {column}")
    finance = homes[["customer_id", "age", "household_annual_income", "financial_assets_estimated",
                     "avg_monthly_consumption", "monthly_debt_service"]].merge(
        customers[["customer_id", "age", "household_annual_income", "financial_assets_estimated",
                   "avg_monthly_consumption", "monthly_debt_service"]],
        on="customer_id", validate="one_to_one", suffixes=("_home", "_customer"))
    for column in ("age", "household_annual_income", "financial_assets_estimated",
                   "avg_monthly_consumption", "monthly_debt_service"):
        if not np.allclose(finance[column + "_home"], finance[column + "_customer"], rtol=0, atol=0.01):
            raise ValueError(f"Customer export conflicts on {column}")
    return customers, details


def serving_frames(homes, loans, customer_source=None, detail_source=None):
    totals = loans.groupby("customer_id").agg(
        all_original=("original_principal", "sum"),
        all_balance=("outstanding_balance", "sum"),
        all_loan_count=("loan_id", "size"),
    )
    homes = homes.join(totals, on="customer_id")
    for col in ("all_original", "all_balance", "all_loan_count"):
        homes[col] = homes[col].fillna(0)
    homes["address"] = homes.full_region_name.astype(str)
    homes["complex_id"] = [
        hashlib.sha256(f"{address}|{name}".encode()).hexdigest()[:20]
        for address, name in zip(homes.address, homes.apt_name)
    ]
    # Each exported home has a reference deal date and price, but no source
    # trade identifier. Identical complex/date/size/price is one reference.
    reference = (
        homes.address.astype(str) + "|" + homes.apt_name.astype(str) + "|"
        + homes.reference_deal_date.astype(str) + "|"
        + homes.exclusive_area_m2.round(3).astype(str) + "|"
        + homes.purchase_reference_price.round(0).astype(str)
    )
    homes["reference_trade_id"] = reference.map(lambda value: hashlib.sha256(value.encode()).hexdigest()[:20])
    if detail_source is not None:
        source_ids = detail_source.set_index("real_asset_id").reference_trade_id
        homes["reference_trade_id"] = homes.real_asset_id.map(source_ids)
        if homes.reference_trade_id.isna().any():
            raise ValueError("Some real estate reference IDs are missing")
    trades = homes.drop_duplicates("reference_trade_id").copy()
    location = homes[["customer_id", "sido", "sigungu", "exclusive_area_m2",
                      "purchase_reference_price"]]
    if customer_source is None:
        customers = homes[["customer_id", "age", "household_size", "household_annual_income",
                           "financial_assets_estimated", "avg_monthly_consumption",
                           "monthly_debt_service", "sido", "sigungu", "exclusive_area_m2",
                           "purchase_reference_price"]].copy()
        customers["is_home_owner"] = 1
        customers["cf_months"] = pd.NA
    else:
        customers = customer_source.merge(location, on="customer_id", validate="one_to_one")
    return homes, trades, customers
