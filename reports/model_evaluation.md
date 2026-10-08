# kNN·부스팅 평가

모델 선택: {"combo": "boosting", "mort_ltv": "boosting", "cl_ratio": "boosting"}

첨부 02_train.py 지정 GBM을 학습하고 2025·2026 기간 검증. 무작위 및 단지 분리 검증도 별도로 실행.
kNN은 원래의 6개 표준화 변수와 k=100. 부스팅은 원래 설정(max_iter=400, learning_rate=0.05)을 사용.
AI 건강 점수·대출 결과·자기자금비율 등 결과 파생값은 입력에서 제외.

| 검증 | 대상 | 모델 | 검증 건수 | log loss / MAE | 정확도 / R² |
|---|---|---|---:|---:|---:|
| selection_2025 | combo | baseline | 5912 | 1.07951 | 0.41221 |
| selection_2025 | combo | knn | 5912 | 0.98147 | 0.51641 |
| selection_2025 | combo | boosting | 5912 | 0.98191 | 0.50795 |
| selection_2025 | mort_ltv | baseline | 4477 | 0.12236 | -0.02753 |
| selection_2025 | mort_ltv | knn | 4477 | 0.06405 | 0.71387 |
| selection_2025 | mort_ltv | boosting | 4477 | 0.06019 | 0.73792 |
| selection_2025 | cl_ratio | baseline | 2437 | 0.01920 | -0.00368 |
| selection_2025 | cl_ratio | knn | 2437 | 0.01840 | 0.06915 |
| selection_2025 | cl_ratio | boosting | 2437 | 0.01809 | 0.08270 |
| heldout_2026 | combo | baseline | 5087 | 1.07819 | 0.41636 |
| heldout_2026 | combo | knn | 5087 | 0.96708 | 0.51661 |
| heldout_2026 | combo | boosting | 5087 | 0.96008 | 0.52290 |
| heldout_2026 | mort_ltv | baseline | 3836 | 0.12186 | -0.03752 |
| heldout_2026 | mort_ltv | knn | 3836 | 0.06515 | 0.68096 |
| heldout_2026 | mort_ltv | boosting | 3836 | 0.06035 | 0.71528 |
| heldout_2026 | cl_ratio | baseline | 2118 | 0.01923 | -0.00009 |
| heldout_2026 | cl_ratio | knn | 2118 | 0.01876 | 0.03792 |
| heldout_2026 | cl_ratio | boosting | 2118 | 0.01858 | 0.05277 |
| random_80_20 | combo | baseline | 5280 | 1.08513 | 0.39470 |
| random_80_20 | combo | knn | 5280 | 0.96733 | 0.51894 |
| random_80_20 | combo | boosting | 5280 | 0.96042 | 0.53201 |
| random_80_20 | mort_ltv | baseline | 3892 | 0.12622 | -0.03798 |
| random_80_20 | mort_ltv | knn | 3892 | 0.06179 | 0.73635 |
| random_80_20 | mort_ltv | boosting | 3892 | 0.05438 | 0.80089 |
| random_80_20 | cl_ratio | baseline | 2084 | 0.01924 | -0.00032 |
| random_80_20 | cl_ratio | knn | 2084 | 0.01855 | 0.06795 |
| random_80_20 | cl_ratio | boosting | 2084 | 0.01830 | 0.09135 |
| unseen_complexes | combo | baseline | 5657 | 1.08261 | 0.39456 |
| unseen_complexes | combo | knn | 5657 | 0.97375 | 0.51564 |
| unseen_complexes | combo | boosting | 5657 | 0.96063 | 0.52431 |
| unseen_complexes | mort_ltv | baseline | 4229 | 0.12385 | -0.04914 |
| unseen_complexes | mort_ltv | knn | 4229 | 0.06168 | 0.72824 |
| unseen_complexes | mort_ltv | boosting | 4229 | 0.05420 | 0.79463 |
| unseen_complexes | cl_ratio | baseline | 2232 | 0.01892 | -0.00106 |
| unseen_complexes | cl_ratio | knn | 2232 | 0.01860 | 0.03630 |
| unseen_complexes | cl_ratio | boosting | 2232 | 0.01846 | 0.04416 |

회귀 MAE는 비율 단위(0.01 = 1%p). 대출 조합 확률은 승인 확률이 아닙니다.

kNN은 유사 집단 설명에 유지하고, 예측기는 첨부 학습 스크립트의 GBM을 사용합니다. 단지 선택은 지역·예산·면적·상환 부담을 Python으로 검사한 뒤 LLM이 근거를 설명합니다.

현재 시점의 소득·자산으로 과거 매입을 설명하므로 시간 검증에도 후향 편향이 남습니다. 성공한 구매자만 있어 대출 승인 또는 거절을 예측할 수 없습니다. 실제 추천 만족도 라벨이 없어 단지 추천 정확도를 주장하지 않습니다.