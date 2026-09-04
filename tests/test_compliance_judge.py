import pytest
from src.ai.compliance_judge import evaluate_email_compliance
from src.config import settings

@pytest.mark.asyncio
async def test_compliance_mock_pass():
    # Verify fallback logic works when API key is not set
    original_key = settings.anthropic_api_key
    settings.anthropic_api_key = "your_anthropic_api_key_here"
    
    result = await evaluate_email_compliance("test email", "STAGE_1")
    assert result["verdict"] == "PASS"
    
    settings.anthropic_api_key = original_key
