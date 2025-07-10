"""Data feed aggregation from Helius, Moralis and DEX Screener."""

import asyncio
import aiohttp
import httpx
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
import logging
import os

from src.api.helius import HeliusAPI

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
    decimals: int = 9  # Default for SOL tokens
    
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
        self.helius = HeliusAPI(self.helius_key)
        
    async def start(self) -> None:
        self.session = aiohttp.ClientSession()
        self.running = True
        asyncio.create_task(self._fetch_loop())
        logger.info("Feed aggregator started")
        
    async def stop(self) -> None:
        self.running = False
        if self.session:
            await self.session.close()
        await self.helius.close()
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
                tasks.append(self._update_token_helius(address))
                
        await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate scores for all tokens
        for token in self.tokens.values():
            token.calculate_score()

        # Extra pump detection
        self._detect_pump_opportunities()
            
    async def _fetch_dex_screener(self) -> None:
        """Fetch new tokens from DEX Screener."""
        # URL corect pentru Solana pe DEX Screener
        url = "https://api.dexscreener.com/latest/dex/search?q=solana"
        
        try:
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Verificăm că avem date valide
                    if not data or not isinstance(data, dict):
                        logger.warning("DEX Screener returned invalid data")
                        return
                    
                    # DEX Screener returnează pairs direct, nu într-un obiect
                    pairs = data.get("pairs", [])
                    if not pairs:
                        logger.debug("No pairs found in DEX Screener response")
                        return
                    
                    # Procesăm primele 20 perechi
                    for pair in pairs[:20]:
                        # Verificăm că e pe Solana
                        if pair.get("chainId") != "solana":
                            continue
                            
                        # Extragem datele cu verificări
                        base_token = pair.get("baseToken", {})
                        if not base_token or not base_token.get("address"):
                            continue
                        
                        # Parseăm volumele și lichiditatea cu grijă
                        volume_m5 = 0
                        volume_h24 = 0
                        liquidity_usd = 0
                        price_change_m5 = 0
                        
                        # Volume
                        volume = pair.get("volume", {})
                        if isinstance(volume, dict):
                            volume_m5 = float(volume.get("m5", 0) or 0)
                            volume_h24 = float(volume.get("h24", 0) or 0)
                        
                        # Liquidity
                        liquidity = pair.get("liquidity", {})
                        if isinstance(liquidity, dict):
                            liquidity_usd = float(liquidity.get("usd", 0) or 0)
                        
                        # Price change
                        price_change = pair.get("priceChange", {})
                        if isinstance(price_change, dict):
                            price_change_m5 = float(price_change.get("m5", 0) or 0)
                        
                        # Creăm token-ul
                        token = TokenData(
                            address=base_token.get("address", ""),
                            symbol=base_token.get("symbol", ""),
                            name=base_token.get("name", ""),
                            price=float(pair.get("priceUsd", 0) or 0),
                            price_change_5m=price_change_m5,
                            volume_5m=volume_m5,
                            volume_24h=volume_h24,
                            liquidity=liquidity_usd,
                            created_at=datetime.fromtimestamp(pair.get("pairCreatedAt", 0) / 1000) if pair.get("pairCreatedAt") else None
                        )
                        
                        # Adăugăm doar dacă are date valide
                        if token.address and (token.volume_5m > 0 or token.liquidity > 0):
                            self.tokens[token.address] = token
                            logger.debug(f"Added token {token.symbol} from DEX Screener")
                            
                else:
                    logger.warning(f"DEX Screener returned status {resp.status}")
                    
        except asyncio.TimeoutError:
            logger.error("DEX Screener timeout")
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

    async def _update_token_helius(self, address: str) -> None:
        """Update token with Helius holder data."""
        try:
            data = await self.helius.get_token_holders(address)
            if address in self.tokens and isinstance(data, dict):
                holders = data.get("total", 0)
                if holders:
                    self.tokens[address].holders = int(holders)
        except Exception as e:
            logger.debug(f"Helius update error for {address}: {e}")

    def _detect_pump_opportunities(self) -> None:
        """Add bonus score for tokens that look like pumps."""
        for token in self.tokens.values():
            if (
                token.volume_5m > 50000
                and token.liquidity > 10000
                and token.price_change_5m > 5
            ):
                token.score += 10
            
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
