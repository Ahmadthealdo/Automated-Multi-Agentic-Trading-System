from pydantic import BaseModel, Field
from typing import Literal

class MarketAnalysis(BaseModel):
    ticker: str
    current_price: float = Field(description="The absolute latest actual closing price of the asset fetched by the tool")
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
    TAKE_PROFIT: float = Field(description="Calculated target Take Profit price as a float, or 0.0 if not applicable.")
    STOP_LOSS: float = Field(description="Calculated target Stop Loss price as a float, or 0.0 if not applicable.")
    justification: str = Field(description="Comprehensive final combined reasoning explanation.")