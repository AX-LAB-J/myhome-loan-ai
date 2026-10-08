import pytest
from fastapi.testclient import TestClient

from housing_app.api import app
from housing_app.housing_repository import HousingRepository

pytestmark = pytest.mark.data


client = TestClient(app)


def test_customer_picker_and_detail_stay_on_selected_id():
    rows = client.get("/api/demo-customers", params={"q": "1"}).json()
    assert rows and all(str(row["customer_id"]).startswith("1") for row in rows)
    selected_id = rows[0]["customer_id"]
    detail = client.get(f"/api/demo-customers/{selected_id}").json()
    assert detail["customer"]["customer_id"] == selected_id
    assert client.get("/api/demo-customers/-1").status_code == 404


def test_plan_bands_use_the_same_cashflow_as_safe_plan():
    buyer = client.get("/api/meta").json()["defaults"]
    response = client.post("/api/plan", json=buyer)
    assert response.status_code == 200
    result = response.json()
    bands = result["bands"]
    assert 0 <= bands["safe"] <= bands["possible"] <= bands["maximum"]
    if result["safe_plan"] is not None:
        assert result["safe_plan"]["surplus"] + 0.01 >= buyer["target_surplus"]


def test_financial_bands_do_not_stop_at_preferred_price():
    buyer = client.get("/api/meta").json()["defaults"]
    buyer.update(price=100_000_000, assets=300_000_000, income=100_000_000)
    result = client.post("/api/plan", json=buyer).json()
    assert result["bands"]["safe"] > buyer["price"]
    assert result["bands"]["safe"] <= result["bands"]["possible"] <= result["bands"]["maximum"]


def test_customer_three_bands_use_distinct_stable_possible_and_limit_scenarios():
    customer = client.get("/api/demo-customers/3").json()["customer"]
    buyer = client.get("/api/meta").json()["defaults"]
    buyer.update(
        age=customer["age"],
        income=customer["household_annual_income"],
        assets=customer["financial_assets_estimated"],
        consumption=customer["avg_monthly_consumption"],
        existing_payment=customer["monthly_debt_service"],
        price=customer["purchase_reference_price"],
        area=customer["exclusive_area_m2"],
        sido=customer["sido"],
        sigungu=customer["sigungu"],
    )
    result = client.post("/api/plan", json=buyer).json()
    bands = result["bands"]
    assert bands["safe"] < bands["possible"] < bands["maximum"]
    assert result["band_assumptions"]["safe_dsr_cap"] == pytest.approx(0.35)
    assert result["band_assumptions"]["possible_dsr_cap"] == 0.4
    assert result["band_assumptions"]["limit_monthly_surplus"] == 100_000
    assert result["plan"]["loan_basis"] == "trained_model"
    assert 0 <= result["plan"]["model_mortgage_ratio"] <= buyer["ltv_cap"]
    assert result["safe_plan"]["surplus"] > buyer["target_surplus"]
    assert result["safe_plan"]["dsr"] <= result["band_assumptions"]["safe_dsr_cap"] + 1e-12
    exploration = client.post("/api/explore", json=buyer).json()
    limit_rows = [
        row
        for row in exploration["rows"]
        if bands["possible"] < row["purchase_reference_price"] <= bands["maximum"]
    ]
    assert limit_rows
    assert all(row["plan"]["loan_basis"] == "limit_scenario" for row in limit_rows)


def test_customer_thirteen_seven_point_two_billion_is_possible_not_stable():
    customer = client.get("/api/demo-customers/13").json()["customer"]
    buyer = client.get("/api/meta").json()["defaults"]
    buyer.update(
        age=customer["age"],
        income=customer["household_annual_income"],
        assets=customer["financial_assets_estimated"],
        consumption=customer["avg_monthly_consumption"],
        existing_payment=customer["monthly_debt_service"],
        price=customer["purchase_reference_price"],
        area=customer["exclusive_area_m2"],
        sido=customer["sido"],
        sigungu=customer["sigungu"],
    )
    result = client.post("/api/plan", json=buyer).json()
    bands = result["bands"]
    assert 640_000_000 < bands["safe"] < 650_000_000
    assert 720_000_000 < bands["possible"] < 725_000_000
    assert 975_000_000 < bands["maximum"] < 985_000_000


def test_explore_respects_area_and_transaction_year():
    buyer = client.get("/api/meta").json()["defaults"]
    result = client.post("/api/explore", json=buyer).json()
    assert result["total"] == len(result["rows"])
    assert all(row["purchase_year"] >= buyer["min_year"] for row in result["rows"])
    assert all(
        buyer["area"] * (1 - buyer["area_tolerance"])
        <= row["exclusive_area_m2"]
        <= buyer["area"] * (1 + buyer["area_tolerance"])
        for row in result["rows"]
    )
    for row in result["rows"][:10]:
        assert row["stress_plan"]["mortgage"] == row["plan"]["mortgage"]
        assert row["stress_plan"]["credit"] == row["plan"]["credit"]
        assert row["stress_plan"]["payment"] >= row["plan"]["payment"]


def test_map_loan_summary_batch_matches_single_complex_query():
    repo = HousingRepository()
    ids = repo.trades("서울특별시", "노원구").complex_id.drop_duplicates().head(3).tolist()
    bulk = repo.complex_loans_bulk(ids)
    for complex_id in ids:
        single = repo.complex_loans(complex_id)
        assert bulk[complex_id]["customers"] == single["customers"]
        assert bulk[complex_id]["original"] == single["original"]
        assert bulk[complex_id]["balance"] == single["balance"]
