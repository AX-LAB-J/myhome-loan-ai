# 화면 데이터 매핑

| 화면 값 | API → 계산/변환 → DB | 단위·범위 |
|---|---|---|
| 고객 선택/나이/가구원 | `/api/demo-customers`, `/api/demo-customers/{id}` → `customers.customer_id,age,household_size` | 합성 고객 ID, 인증 없음 |
| 가구 연소득/월 소득 | 고객 상세 → `customers.household_annual_income` → `/12` | 원/년 → 원/월. 월 소득 관측치가 아닌 환산값으로 표기 |
| 월 총지출 | 고객 상세 → `customers.avg_monthly_consumption` | 원/월, 12개월 평균. 대출 상환 별도 |
| 금융자산 | 고객 상세 → `customers.financial_assets_estimated` | 원, 추정액 |
| 기존 대출 월 상환 | 고객 상세 → `customers.monthly_debt_service` | 원/월. `loans_raw.monthly_payment_estimated`와 중복 합산하지 않음 |
| 대출별 잔액 | 고객 상세 → `loans_raw` 고객 ID 조건 → `loan_type,outstanding_balance` | 원, 계좌별 잔액 자료는 없음 |
| 계좌별 잔액 | 해당 테이블/컬럼 없음 | 정보 없음으로 표시 |
| 기타 동원 자금 | 브라우저 폼 초안 → `Buyer.other_funds` | 원, 서버 검증 후 고객 ID별 브라우저 저장소에 보관. DB 저장 아님 |
| 예비비·목표 여유자금 | 브라우저 폼 → `Buyer.reserve,target_surplus` | 원/일시금, 원/월. 고객 ID별 브라우저 저장소에 보관 |
| 구매력 구간 | `/api/plan` → `affordability_bands` → `financing` | 원. 안정권: 목표 잔여 이상, 가능권: 잔여 0 이상, 한계권: 자금·DSR 충족/잔여 음수. 모두 `Buyer.price` 상한 내 |
| 월 상환/잔여 | `/api/plan`, `/api/explore` → `financing` | 원/월. 기존 상환액을 별도 차감 |
| 단지·가격·면적·기간 | `/api/explore` → `repository.trades` → `apartment_trades` | `complex_id`별 기간·면적 조건 내 최근 거래 1건, 원/㎡/거래연도 |
| 단지 좌표 | `/api/map` → `geocode_cache`, 필요 시 네이버 지오코딩 | 주소별 좌표. 지도는 최대 30개 단지 |
| 구 경계/계좌/동의/동기화 | 없음 | 구현 차단, 예시 수치 미표시 |

`customers`의 합성 기록과 수정한 계산 가정을 혼합 저장하지 않는다. 계산 가정만 고객 ID별 `localStorage`에 남으며 같은 브라우저에서 고객을 다시 선택하면 복원된다. 서버 영속 저장이나 기기 간 동기화는 없다.
