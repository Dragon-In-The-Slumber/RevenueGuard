"""
Shared fixtures.

Two things make the suite runnable offline and deterministic: an in-memory
SQLite database (so tests never touch Postgres or leave state behind), and a
FakeLLM that removes every network call. The previous suite hit the real Claude
API and the real database with no fixtures, so it could not run in CI and cost
money when it did run.
"""

import asyncio
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.persistence.models import Base, Invoice, InvoiceStatus


@pytest_asyncio.fixture
async def engine():
    """A fresh in-memory database per test."""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncSession:
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest.fixture
def no_llm(monkeypatch):
    """
    Force the deterministic path.

    Tests assert on policy and routing, not on model output, so the model is
    removed entirely rather than mocked at the HTTP layer.
    """
    # Both bindings must be patched: agent_policy does
    # `from src.ai.llm import _llm_unavailable`, which is a separate name. Patching
    # only src.ai.llm left decide_action calling the live API, so the suite hit the
    # network and spent 45s timeouts x 4 retries per decision.
    disabled = lambda client_name=None: "test: LLM disabled"
    for target in ("src.ai.llm._llm_unavailable",
                   "src.ai.agent_policy._llm_unavailable",
                   "src.ai.compliance_judge._llm_unavailable"):
        monkeypatch.setattr(target, disabled)
    return True


@pytest.fixture
def fake_llm(monkeypatch):
    """
    A stand-in model returning a scripted AgentAction.

    Lets a test drive the *model* path — including with_structured_output — with
    no network access.
    """
    from src.ai.agent_policy import AgentAction

    scripted = {"value": AgentAction(
        action="WAIT", wait_days=5,
        reasoning="Scripted decision for tests.",
        confidence=0.9, expected_outcome="Client pays unprompted.",
    )}

    class _Structured:
        async def ainvoke(self, _prompt):
            return scripted["value"]

    class _FakeLLM:
        def with_structured_output(self, _schema):
            return _Structured()

        async def ainvoke(self, _prompt):
            class R:
                content = "fake response"
            return R()

    available = lambda client_name=None: None
    for target in ("src.ai.llm._llm_unavailable",
                   "src.ai.agent_policy._llm_unavailable",
                   "src.ai.compliance_judge._llm_unavailable"):
        monkeypatch.setattr(target, available)
    for target in ("src.ai.llm.get_llm",
                   "src.ai.agent_policy.get_llm",
                   "src.ai.compliance_judge.get_llm"):
        monkeypatch.setattr(target, lambda **kw: _FakeLLM())
    return scripted


def make_invoice(**overrides) -> Invoice:
    """An invoice with sane defaults; override only what a test cares about."""
    defaults = dict(
        amount=100000.0,
        client_name="Acme Corp",
        client_email="finance@acmecorp.com",
        due_date=datetime(2026, 1, 1),
        status=InvoiceStatus.OVERDUE,
        escalation_stage="STAGE_1",
        contact_attempts=0,
        relationship_score=1.0,
    )
    defaults.update(overrides)
    return Invoice(**defaults)


@pytest.fixture
def invoice_factory():
    return make_invoice


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """
    No test may touch the network.

    Disabling the model was not enough: every payment link went to the real
    Razorpay API, which made the e2e suite take nine minutes. Stubbing the client
    to None forces the documented mock path, which is also what a contributor
    without keys gets.
    """
    monkeypatch.setattr("src.integrations.razorpay_client.get_client", lambda: None)

    # ChromaDB runs ONNX embedding inference on every retrieval — ~0.16s a call,
    # and a 10-day run over 8 invoices makes hundreds. The profile text is served
    # from the roster instead; no test asserts on retrieved wording.
    async def _profile_text(client_name, query, top_k=3):
        from src.domain.clients import get_profile
        return get_profile(client_name).narrative.strip()

    async def _profile_with_metadata(client_name, query, top_k=3):
        from src.domain.clients import get_profile, profile_as_dict
        profile = get_profile(client_name)
        return {"context": profile.narrative.strip(),
                "metadata": profile_as_dict(profile),
                "matched": bool(profile.narrative)}

    monkeypatch.setattr("src.graph.nodes.search_client_context", _profile_text)
    monkeypatch.setattr("src.rag.vector_store.search_client_context", _profile_text, raising=False)
    monkeypatch.setattr("src.rag.vector_store.search_client_context_with_metadata",
                        _profile_with_metadata, raising=False)

    async def _no_slack(*args, **kwargs):
        return None

    monkeypatch.setattr("httpx.AsyncClient.post", _no_slack, raising=False)

    # Fail loudly rather than silently making a real API call. A test that wants
    # the model path must use the fake_llm fixture, which overrides this.
    def _forbidden(*args, **kwargs):
        raise AssertionError(
            "A test tried to construct a real model client. Use the no_llm or "
            "fake_llm fixture."
        )

    # Every module that imported get_llm by name holds its own binding. Patching
    # only src.ai.llm leaves the others calling the live API — which is how the
    # suite silently went back to hitting the network after an import was hoisted.
    for target in ("src.ai.llm.get_llm",
                   "src.ai.agent_policy.get_llm",
                   "src.ai.compliance_judge.get_llm"):
        monkeypatch.setattr(target, _forbidden)
