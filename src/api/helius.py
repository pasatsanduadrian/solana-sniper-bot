"""Async wrapper for Helius API endpoints used in the bot."""
import os
import httpx
from typing import Any, Dict, Optional

class HeliusAPI:
    """Minimal async client for Helius."""

    BASE_URL = "https://api.helius.xyz"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("HELIUS_KEY", "demo")
        self.session: Optional[httpx.AsyncClient] = None

    async def _client(self) -> httpx.AsyncClient:
        if not self.session:
            self.session = httpx.AsyncClient(timeout=10)
        return self.session

    async def close(self) -> None:
        if self.session:
            await self.session.aclose()
            self.session = None

    async def get_token_holders(self, mint: str) -> Dict[str, Any]:
        """Return holder information for a token mint."""
        client = await self._client()
        url = f"{self.BASE_URL}/v0/tokens/{mint}/holders"
        params = {"api-key": self.api_key}
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_token_metadata(self, mint: str) -> Dict[str, Any]:
        """Return metadata for a token mint."""
        client = await self._client()
        url = f"{self.BASE_URL}/v0/tokens/metadata"
        params = {"api-key": self.api_key, "mint": mint}
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
