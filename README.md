# 내 집 마련 · 지역과 대출

고객의 소득·자산·지출로 감당할 수 있는 집값(안정권·가능권·한계권)과 예상 대출을 계산하고, 조건에 맞는 아파트 단지를 지도·목록으로 보여주는 모바일 웹앱입니다. AI 채팅은 계산기가 검증한 후보만 설명합니다. 제공 CSV 기반 참고 계산이며 실제 매물이나 대출 승인을 보장하지 않습니다.

- 백엔드: Python 3.12 · FastAPI · SQLite · scikit-learn(대출 비율 예측) · LangChain + OpenAI Responses API
- 프론트엔드: React 19 · TypeScript · Vite · 네이버 지도
- 배포: Docker 이미지 → AWS ECR → EC2(Docker Compose + Caddy). 자세한 절차는 [배포 안내](docs/deployment.md)

## 빠른 시작 (Windows)

```bat
cd /d C:\project_side
setup.cmd dev
cd frontend && pnpm install --frozen-lockfile && pnpm build && cd ..
start.cmd
```

http://127.0.0.1:8501 에서 확인합니다. Python 가상환경 이름은 `side`이고, Node.js 24와 pnpm 11이 필요합니다. 처음 설치하는 PC라면 `.env.example`을 `.env`로 복사해 키를 넣습니다. 기존 `.env`는 덮어쓰지 마세요.

## 설정 (`.env`)

| 변수 | 설명 |
|---|---|
| `OPENAI_API_KEY`, `MAIN_MODEL` | AI 채팅 키와 모델 ID |
| `MODEL_TIMEOUT_SECONDS`, `MODEL_MAX_RETRIES` | OpenAI 호출 제한 시간·재시도 (기본 90초·2회) |
| `MODEL_REASONING_EFFORT` | 선택. `low` 등으로 추론 강도 지정 (비우면 모델 기본값) |
| `CHAT_MAX_CONCURRENCY` | 동시에 처리하는 AI 대화 수 (기본 4, 초과분은 대기) |
| `CHAT_HISTORY_TURNS` | 모델에 다시 보내는 이전 대화 턴 수 (기본 6) |
| `NAVER_MAPS_CLIENT_ID`, `NAVER_MAPS_CLIENT_SECRET` | 지도 표시와 주소 좌표 조회 |
| `DATABASE_PATH`, `CHAT_CHECKPOINT_PATH`, `LOG_LEVEL` | 선택. 기본은 `data/housing.sqlite`, `data/chat_checkpoints.sqlite`, `INFO` |

키는 서버에만 있고, 브라우저에는 네이버 지도 공개 Client ID만 전달됩니다.

## 폴더 구조

```text
project_side/
├── housing_app/              # 백엔드
│   ├── api.py                # FastAPI 라우트, 빌드된 화면 제공
│   ├── affordability.py      # 학습 모델 대출 비율 ↔ 계산기 연결 (안정권 상한 기준)
│   ├── finance.py            # 자금 계획·구간 계산 (모든 금액 계산은 여기)
│   ├── llm_advisor.py        # OpenAI 채팅 에이전트와 응답 검증
│   ├── housing_repository.py # 읽기 전용 DB 조회 + 메모리 캐시
│   ├── naver_maps.py         # 지오코딩(병렬)·좌표 캐시
│   ├── recommender.py, prep.py, source_data.py, regions.py, settings.py
├── frontend/src/             # App.tsx, screens/, components/, format.ts, api.ts
├── scripts/                  # 데이터 감사·DB 생성·학습·실행 전 점검(check)
├── tests/                    # pytest (`data` 표시 테스트는 비공개 데이터 필요)
├── deploy/                   # AWS용 compose·Caddy·EC2 설치·ECR 업로드 스크립트
├── docs/                     # 배포, 모바일, 구현 기록(implementation/), 이전 기록(history/)
├── data/, models/            # 비공개 DB·CSV·모델 (Git·이미지 제외)
├── archive/                  # 이전 Streamlit·React 코드, 미사용 CSV 등 (Git 제외)
└── Dockerfile, compose.yaml, requirements*.in/txt, .github/workflows/ci.yml
```

## AI 채팅 구조

1. 브라우저가 질문 한 개와 대화 ID를 `POST /api/chat`으로 보냅니다.
2. 서버가 현재 조건으로 후보 단지를 계산한 뒤, 에이전트가 도구(`get_buyer_constraints`, `get_candidate_list`, `get_candidate_details`, `search_homes_in_district`)로 이를 읽고 구조화된 답(`ChatAnswer`)을 돌려줍니다.
3. 서버는 답에 나온 단지 ID가 이번 요청에서 조회한 후보인지 검증하고, 화면 카드의 금액은 계산기 값을 붙입니다.

비용·속도 최적화: 짧은 고정 시스템 프롬프트(OpenAI 프롬프트 캐시 활용), 필요한 필드만 담은 도구 결과, 이전 턴은 질문·답 텍스트만 재전송, OpenAI 클라이언트 재사용, 동시 실행 제한, 대화별 토큰 사용량 로그. 같은 질문 기준으로 모델에 보내는 양이 이전 deepagents 구성보다 약 77% 줄었습니다.

## 데이터 준비·검증

CSV를 바꿀 때는 `data/raw/`에 넣고 앱을 끈 뒤 실행합니다. 학습 모델은 `scripts.train`을 실행할 때만 바뀝니다.

```powershell
.\side\Scripts\python.exe -m scripts.audit_data
.\side\Scripts\python.exe -m scripts.build_database
.\side\Scripts\python.exe -m scripts.check
```

개발 중 확인:

```powershell
.\side\Scripts\python.exe -m pytest -q
.\side\Scripts\python.exe -m ruff check .
.\side\Scripts\python.exe -m ruff format --check .
```

## 문서

- [배포 안내 (GitHub · Docker · AWS)](docs/deployment.md)
- [모바일 화면 구조와 접속](docs/mobile.md)
- [채팅 메모리](docs/implementation/chat-memory.md), [데이터 매핑](docs/implementation/data-mapping.md), [검수 기록](docs/implementation/validation.md)
- 화면 기획 원본: `mydata-ui-handoff/`
