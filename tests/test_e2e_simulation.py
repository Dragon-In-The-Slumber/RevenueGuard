import pytest
from src.engine.core_loop import process_simulation_tick
from src.persistence.crud import generate_fake_invoices
from src.persistence.database import async_session
from datetime import datetime

@pytest.mark.asyncio
async def test_e2e_batch_and_tick():
    async with async_session() as db:
        # Generate a small batch
        count = await generate_fake_invoices(db, 5)
        assert count == 5
        
        # Run one tick
        processed = await process_simulation_tick(db, datetime.utcnow())
        assert processed > 0
