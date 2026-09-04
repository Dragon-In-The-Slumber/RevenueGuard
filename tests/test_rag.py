import pytest
from src.rag.vector_store import search_client_context
from src.rag.seed_data import seed_database

@pytest.mark.asyncio
async def test_rag_retrieval():
    seed_database()
    result = await search_client_context("Acme Corp", "contract terms")
    assert "Acme Corp" in result
    assert "Net-60 payment terms" in result
