"""
Backward compatibility proxy for schemas.
Exports all schemas from the modular app.schemas package.
"""

from app.schemas.auth import (
    UserSignup,
    UserLogin,
    OperatorProfile,
    TokenResponse,
    AuthMessageResponse
)
from app.schemas.market import MarketAnalysis, Candle, PriceChartResponse
from app.schemas.trading import RiskEvaluation, FinalTradingDecision, TradeExecutionRequest

__all__ = [
    "UserSignup",
    "UserLogin",
    "OperatorProfile",
    "TokenResponse",
    "AuthMessageResponse",
    "MarketAnalysis",
    "Candle",
    "PriceChartResponse",
    "RiskEvaluation",
    "FinalTradingDecision",
    "TradeExecutionRequest"
]