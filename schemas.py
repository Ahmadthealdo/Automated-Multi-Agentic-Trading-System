import re
from pydantic import BaseModel, Field, EmailStr, field_validator
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

# ---------------------------------------------------------
# User Authentication Validation Schemas
# ---------------------------------------------------------
class UserSignup(BaseModel):
    full_name: str = Field(description="Operator full name, stripped of trailing whitespaces")
    email: EmailStr = Field(description="Strict format validated operator email address")
    mobile_number: str = Field(description="Verified mobile number token (Pakistani/International standard)")
    password: str = Field(description="Strict password containing upper, lower, digit, and special char")

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Full name cannot be empty or only whitespace")
        return stripped

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        pattern = r"^(03|\+923)\d{9}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid mobile number. Must match Pakistani standard (e.g. 03001234567 or +923001234567)")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v

class UserLogin(BaseModel):
    email: EmailStr = Field(description="Operator email address")
    password: str = Field(description="Operator raw password")