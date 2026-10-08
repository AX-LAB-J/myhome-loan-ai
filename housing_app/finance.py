"""Buyer-pattern loan estimates and explicit affordability scenarios."""

from dataclasses import dataclass, asdict, replace
import math
from housing_app.prep import monthly_mortgage, monthly_credit_line


@dataclass(frozen=True)
class Buyer:
    age: int = 31
    income: float = 70000000
    assets: float = 100000000
    other_funds: float = 0
    consumption: float = 2500000
    price: float = 500000000
    area: float = 59
    sido: str = "서울특별시"
    sigungu: str = "노원구"
    existing_payment: float = 0
    reserve: float = 0
    cost_rate: float = 0.04
    ltv_cap: float = 0.7
    dsr_cap: float = 0.4
    mortgage_rate: float = 4.5
    term: int = 30
    allow_credit: bool = False
    credit_rate: float = 7
    credit_cap_ratio: float = 0.12
    area_tolerance: float = 0.2
    min_year: int = 2022
    max_results: int = 3
    target_surplus: float = 1_000_000
    model_mortgage_ratio: float | None = None
    model_credit_ratio: float | None = None
    model_basis_price: float | None = None  # price the model ratios were predicted at

    def __post_init__(self):
        numeric = [v for v in asdict(self).values() if isinstance(v, (float, int))]
        if not all(math.isfinite(v) for v in numeric):
            raise ValueError("유효한 숫자를 입력하세요.")
        if not 20 <= self.age <= 100 or self.income <= 0 or self.price <= 0 or self.area <= 0:
            raise ValueError("나이·소득·가격·면적을 확인하세요.")
        if (
            min(
                self.assets,
                self.other_funds,
                self.consumption,
                self.existing_payment,
                self.reserve,
                self.target_surplus,
                self.mortgage_rate,
                self.credit_rate,
            )
            < 0
        ):
            raise ValueError("금액과 금리는 0 이상이어야 합니다.")
        if not (
            0 < self.ltv_cap <= 1
            and 0 < self.dsr_cap <= 1
            and 0 <= self.cost_rate <= 0.3
            and 0 <= self.credit_cap_ratio <= 0.3
            and 0 <= self.area_tolerance <= 1
            and 1 <= self.term <= 50
            and 1 <= self.max_results <= 10
        ):
            raise ValueError("계산 가정 범위를 확인하세요.")


SAFE_DSR_FACTOR = 0.875  # default 40% assumption -> 35% stable band
LIMIT_MONTHLY_SURPLUS = 100_000


def stable_buyer(buyer):
    return replace(buyer, dsr_cap=buyer.dsr_cap * SAFE_DSR_FACTOR)


def limit_buyer(buyer):
    """Exploratory cash-flow scenario, not a model or lending-limit prediction."""
    return replace(buyer, dsr_cap=1.0, model_mortgage_ratio=None, model_credit_ratio=None)


def financing(buyer, price, *, enforce_price_cap=True, loan_basis=None):
    if not math.isfinite(price) or price <= 0:
        raise ValueError("가격은 양수여야 합니다.")
    available = max(0, buyer.assets + buyer.other_funds - buyer.reserve)
    costs = price * buyer.cost_rate
    need = max(0, price + costs - available)
    mortgage_ratio = buyer.ltv_cap if buyer.model_mortgage_ratio is None else min(buyer.ltv_cap, buyer.model_mortgage_ratio)
    credit_ratio = buyer.credit_cap_ratio if buyer.model_credit_ratio is None else min(buyer.credit_cap_ratio, buyer.model_credit_ratio)
    mortgage = min(need, price * mortgage_ratio)
    credit = (
        min(max(0, need - mortgage), price * credit_ratio) if buyer.allow_credit else 0
    )
    shortfall = max(0, need - mortgage - credit)
    payment = float(
        monthly_mortgage(mortgage, buyer.mortgage_rate, buyer.term)
        + monthly_credit_line(credit, buyer.credit_rate)
    )
    dsr = (payment + buyer.existing_payment) * 12 / buyer.income
    surplus = buyer.income / 12 - buyer.consumption - payment - buyer.existing_payment
    reasons = []
    if enforce_price_cap and price > buyer.price:
        reasons.append("희망 가격 상한 초과")
    if shortfall > 0.01:
        reasons.append("동원 자금 및 가정한 대출 한도 부족")
    if dsr > buyer.dsr_cap:
        reasons.append("설정한 상환 부담 비율 초과")
    if surplus < 0:
        reasons.append("월 잉여현금 음수")
    return dict(
        price=float(price),
        costs=costs,
        available=available,
        need=need,
        mortgage=mortgage,
        credit=credit,
        loan=mortgage + credit,
        loan_basis=loan_basis or ("trained_model" if buyer.model_mortgage_ratio is not None else "assumption"),
        model_mortgage_ratio=buyer.model_mortgage_ratio,
        model_credit_ratio=buyer.model_credit_ratio if buyer.allow_credit else None,
        shortfall=shortfall,
        payment=payment,
        dsr=dsr,
        surplus=surplus,
        eligible=not reasons,
        reasons=reasons,
    )


def candidates(repo, buyer):
    trades = repo.trades(buyer.sido, buyer.sigungu)
    if trades.empty:
        return {"status": "NO_DATA", "candidates": [], "examined": 0}
    # Latest observed transaction within requested area/year per complex; never broaden district.
    trades = trades[
        (trades.purchase_year >= buyer.min_year)
        & (
            trades.exclusive_area_m2.between(
                buyer.area * (1 - buyer.area_tolerance), buyer.area * (1 + buyer.area_tolerance)
            )
        )
    ].copy()
    if trades.empty:
        return {"status": "NO_REFERENCE_IN_SCOPE", "candidates": [], "examined": 0}
    trades = trades.drop_duplicates("complex_id", keep="first")
    matched = []
    for r in trades.to_dict("records"):
        # Source anomaly flagged in audit: do not recommend pre-construction reference records.
        if r["build_year"] is not None and r["build_year"] > r["purchase_year"]:
            continue
        plan = financing(buyer, float(r["purchase_reference_price"]), enforce_price_cap=False)
        if plan["eligible"]:
            r["plan"] = plan
            r["price_basis"] = "면적 조건 내 단지의 가장 최근 거래 참조가격"
            r["loan_summary"] = repo.complex_loans(r["complex_id"])
            matched.append(r)
    matched.sort(
        key=lambda x: (
            abs(x["exclusive_area_m2"] - buyer.area),
            -int(x["reference_deal_date"].replace("-", "")[:8]),
            x["plan"]["dsr"],
        )
    )
    return {
        "status": "MATCHES" if matched else "NO_MATCH",
        "candidates": matched[: buyer.max_results],
        "examined": len(trades),
        "matched_count": len(matched),
    }


def max_affordable(buyer):
    return affordability_bands(buyer)["possible"]


def affordability_bands(buyer):
    """Stable, model-based possible, and explicitly speculative limit boundaries."""

    def boundary(scenario_buyer, required_surplus):
        ceiling = max(buyer.price, 1.0)
        for _ in range(40):
            check = financing(scenario_buyer, ceiling, enforce_price_cap=False)
            if (check["shortfall"] > 0.01 or check["dsr"] > scenario_buyer.dsr_cap
                    or check["surplus"] < required_surplus):
                break
            ceiling *= 2
        else:
            raise ValueError("재무 상한을 계산할 수 없습니다.")
        low, high = 0.0, ceiling
        for _ in range(60):
            mid = (low + high) / 2
            result = financing(scenario_buyer, max(mid, 1), enforce_price_cap=False)
            funded = result["shortfall"] <= 0.01 and result["dsr"] <= scenario_buyer.dsr_cap
            if funded and result["surplus"] >= required_surplus:
                low = mid
            else:
                high = mid
        return low

    safe = boundary(stable_buyer(buyer), buyer.target_surplus)
    possible = max(safe, boundary(buyer, 0))
    upper = max(possible, boundary(limit_buyer(buyer), LIMIT_MONTHLY_SURPLUS))
    return {"safe": safe, "possible": possible, "maximum": upper}
