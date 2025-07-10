"""Simple checks for MoralisAPI endpoints."""
import asyncio
import os

from src.api.moralis import MoralisAPI

async def run() -> None:
    api_key = os.getenv("MORALIS_KEY")
    if not api_key:
        print("MORALIS_KEY env var missing")
        return

    api = MoralisAPI(api_key)
    token = "So11111111111111111111111111111111111111112"  # wrapped SOL

    meta = await api.get_token_metadata("mainnet", token)
    print("Token Metadata:", meta)

    price = await api.get_token_price("mainnet", token)
    print("Token Price:", price)

if __name__ == "__main__":
    asyncio.run(run())
