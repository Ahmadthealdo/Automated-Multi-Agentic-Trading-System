from pydantic import BaseModel, Field
from typing import Literal

class MarketAnalysis(BaseModel):
    ticker: str
    price_variance_pct: float = Field(description="The percentage variance over 5 days")
    momentum: Literal["bullish", "bearish", "neutral"]
    summary: str = Field(description="A factual analysis of the 5-day market trend.")

class RiskEvaluation(BaseModel):
    verdict: Literal["APPROVED", "REJECTED"]
    justification: str = Field(description="Single-sentence technical justification.")

class FinalTradingDecision(BaseModel):
    ticker: str
    action: Literal["BUY", "SELL", "HOLD"]
    risk_status: str
    justification: str