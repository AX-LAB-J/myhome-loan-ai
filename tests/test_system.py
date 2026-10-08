import asyncio
from dataclasses import replace
import httpx
import numpy as np
import pytest
from pydantic import Field, SecretStr
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from housing_app.finance import Buyer, financing, candidates, max_affordable
from housing_app.housing_repository import HousingRepository
from housing_app.settings import Settings
from housing_app.llm_advisor import chat_async, compact_messages, validate_advice
from housing_app.naver_maps import geocode
from housing_app.regions import normalize_region


@pytest.mark.data
def test_all_loan_totals_reconcile_without_duplicate_join():
    repo = HousingRepository()
    summary = repo.summary()
    expected = repo.query(
        "SELECT sum(original_principal) AS original,sum(outstanding_balance) AS balance FROM loans_raw"
    ).iloc[0]
    assert summary.customers.sum() == 42225
    assert np.isclose(summary.original.sum(), expected.original, atol=0.01, rtol=0)
    assert np.isclose(summary.balance.sum(), expected.balance, atol=0.01, rtol=0)
    assert (
        summary.trades.sum() == repo.query("SELECT count(*) AS n FROM apartment_trades").iloc[0].n
    )


def test_cash_purchase_never_creates_pattern_loan():
    b = Buyer(assets=1e9, price=5e8)
    p = financing(b, b.price)
    assert p["loan"] == p["payment"] == p["shortfall"] == 0 and p["eligible"]


def test_costs_reserve_existing_debt_are_counted():
    b = Buyer(assets=3e8, price=5e8, reserve=2e7, existing_payment=1e6)
    p = financing(b, b.price)
    assert p["costs"] == 2e7 and p["need"] == 2.4e8
    assert p["dsr"] == pytest.approx((p["payment"] + 1e6) * 12 / b.income)
    assert p["surplus"] == pytest.approx(b.income / 12 - b.consumption - p["payment"] - 1e6)


def test_no_credit_when_disabled_and_zero_rate():
    b = Buyer(assets=0, mortgage_rate=0, allow_credit=False)
    p = financing(b, b.price)
    assert p["credit"] == 0 and p["shortfall"] > 0 and not p["eligible"]
    assert p["payment"] == pytest.approx(p["mortgage"] / 360)


@pytest.mark.data
def test_candidate_scope_and_no_match():
    repo = HousingRepository()
    b = Buyer(income=1e8, assets=3e8)
    result = candidates(repo, b)
    assert result["status"] == "MATCHES"
    assert len({x["complex_id"] for x in result["candidates"]}) == len(result["candidates"])
    for x in result["candidates"]:
        assert x["address"].startswith(b.sido + " " + b.sigungu)
        assert x["plan"]["eligible"]
        assert abs(x["exclusive_area_m2"] - b.area) <= b.area * b.area_tolerance
    assert (
        candidates(repo, replace(b, assets=0, other_funds=0, allow_credit=False))["status"]
        == "NO_MATCH"
    )
    assert candidates(repo, replace(b, sigungu="없는지역"))["status"] == "NO_DATA"


def test_max_price_boundary():
    b = Buyer()
    maximum = max_affordable(b)
    assert financing(b, maximum - 0.01)["eligible"]
    assert not financing(b, maximum + 1000)["eligible"]


def test_region_normalization():
    assert normalize_region("경기도", "용인수지구") == ("경기도", "용인시 수지구")
    assert normalize_region("전남광주통합특별시", "광산구") == ("광주광역시", "광산구")


def test_hallucinated_or_duplicate_ids_rejected():
    result = {"candidates": [{"complex_id": "a"}]}
    for ids in [["not-a"], ["a", "a"], []]:
        with pytest.raises(ValueError):
            validate_advice(
                {"choices": [{"complex_id": i, "reason": "x"} for i in ids], "caveat": "synthetic"},
                result,
            )


class FakeAdvisor(BaseChatModel):
    model_name: str = "gpt-6-luna"
    selected_id: str = "a"
    seen_tools: list[str] = Field(default_factory=list)

    @property
    def _llm_type(self):
        return "test-chat"

    def _get_ls_params(self, stop=None, **kwargs):
        return {"ls_provider": "openai", "ls_model_name": self.model_name}

    def bind_tools(self, tools, **kwargs):
        self.seen_tools = [t.name if hasattr(t, "name") else t["name"] for t in tools]
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if not any(isinstance(m, ToolMessage) for m in messages):
            calls = [
                {"name": "get_candidate_list", "args": {}, "id": "list"},
                {"name": "get_buyer_constraints", "args": {}, "id": "buyer"},
            ]
        else:
            calls = [
                {
                    "name": "ChatAnswer",
                    "args": {
                        "answer": "검증된 후보입니다.",
                        "choices": [
                            {
                                "complex_id": self.selected_id,
                                "reason": "검증된 예산 조건을 충족합니다.",
                            }
                        ],
                        "caveat": "합성 데이터",
                    },
                    "id": "answer",
                }
            ]
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content="", tool_calls=calls))]
        )

    def get_num_tokens_from_messages(self, messages, tools=None):
        return sum(len(str(m.content)) for m in messages)


def test_agent_tool_loop_without_network():
    result = {
        "status": "MATCHES",
        "candidates": [{"complex_id": "a", "apt_name": "검증단지", "plan": {"eligible": True}}],
    }
    model = FakeAdvisor()
    answer = asyncio.run(
        chat_async(
            Settings(openai_api_key=SecretStr("")),
            Buyer(),
            result,
            [{"role": "user", "content": "추천해줘"}],
            model=model,
        )
    )
    assert answer["choices"][0]["complex_id"] == "a"
    assert answer["recommendations"][0]["trade"]["complex_id"] == "a"
    assert set(model.seen_tools) == {
        "get_candidate_list",
        "get_candidate_details",
        "get_buyer_constraints",
        "search_homes_in_district",
        "ChatAnswer",
    }


def test_missing_key_is_reported_before_calling_openai():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        asyncio.run(
            chat_async(
                Settings(openai_api_key=SecretStr("")),
                Buyer(),
                {"status": "NO_MATCH", "candidates": []},
                [{"role": "user", "content": "질문"}],
            )
        )


def test_earlier_turns_are_replayed_as_question_and_answer_text():
    from langchain_core.messages import HumanMessage

    old_answer = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "ChatAnswer",
                "args": {"answer": "첫 답변", "choices": [], "caveat": "c"},
                "id": "a1",
            }
        ],
    )
    messages = [
        HumanMessage("첫 질문"),
        AIMessage(content="", tool_calls=[{"name": "get_candidate_list", "args": {}, "id": "t1"}]),
        ToolMessage(content="{}", tool_call_id="t1"),
        old_answer,
        ToolMessage(content="Returning structured response", tool_call_id="a1"),
        HumanMessage("둘째 질문"),
        AIMessage(content="", tool_calls=[{"name": "get_candidate_list", "args": {}, "id": "t2"}]),
        ToolMessage(content="{}", tool_call_id="t2"),
    ]
    compact = compact_messages(messages, keep_turns=6)
    assert [type(m).__name__ for m in compact] == [
        "HumanMessage",
        "AIMessage",
        "HumanMessage",
        "AIMessage",
        "ToolMessage",
    ]
    assert compact[1].content == "첫 답변" and not compact[1].tool_calls
    assert compact_messages(messages, keep_turns=0)[0].content == "둘째 질문"


def test_chat_agent_applies_region_tool_result_without_network():
    from dataclasses import replace

    class RegionAdvisor(FakeAdvisor):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if not any(isinstance(m, ToolMessage) for m in messages):
                calls = [
                    {
                        "name": "search_homes_in_district",
                        "args": {"sigungu": "성동구"},
                        "id": "region",
                    },
                    {"name": "get_buyer_constraints", "args": {}, "id": "buyer"},
                ]
            else:
                calls = [
                    {
                        "name": "ChatAnswer",
                        "args": {
                            "answer": "성동구 후보입니다.",
                            "choices": [
                                {"complex_id": "seongdong", "reason": "조회된 후보입니다."}
                            ],
                            "caveat": "합성 데이터",
                        },
                        "id": "answer",
                    }
                ]
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="", tool_calls=calls))]
            )

    buyer = Buyer()
    result = {"status": "MATCHES", "candidates": [{"complex_id": "old"}]}

    def search(current, district):
        return replace(current, sigungu=district), {
            "status": "MATCHES",
            "candidates": [{"complex_id": "seongdong"}],
        }

    answer = asyncio.run(
        chat_async(
            Settings(openai_api_key=SecretStr("")),
            buyer,
            result,
            [{"role": "user", "content": "성동구 집을 찾아줘"}],
            model=RegionAdvisor(),
            search_region=search,
        )
    )
    assert answer["applied_region"] == {"sido": buyer.sido, "sigungu": "성동구"}
    assert answer["choices"][0]["complex_id"] == "seongdong"
    assert answer["recommendations"][0]["trade"]["complex_id"] == "seongdong"


def test_chat_agent_reports_no_region_matches_without_network():
    from dataclasses import replace

    class EmptyRegionAdvisor(FakeAdvisor):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if not any(isinstance(m, ToolMessage) for m in messages):
                calls = [
                    {
                        "name": "search_homes_in_district",
                        "args": {"sigungu": "성동구"},
                        "id": "region",
                    },
                    {"name": "get_buyer_constraints", "args": {}, "id": "buyer"},
                ]
            else:
                calls = [
                    {
                        "name": "ChatAnswer",
                        "args": {"answer": "확인했습니다.", "choices": [], "caveat": "합성 데이터"},
                        "id": "answer",
                    }
                ]
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="", tool_calls=calls))]
            )

    buyer = Buyer()
    result = {"status": "NO_MATCH", "candidates": []}
    answer = asyncio.run(
        chat_async(
            Settings(openai_api_key=SecretStr("")),
            buyer,
            result,
            [{"role": "user", "content": "성동구 집을 찾아줘"}],
            model=EmptyRegionAdvisor(),
            search_region=lambda current, district: (replace(current, sigungu=district), result),
        )
    )
    assert answer["recommendations"] == []
    assert "없습니다" in answer["answer"]


def test_chat_checkpointer_keeps_context_and_requires_fresh_tools(tmp_path):
    from langchain_core.messages import HumanMessage
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    class MemoryAdvisor(FakeAdvisor):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            last_user = max(
                i for i, message in enumerate(messages) if isinstance(message, HumanMessage)
            )
            current_tools = [m for m in messages[last_user + 1 :] if isinstance(m, ToolMessage)]
            if not current_tools:
                calls = [
                    {"name": "get_candidate_list", "args": {}, "id": "list"},
                    {"name": "get_buyer_constraints", "args": {}, "id": "buyer"},
                ]
            else:
                user_count = sum(isinstance(m, HumanMessage) for m in messages)
                calls = [
                    {
                        "name": "ChatAnswer",
                        "args": {
                            "answer": f"질문 {user_count}개를 기억합니다.",
                            "choices": [],
                            "caveat": "합성 데이터",
                        },
                        "id": "answer",
                    }
                ]
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="", tool_calls=calls))]
            )

    async def run():
        buyer = Buyer()
        result = {"status": "MATCHES", "candidates": [{"complex_id": "a"}]}
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "chat.sqlite")) as saver:
            first = await chat_async(
                Settings(openai_api_key=SecretStr("")),
                buyer,
                result,
                [{"role": "user", "content": "첫 질문"}],
                model=MemoryAdvisor(),
                thread_id="thread-a",
                checkpointer=saver,
            )
        # A new connection simulates a restarted API worker using the same file.
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "chat.sqlite")) as saver:
            second = await chat_async(
                Settings(openai_api_key=SecretStr("")),
                buyer,
                result,
                [{"role": "user", "content": "앞 질문 기억해?"}],
                model=MemoryAdvisor(),
                thread_id="thread-a",
                checkpointer=saver,
            )
            other = await chat_async(
                Settings(openai_api_key=SecretStr("")),
                buyer,
                result,
                [{"role": "user", "content": "다른 대화"}],
                model=MemoryAdvisor(),
                thread_id="thread-b",
                checkpointer=saver,
            )
        return first, second, other

    first, second, other = asyncio.run(run())
    assert first["answer"] == "질문 1개를 기억합니다."
    assert second["answer"] == "질문 2개를 기억합니다."
    assert other["answer"] == "질문 1개를 기억합니다."


def test_old_checkpoint_tools_cannot_validate_new_answer(tmp_path):
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    class FirstTools(FakeAdvisor):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if not any(isinstance(m, ToolMessage) for m in messages):
                calls = [
                    {"name": "get_candidate_list", "args": {}, "id": "list"},
                    {"name": "get_buyer_constraints", "args": {}, "id": "buyer"},
                ]
            else:
                calls = [
                    {
                        "name": "ChatAnswer",
                        "args": {"answer": "첫 답변", "choices": [], "caveat": "합성 데이터"},
                        "id": "answer",
                    }
                ]
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="", tool_calls=calls))]
            )

    class NoFreshTools(FakeAdvisor):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            calls = [
                {
                    "name": "ChatAnswer",
                    "args": {
                        "answer": "이전 근거만 쓴 답변",
                        "choices": [{"complex_id": "a", "reason": "추천"}],
                        "caveat": "합성 데이터",
                    },
                    "id": "answer",
                }
            ]
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="", tool_calls=calls))]
            )

    async def run():
        buyer = Buyer()
        result = {"status": "MATCHES", "candidates": [{"complex_id": "a"}]}
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "chat.sqlite")) as saver:
            await chat_async(
                Settings(openai_api_key=SecretStr("")),
                buyer,
                result,
                [{"role": "user", "content": "첫 질문"}],
                model=FirstTools(),
                thread_id="thread-a",
                checkpointer=saver,
            )
            with pytest.raises(ValueError, match="현재 후보와 조건을 조회하지 않은 답변"):
                await chat_async(
                    Settings(openai_api_key=SecretStr("")),
                    buyer,
                    result,
                    [{"role": "user", "content": "둘째 질문"}],
                    model=NoFreshTools(),
                    thread_id="thread-a",
                    checkpointer=saver,
                )

    asyncio.run(run())


def test_geocoding_request_and_ambiguous_result():
    settings = Settings(naver_maps_client_id="public", naver_maps_client_secret=SecretStr("secret"))

    def handler(request):
        assert request.url.host == "maps.apigw.ntruss.com"
        assert request.headers["X-NCP-APIGW-API-KEY"] == "secret"
        assert request.url.params["query"] == "서울특별시 노원구 중계동 1"
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "addresses": [
                    {"x": "127.05", "y": "37.65", "jibunAddress": "서울특별시 노원구 중계동 1"}
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        assert geocode("서울특별시 노원구 중계동 1", settings, c)["latitude"] == 37.65
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"status": "OK", "addresses": [{}, {}]})
        )
    ) as c:
        assert geocode("x", settings, c) is None


def test_hwaseong_old_address_resolves_only_to_unique_matching_new_district():
    settings = Settings(naver_maps_client_id="public", naver_maps_client_secret=SecretStr("secret"))
    old = "경기도 화성시 우정읍 조암리"
    new = "경기도 화성시 만세구 우정읍 조암리"

    def handler(request):
        query = request.url.params["query"]
        addresses = (
            [{"x": "126.8139", "y": "37.085715", "jibunAddress": new}] if query == new else []
        )
        return httpx.Response(200, json={"status": "OK", "addresses": addresses})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = geocode(old, settings, client)
    assert result == {"latitude": 37.085715, "longitude": 126.8139, "matched_address": new}

    def ambiguous(request):
        query = request.url.params["query"]
        if query in ("경기도 화성시 동탄구 능동", "경기도 화성시 병점구 능동"):
            return httpx.Response(
                200,
                json={
                    "status": "OK",
                    "addresses": [{"x": "127.0", "y": "37.2", "jibunAddress": query}],
                },
            )
        return httpx.Response(200, json={"status": "OK", "addresses": []})

    with httpx.Client(transport=httpx.MockTransport(ambiguous)) as client:
        assert geocode("경기도 화성시 능동", settings, client) is None

    def exact_lot(request):
        query = request.url.params["query"]
        if query == "경기도 화성시 능동 1124":
            return httpx.Response(
                200,
                json={
                    "status": "OK",
                    "addresses": [
                        {
                            "x": "127.0548994",
                            "y": "37.2094594",
                            "jibunAddress": "경기도 화성시 동탄구 능동 1124 아파트",
                        }
                    ],
                },
            )
        return ambiguous(request)

    with httpx.Client(transport=httpx.MockTransport(exact_lot)) as client:
        result = geocode(
            "경기도 화성시 능동",
            settings,
            client,
            apt_name="동탄숲속마을자연앤경남아너스빌(1124-0)",
        )
    assert result["latitude"] == 37.2094594
    assert result["matched_address"].startswith("경기도 화성시 동탄구 능동 1124")


def test_geocode_prefers_exact_lot_among_multiple_api_results():
    settings = Settings(naver_maps_client_id="public", naver_maps_client_secret=SecretStr("secret"))

    def handler(request):
        if request.url.params["query"].endswith(" 1124"):
            return httpx.Response(
                200,
                json={
                    "status": "OK",
                    "addresses": [
                        {
                            "x": "127.0549",
                            "y": "37.2094",
                            "jibunAddress": "경기도 화성시 동탄구 능동 1124",
                        },
                        {
                            "x": "127.0550",
                            "y": "37.2100",
                            "jibunAddress": "경기도 화성시 동탄구 능동 1125",
                        },
                    ],
                },
            )
        return httpx.Response(200, json={"status": "OK", "addresses": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = geocode("경기도 화성시 능동", settings, client, apt_name="아파트(1124-0)")
    assert result == {
        "latitude": 37.2094,
        "longitude": 127.0549,
        "matched_address": "경기도 화성시 동탄구 능동 1124",
    }


class FakeChatAdvisor(FakeAdvisor):
    saw_history: bool = False

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.saw_history = any(m.content == "이전 질문" for m in messages)
        if not any(isinstance(m, ToolMessage) for m in messages):
            return super()._generate(messages, stop, run_manager, **kwargs)
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "ChatAnswer",
                                "args": {
                                    "answer": "현재 조건에 맞는 후보가 없습니다.",
                                    "choices": [],
                                    "caveat": "합성 데이터",
                                },
                                "id": "answer",
                            }
                        ],
                    )
                )
            ]
        )


def test_chat_replays_history_and_explains_empty_candidates():

    model = FakeChatAdvisor()
    answer = asyncio.run(
        chat_async(
            Settings(openai_api_key=SecretStr("")),
            Buyer(),
            {"status": "NO_MATCH", "candidates": []},
            [
                {"role": "user", "content": "이전 질문"},
                {"role": "assistant", "content": "이전 답변"},
                {"role": "user", "content": "왜 없나요?"},
            ],
            model=model,
        )
    )
    assert model.saw_history and not answer["choices"] and "없습니다" in answer["answer"]
    assert "ChatAnswer" in model.seen_tools
