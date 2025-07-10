import asyncio
import pytest

from src.api.dexscreener import DexScreenerAPI

@pytest.mark.asyncio
async def test_search_tokens_returns_list():
    api = DexScreenerAPI()
    try:
        pairs = await api.search_tokens("solana")
    except Exception:
        pytest.skip("network unavailable")
    assert isinstance(pairs, list)


