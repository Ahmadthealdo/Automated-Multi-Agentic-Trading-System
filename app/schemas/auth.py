import re
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator

class UserSignup(BaseModel):
    full_name: str = Field(description="Operator full name, stripped of trailing whitespaces")
    email: EmailStr = Field(description="Strict format validated operator email address")
    mobile_number: str = Field(description="Verified mobile number token (Pakistani/International standard)")
    password: str = Field(description="Strict password containing at least 6 characters")

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
            raise ValueError("Invalid mobile number. Must match standard format (e.g. 03001234567 or +923001234567)")
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

class OperatorProfile(BaseModel):
    id: Optional[int] = None
    full_name: str
    email: EmailStr
    mobile_number: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    operator: OperatorProfile

class AuthMessageResponse(BaseModel):
    status: str
    message: str
    access_token: Optional[str] = None
    token_type: Optional[str] = "bearer"
    operator: Optional[OperatorProfile] = None
