# 내 집 마련 · 지역과 대출

> 현재 화면은 제공 CSV의 고객 선택 후 구매력·탐색·재무정보·계산 가정을 보여줍니다. 구현 범위와 미지원 기능은 [조사](docs/implementation/discovery.md), [데이터 매핑](docs/implementation/data-mapping.md), [검수](docs/implementation/validation.md)를 확인하세요.

제공 CSV를 가져온 DB에서 고객 재무정보와 지역별 아파트 거래 참조가격을 조회합니다. 저장된 학습 모델의 대출 비율 예측을 자금 계산의 상한으로 적용하고, Deep Agent가 조건에 맞는 단지를 설명하는 React + TypeScript / FastAPI 앱입니다. 실제 매물·실제 대출승인을 제공하는 서비스가 아닙니다.

## 시작하기

Python **3.12**와 Node.js **24**를 사용합니다. Python 가상환경 이름은 **`side`**입니다. 프론트엔드는 pnpm 11로 한 번 빌드합니다.

```bat
cd /d C:\project_side
setup.cmd dev
cd frontend
pnpm install --frozen-lockfile
pnpm build
cd ..
start.cmd
```

현재 PC에는 `side` 환경과 개발 의존성 설치가 완료되어 있습니다. `setup.cmd`는 실행 의존성만, `setup.cmd dev`는 테스트·정적 검사까지 설치합니다. `pnpm`이 없다면 `npm install -g pnpm@11.19.0`으로 설치합니다. 설치 스크립트는 `.env`를 생성하거나 덮어쓰지 않습니다.

앱 주소: http://127.0.0.1:8501

PowerShell에서 환경 활성화는 선택 사항입니다. 활성화 없이 `side\Scripts\python.exe`를 직접 실행할 수 있습니다.

```powershell
.\side\Scripts\Activate.ps1
python -m scripts.check
```

## 설정

**기존 `.env`를 그대로 사용합니다. 키를 예시 파일로 옮기거나 `.env.example`로 덮어쓰지 마세요.** 처음 설치하는 새 PC에서만 `.env`가 없는지 확인하고 예시를 복사합니다.

- `OPENAI_API_KEY`: OpenAI 채팅
- `MAIN_MODEL`: 사용할 OpenAI 모델 ID
- `CHAT_CHECKPOINT_PATH`: LangGraph 채팅 상태 저장 경로 (기본값 `data/chat_checkpoints.sqlite`)
- `NAVER_MAPS_CLIENT_ID`, `NAVER_MAPS_CLIENT_SECRET`: 지도 및 주소 좌표 조회

설정 로더: `housing_app/settings.py`. LLM 연결: `housing_app/llm_advisor.py`. 모델 변경은 `.env`의 `MAIN_MODEL`만 수정한 뒤 앱을 재시작합니다. 키와 모델 이름은 브라우저에서 직접 API를 호출하는 데 사용되지 않으며, 네이버 공개 Client ID만 지도 스크립트에 전달됩니다.

채팅은 대화별 UUID를 사용해 LangGraph 상태를 별도 SQLite 파일에 저장합니다. 브라우저는 새 질문 한 개만 전송하며, 같은 탭을 새로고침하면 `sessionStorage`의 대화 ID와 표시용 이력을 복원합니다. 고객 변경·계산 가정 저장·새 채팅 시작 시 이전 대화의 체크포인트를 삭제하고 새 ID를 만듭니다. 이 파일에는 대화와 도구 결과가 포함될 수 있으므로 실제 고객 DB로 전환하기 전 접근 제어와 보존 기간을 별도로 정해야 합니다.

## 폴더 구조

```text
project_side/
├── frontend/                # React + TypeScript 화면, 네이버 지도
│   └── dist/                # 빌드 결과 (Git 제외)
├── housing_app/api.py       # FastAPI 진입점 및 정적 화면 제공
├── housing_app/             # 금융 계산, DB 조회, LLM, 지도 좌표
├── scripts/                 # 데이터 감사, DB 생성, 학습, 준비 상태 검사
├── tests/                   # 외부 API를 호출하지 않는 테스트
├── data/raw/                # 현재 제공 CSV 4개와 이전 참고 CSV (Git·이미지 제외)
├── data/housing.sqlite      # 조회 DB 및 지도 좌표 캐시
├── models/                  # 학습 모델 (Git·이미지 제외)
├── reports/                 # 앱에서 사용하는 검증 보고서
├── docs/                    # 설계, 모바일, 배포 안내
├── side/                    # 가상환경 (Git·이미지 제외)
├── .env                     # 기존 키 보존 (Git·이미지 제외)
├── requirements.in          # 직접 실행 의존성
├── requirements.txt         # 하위 의존성까지 버전·해시 고정
├── requirements-dev.in/txt  # 개발 의존성 및 잠금 파일
└── Dockerfile / compose.yaml
```

현재 앱은 기존 주택 구매 고객 파일 4개(`home_purchases.csv`, `loans_raw.csv`, `customers_preprocessed.csv`, `real_estate_detail_preprocessed.csv`)에 전체 고객 파일 3개(`customer_financial_profiles.csv`, `customer_debt_summary.csv`, `accounts.csv`)를 연결합니다. 전체 80,000명의 고객을 이름이나 ID로 선택할 수 있고, 주택 구매 이력이 있는 42,225명은 기존 거래·대출 상세를 유지합니다. 주택 구매 이력이 없는 고객의 구매력 계산에는 활성 계좌 잔액 합계를 사용하고, 프로필의 추정 금융자산은 참고값으로 별도 표시합니다. 이 고객의 월 소비액은 관측 지출이 아닌 프로필의 소비 예산이며, 거주지는 시·도까지만 제공됩니다. `housing_app/source_data.py`가 지역 컬럼을 API·모델 입력 형식으로 변환합니다. 저장된 `models/home_loan_models.joblib`은 이번 데이터 반영에서 재학습하지 않았습니다. 데이터 검증 결과는 `reports/data_audit.json`에 기록됩니다. 기존 Streamlit `app.py`와 `housing_app/ui.py`는 이전 구현 참고용이며 실행 진입점에서는 사용하지 않습니다.

대출 계산은 선택 고객의 희망 가격·면적·재무정보에서 학습 모델의 주담대 LTV와 한도대출 비율을 예측합니다. 이 비율을 같은 고객의 탐색 가격에 적용하고, 화면에서 설정한 LTV·한도대출 상한 중 더 낮은 값을 사용합니다. 실제 필요한 자금만 빌린 것으로 계산하며 부족 자금·DSR·월 잔여금을 함께 확인합니다. 모델 비율은 과거 구매자 패턴의 추정치이며 금융기관의 승인 한도가 아닙니다.

구매력 구간은 과거 구매 참조가격에서 계산을 멈추지 않습니다. 안정권은 모델 예측 대출 비율과 설정 DSR의 87.5%(기본 35%)를 적용하고 목표 월 여유자금을 유지하는 가격입니다. 가능권은 모델 예측 대출 비율과 설정 DSR(기본 40%) 안에서 월 적자를 내지 않는 가격입니다. 한계권은 모델 예측 대출 비율과 설정 DSR을 넘을 수 있는 별도 시나리오로, 설정한 LTV 상한 안에서 월 10만 원을 남기는 가격입니다. 한계권의 대출액은 금융기관 승인 예측이 아니며 단지 목록·상세에서도 경고를 표시합니다. 인접 상한이 같으면 해당 가격 구간을 비어 있다고 표시합니다. 과거 구매 참조가격은 모델 입력에 사용하지만 단지 추천 가격을 제한하지 않습니다.

## 데이터 준비·검증

CSV를 바꿀 때는 일곱 입력 파일을 `data/raw`에 복사한 뒤 앱을 종료하고 다음 순서로 실행합니다. 서로 다른 내보내기 버전을 섞으면 고객·부동산 ID 또는 금액 검증에서 실패합니다. 학습 모델은 그대로 둡니다.

```powershell
.\side\Scripts\python.exe -m scripts.audit_data
.\side\Scripts\python.exe -m scripts.build_database
.\side\Scripts\python.exe -m scripts.check
```

DB 생성은 일곱 CSV를 검증한 뒤 새 DB 파일을 만들어 교체합니다. 실행 중인 서버를 유지하면서 전체 고객 파일만 갱신하려면 `python -m scripts.import_customer_supplements`를 사용할 수 있습니다. 기존 지도 좌표 캐시는 유지됩니다. `scripts.train`을 실행할 때만 학습 모델이 교체됩니다.

```powershell
.\side\Scripts\python.exe -m pip check
.\side\Scripts\python.exe -m pytest -q
.\side\Scripts\python.exe -m ruff check .
.\side\Scripts\python.exe -m ruff format --check .
```

테스트는 실제 `.env` 파일을 바꾸지 않고 API 키를 테스트 프로세스에서만 비활성화합니다. 현재 데이터 규모·합계와 모델 호환성까지 확인하므로 제공 CSV와 모델이 필요합니다.

의존성 변경은 `.in` 파일을 수정한 뒤 [의존성 관리 안내](docs/deployment.md)에 따라 잠금 파일을 갱신합니다. scikit-learn/numpy 변경 시 저장 모델 호환성을 확인하고 필요하면 재학습합니다. Git에는 코드·잠금 파일·검증 보고서를 포함하고 키·대용량 데이터·가상환경은 포함하지 않습니다.

## Docker·모바일

- [Docker 배포와 의존성 관리](docs/deployment.md)
- [휴대폰 접속 안내](docs/mobile.md)
- [데이터·모델 평가 및 설계](docs/design.md)
- [정리 내역과 검증 결과](docs/cleanup.md)

같은 Wi-Fi 테스트는 `start-mobile.cmd`를 사용합니다. Docker는 프론트엔드도 이미지 안에서 빌드하며 `docker compose --env-file .env.example up --build -d`로 실행합니다. **기존 로컬 서버와 동시에 8501 포트를 사용할 수 없습니다.** `.env`는 별도 읽기 전용 파일로 컨테이너에 연결되며 이미지에 포함되지 않습니다.

현재는 로컬 실행과 배포 준비 단계입니다. 인터넷 공개 전에 인증·호출량 제한·HTTPS·지속 저장소를 구성해야 합니다.
