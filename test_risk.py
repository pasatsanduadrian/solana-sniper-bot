import pytest
from src.bot.risk import RiskManager
from src.bot.feeds import TokenData

@pytest.mark.asyncio
async def test_risk_manager_position_size():
    rm = RiskManager(base_position=10.0)
    token = TokenData(address="x", liquidity=120000, holders=1500, price_change_5m=2)
    risk = rm.assess_token_risk(token)
    size = rm.position_size(risk)
    assert size <= rm.base_position
    assert size > 0
