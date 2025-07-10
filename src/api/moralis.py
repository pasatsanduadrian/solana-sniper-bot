import os
import httpx
from typing import Any, Dict, Optional

class MoralisAPI:
    """Simple async wrapper for Moralis Solana endpoints."""

    BASE_URL = "https://solana-gateway.moralis.io"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("MORALIS_KEY")
        if not self.api_key:
            raise ValueError("Moralis API key not provided")
        self.headers = {"X-API-Key": self.api_key}

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def get_token_metadata(self, network: str, address: str) -> Dict[str, Any]:
        """Retrieve metadata for a SPL token."""
        return await self._get(f"/token/{network}/{address}/metadata")

    async def get_token_price(self, network: str, address: str) -> Dict[str, Any]:
        """Retrieve token price information."""
        return await self._get(f"/token/{network}/{address}/price")

    async def get_wallet_tokens(self, network: str, address: str) -> Dict[str, Any]:
        """Retrieve SPL token balances for a wallet."""
        return await self._get(f"/account/{network}/{address}/tokens")


async def main() -> None:
    """Basic usage example printing a few API calls."""
    api = MoralisAPI()
    # Wrapped SOL address
    sol_address = "So11111111111111111111111111111111111111112"
    metadata = await api.get_token_metadata("mainnet", sol_address)
    print("Metadata:", metadata)
    price = await api.get_token_price("mainnet", sol_address)
    print("Price:", price)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
