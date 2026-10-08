import pytest

"""The deployed model and inference use the attached pre-purchase DSR feature."""

import joblib

from housing_app.prep import MODEL_DIR, NUM_FEATURES, load_purchases, user_frame
from housing_app.recommender import Recommender
from housing_app.source_data import load_sources, load_detail_sources
from housing_app.housing_repository import HousingRepository

pytestmark = pytest.mark.data


def test_existing_debt_reaches_deployed_model():
    data = load_purchases()
    assert "pre_dsr" in NUM_FEATURES
    assert (data.existing_pay > 0).any()
    assert (data.loc[data.existing_pay > 0, "pre_dsr"] > 0).all()

    deployed = joblib.load(MODEL_DIR / "home_loan_models.joblib")
    assert all(
        "pre_dsr" in deployed[target].feature_names_in_
        for target in ("combo", "mort_ltv", "cl_ratio")
    )
    engine = Recommender()
    u = user_frame(70e6, 100e6, 2.5e6, 500e6, 59, 31, "서울특별시", engine.cats, 1e6)
    assert u.pre_dsr.iloc[0] == 12e6 / 70e6


def test_supplied_csv_reaches_customer_and_loan_tables():
    homes, loans = load_sources()
    repo = HousingRepository()
    customer = repo.query("SELECT * FROM customers WHERE customer_id=1").iloc[0]
    source = homes[homes.customer_id == 1].iloc[0]
    assert customer.sido == source.sido
    assert customer.sigungu == source.sigungu
    assert customer.purchase_reference_price == source.purchase_reference_price
    assert len(repo.customer_loans(1)) == len(loans[loans.customer_id == 1])


def test_customer_and_property_exports_reach_serving_database():
    homes, _ = load_sources()
    customers, details = load_detail_sources(homes)
    repo = HousingRepository()
    customer = repo.query("SELECT * FROM customers WHERE customer_id=3").iloc[0]
    source_customer = customers[customers.customer_id == 3].iloc[0]
    assert customer.cf_months == source_customer.cf_months == 12
    assert customer.occupation == source_customer.occupation
    detail = repo.query("SELECT * FROM real_estate_detail WHERE customer_id=3").iloc[0]
    source_detail = details[details.customer_id == 3].iloc[0]
    assert detail.reference_trade_id == source_detail.reference_trade_id
    assert detail.floor == source_detail.floor
    assert (
        repo.query("SELECT count(DISTINCT reference_trade_id) AS n FROM apartment_trades").iloc[0].n
        == details.reference_trade_id.nunique()
    )
