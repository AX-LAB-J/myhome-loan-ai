"""Streamlit housing explorer, transparent simulation and evidence-limited agent."""

import json
from dataclasses import asdict
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from housing_app.finance import Buyer, financing, candidates, max_affordable
from housing_app.housing_repository import HousingRepository
from housing_app.settings import Settings, BASE
from housing_app.naver_maps import cached_markers, map_html


def money(v):
    return f"{v / 1e8:,.2f}억 원" if abs(v) >= 1e8 else f"{v / 1e4:,.0f}만 원"


@st.cache_resource
def pattern_engine():
    from housing_app.recommender import Recommender

    return Recommender()


@st.cache_data
def read_report(name):
    return json.loads((BASE / "reports" / name).read_text(encoding="utf-8"))


def table(df, rename=None):
    st.dataframe(df.rename(columns=rename or {}), hide_index=True, width="stretch")


def candidate_card(r, index):
    p = r["plan"]
    with st.container(border=True):
        st.subheader(f"{index}. {r['apt_name']}")
        st.caption(
            f"{r['address']} · {r['exclusive_area_m2']:g}㎡ · 거래 참조일 {r['reference_deal_date']}"
        )
        cols = st.columns(4)
        for c, label, value in zip(
            cols,
            ["거래 참조가격", "필요 대출", "예상 월 상환", "상환 부담 비율"],
            [money(p["price"]), money(p["loan"]), money(p["payment"]), f"{p['dsr']:.1%}"],
        ):
            c.metric(label, value)
        st.write(
            f"주담대 {money(p['mortgage'])} / 한도대출 {money(p['credit'])} / 부대비용 {money(p['costs'])} / 월 잉여 {money(p['surplus'])}"
        )
        ls = r["loan_summary"]
        st.caption(
            f"해당 단지의 합성 고객 {int(ls['customers']):,}명 · 전체 대출 최초 원금 합계 {money(ls['original'])} · 잔액 합계 {money(ls['balance'])}"
        )


def main():
    st.set_page_config(
        page_title="내 집 마련 · 지역과 대출",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.html("<style>" + (BASE / "assets" / "mobile.css").read_text(encoding="utf-8") + "</style>")
    settings = Settings()
    if not settings.database_path.exists():
        st.error("조회 DB가 없습니다. 먼저 python -m scripts.build_database를 실행하세요.")
        return
    repo = HousingRepository(settings.database_path)
    regions = repo.regions()
    with st.sidebar:
        st.header("내 집 마련")
        page = st.radio(
            "화면",
            [
                "AI 채팅",
                "지역·고객 대출",
                "네이버 지도",
                "추천 단지",
                "내 대출 계획·유사 구매자",
                "검증 결과",
            ],
            key="current_page",
            label_visibility="collapsed",
        )
        if st.button("새 대화", use_container_width=True):
            st.session_state["chat_messages"] = []
        with st.expander("내 조건 · 지역 설정", expanded=False):
            st.header("내 조건")
            age = st.number_input("나이", 20, 79, 31)
            income = st.number_input("가구 연소득 (만원·세전)", 500, 200000, 7000, 100)
            assets = st.number_input("금융자산 (만원)", 0, 500000, 10000, 500)
            other = st.number_input("기타 동원 자금 (만원)", 0, 500000, 0, 500)
            consumption = st.number_input("월 소비 (만원·대출상환 제외)", 0, 5000, 250, 10)
            existing = st.number_input("기존 대출 월 상환액 (만원)", 0, 10000, 0, 10)
            reserve = st.number_input("남겨둘 예비비 (만원)", 0, 500000, 0, 100)
            st.subheader("찾는 주택")
            sido = st.selectbox("시·도", list(regions), index=list(regions).index("서울특별시"))
            districts = regions[sido]
            gu = st.selectbox(
                "시·군·구",
                districts,
                index=districts.index("노원구") if "노원구" in districts else 0,
            )
            price = st.number_input("주택가격 상한 (만원)", 3000, 400000, 50000, 1000)
            area = st.number_input("희망 전용면적 (㎡)", 12, 270, 59)
            tolerance = st.slider("면적 허용 범위 (±%)", 0, 50, 20)
            year = st.selectbox("거래 참조 시작연도", list(range(2018, 2027)), index=4)
            count = st.slider("추천 단지 수", 1, 10, 3)
            with st.expander("대출·비용 계산 가정"):
                st.caption(
                    "아래 비율은 현재 규제를 반영한 한도가 아니라 사용자가 조정하는 시뮬레이션 가정입니다."
                )
                ltv = st.slider("주담대 비율 상한 (%)", 0, 100, 70)
                dsr = st.slider("상환 부담 비율 상한 (%)", 5, 70, 40)
                rate = st.number_input("주담대 연금리 (%)", 0.0, 25.0, 4.5, 0.1)
                term = st.number_input("주담대 만기 (년)", 1, 50, 30)
                cost = st.number_input("부대비용 적립률 (%)", 0.0, 20.0, 4.0, 0.5)
                allow = st.checkbox("한도대출도 가정에 포함", False)
                credit_rate = st.number_input("한도대출 연금리 (%)", 0.0, 25.0, 7.0, 0.1)
                st.caption(
                    "한도대출은 주택가격의 최대 12%, 월 부담은 잔액 × (월금리 + 0.3%)인 기존 합성 데이터 가정입니다. 실제 DSR 산정과 다를 수 있습니다."
                )
        with st.expander("서비스 안내 · 연결 상태"):
            st.caption(
                "합성 고객의 교육용 DB입니다. 가격은 과거 거래 참조값이며 현재 매물·시세가 아닙니다. 대출 계산은 입력 가정에 따른 시뮬레이션이며 금융기관의 승인을 보장하지 않습니다."
            )
            st.caption(f"OpenAI 모델: {settings.main_model}")
            st.caption(
                "OpenAI 키 설정됨 · 실제 인증은 질문할 때 확인합니다."
                if settings.openai_api_key.get_secret_value()
                else "OpenAI 키 미설정"
            )
            st.caption(
                "대화는 현재 세션에서 유지되며 조건을 바꾸면 초기화됩니다. 최근 20개 메시지와 입력 조건·후보 집계가 AI에 전달됩니다."
            )
    if ltv == 0:
        st.warning(
            "주담대 비율 상한은 1% 이상으로 설정하세요. 현금 구매는 필요 대출이 자동으로 0이 됩니다."
        )
        return
    buyer = Buyer(
        age=age,
        income=income * 1e4,
        assets=assets * 1e4,
        other_funds=other * 1e4,
        consumption=consumption * 1e4,
        existing_payment=existing * 1e4,
        reserve=reserve * 1e4,
        price=price * 1e4,
        area=area,
        sido=sido,
        sigungu=gu,
        area_tolerance=tolerance / 100,
        min_year=year,
        max_results=count,
        ltv_cap=ltv / 100,
        dsr_cap=dsr / 100,
        mortgage_rate=rate,
        term=term,
        cost_rate=cost / 100,
        allow_credit=allow,
        credit_rate=credit_rate,
    )
    result = candidates(repo, buyer)
    signature = json.dumps(asdict(buyer), sort_keys=True)
    if st.session_state.get("buyer_signature") != signature:
        st.session_state["chat_messages"] = []
        st.session_state["buyer_signature"] = signature
    if page == "지역·고객 대출":
        st.subheader(f"{sido} {gu} · 보유 아파트 소재지 기준")
        st.caption(
            "모든 기간의 합성 주택 보유 고객을 조회합니다. 원금은 최초 실행액, 잔액은 현재 미상환액이며 고객의 전체 대출을 합산합니다. 후보 추천의 가격·면적 조건은 추천 단지 화면에 적용됩니다."
        )
        customers = repo.customers(sido, gu)
        cols = st.columns(3)
        cols[0].metric("고객", f"{len(customers):,}명")
        cols[1].metric("최초 대출원금 합계", money(customers.all_original.sum()))
        cols[2].metric("현재 대출잔액 합계", money(customers.all_balance.sum()))
        with st.expander("전국·시도별 비교", expanded=False):
            all_summary = repo.summary()
            table(
                all_summary,
                {
                    "sido": "시·도",
                    "sigungu": "시·군·구",
                    "trades": "고유 거래 참조 수",
                    "avg_price": "평균 참조가격(원)",
                    "min_price": "최저(원)",
                    "max_price": "최고(원)",
                    "customers": "고객 수",
                    "original": "최초 원금 합계(원)",
                    "balance": "잔액 합계(원)",
                },
            )
        table(
            customers,
            {
                "customer_id": "합성 고객 ID",
                "sido": "시도",
                "sigungu": "시군구",
                "apt_name": "아파트",
                "exclusive_area_m2": "면적(㎡)",
                "purchase_reference_price": "매입 참조가격(원)",
                "estimated_value": "DB 평가액(원)",
                "all_loan_count": "대출 수",
                "all_original": "최초 원금 합계(원)",
                "all_balance": "잔액 합계(원)",
            },
        )
        if len(customers):
            customer = st.selectbox("대출 상세를 볼 고객 ID", customers.customer_id.tolist())
            table(
                repo.customer_loans(customer),
                {
                    "original_principal": "최초 원금(원)",
                    "outstanding_balance": "현재 잔액(원)",
                    "interest_rate": "금리(%)",
                    "housing_purchase_linked": "주택 구매 연결",
                },
            )
    if page == "추천 단지":
        st.subheader(f"{sido} {gu} · 내 조건에 맞는 단지")
        statuses = {
            "NO_DATA": "이 지역은 DB 자료가 없습니다.",
            "NO_REFERENCE_IN_SCOPE": "선택한 거래연도·면적에 해당하는 참조자료가 없습니다.",
            "NO_MATCH": "조회한 단지 중 가격·자금·상환 부담 조건을 모두 충족하는 단지가 없습니다.",
        }
        if result["status"] != "MATCHES":
            st.warning(statuses[result["status"]])
        else:
            st.caption(
                f"검토 {result['examined']:,}개 단지 중 조건 충족 {result['matched_count']:,}개. 면적 근접도 → 거래일 최신 → 상환 부담 순서로 {len(result['candidates'])}개 표시."
            )
            for i, r in enumerate(result["candidates"], 1):
                candidate_card(r, i)
    if page == "네이버 지도":
        st.subheader(f"네이버 지도 · {sido} {gu}")
        browse = repo.trades(sido, gu).drop_duplicates("complex_id").head(30).to_dict("records")
        for row in browse:
            row["loan_summary"] = repo.complex_loans(row["complex_id"])
        if not settings.naver_maps_client_id:
            st.info("네이버 지도 키를 설정해주세요.")
        else:
            markers, missing = cached_markers(browse, settings, resolve=False)
            map_slot = st.empty()
            with map_slot.container():
                components.html(map_html(markers, settings.naver_maps_client_id), height=575)
            # Show the base map first; resolve uncached coordinates once per region/session.
            region_key = f"{sido}|{gu}"
            attempted = st.session_state.setdefault("map_regions_attempted", set())
            if missing and region_key not in attempted:
                attempted.add(region_key)
                try:
                    markers, missing = cached_markers(browse, settings, resolve=True)
                    with map_slot.container():
                        components.html(
                            map_html(markers, settings.naver_maps_client_id), height=575
                        )
                except Exception as exc:
                    st.warning(
                        f"지도는 표시하지만 단지 좌표 조회에 실패했습니다 ({type(exc).__name__})."
                    )
            with st.expander("지도 안내 · 좌표 새로고침"):
                st.caption(
                    "선택 지역의 최근 참조 단지 최대 30개입니다. 가격과 대출은 합성 DB 정보이며 추천 조건 충족 여부와 별개입니다."
                )
                if missing:
                    st.caption(
                        f"좌표 미확인 {len(missing)}개. 여러 위치가 검색되면 임의로 표시하지 않습니다."
                    )
                if st.button("단지 좌표 다시 불러오기"):
                    attempted.discard(region_key)
                    st.rerun()
        with st.expander("단지별 거래 참조 목록"):
            table(repo.trades(sido, gu).drop(columns=["complex_id", "reference_trade_id"]))
    if page == "내 대출 계획·유사 구매자":
        st.subheader("입력한 가격 상한으로 구매할 때")
        p = financing(buyer, buyer.price)
        cols = st.columns(4)
        for col, label, v in zip(
            cols,
            ["필요 대출", "월 신규 상환", "상환 부담 비율", "자금 부족"],
            [money(p["loan"]), money(p["payment"]), f"{p['dsr']:.1%}", money(p["shortfall"])],
        ):
            col.metric(label, v)
        st.caption(
            "상환 부담 비율 = (신규 월 상환 + 기존 월 상환) × 12 / 세전 가구 연소득. 세금·금리변동을 반영하지 않은 시뮬레이션입니다."
        )
        if p["eligible"]:
            st.success("입력한 가정 안에서 자금·상환 조건을 충족합니다.")
        else:
            st.warning(" / ".join(p["reasons"]))
        st.metric("입력 가정에서 계산한 최대 가격", money(max_affordable(buyer)))
        st.subheader("나와 비슷한 합성 구매자")
        if not (BASE / "models" / "home_loan_models.joblib").exists():
            st.info("먼저 python -m scripts.train를 실행하세요.")
        else:
            from housing_app.prep import user_frame

            engine = pattern_engine()
            inp = asdict(buyer)
            u = user_frame(
                buyer.income,
                buyer.assets,
                buyer.consumption,
                buyer.price,
                buyer.area,
                buyer.age,
                buyer.sido,
                engine.cats,
            )
            group = engine.similar_group(u)
            desc, share, stats = engine.group_summary(group)
            st.write(" · ".join(f"{k}: {v}" for k, v in desc.items()))
            _, proba, _, _, _, _ = engine.predict(inp, group)
            compare = pd.DataFrame({"유사 집단 비중": share, "부스팅 구매 패턴 확률": proba})
            st.dataframe(compare.style.format("{:.1%}"), width="stretch")
            st.dataframe(stats.T, width="stretch")
            st.caption(
                "이 확률은 대출 승인 확률이 아닙니다. 대출 조합 정확도는 2026년 평가 약 51.8%이며 한도대출 비율 예측력은 낮습니다. 위 자금 계산에는 이 확률을 한도로 사용하지 않습니다."
            )
            with st.expander("기존 유사 구매자 대안 통계 (선택 지역 밖 포함 가능)"):
                target = max_affordable(buyer)
                if target >= 3e7:
                    alt = engine.alternatives(u, target, buyer.sido)
                    st.caption(alt["region_basis"])
                    st.dataframe(alt["regions"])
                    st.dataframe(alt["price_bands"])
                    st.dataframe(alt["area_bands"])
                else:
                    st.info("현재 가정에서 3천만 원 이상 대안 통계를 만들 수 없습니다.")
    if page == "AI 채팅":
        ready = bool(settings.openai_api_key.get_secret_value().strip())
        messages = st.session_state.setdefault("chat_messages", [])
        lookup = {x["complex_id"]: x for x in result["candidates"]}

        def render_message(message):
            with st.chat_message(message["role"]):
                st.write(message["content"])
                for i, choice in enumerate(message.get("choices", []), 1):
                    candidate_card(lookup[choice["complex_id"]], i)
                    st.write(choice["reason"])
                if message.get("caveat"):
                    st.caption(message["caveat"])

        for message in messages:
            render_message(message)
        question = st.chat_input(
            "메시지를 입력하세요" if ready else "OpenAI 키 설정이 필요합니다",
            disabled=not ready,
            max_chars=4000,
        )
        if question:
            user_message = {"role": "user", "content": question}
            render_message(user_message)
            from housing_app.llm_advisor import chat

            try:
                with st.spinner("DB 후보와 현재 조건을 확인하는 중…"):
                    answer = chat(settings, buyer, result, messages + [user_message])
                reply = {
                    "role": "assistant",
                    "content": answer["answer"],
                    "choices": answer["choices"],
                    "caveat": answer["caveat"],
                }
                messages.extend([user_message, reply])
                render_message(reply)
            except Exception as exc:
                st.error(
                    f"AI 호출 실패 ({type(exc).__name__}). OpenAI 키·모델 접근 권한·연결 상태를 확인하세요. 실패한 질문은 대화 이력에 저장하지 않았습니다."
                )
    if page == "검증 결과":
        st.subheader("CSV 및 모델 평가")
        report = read_report("model_evaluation.json")
        st.write(
            f"학습 대상 {report['rows']:,}명 · 2025년 검증으로 선택한 모델: {report['selected']}"
        )
        table(pd.DataFrame(report["results"]))
        st.caption(
            "회귀 MAE는 비율 단위(0.01 = 1%p). 2026년 평가, 무작위 평가, 단지 분리 평가를 실행했습니다. 건강 AI 점수·대출 결과 파생변수는 입력에서 제외했습니다."
        )
        st.warning(
            "현재 소득·자산으로 과거 구매를 설명하는 후향 편향과 주택 보유자만의 표본 편향이 남습니다. 추천 적합도 라벨이 없어 실제 추천 정확도를 측정한 것은 아닙니다."
        )
        st.markdown((BASE / "reports" / "data_audit.md").read_text(encoding="utf-8"))
        st.caption(
            "지역명: 전라북도는 전북특별자치도로 통합. 기존 코드의 전남광주통합특별시 표기는 구는 광주, 시·군은 전남으로 분리. 원본 지역명은 DB에 보존합니다."
        )
