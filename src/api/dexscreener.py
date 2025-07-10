import aiohttp
from typing import Any, Dict, List

class DexScreenerAPI:
    """Minimal async client for DEX Screener public endpoints."""

    BASE_URL = "https://api.dexscreener.com/latest"

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        self.session = session

    async def search_tokens(self, query: str) -> List[Dict[str, Any]]:
        """Search for pairs by query and return raw pair data."""
        url = f"{self.BASE_URL}/dex/search"
        params = {"q": query}
        close_session = False
        if not self.session:
            self.session = aiohttp.ClientSession()
            close_session = True
        try:
            async with self.session.get(url, params=params, timeout=10) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("pairs", []) if isinstance(data, dict) else []
        finally:
            if close_session:
                await self.session.close()
                self.session = None
