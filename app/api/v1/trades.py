from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.db.session import get_db_engine, get_async_session_factory
from app.models.trading import TradingHistory
from app.models.user import SystemUser
from app.agents.runner import run_trading_desk
from app.services.audit_service import audit_trade_status
from app.api.deps import get_current_user_optional

router = APIRouter(tags=["Trading Desk Operations"])

@router.post("/trade")
async def api_execute_trade(
    request: Request,
    current_user: Optional[SystemUser] = Depends(get_current_user_optional)
):
    """
    Triggers the multi-agent cognitive pipeline:
    Analyzes asset momentum, audits risk compliance, sizes the trade, and returns the decision.
    Accepts JWT Bearer token authentication or fallback operator parameters.
    """
    payload = await request.json()
    ticker = payload.get("ticker")
    interval = payload.get("interval")
    period = payload.get("period")
    strategy = payload.get("strategy")
    
    # Use authenticated user data if available, fallback to payload values
    user_name = payload.get("user_name") or (current_user.full_name if current_user else None)
    user_email = payload.get("user_email") or (current_user.email if current_user else None)
    user_phone = payload.get("user_phone") or (current_user.verified_phone if current_user else None)

    if not all([ticker, interval, period, strategy, user_name, user_email, user_phone]):
        raise HTTPException(
            status_code=400,
            detail="Missing required parameters for operational execution (ticker, interval, period, strategy, operator credentials)."
        )

    try:
        decision = await run_trading_desk(
            ticker_input=ticker,
            interval=interval,
            period=period,
            strategy=strategy,
            user_name=user_name,
            user_email=user_email,
            user_phone=user_phone
        )
        if not decision:
            raise HTTPException(status_code=500, detail="Multi-agent quantitative execution pipeline failed.")
        return decision.model_dump() if hasattr(decision, "model_dump") else decision.dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def api_get_history(
    current_user: Optional[SystemUser] = Depends(get_current_user_optional)
):
    """
    Fetches recent trading history records and audits their live execution status.
    Optionally scoped to authenticated operator.
    """
    try:
        engine = get_db_engine()
        session_factory = get_async_session_factory(engine)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Database connection setup failed: {err}")

    try:
        async with session_factory() as db_session:
            stmt = select(TradingHistory).order_by(TradingHistory.timestamp.desc()).limit(15)
            result = await db_session.execute(stmt)
            records = result.scalars().all()

            # Audit trade status dynamically for any running records
            for r in records:
                await audit_trade_status(r, db_session)

            await db_session.commit()

            return [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else "",
                    "user_name": r.user_name,
                    "ticker": r.ticker,
                    "action": r.action,
                    "risk_status": r.risk_status,
                    "stable_capital": r.stable_capital,
                    "budget_allocation": r.budget_allocation,
                    "entry_price": r.entry_price,
                    "take_profit": r.take_profit,
                    "stop_loss": r.stop_loss,
                    "justification": r.justification,
                    "status": r.status or "RUNNING"
                }
                for r in records
            ]
    finally:
        await engine.dispose()
