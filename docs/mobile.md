# 모바일 화면 및 접속

현재 React 진입점은 `frontend/src/main.tsx` → `MobileApp.tsx`이며 스타일은 `frontend/src/mobile.css`입니다. 네이버 지도 컴포넌트는 `NaverMap.tsx`, API는 `housing_app/api.py`, LLM은 `housing_app/llm_advisor.py`에서 관리합니다. `App.tsx`와 `styles.css`는 이전 화면의 참고 코드이며 현재 빌드에 포함되지 않습니다.

현재 데이터는 합성 CSV/SQLite와 직접 입력한 계산 가정입니다. 추후 전처리된 DB를 연결할 예정이며, 이번 정리에서는 DB 연결을 변경하지 않았습니다. 고객 선택은 로컬 데모 기능으로 인증이 없으므로 외부 공개 서비스용으로 사용하지 않습니다.

## 실행과 휴대폰 접속

```powershell
cd C:\project_side\frontend
pnpm install --frozen-lockfile
pnpm build
cd ..
.\start.cmd
```

PC에서는 `http://127.0.0.1:8501`로 접속합니다. 같은 Wi-Fi의 휴대폰에서는 기존 서버를 종료하고 `start-mobile.cmd`를 실행한 뒤 PC의 사설 IPv4 주소로 접속합니다. 네이버 지도 사용 URL에 실제 접속 주소가 등록되어 있어야 합니다. `.env`는 보존하고 키 값은 브라우저로 전달하지 않습니다. 브라우저에는 지도용 공개 Client ID만 제공됩니다.

## 지도 마커 출처

`apartment_trades.address` → `/api/map` → `geocode_cache`/네이버 지오코딩 → `NaverMap.tsx`의 마커입니다. 기본 노원구 조회에서 최근 단지 최대 30개를 반환하며, 확인 시 30개가 유효 좌표를 가졌습니다. 마커 선택 시 현재 목록과 같은 면적·거래 기간의 거래 참조값을 사용합니다. 지도 SDK 인증과 실제 휴대폰 지도 조작은 별도 검수가 필요합니다.
