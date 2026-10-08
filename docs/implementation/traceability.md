# 버튼 추적표 (2026-10-06)

상태가 `부분 구현`인 항목은 전체 완료 또는 검수 통과를 뜻하지 않는다.

| ID | 화면/영역 | 요소 | 파일·핸들러/API | 상태·검수 근거 |
|---|---|---|---|---|
| C01 | 1. 화면 구조와 공통 규칙 | 햄버거 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| C02 | 1. 화면 구조와 공통 규칙 | 하단 ‘조건을 말로 바꿔 보세요’ | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| C03 | 1. 화면 구조와 공통 규칙 | 하단 파란 종이비행기 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| C04 | 1. 화면 구조와 공통 규칙 | 숫자 입력 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| H01 | 2. S01 홈 / 내 구매력 | 햄버거 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| H02 | 2. S01 홈 / 내 구매력 | 계산 근거 보기 | frontend/src/App.tsx·screens/, housing_app/api.py | 주석에 따라 삭제 · DEC-D01 사용자 확정 |
| H03 | 2. S01 홈 / 내 구매력 | 금리 +1%p로 다시 계산 | frontend/src/App.tsx·screens/, housing_app/api.py | 미구현 · 통합 검수 필요 |
| H04 | 2. S01 홈 / 내 구매력 | 이 범위에서 지역 찾기 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| H05 | 2. S01 홈 / 내 구매력 | 하단 채팅 입력/전송 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| N01 | 3. S02 왼쪽 사이드 메뉴 | X | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| N02 | 3. S02 왼쪽 사이드 메뉴 | 사용자 바꾸기 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| N03 | 3. S02 왼쪽 사이드 메뉴 | 내 구매력 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| N04 | 3. S02 왼쪽 사이드 메뉴 | 지역·단지 찾기 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| N05 | 3. S02 왼쪽 사이드 메뉴 | 내 재무 정보 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| N06 | 3. S02 왼쪽 사이드 메뉴 | 계산 가정 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| N07 | 3. S02 왼쪽 사이드 메뉴 | 마이데이터 연결 관리 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| N08 | 3. S02 왼쪽 사이드 메뉴 | 바깥 배경 / Escape | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| L01 | 4. S03 지역·단지 찾기 — 목록 | 목록 / 지도 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| L02 | 4. S03 지역·단지 찾기 — 목록 | 자세히 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| L03 | 4. S03 지역·단지 찾기 — 목록 | 지역 드롭다운 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| L04 | 4. S03 지역·단지 찾기 — 목록 | 전용면적 드롭다운 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| L05 | 4. S03 지역·단지 찾기 — 목록 | YYYY년 이후 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| L06 | 4. S03 지역·단지 찾기 — 목록 | 전체/안정권/가능권/한계권 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| L07 | 4. S03 지역·단지 찾기 — 목록 | 가격 낮은 순 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| L08 | 4. S03 지역·단지 찾기 — 목록 | 단지 카드 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| L09 | 4. S03 지역·단지 찾기 — 목록 | 시장 참고 펼침/접힘 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| L10 | 4. S03 지역·단지 찾기 — 목록 | 하단 채팅 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| G01 | 5. S04 구 단위 히트맵 | 목록 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| G02 | 5. S04 구 단위 히트맵 | 범위 칩 3개 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| G03 | 5. S04 구 단위 히트맵 | 필터 아이콘 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| G04 | 5. S04 구 단위 히트맵 | 구 폴리곤 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| G05 | 5. S04 구 단위 히트맵 | + / 핀치 확대 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| G06 | 5. S04 구 단위 히트맵 | − / 핀치 축소 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| G07 | 5. S04 구 단위 히트맵 | 이 구 단지 보기 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| G08 | 5. S04 구 단위 히트맵 | 선택 구 카드 ‘목록’ | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| G09 | 5. S04 구 단위 히트맵 | 하단 채팅 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| M01 | 6. S05 아파트별 지도 | 목록 / 지도 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| M02 | 6. S05 아파트별 지도 | 지역·면적·기간 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| M03 | 6. S05 아파트별 지도 | 단지 마커 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| M04 | 6. S05 아파트별 지도 | + / − | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| M05 | 6. S05 아파트별 지도 | 단지 상세 보기 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| M06 | 6. S05 아파트별 지도 | 하단 채팅 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| P01 | 7. S06 아파트 상세 | 뒤로가기 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| P02 | 7. S06 아파트 상세 | 계산 근거 보기 | frontend/src/App.tsx·screens/, housing_app/api.py | 주석에 따라 삭제 · DEC-D01 사용자 확정 |
| P03 | 7. S06 아파트 상세 | 하단 채팅 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| F01 | 8. S07 내 재무 정보 | 햄버거 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| F02 | 8. S07 내 재무 정보 | 다시 불러오기 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| F03 | 8. S07 내 재무 정보 | 기타 동원 자금 입력 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| F04 | 8. S07 내 재무 정보 | 저장하고 다시 계산 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| F05 | 8. S07 내 재무 정보 | 하단 채팅 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| F06 | 8. S07 내 재무 정보 | 집을 사면 계산에서 빼기 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| F07 | 8. S07 내 재무 정보 | 기타 ‘고치기’ | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| A01 | 9. S08 계산 가정 | 기본값으로 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| A02 | 9. S08 계산 가정 | 목표 여유자금 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| A03 | 9. S08 계산 가정 | 예비비 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| A04 | 9. S08 계산 가정 | 주담대 금리·만기 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| A05 | 9. S08 계산 가정 | 한도대출도 포함 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| A06 | 9. S08 계산 가정 | 한도대출 금리 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| A07 | 9. S08 계산 가정 | 비율 상한 2개·부대비용 적립률 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| A08 | 9. S08 계산 가정 | 금리 +1%p로 함께 계산 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| A09 | 9. S08 계산 가정 | 저장하고 다시 계산 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| A10 | 9. S08 계산 가정 | 하단 채팅 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| D01 | 10. S09 마이데이터 연결 관리 | 햄버거 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| D02 | 10. S09 마이데이터 연결 관리 | 지금 다시 불러오기 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| D03 | 10. S09 마이데이터 연결 관리 | 개인(신용)정보 수집·이용 동의 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| D04 | 10. S09 마이데이터 연결 관리 | 서비스 이용 안내 확인 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| D05 | 10. S09 마이데이터 연결 관리 | 연결 해제 | frontend/src/App.tsx·screens/, housing_app/api.py | 차단 또는 미구현 · docs/implementation/decisions.md 참조 |
| Q01 | 11. S10 LLM 채팅 바텀시트 | X / 바깥 배경 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| Q02 | 11. S10 LLM 채팅 바텀시트 | 새로 시작 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| Q03 | 11. S10 LLM 채팅 바텀시트 | 조건 칩 X | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 월 상환액 조건만 적용/되돌리기, 전체 시나리오 미검수 |
| Q04 | 11. S10 LLM 채팅 바텀시트 | 되돌리기 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 월 상환액 조건만 적용/되돌리기, 전체 시나리오 미검수 |
| Q05 | 11. S10 LLM 채팅 바텀시트 | 바뀐 결과 보기 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 월 상환액 조건만 적용/되돌리기, 전체 시나리오 미검수 |
| Q06 | 11. S10 LLM 채팅 바텀시트 | 제안 칩 3개 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
| Q07 | 11. S10 LLM 채팅 바텀시트 | 입력 및 전송 | frontend/src/App.tsx·screens/, housing_app/api.py | 부분 구현 · 브라우저/빌드 또는 코드 확인, 전체 시나리오 미검수 |
