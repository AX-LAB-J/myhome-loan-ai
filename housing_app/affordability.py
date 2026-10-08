"""Bind the trained loan-ratio regressors to the finance calculator.

Every screen (bands, complex plans, chat) uses one set of model ratios: the ones predicted
for buying at the buyer's stable-band ceiling. Results are memoized per ``Buyer`` because the
browser asks for /plan, /explore and /patterns with the same inputs at once.
"""

import math
from dataclasses import replace
from functools import lru_cache

from housing_app.finance import Buyer, affordability_bands
from housing_app.prep import user_frame
from housing_app.recommender import FEATURES, Recommender

ANCHOR_TOLERANCE = 10_000  # won; stop re-predicting once the ceiling moves less than this
ANCHOR_ROUNDS = 5


class ModelPredictionError(RuntimeError):
    """The saved regressors returned a non-finite ratio."""


@lru_cache(maxsize=1)
def recommender() -> Recommender:
    return Recommender()


def predicted_ratios(buyer: Buyer, price: float) -> Buyer:
    """Saved regressors' loan ratios for buying at ``price``, capped by the assumptions."""
    engine = recommender()
    frame = user_frame(
        buyer.income,
        buyer.assets,
        buyer.consumption,
        price,
        buyer.area,
        buyer.age,
        buyer.sido,
        engine.cats,
        buyer.existing_payment,
    )
    mortgage_ratio = float(engine.models["mort_ltv"].predict(frame[FEATURES])[0])
    credit_ratio = float(engine.models["cl_ratio"].predict(frame[FEATURES])[0])
    if not math.isfinite(mortgage_ratio) or not math.isfinite(credit_ratio):
        raise ModelPredictionError("학습 모델의 대출 예측값이 유효하지 않습니다.")
    return replace(
        buyer,
        model_mortgage_ratio=max(0.0, min(mortgage_ratio, buyer.ltv_cap)),
        model_credit_ratio=max(0.0, min(credit_ratio, buyer.credit_cap_ratio)),
        model_basis_price=price,
    )


@lru_cache(maxsize=512)
def model_buyer(buyer: Buyer) -> Buyer:
    """Predict ratios at the stable-band ceiling; the ceiling depends on the ratios, so
    re-predict at the new ceiling until it settles. Without a stable band, use the buyer's
    own price."""
    anchored = predicted_ratios(buyer, buyer.price)
    for _ in range(ANCHOR_ROUNDS):
        safe = bands(anchored)["safe"]
        if safe < 1:
            return predicted_ratios(buyer, buyer.price)
        if abs(safe - anchored.model_basis_price) < ANCHOR_TOLERANCE:
            break
        anchored = predicted_ratios(buyer, safe)
    return anchored


def bands(buyer: Buyer) -> dict:
    return dict(_bands(buyer))


@lru_cache(maxsize=1024)
def _bands(buyer: Buyer) -> tuple:
    return tuple(affordability_bands(buyer).items())
