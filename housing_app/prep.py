# =============================================================================
# 공통 데이터 준비 모듈 — 학습(scripts/model_evaluation.py)과 API 서버가 같이 사용
#   - 분석 대상 필터, 광주·전남 시도명 매핑, 파생 변수, 월상환 공식
# =============================================================================
from pathlib import Path
import os

import numpy as np
import pandas as pd
from housing_app.source_data import load_sources

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("HOME_LOAN_DATA_DIR", str(BASE_DIR / "data" / "raw")))
MODEL_DIR = BASE_DIR / "models"

MIN_GROUP = 30  # 화면에 보여줄 집단의 최소 인원
LTV_CAP = 0.70  # 주담대 LTV 상한 (데이터 최대 0.699)
DSR_OK, DSR_WARN = 0.30, 0.40  # DSR 판정: 30% 미만 여유 / 30~40% 주의 / 40% 초과 어려움
CL_EXTRA = 0.003  # 마이너스통장 월상환 = 잔액 × (월금리 + 0.3%)  ← 데이터에서 역산한 공식
CURRENT_YEAR = 2026

# 대출 조합 코드
COMBO_NAMES = {0: "대출 없음", 1: "주담대만", 2: "주담대 + 마이너스통장"}

# 모델·kNN에 쓰는 입력 변수 (사용자가 화면에서 입력하는 항목으로만 구성)
#   금액은 분포가 오른쪽으로 길어서 log 변환
NUM_FEATURES = [
    "age_at_purchase",
    "log_income",
    "log_assets",
    "log_consumption",
    "log_price",
    "exclusive_area_m2",
    "purchase_year",
    "pre_dsr",
]
KNN_FEATURES = [
    "age_at_purchase",
    "log_income",
    "log_assets",
    "log_consumption",
    "log_price",
    "exclusive_area_m2",
]

GWANGJU_GU = {"광산구", "동구", "서구", "남구", "북구"}


def monthly_mortgage(principal, annual_rate_pct, term_years):
    """주담대 월상환액 — 원리금균등 (데이터의 monthly_payment와 오차 0 확인)"""
    r = np.asarray(annual_rate_pct) / 100 / 12
    n = np.asarray(term_years) * 12
    with np.errstate(divide="ignore", invalid="ignore"):
        factor = np.where(r == 0, 1 / n, r / (1 - (1 + r) ** -n))
    return np.asarray(principal) * factor


def monthly_credit_line(principal, annual_rate_pct):
    """마이너스통장 월상환액 — 잔액 × (월금리 + 0.3%) (데이터에서 역산, 오차 0 확인)"""
    return np.asarray(principal) * (np.asarray(annual_rate_pct) / 100 / 12 + CL_EXTRA)


def add_features(df):
    """입력 변수 파생 (학습 데이터와 사용자 입력에 똑같이 적용)"""
    df = df.copy()
    df["log_income"] = np.log(df["household_annual_income"])
    df["log_assets"] = np.log(df["financial_assets_estimated"].clip(lower=1e5))
    df["log_consumption"] = np.log(df["avg_monthly_consumption"].clip(lower=1e4))
    df["log_price"] = np.log(df["purchase_price_est"])
    existing = df["existing_pay"] if "existing_pay" in df else 0.0
    df["pre_dsr"] = existing * 12 / df["household_annual_income"]
    df["sido"] = df["sido"].astype("category")
    return df


def load_purchases():
    """home_purchases + 대출별 금리를 합쳐 분석용 테이블을 만든다"""
    hp, loans = load_sources()

    # 1) 분석 대상: 최근 5년(2022~) 매입, 매입 당시 20세 이상, 자기자금 > 0 (대출>매입가 1건 제외)
    hp = hp[
        (hp.purchase_year >= 2022) & (hp.under20_at_purchase == 0) & (hp.own_funds_est > 0)
    ].copy()

    # 2) '전남광주통합특별시' → 구(區)는 광주광역시, 시·군은 전라남도로 되돌림 (사용자 결정 A)
    # load_sources resolves the split regional fields in the supplied export.

    # 3) 마이너스통장 금리는 home_purchases에 없어서 loans_raw에서 가져옴 (구매연결 대출만)
    cl = (
        loans[(loans.loan_type == "CREDIT_LINE") & (loans.housing_purchase_linked == 1)]
        .groupby("customer_id")
        .interest_rate.mean()
        .rename("cl_rate")
    )
    hp = hp.merge(cl, on="customer_id", how="left")

    # 4) 목표 변수(모델이 맞출 값)
    hp["combo"] = np.select(
        [hp.loan_types == "CREDIT_LINE+MORTGAGE", hp.loan_types == "MORTGAGE"], [2, 1], default=0
    )
    hp["mort_ltv"] = hp.mortgage_principal / hp.purchase_price_est  # 주담대 LTV
    hp["cl_ratio"] = hp.other_loan_principal / hp.purchase_price_est  # 마통 / 매입가
    hp["loan_ratio"] = hp.total_loan_principal.fillna(0) / hp.purchase_price_est

    # 5) 매입 당시 기준 월상환·DSR 재계산 (마통은 최초 한도 전액 사용 가정 = 새 사용자와 같은 조건)
    pay = np.where(
        hp.combo > 0,
        monthly_mortgage(hp.mortgage_principal, hp.mortgage_rate, hp.mortgage_term_years),
        0.0,
    )
    pay = pay + np.where(
        hp.combo == 2, monthly_credit_line(hp.other_loan_principal, hp.cl_rate), 0.0
    )
    hp["pay_orig"] = np.nan_to_num(pay)
    hp["dsr_orig"] = hp.pay_orig * 12 / hp.household_annual_income

    # The attached training pipeline counts loans already active at purchase.
    other = loans[loans.housing_purchase_linked == 0].merge(
        hp[["customer_id", "purchase_date"]], on="customer_id"
    )
    live = other[
        (other.opened_at <= other.purchase_date) & (other.maturity_date > other.purchase_date)
    ]
    hp["existing_pay"] = hp.customer_id.map(
        live.groupby("customer_id").monthly_payment_estimated.sum()
    ).fillna(0.0)
    hp["dsr_total"] = (hp.pay_orig + hp.existing_pay) * 12 / hp.household_annual_income

    return add_features(hp)


def user_frame(income, assets, consumption, price, area, age, sido, categories, existing_pay=0.0):
    """사용자 입력 1건을 모델 입력 형태(DataFrame)로 변환"""
    df = pd.DataFrame(
        [
            {
                "household_annual_income": income,
                "financial_assets_estimated": assets,
                "avg_monthly_consumption": consumption,
                "purchase_price_est": price,
                "exclusive_area_m2": area,
                "age_at_purchase": age,
                "purchase_year": CURRENT_YEAR,
                "sido": sido,
                "existing_pay": existing_pay,
            }
        ]
    )
    df = add_features(df)
    df["sido"] = pd.Categorical(df["sido"], categories=categories)
    return df
