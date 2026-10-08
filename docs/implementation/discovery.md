# 구현 조사 (2026-10-06)

- 실행: `side\Scripts\python.exe -m uvicorn housing_app.api:app --host 127.0.0.1 --port 8501`, `cd frontend; pnpm build`.
- React 19, TypeScript, Vite, FastAPI, SQLite. 루트와 하위 폴더에서 MySQL 접속 문자열, 드라이버, 설정 파일, 덤프를 찾지 못했다. `.env`에는 OpenAI·네이버 지도 설정명만 있다. 사용자에게 MySQL 위치를 문의했다.
- 로컬 DB는 `data/housing.sqlite`이며 `customers` 42,225건(고유 고객 ID 42,225), `loans_raw` 52,846건과 거래 테이블이 있다. README와 데이터 감사 보고서는 이를 합성 데이터로 명시한다. 2026-09-11이 거래 참조일 최댓값이다.
- 기존 UI는 AI 채팅, 추천, 지도, 지역 대출, 입력 기반 계획을 제공했다. 계좌, 마이데이터 외부 연결, 동의, 동기화, 권한 관리, 사용자별 설정 저장소가 없다.
- 계산기는 `housing_app/finance.py`의 `financing`, `max_affordable`를 사용한다. 신규 구매력 구간도 같은 `financing`으로 구한다. 기존 상환액은 `consumption`과 별도로 차감한다.
- 지도는 `frontend/src/NaverMap.tsx`, `housing_app/naver_maps.py`와 네이버 Client ID를 사용한다. 구 경계 폴리곤 자료는 없다.
- OpenAI 비밀키는 서버 `Settings`에서만 읽으며 브라우저에는 노출하지 않는다. 네이버 공개 Client ID만 `/api/meta`에 전달한다. 실제 외부 서비스 호출 성공은 검증하지 않았다.
- 현재 고객 선택은 합성 로컬 DB 탐색 기능이다. 고객 ID로 조회할 수 있으므로 인증된 실서비스에 그대로 배포하면 안 된다.
