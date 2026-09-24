from fastapi import APIRouter
from app.services.market_service import get_price_chart_data

router = APIRouter(tags=["Market Analysis"])

@router.get("/price-chart")
async def api_get_price_chart(ticker: str, period: str = "7d", interval: str = "15m"):
    """Fetch candlestick price chart data for an asset ticker."""
    return await get_price_chart_data(ticker=ticker, period=period, interval=interval)
