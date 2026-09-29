from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class MarketAnalysis(BaseModel):
    ticker: str
    current_price: float = Field(description="The absolute latest actual closing price of the asset fetched by the tool")
    price_variance_pct: float = Field(description="The percentage variance over the fetched period")
    momentum: Literal["bullish", "bearish", "neutral"]
    summary: str = Field(description="A factual analysis of the market trend and indicator signals")

class Candle(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class PriceChartResponse(BaseModel):
    status: str
    ticker: str
    current_price: float
    open: float
    high: float
    low: float
    volume: int
    price_change_pct: float
    candles: List[Candle]
