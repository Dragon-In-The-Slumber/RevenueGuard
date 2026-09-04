import pytest
from src.graph.builder import compiled_graph

@pytest.mark.asyncio
async def test_full_graph_pass_through():
    state = {
        "invoice_id": 1,
        "client_name": "Test Client",
        "client_email": "test@test.com",
        "amount": 100.0,
        "due_date": "2024-01-01",
        "current_status": "ISSUED",
        "days_overdue": 5,
        "escalation_stage": "STAGE_1",
        "audit_entries": []
    }
    
    final_state = await compiled_graph.ainvoke(state)
    assert final_state["new_status"] == "NOTIFIED_1"
    assert len(final_state["audit_entries"]) > 0
    assert "drafted_email" in final_state
