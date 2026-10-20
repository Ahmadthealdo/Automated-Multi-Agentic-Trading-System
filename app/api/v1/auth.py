from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.user import SystemUser
from app.schemas.auth import (
    UserSignup,
    UserLogin,
    OperatorProfile,
    TokenResponse,
    AuthMessageResponse
)
from app.core.security import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(tags=["Authentication & Security"])

@router.post("/signup", response_model=AuthMessageResponse, status_code=status.HTTP_201_CREATED)
async def api_signup(user: UserSignup, db: AsyncSession = Depends(get_db_session)):
    """
    Registers a new human trading desk operator, hashes credentials with bcrypt,
    generates an initial JWT access token, and returns the profile.
    """
    stmt = select(SystemUser).where(SystemUser.email == user.email)
    result = await db.execute(stmt)
    existing = result.scalars().first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account registration conflict. Email already registered. Please proceed to Login."
        )

    hashed_pwd = hash_password(user.password)
    new_user = SystemUser(
        full_name=user.full_name,
        email=user.email,
        verified_phone=user.mobile_number,
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Issue JWT token upon successful registration
    token = create_access_token(
        subject=new_user.email,
        extra_claims={
            "user_id": new_user.id,
            "full_name": new_user.full_name
        }
    )

    operator_data = OperatorProfile(
        id=new_user.id,
        full_name=new_user.full_name,
        email=new_user.email,
        mobile_number=new_user.verified_phone
    )

    return AuthMessageResponse(
        status="success",
        message="Operator registered and authenticated successfully.",
        access_token=token,
        token_type="bearer",
        operator=operator_data
    )

@router.post("/login")
async def api_login(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Dual-mode Authentication Endpoint:
    Accepts BOTH standard JSON payload ({"email": "...", "password": "..."})
    AND standard OAuth2 urlencoded Form data (username=...&password=...).
    Returns a cryptographically signed JWT Bearer access token and operator profile.
    """
    email: Optional[str] = None
    password: Optional[str] = None

    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await request.json()
        email = body.get("email") or body.get("username")
        password = body.get("password")
    elif "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        email = form.get("username") or form.get("email")
        password = form.get("password")
    else:
        # Fallback: attempt json then form
        try:
            body = await request.json()
            email = body.get("email") or body.get("username")
            password = body.get("password")
        except Exception:
            form = await request.form()
            email = form.get("username") or form.get("email")
            password = form.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing email (or username) and password."
        )

    stmt = select(SystemUser).where(SystemUser.email == email.strip())
    result = await db.execute(stmt)
    db_user = result.scalars().first()

    if not db_user or not verify_password(password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operational credentials. Access Denied.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Issue signed JWT token
    access_token = create_access_token(
        subject=db_user.email,
        extra_claims={
            "user_id": db_user.id,
            "full_name": db_user.full_name
        }
    )

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "operator": {
            "id": db_user.id,
            "full_name": db_user.full_name,
            "email": db_user.email,
            "mobile_number": db_user.verified_phone
        }
    }

@router.post("/token", response_model=TokenResponse)
async def api_oauth2_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Standard RFC 6749 OAuth2 Password Grant Token endpoint for Swagger UI Authorize dialog.
    """
    stmt = select(SystemUser).where(SystemUser.email == form_data.username.strip())
    result = await db.execute(stmt)
    db_user = result.scalars().first()

    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = create_access_token(
        subject=db_user.email,
        extra_claims={
            "user_id": db_user.id,
            "full_name": db_user.full_name
        }
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        operator=OperatorProfile(
            id=db_user.id,
            full_name=db_user.full_name,
            email=db_user.email,
            mobile_number=db_user.verified_phone
        )
    )

@router.get("/me", response_model=OperatorProfile)
async def api_get_current_operator(
    current_user: SystemUser = Depends(get_current_user)
):
    """
    Protected Endpoint:
    Returns the currently authenticated operator's profile decoded from the JWT token.
    """
    return OperatorProfile(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        mobile_number=current_user.verified_phone
    )
