# 화면 데이터 매핑

모든 금액의 API 단위는 원입니다. 화면에서 만 원·억 원으로 변환하며 월·연 단위를 구분합니다.

| 화면 값 | 출처와 처리 |
|---|---|
| 고객 이름·ID·나이·가구원 | `/api/demo-customers` → `customer_profiles`. 이름 또는 ID 검색 |
| 가구 연소득 | 구매 고객은 `customers.household_annual_income`, 구매 이력이 없으면 `customer_profiles.household_annual_income` |
| 월 소득 | 연소득을 12로 나눈 환산값 |
| 금융자산·가용 자금 | 구매 고객은 금융자산 추정액, 구매 이력이 없으면 활성 계좌 잔액 합계를 계산 입력에 사용 |
| 계좌별 잔액 | `/api/demo-customers/{id}` → `accounts`, 고객 ID 조건. 합계는 `status=ACTIVE`만 포함 |
| 월 소비 | 구매 고객은 `customers.avg_monthly_consumption`, 구매 이력이 없으면 프로필의 `monthly_consumption_budget`. 후자는 관측 지출이 아닌 예산 |
| 기존 대출 월 상환 | 구매 고객은 `customers.monthly_debt_service`, 구매 이력이 없으면 `customer_debt_summary.monthly_debt_service`. 소비와 별도 차감 |
| 대출별 잔액 | 구매 고객은 `loans_raw.outstanding_balance`, 구매 이력이 없으면 부채 요약의 대출 유형별 잔액 |
| 보유 주택 | `real_estate_detail`, 고객 ID 조건. 구매 기록이 없으면 `property=null` |
| 기타 자금·예비비·목표 여유자금 | 고객별 브라우저 계산 가정 → `Buyer.other_funds,reserve,target_surplus`. 원천 DB에 덮어쓰지 않음 |
| 학습 모델 예측 비율 | `affordability.model_buyer` → 저장된 GBM의 주담대·한도대출 비율. 안정권 상한 가격을 기준으로 계산 |
| 구매력 경계 | `/api/plan` → `affordability.bands` → `finance.affordability_bands`. 안정·가능·한계 시나리오의 가격 상한 |
| 필요한 대출·월 상환·잔여금 | `finance.financing`. 필요한 자금만 대출하고 기존 상환액을 별도 반영 |
| 지역·단지 목록 | `/api/explore` → `apartment_trades`. 지역·면적·거래 시작연도 조건 후 단지별 최근 거래 선택 |
| 채팅 후보 | `finance.candidates`. 현재 고객의 자금·상환 조건을 충족한 단지. 과거 구매가격을 현재 검색 상한으로 쓰지 않음 |
| 단지 좌표 | `/api/map`, `/api/map/resolve` → `geocode_cache` 또는 네이버 지오코딩. 선택한 단지와 보유 주택을 전달 |
| 금리 상승 비교 | 동일 고객·가격·만기의 금리를 +1%p 바꿔 서버에서 재계산 |

한계권 단지는 모델 비율·DSR 상한을 넘을 수 있는 별도 시나리오로 계산하고 `loan_basis=limit_scenario`로 구분합니다. 지도 위치는 단지 주소의 지오코딩 결과이며 현재 매물 정보가 아닙니다.

계산 가정은 고객 ID별 `localStorage`, 대화 복원 정보는 같은 탭의 `sessionStorage`에 저장합니다. 서버의 대화 상태는 별도 SQLite 체크포인트에 보관합니다. 로그인·금융기관 동의·실시간 동기화는 현재 연결되지 않았습니다.
