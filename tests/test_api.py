"""The browser-facing API preserves the local finance and DB behavior."""

from fastapi.testclient import TestClient

from housing_app.api import app
from housing_app import api as housing_api


def test_complete_customer_profiles_are_searchable_and_joined():
    client = TestClient(app)
    for customer_id, name in ((68729, "신지우"), (77193, "황예준"),
                              (6507, "황윤서"), (2098, "송민준")):
        by_id = client.get("/api/demo-customers", params={"q": str(customer_id)}).json()
        by_name = client.get("/api/demo-customers", params={"q": name}).json()
        assert any(row["customer_id"] == customer_id and row["display_name"] == name
                   for row in by_id)
        assert any(row["customer_id"] == customer_id for row in by_name)
        detail = client.get(f"/api/demo-customers/{customer_id}").json()
        assert detail["customer"]["name"] == name
        assert detail["customer"]["consumption_source"] == "budget"
        assert len(detail["accounts"]) == 2
        assert abs(detail["customer"]["account_balance_total"]
                   - sum(account["balance"] for account in detail["accounts"])) < 0.01
        assert detail["property"] is None
    purchaser = client.get("/api/demo-customers/1").json()
    assert purchaser["customer"]["consumption_source"] == "observed"
    assert purchaser["property"] is not None


def test_api_exposes_imported_data_without_secrets():
    client = TestClient(app)
    meta = client.get("/api/meta")
    assert meta.status_code == 200
    data = meta.json()
    assert data["synthetic"] is False
    assert data["openai_ready"] is False
    assert "openai_api_key" not in data
    assert "naver_maps_client_secret" not in data
    assert client.get("/api/health").json() == {"status": "ok", "database": True}
    assert client.get("/").status_code == 200


def test_region_totals_and_customer_loan_drilldown():
    client = TestClient(app)
    params = {"sido": "서울특별시", "sigungu": "노원구"}
    summary = client.get("/api/regions/summary").json()
    region = next(row for row in summary if all(row[key] == value for key, value in params.items()))
    customers = client.get("/api/customers", params=params).json()
    assert customers["total"] == region["customers"]
    assert customers["total"] > len(customers["rows"])
    customer_id = customers["rows"][0]["customer_id"]
    loans = client.get(f"/api/customers/{customer_id}/loans").json()
    assert len(loans) == customers["rows"][0]["all_loan_count"]
    assert round(sum(row["original_principal"] for row in loans)) == round(
        customers["rows"][0]["all_original"]
    )
    trades = client.get("/api/trades", params=params).json()
    assert trades["total"] == region["trades"]
    assert (
        client.get("/api/customers", params={"sido": "서울특별시", "sigungu": "없는구"}).status_code
        == 400
    )


def test_plan_recommendation_patterns_and_cached_map():
    client = TestClient(app)
    buyer = client.get("/api/meta").json()["defaults"]
    buyer["income"] = 100_000_000
    buyer["assets"] = 300_000_000
    plan = client.post("/api/plan", json=buyer).json()
    assert plan["plan"]["price"] == buyer["price"]
    assert plan["plan"]["loan_basis"] == "trained_model"
    assert plan["plan"]["mortgage"] <= buyer["price"] * plan["plan"]["model_mortgage_ratio"] + 0.01
    assert plan["max_affordable"] == plan["bands"]["possible"]
    assert plan["bands"]["maximum"] >= plan["max_affordable"]
    recommendation = client.post("/api/recommendations", json=buyer).json()
    assert recommendation["status"] == "MATCHES"
    assert recommendation["candidates"]
    patterns = client.post("/api/patterns", json=buyer).json()
    assert patterns["share"] and patterns["probability"]
    markers = client.get("/api/map", params={"sido": buyer["sido"], "sigungu": buyer["sigungu"]})
    assert markers.status_code == 200
    assert markers.json()["markers"] == []  # Test keys are disabled; no external geocoding.
    assert (
        client.post(
            "/api/chat",
            json={
                "buyer": buyer,
                "thread_id": "c0a801cb-921e-4cb2-8114-cf0d588da15a",
                "message": "안녕",
            },
        ).status_code
        == 503
    )


def test_seodaemun_recommendations_use_affordability_not_past_purchase_price():
    client = TestClient(app)
    meta = client.get("/api/meta").json()
    customer = client.get("/api/demo-customers/13").json()["customer"]
    buyer = meta["defaults"]
    buyer.update(
        age=customer["age"], income=customer["household_annual_income"],
        assets=customer["financial_assets_estimated"],
        consumption=customer["avg_monthly_consumption"],
        existing_payment=customer["monthly_debt_service"],
        price=customer["purchase_reference_price"], area=customer["exclusive_area_m2"],
        sido="서울특별시", sigungu="서대문구",
    )
    bands = client.post("/api/plan", json=buyer).json()["bands"]
    result = client.post("/api/recommendations", json=buyer).json()
    assert result["status"] == "MATCHES"
    assert len(result["candidates"]) == 3
    assert all(buyer["price"] < row["purchase_reference_price"] <= bands["possible"]
               for row in result["candidates"])
    assert all(row["plan"]["eligible"] for row in result["candidates"])


def test_map_selection_uses_exact_visible_complexes(monkeypatch):
    from types import SimpleNamespace

    repo = housing_api.repository()
    all_trades = repo.trades("서울특별시", "성동구").drop_duplicates("complex_id")
    selected = all_trades.iloc[-1].complex_id
    monkeypatch.setattr(housing_api, "Settings", lambda: SimpleNamespace(naver_maps_client_id="test"))
    monkeypatch.setattr(housing_api, "cached_markers", lambda rows, settings, resolve: (rows, []))
    response = TestClient(app).post(
        "/api/map/resolve?sido=서울특별시&sigungu=성동구",
        json={"complex_ids": [selected]},
    )
    assert response.status_code == 200
    assert [row["complex_id"] for row in response.json()["markers"]] == [selected]


def test_customer_home_remains_on_map_when_band_has_no_complexes(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(housing_api, "Settings", lambda: SimpleNamespace(naver_maps_client_id="test"))
    monkeypatch.setattr(housing_api, "cached_markers", lambda rows, settings, resolve: (rows, []))
    response = TestClient(app).post(
        "/api/map/resolve?sido=서울특별시&sigungu=강동구",
        json={"complex_ids": [], "customer_id": 7},
    )
    assert response.status_code == 200
    assert len(response.json()["markers"]) == 1
    assert response.json()["markers"][0]["is_owned"] is True


def test_chat_route_uses_existing_agent_without_live_api(monkeypatch, tmp_path):
    from housing_app import llm_advisor

    observed = {}

    async def fake_chat(
        settings, buyer, result, messages, search_region=None, thread_id=None, checkpointer=None
    ):
        observed["buyer"] = buyer
        observed["result"] = result
        observed["messages"] = messages
        observed["search_region"] = search_region
        observed["thread_id"] = thread_id
        observed["checkpointer"] = checkpointer
        return {"answer": "안녕하세요", "choices": [], "caveat": "합성 데이터"}

    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setenv("CHAT_CHECKPOINT_PATH", str(tmp_path / "chat.sqlite"))
    monkeypatch.setattr(llm_advisor, "chat_async", fake_chat)
    client = TestClient(app)
    buyer = client.get("/api/meta").json()["defaults"]
    response = client.post(
        "/api/chat",
        json={
            "buyer": buyer,
            "thread_id": "c0a801cb-921e-4cb2-8114-cf0d588da15a",
            "message": "안녕",
        },
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "안녕하세요"
    assert observed["result"]["status"] in {"MATCHES", "NO_MATCH"}
    assert observed["messages"] == [{"role": "user", "content": "안녕"}]
    assert observed["thread_id"] == "c0a801cb-921e-4cb2-8114-cf0d588da15a"
    assert observed["checkpointer"] is not None
    changed, scoped = observed["search_region"](observed["buyer"], "성동구")
    assert changed.sigungu == "성동구"
    assert scoped["status"] in {"MATCHES", "NO_MATCH", "NO_DATA", "NO_REFERENCE_IN_SCOPE"}


def test_delete_chat_removes_checkpoint(monkeypatch, tmp_path):
    import asyncio
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from langgraph.graph import StateGraph, MessagesState, START

    path = tmp_path / "chat.sqlite"
    thread_id = "c0a801cb-921e-4cb2-8114-cf0d588da15a"

    async def seed_and_read(seed):
        async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
            config = {"configurable": {"thread_id": thread_id}}
            if seed:
                graph = StateGraph(MessagesState)
                graph.add_node(
                    "reply", lambda state: {"messages": [{"role": "assistant", "content": "saved"}]}
                )
                graph.add_edge(START, "reply")
                await graph.compile(checkpointer=saver).ainvoke(
                    {"messages": [{"role": "user", "content": "hello"}]}, config
                )
            return await saver.aget_tuple(config)

    assert asyncio.run(seed_and_read(True)) is not None
    monkeypatch.setenv("CHAT_CHECKPOINT_PATH", str(path))
    response = TestClient(app).delete(f"/api/chat/{thread_id}")
    assert response.status_code == 200
    assert asyncio.run(seed_and_read(False)) is None


def test_failed_chat_discards_old_checkpoint(monkeypatch, tmp_path):
    import asyncio
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from langgraph.graph import StateGraph, MessagesState, START
    from housing_app import llm_advisor

    path = tmp_path / "chat.sqlite"
    thread_id = "c0a801cb-921e-4cb2-8114-cf0d588da15a"

    async def checkpoint(seed):
        async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
            config = {"configurable": {"thread_id": thread_id}}
            if seed:
                graph = StateGraph(MessagesState)
                graph.add_node(
                    "reply", lambda state: {"messages": [{"role": "assistant", "content": "old"}]}
                )
                graph.add_edge(START, "reply")
                await graph.compile(checkpointer=saver).ainvoke(
                    {"messages": [{"role": "user", "content": "old"}]}, config
                )
            return await saver.aget_tuple(config)

    async def fail_chat(*args, **kwargs):
        raise ValueError("invalid current response")

    assert asyncio.run(checkpoint(True)) is not None
    monkeypatch.setenv("CHAT_CHECKPOINT_PATH", str(path))
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(llm_advisor, "chat_async", fail_chat)
    client = TestClient(app)
    buyer = client.get("/api/meta").json()["defaults"]
    response = client.post(
        "/api/chat", json={"buyer": buyer, "thread_id": thread_id, "message": "new"}
    )
    assert response.status_code == 502
    assert asyncio.run(checkpoint(False)) is None
