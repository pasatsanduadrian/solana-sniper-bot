# trading.py - Engine complet de trading
import asyncio
import httpx
import logging
import base64
from datetime import datetime
from typing import Dict, Optional
from solana.rpc.async_api import AsyncClient
from solders.transaction import Transaction
from solders.signature import Signature

from src.bot.feeds import FeedAggregator, TokenData
from src.bot.config import settings

logger = logging.getLogger("bot.trading")

JUPITER_URL = "https://quote-api.jup.ag/v6"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"

class Position:
    """Track an open position."""
    
    def __init__(self, token: TokenData, amount_in: float, amount_out: float):
        self.token = token
        self.amount_in = amount_in  # USDC spent
        self.amount_out = amount_out  # Tokens received
        self.entry_price = token.price
        self.entry_time = datetime.utcnow()
        self.exit_price: Optional[float] = None
        self.exit_time: Optional[datetime] = None
        self.tx_signature: Optional[str] = None
        
    @property
    def current_value(self) -> float:
        """Get current position value in USDC."""
        if self.exit_price:
            return self.amount_out * self.exit_price
        return self.amount_out * self.token.price
        
    @property
    def pnl(self) -> float:
        """Get profit/loss."""
        return self.current_value - self.amount_in
        
    @property
    def pnl_percent(self) -> float:
        """Get profit/loss percentage."""
        if self.amount_in == 0:
            return 0
        return (self.pnl / self.amount_in) * 100

async def jup_quote(input_mint: str, output_mint: str, amount: int) -> dict:
    """Request a swap quote from Jupiter."""
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": amount,
        "slippageBps": 100  # 1% slippage
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{JUPITER_URL}/quote", params=params)
        r.raise_for_status()
        return r.json()

async def jup_swap_tx(quote: dict, user_public_key: str) -> dict:
    """Generate swap transaction from Jupiter."""
    payload = {
        "quoteResponse": quote,
        "userPublicKey": user_public_key,
        "wrapUnwrapSOL": True
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{JUPITER_URL}/swap", json=payload)
        r.raise_for_status()
        return r.json()

class TradingEngine:
    """Advanced trading engine with position management."""
    
    def __init__(self, feeds: FeedAggregator) -> None:
        self.feeds = feeds
        self.running = False
        self.positions: Dict[str, Position] = {}
        self.total_invested = 0.0
        self.total_realized_pnl = 0.0
        
        # Trading parameters
        self.position_size = 10.0  # 10 USDC per position
        self.max_positions = 5
        self.take_profit = 50.0  # 50% profit target
        self.stop_loss = -20.0  # 20% stop loss
        
        # Constants
        self.USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        self.SOL_MINT = "So11111111111111111111111111111111111111112"
        
    async def start(self) -> None:
        self.running = True
        self.client = AsyncClient(SOLANA_RPC)
        asyncio.create_task(self._trade_loop())
        logger.info("Trading engine started")
        
    async def stop(self) -> None:
        self.running = False
        await self.client.close()
        logger.info("Trading engine stopped")
        
    async def _trade_loop(self) -> None:
        while self.running:
            try:
                await self.execute_strategy()
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(10)
                
    async def execute_strategy(self) -> None:
        """Main trading strategy."""
        
        # 1. Check existing positions for exit
        await self._check_exit_conditions()
        
        # 2. Find new opportunities if we have slots
        if len(self.positions) < self.max_positions:
            await self._find_entries()
            
    async def _check_exit_conditions(self) -> None:
        """Check if any position should be closed."""
        for address, position in list(self.positions.items()):
            pnl_percent = position.pnl_percent
            
            # Check take profit or stop loss
            if pnl_percent >= self.take_profit or pnl_percent <= self.stop_loss:
                logger.info(f"Closing position {position.token.symbol}: {pnl_percent:.2f}%")
                await self._close_position(address)
                
    async def _find_entries(self) -> None:
        """Find new tokens to buy."""
        top_tokens = self.feeds.get_top_tokens(10)
        
        for token in top_tokens:
            # Skip if already in position
            if token.address in self.positions:
                continue
                
            # Entry criteria
            if (token.score >= 60 and 
                token.volume_5m > 50000 and 
                token.liquidity > 20000 and
                token.price_change_5m > 5):
                
                logger.info(f"Entry signal for {token.symbol} (score: {token.score})")
                await self._open_position(token)
                
                # Only open one position per cycle
                break
                
    async def _open_position(self, token: TokenData) -> None:
        """Open a new position."""
        if not settings.public_key:
            logger.error("No wallet configured")
            return
            
        try:
            # Convert USDC amount to smallest unit (6 decimals)
            amount_lamports = int(self.position_size * 1_000_000)
            
            # Get quote
            quote = await jup_quote(self.USDC_MINT, token.address, amount_lamports)
            
            if not quote:
                logger.error(f"No quote for {token.symbol}")
                return
                
            # Expected output amount
            out_amount = int(quote["outAmount"]) / (10 ** token.decimals)
            
            # Generate transaction
            swap_data = await jup_swap_tx(quote, settings.public_key)
            
            # Send transaction (simplified - needs proper signing)
            # tx_sig = await self._send_transaction(swap_data)
            
            # Create position
            position = Position(token, self.position_size, out_amount)
            # position.tx_signature = tx_sig
            self.positions[token.address] = position
            self.total_invested += self.position_size
            
            logger.info(f"Opened position: {self.position_size} USDC -> {out_amount} {token.symbol}")
            
        except Exception as e:
            logger.error(f"Failed to open position: {e}")
            
    async def _close_position(self, address: str) -> None:
        """Close an existing position."""
        if address not in self.positions:
            return
            
        position = self.positions[address]
        
        try:
            # Get quote for selling
            amount_lamports = int(position.amount_out * (10 ** position.token.decimals))
            quote = await jup_quote(address, self.USDC_MINT, amount_lamports)
            
            if quote:
                # Expected USDC output
                usdc_out = int(quote["outAmount"]) / 1_000_000
                
                # Send transaction (simplified)
                # tx_sig = await self._send_transaction(swap_data)
                
                # Update position
                position.exit_price = position.token.price
                position.exit_time = datetime.utcnow()
                
                # Update stats
                realized_pnl = usdc_out - position.amount_in
                self.total_realized_pnl += realized_pnl
                
                logger.info(f"Closed {position.token.symbol}: PnL {realized_pnl:.2f} USDC ({position.pnl_percent:.2f}%)")
                
            # Remove position
            del self.positions[address]
            
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            
    def get_stats(self) -> dict:
        """Get trading statistics."""
        open_pnl = sum(p.pnl for p in self.positions.values())
        total_pnl = self.total_realized_pnl + open_pnl
        
        return {
            "positions": len(self.positions),
            "total_invested": self.total_invested,
            "open_pnl": open_pnl,
            "realized_pnl": self.total_realized_pnl,
            "total_pnl": total_pnl,
            "roi_percent": (total_pnl / self.total_invested * 100) if self.total_invested > 0 else 0
        }
