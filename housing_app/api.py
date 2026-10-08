"""HTTP interface over the imported customer and housing data."""

import json
import math
from dataclasses import replace
from functools import lru_cache
from uuid import UUID

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from housing_app.finance import (
    Buyer, LIMIT_MONTHLY_SURPLUS, SAFE_DSR_FACTOR, affordability_bands,
    candidates, financing, limit_buyer, max_affordable, stable_buyer,
)
from housing_app.housing_repository import HousingRepository
from housing_app.naver_maps import cached_markers
from housing_app.prep import user_frame
from housing_app.recommender import FEATURES, Recommender
from housing_app.regions import normalize_region
from housing_app.settings import BASE, Settings


class BuyerInput(BaseModel):
    age: int = Field(31, ge=20, le=79)
    income: float = Field(70_000_000, gt=0)
    assets: float = Field(100_000_000, ge=0)
    other_funds: float = Field(0, ge=0)
    consumption: float = Field(2_500_000, ge=0)
    price: float = Field(500_000_000, gt=0)
    area: float = Field(59, gt=0, le=270)
    sido: str = Field("서울특별시", min_length=1, max_length=30)
    sigungu: str = Field("노원구", min_length=1, max_length=30)
    existing_payment: float = Field(0, ge=0)
    reserve: float = Field(0, ge=0)
    cost_rate: float = Field(0.04, ge=0, le=0.3)
    ltv_cap: float = Field(0.7, gt=0, le=1)
    dsr_cap: float = Field(0.4, gt=0, le=1)
    mortgage_rate: float = Field(4.5, ge=0, le=25)
    term: int = Field(30, ge=1, le=50)
    allow_credit: bool = False
    credit_rate: float = Field(7, ge=0, le=25)
    credit_cap_ratio: float = Field(0.12, ge=0, le=0.3)
    area_tolerance: float = Field(0.2, ge=0, le=1)
    min_year: int = Field(2022, ge=2018, le=2026)
    max_results: int = Field(3, ge=1, le=10)
    target_surplus: float = Field(1_000_000, ge=0)

    def buyer(self) -> Buyer:
        return Buyer(**self.model_dump())


class ChatRequest(BaseModel):
    buyer: BuyerInput
    thread_id: UUID
    message: str = Field(min_length=1, max_length=4000)


class MapSelection(BaseModel):
    complex_ids: list[str] = Field(default_factory=list, max_length=30)
    customer_id: int | None = Field(default=None, gt=0)


@lru_cache(maxsize=1)
def repository() -> HousingRepository:
    return HousingRepository(Settings().database_path)


@lru_cache(maxsize=1)
def patterns() -> Recommender:
    return Recommender()


def clean(value):
    """Convert pandas/numpy values to strict JSON without leaking NaN into responses."""
    if isinstance(value, pd.DataFrame):
        return json.loads(value.to_json(orient="records", date_format="iso"))
    if isinstance(value, pd.Series):
        return clean(value.to_dict())
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def require_region(sido: str, sigungu: str):
    if sigungu not in repository().regions().get(sido, []):
        raise HTTPException(status_code=400, detail="DB에 없는 시·군·구입니다.")


def validated_buyer(data: BuyerInput):
    require_region(data.sido, data.sigungu)
    return model_buyer(data.buyer())


def model_buyer(buyer: Buyer) -> Buyer:
    """Predict loan ratios for a purchase at the stable-band ceiling and use them everywhere.

    The ceiling depends on the ratios, so re-predict at the new ceiling until it settles.
    Without a stable band, fall back to the buyer's own price.
    """
    anchored = predicted_ratios(buyer, buyer.price)
    for _ in range(5):
        safe = affordability_bands(anchored)["safe"]
        if safe < 1:
            return predicted_ratios(buyer, buyer.price)
        if abs(safe - anchored.model_basis_price) < 10_000:
            break
        anchored = predicted_ratios(buyer, safe)
    return anchored


def predicted_ratios(buyer: Buyer, price: float) -> Buyer:
    """Saved regressors' loan ratios for buying at ``price``, capped by the assumptions."""
    engine = patterns()
    frame = user_frame(
        buyer.income, buyer.assets, buyer.consumption, price, buyer.area,
        buyer.age, buyer.sido, engine.cats, buyer.existing_payment,
    )
    mortgage_ratio = float(engine.models["mort_ltv"].predict(frame[FEATURES])[0])
    credit_ratio = float(engine.models["cl_ratio"].predict(frame[FEATURES])[0])
    if not math.isfinite(mortgage_ratio) or not math.isfinite(credit_ratio):
        raise HTTPException(status_code=503, detail="학습 모델의 대출 예측값이 유효하지 않습니다.")
    return replace(
        buyer,
        model_mortgage_ratio=max(0.0, min(mortgage_ratio, buyer.ltv_cap)),
        model_credit_ratio=max(0.0, min(credit_ratio, buyer.credit_cap_ratio)),
        model_basis_price=price,
    )


app = FastAPI(title="내 집 마련 API", version="1.0.0")

@app.get("/api/health")
def health():
    return {"status": "ok", "database": Settings().database_path.is_file()}


@app.get("/api/meta")
def meta():
    settings = Settings()
    return {
        "regions": repository().regions(),
        "defaults": BuyerInput().model_dump(),
        "model": settings.main_model,
        "openai_ready": bool(settings.openai_api_key.get_secret_value()),
        "naver_client_id": settings.naver_maps_client_id,
        "synthetic": False,
    }


@app.get("/api/regions/summary")
def region_summary():
    return clean(repository().summary())


@app.get("/api/trades")
def trades(
    sido: str, sigungu: str, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200)
):
    require_region(sido, sigungu)
    frame = repository().trades(sido, sigungu)
    return {"total": len(frame), "rows": clean(frame.iloc[offset : offset + limit])}


@app.get("/api/customers")
def customers(
    sido: str, sigungu: str, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200)
):
    require_region(sido, sigungu)
    frame = repository().customers(sido, sigungu)
    return {"total": len(frame), "rows": clean(frame.iloc[offset : offset + limit])}


@app.get("/api/customers/{customer_id}/loans")
def customer_loans(customer_id: int):
    if customer_id < 0:
        raise HTTPException(status_code=400, detail="고객 ID를 확인하세요.")
    return clean(repository().customer_loans(customer_id))


@app.get("/api/demo-customers")
def demo_customers(q: str = Query("", max_length=20), limit: int = Query(30, ge=1, le=100)):
    """Search all supplied customer profiles by their source name or customer ID."""
    where = "WHERE p.name LIKE ? OR CAST(p.customer_id AS TEXT) LIKE ?" if q else ""
    params = (f"%{q}%", f"{q}%", limit) if q else (limit,)
    order = ("CASE WHEN p.customer_id IN (68729,77193,6507,2098) THEN 0 ELSE 1 END, "
             "p.customer_id" if q and not q.isdigit() else "p.customer_id")
    rows = repository().query(
        "SELECT p.customer_id,p.name AS display_name,p.age,p.household_size "
        f"FROM customer_profiles p {where} ORDER BY {order} LIMIT ?", params,
    )
    return clean(rows)


@app.get("/api/demo-customers/{customer_id}")
def demo_customer(customer_id: int):
    profile = repository().query(
        "SELECT p.customer_id,p.name,p.age,p.region,p.household_size,p.household_annual_income,"
        "p.financial_assets_estimated,p.monthly_consumption_budget,"
        "d.monthly_debt_service,d.is_home_owner,d.personal_loan_balance,"
        "d.credit_line_balance,d.mortgage_balance "
        "FROM customer_profiles p JOIN customer_debt_summary d ON d.customer_id=p.customer_id "
        "WHERE p.customer_id=? LIMIT 1", (customer_id,),
    )
    if profile.empty:
        raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")
    source = profile.iloc[0]
    frame = repository().query(
        "SELECT customer_id,age,household_annual_income,financial_assets_estimated,"
        "avg_monthly_consumption,monthly_debt_service,is_home_owner,cf_months,"
        "sido,sigungu,exclusive_area_m2,purchase_reference_price "
        "FROM customers WHERE customer_id=? LIMIT 1",
        (customer_id,),
    )
    accounts = repository().query(
        "SELECT account_type,balance,status FROM accounts WHERE customer_id=? ORDER BY account_id",
        (customer_id,),
    )
    account_balance_total = float(accounts.loc[accounts.status == "ACTIVE", "balance"].sum())
    if frame.empty:
        sido, _ = normalize_region(source.region, "")
        customer = {
            "customer_id": customer_id, "name": source["name"], "age": source.age,
            "household_annual_income": source.household_annual_income,
            "financial_assets_estimated": source.financial_assets_estimated,
            "account_balance_total": account_balance_total,
            "avg_monthly_consumption": source.monthly_consumption_budget,
            "monthly_debt_service": source.monthly_debt_service,
            "is_home_owner": source.is_home_owner, "cf_months": None,
            "sido": sido, "sigungu": None, "exclusive_area_m2": None,
            "purchase_reference_price": None, "consumption_source": "budget",
            "residence_region": source.region,
        }
        debts = [
            {"loan_type": label + " 잔액(요약)", "outstanding_balance": source[key],
             "monthly_payment_estimated": None}
            for key, label in (("personal_loan_balance", "개인 대출"),
                               ("credit_line_balance", "한도대출"),
                               ("mortgage_balance", "주택담보대출"))
            if source[key] > 0
        ]
        return clean({"customer": customer, "loans": debts, "property": None,
                      "accounts": accounts})
    loans = repository().query(
        "SELECT loan_type,outstanding_balance,monthly_payment_estimated "
        "FROM loans_raw WHERE customer_id=? ORDER BY loan_id",
        (customer_id,),
    )
    property_detail = repository().query(
        "SELECT real_asset_id,apt_name,exclusive_area_m2,floor,build_year,"
        "reference_deal_date,purchase_reference_price,reference_trade_id "
        "FROM real_estate_detail WHERE customer_id=? LIMIT 1",
        (customer_id,),
    )
    customer = frame.iloc[0].to_dict()
    customer.update(name=source["name"], residence_region=source.region,
                    consumption_source="observed", account_balance_total=account_balance_total)
    return clean({"customer": customer, "loans": loans, "accounts": accounts,
                  "property": property_detail.iloc[0].to_dict() if not property_detail.empty else None})


@app.post("/api/recommendations")
def recommendations(data: BuyerInput):
    buyer = validated_buyer(data)
    return clean(candidates(repository(), buyer))


@app.post("/api/plan")
def plan(data: BuyerInput):
    buyer = validated_buyer(data)
    bands = affordability_bands(buyer)
    safe_plan = financing(stable_buyer(buyer), bands["safe"], enforce_price_cap=False) if bands["safe"] >= 1 else None
    binding_reasons = financing(limit_buyer(buyer), max(bands["maximum"] + 1_000_000, 1), enforce_price_cap=False)["reasons"]
    return clean(
        {
            "plan": financing(buyer, buyer.price),
            "safe_plan": safe_plan,
            "max_affordable": max_affordable(buyer),
            "bands": bands,
            "binding_reasons": binding_reasons,
            "band_assumptions": {
                "safe_dsr_cap": buyer.dsr_cap * SAFE_DSR_FACTOR,
                "possible_dsr_cap": buyer.dsr_cap,
                "limit_monthly_surplus": LIMIT_MONTHLY_SURPLUS,
                "limit_uses_model_loan_cap": False,
            },
        }
    )


@app.post("/api/explore")
def explore(data: BuyerInput):
    """Return all scoped complex references for the mobile list, including unaffordable ones."""
    buyer = validated_buyer(data)
    frame = repository().trades(buyer.sido, buyer.sigungu)
    frame = frame[
        (frame.purchase_year >= buyer.min_year)
        & frame.exclusive_area_m2.between(
            buyer.area * (1 - buyer.area_tolerance),
            buyer.area * (1 + buyer.area_tolerance),
        )
    ]
    if frame.empty:
        return {"total": 0, "rows": []}
    frame = frame.drop_duplicates("complex_id", keep="first")
    bands = affordability_bands(buyer)
    rows = []
    for row in frame.to_dict("records"):
        if row["build_year"] is not None and row["build_year"] > row["purchase_year"]:
            continue
        price = float(row["purchase_reference_price"])
        scenario = limit_buyer(buyer) if bands["possible"] < price <= bands["maximum"] else buyer
        basis = "limit_scenario" if scenario is not buyer else None
        row["plan"] = financing(scenario, price, enforce_price_cap=False, loan_basis=basis)
        row["stress_plan"] = financing(replace(scenario, mortgage_rate=scenario.mortgage_rate + 1), price, enforce_price_cap=False, loan_basis=basis)
        rows.append(row)
    rows.sort(key=lambda row: row["purchase_reference_price"])
    return clean({"total": len(rows), "rows": rows})


@app.post("/api/patterns")
def buyer_patterns(data: BuyerInput):
    buyer = validated_buyer(data)
    engine = patterns()
    u = user_frame(
        buyer.income,
        buyer.assets,
        buyer.consumption,
        buyer.price,
        buyer.area,
        buyer.age,
        buyer.sido,
        engine.cats,
        buyer.existing_payment,
    )
    group = engine.similar_group(u)
    description, share, stats = engine.group_summary(group)
    _, probability, _, _, _, _ = engine.predict(data.model_dump(), group)
    result = {
        "description": description,
        "share": share.to_dict(),
        "probability": probability.to_dict(),
        "stats": stats.reset_index(),
        "loan_prediction": None,
    }
    # The same ratios every finance surface uses, shown at the stable-band ceiling.
    safe_price = affordability_bands(buyer)["safe"]
    if safe_price >= 1:
        ratios = buyer.model_mortgage_ratio, buyer.model_credit_ratio
        result["loan_prediction"] = {
            "basis_price": safe_price,
            "mortgage_ratio": ratios[0],
            "credit_ratio": ratios[1],
            "mortgage": safe_price * ratios[0],
            "credit": safe_price * ratios[1],
            "total": safe_price * sum(ratios),
        }
    target = max_affordable(buyer)
    if target >= 30_000_000:
        alternatives = engine.alternatives(u, target, buyer.sido)
        result["alternatives"] = {
            "region_basis": alternatives["region_basis"],
            "regions": alternatives["regions"].reset_index(),
            "price_bands": alternatives["price_bands"].reset_index(),
            "area_bands": alternatives["area_bands"].reset_index(),
        }
    return clean(result)


def map_data(sido: str, sigungu: str, resolve: bool, complex_ids: list[str] | None = None,
             customer_id: int | None = None):
    require_region(sido, sigungu)
    settings = Settings()
    trades = repository().trades(sido, sigungu).drop_duplicates("complex_id")
    if complex_ids is not None:
        wanted = list(dict.fromkeys(complex_ids))
        trades = trades[trades.complex_id.isin(wanted)]
        trades = trades.set_index("complex_id").reindex(wanted).dropna(subset=["apt_name"]).reset_index()
    rows = trades.head(30).to_dict("records")
    if customer_id is not None:
        owned = repository().query(
            "SELECT complex_id,apt_name,address,exclusive_area_m2,purchase_reference_price,"
            "reference_deal_date,build_year,purchase_year,sido,sigungu "
            "FROM housing_customers WHERE customer_id=?",
            (customer_id,),
        )
        if not owned.empty:
            own = owned.iloc[0].to_dict()
            if own["sido"] == sido and own["sigungu"] == sigungu:
                own["is_owned"] = True
                rows.append(own)
    loan_summaries = repository().complex_loans_bulk(row["complex_id"] for row in rows)
    for row in rows:
        row["loan_summary"] = loan_summaries[row["complex_id"]]
    if not settings.naver_maps_client_id:
        return {"markers": [], "missing": len(rows)}
    try:
        markers, missing = cached_markers(rows, settings, resolve)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"좌표 조회 실패: {type(exc).__name__}"
        ) from None
    return clean({"markers": markers, "missing": len(missing)})


@app.get("/api/map")
def map_markers(sido: str, sigungu: str):
    return map_data(sido, sigungu, False)


@app.post("/api/map/resolve")
def map_resolve(sido: str, sigungu: str, selection: MapSelection | None = None):
    return map_data(sido, sigungu, True,
                    selection.complex_ids if selection else None,
                    selection.customer_id if selection else None)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    from housing_app.llm_advisor import chat_async
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    settings = Settings()
    if not settings.openai_api_key.get_secret_value():
        raise HTTPException(status_code=503, detail="OpenAI 키가 설정되지 않았습니다.")
    buyer = validated_buyer(request.buyer)
    result = candidates(repository(), buyer)
    regions = repository().regions()

    def search_region(current_buyer: Buyer, district: str):
        matches = [sido for sido, districts in regions.items() if district in districts]
        if current_buyer.sido in matches:
            sido = current_buyer.sido
        elif len(matches) == 1:
            sido = matches[0]
        else:
            return None
        updated = model_buyer(replace(current_buyer, sido=sido, sigungu=district))
        return updated, candidates(repository(), updated)

    try:
        settings.chat_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        async with AsyncSqliteSaver.from_conn_string(
            str(settings.chat_checkpoint_path)
        ) as checkpointer:
            answer = await chat_async(
                settings,
                buyer,
                result,
                [{"role": "user", "content": request.message}],
                search_region=search_region,
                thread_id=str(request.thread_id),
                checkpointer=checkpointer,
            )
        return clean(answer)
    except Exception as exc:
        # A failed graph run may have written partial tool/assistant messages.
        # Discard this conversation so the next request cannot inherit them.
        if settings.chat_checkpoint_path.is_file():
            try:
                async with AsyncSqliteSaver.from_conn_string(
                    str(settings.chat_checkpoint_path)
                ) as checkpointer:
                    await checkpointer.adelete_thread(str(request.thread_id))
            except Exception:
                pass
        raise HTTPException(status_code=502, detail=f"AI 응답 실패: {type(exc).__name__}") from None


@app.delete("/api/chat/{thread_id}")
async def delete_chat(thread_id: UUID):
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    path = Settings().chat_checkpoint_path
    if not path.is_file():
        return {"deleted": True}
    async with AsyncSqliteSaver.from_conn_string(str(path)) as checkpointer:
        await checkpointer.adelete_thread(str(thread_id))
    return {"deleted": True}


@app.get("/api/validation")
def validation():
    model_report = json.loads(
        (BASE / "reports" / "model_evaluation.json").read_text(encoding="utf-8")
    )
    model_report["evaluation_source"] = "이전 학습 CSV; 현재 제공 CSV는 추론에만 사용"
    return {
        "model": model_report,
        "audit": json.loads((BASE / "reports" / "data_audit.json").read_text(encoding="utf-8")),
    }


FRONTEND = BASE / "frontend" / "dist"
if FRONTEND.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        target = (FRONTEND / path).resolve()
        if path and target.is_file() and target.is_relative_to(FRONTEND.resolve()):
            return FileResponse(target)
        return FileResponse(FRONTEND / "index.html")
