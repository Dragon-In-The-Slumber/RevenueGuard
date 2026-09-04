import pytest
from src.graph.state import RecoveryState
from src.graph.nodes import check_overdue, check_cooldown

@pytest.mark.asyncio
async def test_check_overdue():
    state = RecoveryState(
        invoice_id=1,
        client_name="Test",
        client_email="test@test.com",
        amount=100.0,
        due_date="2024-01-01",
        current_status="ISSUED",
        days_overdue=5,
        escalation_stage="STAGE_1",
        audit_entries=[],
        should_send_email=False
    )
    new_state = await check_overdue(state)
    assert new_state["new_status"] == "OVERDUE"
    assert len(new_state["audit_entries"]) == 1

@pytest.mark.asyncio
async def test_check_cooldown():
    state = RecoveryState(should_send_email=False)
    new_state = await check_cooldown(state)
    assert new_state["should_send_email"] is True
