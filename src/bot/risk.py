"""Simple risk management utilities for the trading engine."""
from __future__ import annotations

from dataclasses import dataclass

from .feeds import TokenData

@dataclass
class RiskManager:
    """Basic risk management and position sizing."""

    base_position: float = 10.0
    max_risk: float = 0.5  # 0-1 scale
    stop_loss_percent: float = 15.0

    def assess_token_risk(self, token: TokenData) -> float:
        """Return a risk score between 0 and 1."""
        risk = 0.5
        if token.liquidity > 100000:
            risk -= 0.2
        if token.holders > 1000:
            risk -= 0.1
        if token.price_change_5m > 10:
            risk += 0.2
        return max(0.0, min(1.0, risk))

    def position_size(self, risk_score: float) -> float:
        """Calculate dynamic position size based on risk."""
        factor = 1.0 - min(risk_score, self.max_risk)
        return self.base_position * factor

    def stop_loss_triggered(self, entry: float, current: float) -> bool:
        """Check if stop loss should trigger."""
        change = (current - entry) / entry * 100
        return change <= -self.stop_loss_percent
