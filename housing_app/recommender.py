# =============================================================================
# 추천 계산 로직 (화면과 분리 — housing_app/api.py가 이 모듈을 호출)
#   1. 비슷한 구매자 집단(kNN) 통계: 대출 조합 비중, 대출금액·LTV·금리·월상환·DSR·자기자금비율 범위
#   2. 내 조건 예측: GBM(조합 확률, LTV, 마통 비율) + 집단 중앙값(금리, 만기) → 월상환·DSR·판정
#   3. 대안: 감당 가능한 최대 가격 역산 → 비슷한 사람들이 그 가격 이하에서 많이 산 가격대·면적·지역
#   ※ 개인정보 보호: 개별 행은 절대 반환하지 않고, MIN_GROUP(30)명 이상 집단의 통계만 반환
# =============================================================================
import joblib
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from housing_app.prep import (
    COMBO_NAMES,
    DSR_OK,
    DSR_WARN,
    KNN_FEATURES,
    LTV_CAP,
    MIN_GROUP,
    MODEL_DIR,
    NUM_FEATURES,
    load_purchases,
    monthly_credit_line,
    monthly_mortgage,
    user_frame,
)

FEATURES = NUM_FEATURES + ["sido"]
PERSON_FEATURES = [
    "age_at_purchase",
    "log_income",
    "log_assets",
    "log_consumption",
]  # 대안 추천용 (집 조건 제외)
CL_MAX_RATIO = 0.12  # 마통 한도: 데이터 99% 분위수 (매입가의 12%)
PYEONG = 3.3058  # 1평 = 3.3058㎡
# 3단계 검증 오차 (GBM, 검증 A) — 화면에 '예측 오차 범위'로 표시
ERR_DSR = 0.028
ERR_LOAN_PCT = 0.12


def judge(dsr, surplus, shortfall):
    """감당 가능 판정: 어려움(DSR>40% 또는 월 적자 또는 자금 부족) / 주의(DSR 30~40%) / 여유"""
    dsr, surplus, shortfall = map(np.asarray, (dsr, surplus, shortfall))
    return np.where(
        (dsr > DSR_WARN) | (surplus < 0) | (shortfall > 0),
        "어려움",
        np.where(dsr > DSR_OK, "주의", "여유"),
    )


def iqr_text(s, fmt):
    """'중앙값 (25%~75%)' 문자열"""
    q = s.quantile([0.5, 0.25, 0.75])
    return f"{fmt(q[0.5])} ({fmt(q[0.25])} ~ {fmt(q[0.75])})"


def won(x):
    """원 → '3.25억' / '4,500만' 형식"""
    if pd.isna(x):
        return "-"
    return f"{x / 1e8:,.2f}억" if abs(x) >= 1e8 else f"{x / 1e4:,.0f}만"


def pct(x):
    return "-" if pd.isna(x) else f"{x * 100:.1f}%"


class Recommender:
    def __init__(self):
        self.d = load_purchases()
        m = joblib.load(MODEL_DIR / "home_loan_models.joblib")
        self.models, self.cats = m, m["sido_categories"]
        # 비슷한 구매자 kNN (사람 + 희망 집 조건)
        self.nn = NearestNeighbors().fit(m["scaler"].transform(self.d[KNN_FEATURES]))
        # 대안 추천용 kNN (사람 조건만 — 집 가격·면적은 대안이므로 제외)
        self.p_scaler = StandardScaler().fit(self.d[PERSON_FEATURES])
        self.nn_person = NearestNeighbors().fit(self.p_scaler.transform(self.d[PERSON_FEATURES]))

    # -------------------------------------------------------------------------
    def regions(self):
        """화면 선택 목록: {시도: [시군구...]} — 거래가 많은 시군구가 먼저 오도록 정렬"""
        return {
            s: list(g.sigungu.value_counts().index)
            for s, g in self.d.groupby("sido", observed=True)
        }

    # -------------------------------------------------------------------------
    # 1. 비슷한 구매자 집단
    # -------------------------------------------------------------------------
    def similar_group(self, u):
        """가까운 100명부터 시작, 대출 이용자가 30명 미만이면 인원을 2배씩 늘림"""
        x = self.models["scaler"].transform(u[KNN_FEATURES])
        for k in sorted(
            {min(n, len(self.d)) for n in [100, 200, 400, 800, 1600, 3200, 6400, len(self.d)]}
        ):
            idx = self.nn.kneighbors(x, n_neighbors=k, return_distance=False)[0]
            g = self.d.iloc[idx]
            if (g.combo > 0).sum() >= MIN_GROUP:
                break
        return g

    def group_summary(self, g):
        """집단 통계표 (개별 값 없이 분위수만). 30명 미만 조합은 숨김"""
        desc = {
            "인원": f"{len(g):,}명",
            "매입 당시 나이": f"{g.age_at_purchase.quantile(0.1):.0f}~{g.age_at_purchase.quantile(0.9):.0f}세",
            "가구 연소득": f"{won(g.household_annual_income.quantile(0.1))} ~ {won(g.household_annual_income.quantile(0.9))}",
            "매입가": f"{won(g.purchase_price_est.quantile(0.1))} ~ {won(g.purchase_price_est.quantile(0.9))}",
        }
        share = (
            g.combo.value_counts(normalize=True)
            .reindex([0, 1, 2], fill_value=0)
            .rename(index=COMBO_NAMES)
        )

        rows = []
        loaners = g[g.combo > 0]
        for name, sub in [
            ("대출 이용자 전체", loaners),
            (COMBO_NAMES[1], g[g.combo == 1]),
            (COMBO_NAMES[2], g[g.combo == 2]),
        ]:
            if len(sub) < MIN_GROUP:
                rows.append({"구분": name, "인원": f"{len(sub)}명 (30명 미만 — 표시 안 함)"})
                continue
            cl = sub[sub.combo == 2]
            rows.append(
                {
                    "구분": name,
                    "인원": f"{len(sub)}명",
                    "총 대출금액": iqr_text(sub.total_loan_principal, won),
                    "주담대 LTV": iqr_text(sub.mort_ltv, pct),
                    "주담대 금리": iqr_text(sub.mortgage_rate, lambda v: f"{v:.2f}%"),
                    "마통 금리": iqr_text(cl.cl_rate, lambda v: f"{v:.2f}%")
                    if len(cl) >= MIN_GROUP
                    else "-",
                    "만기": f"{sub.mortgage_term_years.mode()[0]:.0f}년 (최빈)",
                    "월 상환액": iqr_text(sub.pay_orig, won),
                    "DSR (전체 대출)": iqr_text(sub.dsr_total, pct),
                    "자기자금 비율": iqr_text(sub.own_funds_ratio, pct),
                }
            )
        return desc, share, pd.DataFrame(rows).set_index("구분").fillna("-")

    # -------------------------------------------------------------------------
    # 2. 내 조건 예측
    # -------------------------------------------------------------------------
    def plan(self, U, cash, consumption, rates, use_cl, existing_pay=0.0):
        """여러 가격(U의 각 행)에 대해 대출 계획·월상환·DSR·판정을 한 번에 계산"""
        price = U.purchase_price_est.to_numpy()
        income = U.household_annual_income.to_numpy()
        ltv = np.clip(self.models["mort_ltv"].predict(U[FEATURES]), 0, LTV_CAP)
        cl_r = (
            np.clip(self.models["cl_ratio"].predict(U[FEATURES]), 0, CL_MAX_RATIO)
            if use_cl
            else 0.0
        )

        pattern_loan = price * (ltv + cl_r)  # 비슷한 사람들 패턴대로 빌릴 때
        need_loan = np.maximum(price - cash, 0)  # 보유 자금으로 모자라는 금액
        loan = need_loan  # Do not borrow simply because similar buyers did.
        mort = np.minimum(loan, price * LTV_CAP)  # 주담대는 LTV 70%까지
        cl = np.minimum(loan - mort, price * CL_MAX_RATIO) if use_cl else np.zeros_like(price)
        shortfall = loan - mort - cl  # 대출로도 못 채우는 금액 = 자금 부족

        pay = monthly_mortgage(mort, rates["mort"], rates["term"]) + monthly_credit_line(
            cl, rates["cl"]
        )
        dsr = (pay + existing_pay) * 12 / income
        surplus = income / 12 - consumption - pay - existing_pay
        return pd.DataFrame(
            {
                "price": price,
                "mort": mort,
                "cl": cl,
                "loan": mort + cl,
                "pattern_loan": pattern_loan,
                "need_loan": need_loan,
                "shortfall": shortfall,
                "pay": pay,
                "dsr": dsr,
                "surplus": surplus,
                "verdict": judge(dsr, surplus, shortfall),
            }
        )

    def predict(self, inp, g):
        """inp: 사용자 입력 dict (원 단위), g: 비슷한 구매자 집단"""
        u = user_frame(
            inp["income"],
            inp["assets"],
            inp["consumption"],
            inp["price"],
            inp["area"],
            inp["age"],
            inp["sido"],
            self.cats,
            inp.get("existing_pay", inp.get("existing_payment", 0.0)),
        )
        proba = pd.Series(
            self.models["combo"].predict_proba(u[FEATURES])[0],
            index=[COMBO_NAMES[i] for i in range(3)],
        )
        use_cl = proba.iloc[2] >= proba.iloc[1]  # 대출을 쓴다면 어느 조합이 더 흔한지
        loaners = g[g.combo > 0]
        cl_grp = g[g.combo == 2]
        rates = {  # 금리·만기는 입력으로 설명되지 않아(3단계) 집단 중앙값/최빈값 사용
            "mort": loaners.mortgage_rate.median(),
            "cl": cl_grp.cl_rate.median()
            if len(cl_grp) >= MIN_GROUP
            else self.d[self.d.combo == 2].cl_rate.median(),
            "term": loaners.mortgage_term_years.mode()[0],
        }
        rates["mort"] = inp.get("mort_rate", inp.get("mortgage_rate")) or rates["mort"]
        rates["cl"] = inp.get("cl_rate", inp.get("credit_rate")) or rates["cl"]
        rates["term"] = inp.get("term", inp.get("term_years")) or rates["term"]
        cash = inp.get("cash", inp["assets"]) + inp["other_funds"]
        p = self.plan(
            u,
            cash,
            inp["consumption"],
            rates,
            use_cl,
            inp.get("existing_pay", inp.get("existing_payment", 0.0)),
        ).iloc[0]
        return u, proba, use_cl, rates, cash, p

    # -------------------------------------------------------------------------
    # 3. 대안 추천
    # -------------------------------------------------------------------------
    def max_affordable(self, inp, rates, use_cl, cash):
        """가격을 바꿔가며 판정을 계산해, '여유'와 '어려움 아님'의 최대 가격을 찾음"""
        prices = np.linspace(3e7, max(inp["price"], 3e7), 150)
        U = pd.concat(
            [
                user_frame(
                    inp["income"],
                    inp["assets"],
                    inp["consumption"],
                    p,
                    inp["area"],
                    inp["age"],
                    inp["sido"],
                    self.cats,
                    inp.get("existing_pay", inp.get("existing_payment", 0.0)),
                )
                for p in prices
            ],
            ignore_index=True,
        )
        P = self.plan(
            U,
            cash,
            inp["consumption"],
            rates,
            use_cl,
            inp.get("existing_pay", inp.get("existing_payment", 0.0)),
        )
        ok = P[P.verdict != "어려움"].price.max()
        comfy = P[P.verdict == "여유"].price.max()
        return (None if pd.isna(ok) else ok), (None if pd.isna(comfy) else comfy)

    def region_context(self, sido, sigungu):
        """희망 지역 시세: 시군구 30건 이상이면 시군구, 아니면 시도로 넓힘"""
        sub = self.d[(self.d.sido == sido) & (self.d.sigungu == sigungu)]
        basis, short = f"{sido} {sigungu}", f"{sigungu}에서"
        if len(sub) < MIN_GROUP:
            sub, basis, short = (
                self.d[self.d.sido == sido],
                f"{sido} 전체 ({sigungu} 거래 30건 미만 → 시도로 확대)",
                f"{sido} 시세로",
            )
        return basis, {
            "기준": short,
            "거래 건수": len(sub),
            "매입가": won(sub.purchase_price_est.median()),
            "매입가 구간": f"{won(sub.purchase_price_est.quantile(0.25))} ~ {won(sub.purchase_price_est.quantile(0.75))}",
            "전용면적": f"{sub.exclusive_area_m2.median():.0f}㎡",
            "전용면적 구간": f"{sub.exclusive_area_m2.quantile(0.25):.0f}㎡ ~ {sub.exclusive_area_m2.quantile(0.75):.0f}㎡",
            "평당가 중앙값": sub.price_per_pyeong.median(),
        }

    def alternatives(self, u, max_price, sido):
        """비슷한 사람들(사람 조건 기준)이 max_price 이하에서 많이 산 가격대·면적·지역"""
        x = self.p_scaler.transform(u[PERSON_FEATURES])
        pool = None
        for k in sorted({min(n, len(self.d)) for n in [3000, 6000, 12000, len(self.d)]}):
            idx = self.nn_person.kneighbors(x, n_neighbors=k, return_distance=False)[0]
            pool = self.d.iloc[idx]
            pool = pool[pool.purchase_price_est <= max_price]
            if len(pool) >= MIN_GROUP * 5:
                break
        out = {"pool_n": len(pool)}

        # 가격대 (5천만 원 단위)
        edges = np.arange(0, max_price + 5e7, 5e7)
        band = pd.cut(pool.purchase_price_est, edges, right=True)
        t = pool.groupby(band, observed=True).agg(
            인원=("combo", "size"), 면적중앙=("exclusive_area_m2", "median")
        )
        t = t[t.인원 >= MIN_GROUP]
        t.index = [f"{won(iv.left)} ~ {won(iv.right)}" for iv in t.index]
        t["비중"] = (t.인원 / len(pool)).map(pct)
        t["면적중앙"] = t.면적중앙.map(lambda v: f"{v:.0f}㎡ ({v / PYEONG:.0f}평)")
        out["price_bands"] = t.sort_values("인원", ascending=False).head(6).rename_axis("가격대")

        # 면적대
        a_edges = [0, 40, 60, 85, 102, 135, 1000]
        a_labels = ["40㎡ 미만", "40~60㎡", "60~85㎡", "85~102㎡", "102~135㎡", "135㎡ 이상"]
        t = pool.groupby(
            pd.cut(pool.exclusive_area_m2, a_edges, labels=a_labels), observed=True
        ).agg(인원=("combo", "size"), 매입가중앙=("purchase_price_est", "median"))
        t = t[t.인원 >= MIN_GROUP]
        t["비중"] = (t.인원 / len(pool)).map(pct)
        t["매입가중앙"] = t.매입가중앙.map(won)
        out["area_bands"] = t.rename_axis("면적대")

        # 지역: ① 비슷한 사람들 중 희망 시도 안의 시군구 → ② 희망 시도 전체 거래(가격 이하) → ③ 전국 시도
        def region_table(df, key):
            r = df.groupby(key, observed=True).agg(
                건수=("combo", "size"),
                매입가중앙=("purchase_price_est", "median"),
                면적중앙=("exclusive_area_m2", "median"),
            )
            r = r[r.건수 >= MIN_GROUP].sort_values("건수", ascending=False).head(8)
            r["매입가중앙"] = r.매입가중앙.map(won)
            r["면적중앙"] = r.면적중앙.map(lambda v: f"{v:.0f}㎡")
            return r.rename_axis("지역")

        r = region_table(pool[pool.sido == sido], "sigungu")
        basis = f"나와 비슷한 구매자들이 {sido}에서 {won(max_price)} 이하로 산 시군구"
        if len(r) < 3:
            market = self.d[(self.d.sido == sido) & (self.d.purchase_price_est <= max_price)]
            r = region_table(market, "sigungu")
            basis = f"{sido} 전체 거래 중 {won(max_price)} 이하 거래가 많은 시군구 (비슷한 구매자만으로는 30명 미만)"
        if len(r) == 0:
            r = region_table(pool, "sido")
            basis = f"나와 비슷한 구매자들이 {won(max_price)} 이하로 산 시도 (전국으로 확대)"
        out["regions"], out["region_basis"] = r, basis
        return out
