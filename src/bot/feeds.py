# feeds.py - Implementare completă feeds
import asyncio
import aiohttp
import httpx
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger("bot.feeds")

@dataclass
class TokenData:
    """Enhanced token information."""
    
    address: str
    symbol: str = ""
    name: str = ""
    price: float = 0.0
    price_change_5m: float = 0.0
    volume_5m: float = 0.0
    volume_24h: float = 0.0
    market_cap: float = 0.0
    liquidity: float = 0.0
    holders: int = 0
    created_at: Optional[datetime] = None
    score: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def calculate_score(self) -> float:
        """Calculate trading score based on metrics."""
        score = 0.0
        
        # Volume score (0-30 points)
        if self.volume_5m > 100000:  # >100k USDC
            score += 30
        elif self.volume_5m > 50000:
            score += 20
        elif self.volume_5m > 10000:
            score += 10
            
        # Price momentum (0-30 points)
        if self.price_change_5m > 10:
            score += 30
        elif self.price_change_5m > 5:
            score += 20
        elif self.price_change_5m > 2:
            score += 10
            
        # Liquidity score (0-20 points)
        if self.liquidity > 50000:
            score += 20
        elif self.liquidity > 20000:
            score += 10
            
        # Age penalty (0-20 points)
        if self.created_at:
            age_hours = (datetime.utcnow() - self.created_at).total_seconds() / 3600
            if age_hours < 1:  # Less than 1 hour old
                score += 20
            elif age_hours < 6:
                score += 10
                
        self.score = score
        return score

class FeedAggregator:
    """Aggregates token data from multiple services."""
    
    def __init__(self) -> None:
        self.session: Optional[aiohttp.ClientSession] = None
        self.tokens: Dict[str, TokenData] = {}
        self.running = False
        self.helius_key = os.getenv("HELIUS_KEY", "demo")
        self.moralis_key = os.getenv("MORALIS_KEY")
        
    async def start(self) -> None:
        self.session = aiohttp.ClientSession()
        self.running = True
        asyncio.create_task(self._fetch_loop())
        logger.info("Feed aggregator started")
        
    async def stop(self) -> None:
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Feed aggregator stopped")
        
    async def _fetch_loop(self) -> None:
        while self.running:
            try:
                await self._fetch_feeds()
                await asyncio.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logger.error(f"Error in fetch loop: {e}")
                await asyncio.sleep(10)
                
    async def _fetch_feeds(self) -> None:
        """Fetch data from all sources."""
        tasks = []
        
        # Fetch new tokens from DEX Screener
        tasks.append(self._fetch_dex_screener())
        
        # Update existing tokens with Moralis data
        if self.moralis_key:
            for address in list(self.tokens.keys())[:5]:  # Rate limit: 5 at a time
                tasks.append(self._update_token_moralis(address))
                
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate scores for all tokens
        for token in self.tokens.values():
            token.calculate_score()
            
    async def _fetch_dex_screener(self) -> None:
        """Fetch new tokens from DEX Screener."""
        url = "https://api.dexscreener.com/latest/dex/tokens/solana"
        
        try:
            async with self.session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    for pair in data.get("pairs", [])[:20]:  # Top 20 tokens
                        if pair.get("chainId") == "solana":
                            token = TokenData(
                                address=pair.get("baseToken", {}).get("address", ""),
                                symbol=pair.get("baseToken", {}).get("symbol", ""),
                                name=pair.get("baseToken", {}).get("name", ""),
                                price=float(pair.get("priceUsd", 0)),
                                price_change_5m=float(pair.get("priceChange", {}).get("m5", 0)),
                                volume_5m=float(pair.get("volume", {}).get("m5", 0)),
                                volume_24h=float(pair.get("volume", {}).get("h24", 0)),
                                liquidity=float(pair.get("liquidity", {}).get("usd", 0)),
                                created_at=datetime.fromtimestamp(pair.get("pairCreatedAt", 0) / 1000)
                            )
                            self.tokens[token.address] = token
                            
        except Exception as e:
            logger.error(f"DEX Screener error: {e}")
            
    async def _update_token_moralis(self, address: str) -> None:
        """Update token with Moralis data."""
        if not self.moralis_key:
            return
            
        try:
            data = await fetch_moralis(address, self.moralis_key)
            if address in self.tokens and "usdPrice" in data:
                self.tokens[address].price = float(data["usdPrice"])
                self.tokens[address].last_updated = datetime.utcnow()
        except Exception as e:
            logger.debug(f"Moralis update error for {address}: {e}")
            
    def get_top_tokens(self, limit: int = 10) -> list[TokenData]:
        """Get top tokens by score."""
        sorted_tokens = sorted(
            self.tokens.values(), 
            key=lambda x: x.score, 
            reverse=True
        )
        return sorted_tokens[:limit]

async def fetch_moralis(address: str, api_key: str) -> dict:
    """Fetch token price info from Moralis."""
    url = f"https://deep-index.moralis.io/api/v2/erc20/{address}/price?chain=solana"
    headers = {"X-API-Key": api_key}
    
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
