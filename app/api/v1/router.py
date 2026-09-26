from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.market import router as market_router
from app.api.v1.trades import router as trades_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(market_router)
api_router.include_router(trades_router)
