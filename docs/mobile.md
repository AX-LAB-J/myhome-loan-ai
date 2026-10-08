# 모바일 화면 및 접속

## 화면 코드 구조

| 파일 | 역할 |
|---|---|
| `frontend/src/main.tsx` | React 진입점 |
| `frontend/src/App.tsx` | 상태·데이터 요청·헤더·화면 전환 |
| `frontend/src/screens/*.tsx` | 화면 6개 (홈, 지역·단지 찾기, 단지 상세, 내 재무 정보, 계산 가정, 데이터 연결 현황) |
| `frontend/src/components/` | 메뉴(`Drawer`), 채팅(`ChatSheet`), 네이버 지도(`NaverMap`), 공통 부품(`ui.tsx`) |
| `frontend/src/format.ts` | 금액·비율 표시, 구매력 구간 계산 |
| `frontend/src/api.ts` | API 응답 타입과 fetch 함수 |
| `frontend/src/styles.css` | 전체 스타일 |

## 실행과 휴대폰 접속

PC에서는 `start.cmd` 실행 후 `http://127.0.0.1:8501`로 접속합니다. 같은 Wi-Fi의 휴대폰에서는 기존 서버를 종료하고 `start-mobile.cmd`를 실행한 뒤 PC의 사설 IPv4 주소로 접속합니다. 네이버 클라우드 콘솔의 Maps 서비스 URL에 실제 접속 주소가 등록되어 있어야 지도가 표시됩니다. 브라우저에는 지도용 공개 Client ID만 전달되고, Client Secret과 OpenAI 키는 서버에만 있습니다.

## 지도 마커 출처

`apartment_trades.address` → `POST /api/map/resolve` → `geocode_cache` 또는 네이버 지오코딩(최대 8건 병렬) → `NaverMap.tsx` 마커. 한 번 찾은 좌표는 DB에 캐시되어 다음부터 외부 호출 없이 표시됩니다. 마커를 누르면 현재 목록과 같은 면적·거래 기간의 거래 참조값을 보여줍니다.
