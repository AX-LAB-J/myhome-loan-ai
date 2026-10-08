"""Leakage-aware model comparison; 2025 selects, 2026 reports held-out performance."""

import json
import time
from pathlib import Path
import joblib
import numpy as np
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import accuracy_score, f1_score, log_loss, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split, GroupShuffleSplit
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer
from threadpoolctl import threadpool_limits
from housing_app.prep import load_purchases, NUM_FEATURES, KNN_FEATURES, MODEL_DIR

BASE = Path(__file__).resolve().parents[1]
FEATURES = NUM_FEATURES + ["sido"]
TARGETS = {"combo": ("combo", 0), "mort_ltv": ("mort_ltv", 1), "cl_ratio": ("cl_ratio", 2)}


def model(kind, target, n):
    clf = target == "combo"
    if kind == "baseline":
        return DummyClassifier(strategy="prior") if clf else DummyRegressor(strategy="median")
    if kind == "knn":
        # Original kNN's six standardized personal + housing features, k=100.
        transform = ColumnTransformer(
            [("numeric", StandardScaler(), KNN_FEATURES)], remainder="drop"
        )
        estimator = (
            KNeighborsClassifier(n_neighbors=min(100, n))
            if clf
            else KNeighborsRegressor(n_neighbors=min(100, n), weights="uniform")
        )
        return make_pipeline(transform, estimator)
    estimator = (HistGradientBoostingClassifier if clf else HistGradientBoostingRegressor)(
        categorical_features="from_dtype",
        learning_rate=0.05,
        max_iter=400,
        early_stopping=True,
        validation_fraction=0.15,
        random_state=42,
    )
    return estimator


def evaluate(train, test, label):
    rows = []
    started = time.monotonic()
    assert not set(train.customer_id) & set(test.customer_id)
    for target, (col, cmin) in TARGETS.items():
        tr = train[train.combo >= cmin]
        te = test[test.combo >= cmin]
        for kind in ["baseline", "knn", "boosting"]:
            m = model(kind, target, len(tr))
            m.fit(tr[FEATURES], tr[col])
            pred = m.predict(te[FEATURES])
            row = dict(split=label, target=target, model=kind, train_n=len(tr), test_n=len(te))
            if target == "combo":
                proba = np.clip(m.predict_proba(te[FEATURES]), 1e-6, 1)
                proba /= proba.sum(axis=1, keepdims=True)
                row.update(
                    log_loss=float(log_loss(te[col], proba, labels=[0, 1, 2])),
                    accuracy=float(accuracy_score(te[col], pred)),
                    macro_f1=float(f1_score(te[col], pred, average="macro")),
                    brier=float(
                        np.mean(np.sum((proba - np.eye(3)[te[col].to_numpy(int)]) ** 2, axis=1))
                    ),
                )
            else:
                row.update(
                    mae=float(mean_absolute_error(te[col], pred)), r2=float(r2_score(te[col], pred))
                )
            rows.append(row)
            print(label, target, kind, json.dumps(row), flush=True)
    print("split seconds", round(time.monotonic() - started, 1), flush=True)
    return rows


def run():
    d = load_purchases().reset_index(drop=True)
    selection = evaluate(d[d.purchase_year <= 2024], d[d.purchase_year == 2025], "selection_2025")
    # The supplied 02_train.py deploys GBM for all three targets. Keep the
    # baseline/kNN comparisons in the report, but persist that exact family.
    selected = {target: "boosting" for target in TARGETS}
    temporal = evaluate(d[d.purchase_year <= 2025], d[d.purchase_year == 2026], "heldout_2026")
    tr, te = train_test_split(d, test_size=0.2, random_state=42, stratify=d.combo)
    random = evaluate(tr, te, "random_80_20")
    # Also keep apartments out of both sides to check shared-complex dependence.
    groups = (
        d.sido.astype(str)
        + "|"
        + d.sigungu.astype(str)
        + "|"
        + d.umd_nm.fillna("")
        + "|"
        + d.apt_name.fillna("")
    )
    tr_idx, te_idx = next(
        GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42).split(d, groups=groups)
    )
    grouped = evaluate(d.iloc[tr_idx], d.iloc[te_idx], "unseen_complexes")
    report = {
        "selected": selected,
        "features": FEATURES,
        "rows": len(d),
        "results": selection + temporal + random + grouped,
        "selection_rule": "Attached 02_train.py specifies GBM for all targets; 2025 and 2026 are validation only.",
        "scope": "Synthetic buyer-pattern prediction only. Not approval, property valuation, or affordability ground truth.",
        "limitations": [
            "Current incomes/assets explain historical purchases; time split cannot eliminate this hindsight bias.",
            "Only successful homeowners, so cannot estimate approval probability or outcomes for rejected applicants.",
            "Apartment recommendation has no labeled relevance outcomes; use deterministic constraints, not claim validated recommendation accuracy.",
            "Conditional ratio metrics assume the observed loan combination; do not interpret as end-to-end approval accuracy.",
        ],
    }
    (BASE / "reports" / "model_evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# kNN·부스팅 평가",
        "",
        "모델 선택: " + json.dumps(selected, ensure_ascii=False),
        "",
        "첨부 02_train.py 지정 GBM을 학습하고 2025·2026 기간 검증. 무작위 및 단지 분리 검증도 별도로 실행.",
        "kNN은 원래의 6개 표준화 변수와 k=100. 부스팅은 원래 설정(max_iter=400, learning_rate=0.05)을 사용.",
        "AI 건강 점수·대출 결과·자기자금비율 등 결과 파생값은 입력에서 제외.",
        "",
        "| 검증 | 대상 | 모델 | 검증 건수 | log loss / MAE | 정확도 / R² |",
        "|---|---|---|---:|---:|---:|",
    ]
    for x in report["results"]:
        lines.append(
            f"| {x['split']} | {x['target']} | {x['model']} | {x['test_n']} | {x.get('log_loss', x.get('mae')):.5f} | {x.get('accuracy', x.get('r2')):.5f} |"
        )
    lines += [
        "",
        "회귀 MAE는 비율 단위(0.01 = 1%p). 대출 조합 확률은 승인 확률이 아닙니다.",
        "",
        "kNN은 유사 집단 설명에 유지하고, 예측기는 첨부 학습 스크립트의 GBM을 사용합니다. 단지 선택은 지역·예산·면적·상환 부담을 Python으로 검사한 뒤 LLM이 근거를 설명합니다.",
        "",
        "현재 시점의 소득·자산으로 과거 매입을 설명하므로 시간 검증에도 후향 편향이 남습니다. 성공한 구매자만 있어 대출 승인 또는 거절을 예측할 수 없습니다. 실제 추천 만족도 라벨이 없어 단지 추천 정확도를 주장하지 않습니다.",
    ]
    (BASE / "reports" / "model_evaluation.md").write_text("\n".join(lines), encoding="utf-8")
    final = {
        "sido_categories": list(d.sido.cat.categories),
        "selected": selected,
        "training_rows": len(d),
    }
    for target, (col, cmin) in TARGETS.items():
        tr = d[d.combo >= cmin]
        final[target] = model(selected[target], target, len(tr)).fit(tr[FEATURES], tr[col])
    final["scaler"] = StandardScaler().fit(d[KNN_FEATURES])
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(final, MODEL_DIR / "home_loan_models.joblib")
    print("SELECTED", selected, flush=True)


if __name__ == "__main__":
    with threadpool_limits(limits=4):
        run()
