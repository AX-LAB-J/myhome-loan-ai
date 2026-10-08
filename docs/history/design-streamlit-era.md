# 내 집 마련: 지역·단지·대출 조회와 Deep Agent 추천

기존 5개 Python 파일을 기반으로 확장했습니다. 수정 전 파일은 프로젝트 밖 `C:/ai_campus/project_side_archive/20260930_before_layout/original/`에 보존했습니다.
데이터는 합성 고객의 교육용 데이터입니다. 실제 금융기관의 대출 거래 공개 서비스가 아니며 현재 매물 존재·시세·대출승인을 보장하지 않습니다.

## 실행

환경 설치·실행·폴더 구조는 [README](../README.md)를 확인하세요. 가상환경은 `side`, 실행 코드는 `housing_app`, 분석·학습 도구는 `scripts`입니다.

## API 연결 준비

기존 `.env`를 유지합니다. 새 환경에서 `.env`가 없을 때만 `.env.example`을 복사합니다. 상위 `project/.env`는 자동으로 읽지 않습니다.

```dotenv
OPENAI_API_KEY=
MAIN_MODEL=gpt-6-luna
NAVER_MAPS_CLIENT_ID=
NAVER_MAPS_CLIENT_SECRET=
```

모델 기본값은 `project/src/deep_agent_app/settings.py`와 동일한 `gpt-6-luna`입니다. 모델 접근 오류가 발생해도 다른 모델로 자동 변경하지 않습니다.

네이버 Cloud 콘솔에서 **Dynamic Map과 Geocoding**을 활성화하고 사용 웹 서비스 URL에 로컬 접속 주소(`http://127.0.0.1:8501`, localhost로 접속한다면 해당 주소도)를 등록해야 합니다. 실제 키 연결 후 iframe의 인증과 허용 URL 동작을 확인하세요.

- 공개 지도 Client ID만 브라우저에 전달됩니다. Client Secret은 서버의 Geocoding 호출에서만 사용합니다.
- 지도 좌표는 사용자가 버튼을 눌렀을 때 최대 30개 단지를 조회합니다. 성공한 주소는 로컬 DB에 캐시됩니다.
- API가 여러 위치를 반환하면 첫 결과를 임의로 선택하지 않습니다. 미확인 주소는 지도에서 제외합니다.
- 지도 API는 네이버 부동산 매물 API가 아닙니다. 지도 위의 단지·가격·대출 정보는 제공 CSV로 구성됩니다.
- OpenAI는 첫 번째 ‘AI 채팅’ 탭에서 질문을 전송할 때만 호출합니다. 대화는 브라우저 세션에 유지하며 최근 20개 메시지를 전달합니다. 조건 변경 시 대화를 초기화합니다. 사용자 조건, 검증된 후보, 단지 집단 대출 합계를 전달하며 개인별 행은 보내지 않습니다. LangSmith 추적은 꺼두었습니다.
- 키 없이 DB 조회·조건 필터·대출 시뮬레이션·학습 모델은 실행 가능합니다. AI 응답과 지도 연결 성공을 가장하지 않습니다.

## 화면과 추천 기준

1. **지역·고객 대출**: 전국 시·군·구별 비교, 선택 지역의 고객별 아파트 가격·최초 원금·잔액, 대출 건별 상세.
2. **단지 후보·지도**: 선택한 구 안에서 거래 시작연도, 면적 허용범위, 가격 상한, 자금 부족, 월 상환 부담을 검사합니다. 면적 근접 → 참조일 최신 → 상환 부담 순으로 정렬합니다.
3. **내 대출 계획·유사 구매자**: 기존 kNN 집단 통계 및 부스팅 패턴 확률을 유지하고 실제 입력 자금 계산과 분리합니다.
4. **AI 채팅 (첫 번째 탭)**: Deep Agent가 읽기 전용 도구로 검증된 단지를 비교합니다. 구조화된 단지 ID를 검증하고 숫자 카드는 Python 계산 결과만 표시합니다.
5. **검증 결과**: CSV 정합성 및 각 모델의 검증 결과.

추천하지 못하는 경우 `NO_DATA`(지역 자료 없음), `NO_REFERENCE_IN_SCOPE`(연도·면적 참조자료 없음), `NO_MATCH`(자료는 있으나 자금 조건 미충족)를 구분합니다. 선택한 구 밖으로 자동 확대하지 않습니다. 기존 대안 통계의 지역 확대는 별도의 설명된 패널에서만 표시합니다.

가격은 조건에 맞는 면적의 **단지별 가장 최근 거래 참조가격**입니다. 현재 DB 평가액과 구분합니다. 동일 단지는 정규화 주소+단지명으로 묶고 같은 거래 ID를 지역 가격 집계에서 중복 계산하지 않습니다. 이름이 바뀐 같은 단지나 과거 행정구역 개편을 완전히 통합한 공식 단지 마스터는 아닙니다.

지역은 보유 아파트 소재지입니다. `전라북도→전북특별자치도`, 시·구 붙임 표기를 정리했습니다. 기존 코드의 `전남광주통합특별시` 분리 규칙(구는 광주, 시·군은 전남)을 유지하며 원본 지역명도 보존했습니다.

## 데이터 검증

- 주택 보유 고객·부동산 각 42,225행, 대출 52,846행, 건강 AI 파일 80,000행.
- 건강 파일의 나머지 고객을 대출 없음으로 단정하지 않습니다. 현재 조회 서비스는 제공된 주택 보유자 범위입니다.
- 학습 대상 26,400행: 2022년 이후, 매입 당시 20세 이상, 자기자금 양수.
- 고객·자산 기본키, 연결, 매입 연결 최초 원금, 고객별 잔액 합계를 검증했습니다.
- 건축연도가 매입연도보다 늦은 원본 7행은 보고서에 표시했습니다. 단지 추천에서는 제외합니다.
- `original_principal`은 최초 원금, `outstanding_balance`는 잔액입니다. `principal`은 이 데이터에서 잔액과 같아 최초 원금으로 사용하지 않습니다.
- 조회 대출은 **전체 대출**, 구매 패턴 학습은 **주택 구매 연결 대출**입니다.

## kNN·부스팅 평가 결론

2022~2024 학습 / 2025 검증으로 예측기 선택 후, 2026년은 모델 선택에 쓰지 않고 평가했습니다. 무작위 80/20 및 단지 단위 분리 검증도 수행했습니다.

| 2026년 독립 평가 | 기준선 | kNN | 부스팅 |
|---|---:|---:|---:|
| 대출 조합 정확도 | 41.64% | 51.66% | 51.82% |
| 조합 log loss (낮을수록 좋음) | 1.0782 | 0.9671 | 0.9620 |
| 주담대 LTV MAE | 12.19%p | 6.52%p | 6.03%p |
| 한도대출/가격 비율 MAE | 1.923%p | 1.876%p | 1.857%p |

주담대 비율은 유용한 패턴 신호가 있으나 조합 예측은 제한적이고 한도대출 비율 R²는 0.052로 낮습니다. 부스팅을 구매 패턴 참고값으로 유지하고 kNN은 유사 집단 설명에 씁니다. 근소한 조합 성능 차이를 확실한 우월성으로 주장하지 않습니다.

현재 소득·자산·소비로 과거 구매를 설명하는 후향 편향, 구매 성공자만 있는 선택 편향이 남습니다. 건강 AI 점수나 대출 결과 파생값은 입력에 넣지 않습니다. 조건부 대출비율 성능을 대출승인 또는 전체 추천 정확도로 해석하지 않습니다. 추천 적합도 평가용 정답 데이터는 제공되지 않았습니다.

원금·월상환·자금부족 판정은 모델 확률 대신 명시적 계산을 사용합니다. 현금이 충분하면 불필요한 대출을 만들지 않습니다. 기존 월상환, 예비비, 부대비용을 반영합니다. LTV 70%, 상환 부담 40% 등은 조정 가능한 가정이며 현행 규제라고 주장하지 않습니다.

## 구성

- `frontend/src/MobileApp.tsx`, `frontend/src/mobile.css`: 현재 React 모바일 화면과 스타일
- `frontend/src/App.tsx`, `frontend/src/styles.css`: 이전 화면 참고 코드, 현재 진입점에서는 미사용
- `frontend/src/NaverMap.tsx`: 브라우저 네이버 지도
- `housing_app/api.py`: FastAPI 및 화면 제공
- `app.py`, `housing_app/ui.py`: 이전 Streamlit 구현 참고용
- `housing_app/prep.py`, `housing_app/recommender.py`: 기존 전처리·유사 집단·구매 패턴
- `scripts/train.py`, `scripts/model_evaluation.py`: 비교 검증과 선택 모델 저장
- `scripts/audit_data.py`, `scripts/build_database.py`: CSV 검사, SQLite 생성
- `housing_app/housing_repository.py`, `housing_app/regions.py`: 조회와 지역 정규화
- `housing_app/finance.py`: 자금 계산과 단지 선별
- `housing_app/llm_advisor.py`: OpenAI Responses와 Deep Agents 도구 호출
- `housing_app/naver_maps.py`: 서버 Geocoding과 지도 마커
- `tests/test_system.py`, `tests/test_api.py`: 합계·필터·경계·LLM 도구·지도 mock·HTTP API 검사

## 외부 문서

- [OpenAI Responses](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [Deep Agents profiles](https://docs.langchain.com/oss/python/deepagents/profiles)
- [NAVER Dynamic Map](https://navermaps.github.io/maps.js.en/docs/tutorial-2-Getting-Started.html)
- [NAVER Geocoding](https://api.ncloud-docs.com/docs/en/application-maps-geocoding)

자동 테스트는 외부 통신 없는 가짜 모델과 HTTP mock을 사용합니다. 브라우저에서 네이버 지도 스크립트와 마커 렌더링은 확인했으며, 배경 타일은 현재 접속 주소에서 네이버 인증 실패가 나타납니다. OpenAI의 실제 응답은 검증하지 않았습니다.
