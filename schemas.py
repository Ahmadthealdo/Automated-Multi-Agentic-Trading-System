from pydantic import BaseModel, Field
from typing import Literal

class MarketAnalysis(BaseModel):
    ticker: str
    price_variance_pct: float = Field(description="The percentage variance over 5 days")
    momentum: Literal["bullish", "bearish", "neutral"]
    summary: str = Field(description="A factual analysis of the 5-day market trend.")

class RiskEvaluation(BaseModel):
    stable_capital: str = Field(description="Current account stable capital, e.g. $10,000.00 USDT")
    risk_tier: str = Field(description="Evaluated risk tier (High Probability / Medium Probability / Zero Allocation)")
    verdict: Literal["APPROVED", "REJECTED"]
    action_command: str = Field(description="Final Action Command (STRONG BUY / BUY / HOLD / SELL / STRONG SELL)")
    budget_allocation: str = Field(description="Calculated trade budget allocation (e.g. Allocate 5% ($500.00 USDT))")
    justification: str = Field(description="Single-sentence compliance justification explaining safety and risk matching.")

class FinalTradingDecision(BaseModel):
    ticker: str
    action: Literal["STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"]
    risk_status: str
    stable_capital: str = Field(description="Available stable capital balance.")
    budget_allocation: str = Field(description="Exact capital allocation budget.")
    justification: str = Field(description="Comprehensive final combined reasoning explanation.")