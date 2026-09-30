import asyncio
from datetime import datetime, timezone, timedelta
import yfinance as yf
import pandas as pd
from app.models.trading import TradingHistory

async def audit_trade_status(record: TradingHistory, db_session) -> str:
    """
    Checks the chart data (via yfinance) starting from the trade's creation timestamp
    to determine whether it hit its entry, take profit, or stop loss.
    Updates the record.status field and marks it as PROFIT, LOSS, or INACTIVE.
    """
    if record.status in ("PROFIT", "LOSS", "INACTIVE"):
        return record.status

    # If it was a HOLD or REJECTED trade, it never executed -> INACTIVE
    if record.action == "HOLD" or record.risk_status == "REJECTED":
        record.status = "INACTIVE"
        db_session.add(record)
        return "INACTIVE"

    try:
        entry = float(record.entry_price) if record.entry_price else 0.0
        tp = float(record.take_profit) if record.take_profit else 0.0
        sl = float(record.stop_loss) if record.stop_loss else 0.0
    except (TypeError, ValueError):
        record.status = "INACTIVE"
        db_session.add(record)
        return "INACTIVE"

    if entry <= 0 or tp <= 0 or sl <= 0:
        record.status = "INACTIVE"
        db_session.add(record)
        return "INACTIVE"

    start_time = record.timestamp
    if start_time and start_time.tzinfo is not None:
        start_time = start_time.astimezone(timezone.utc).replace(tzinfo=None)
    elif not start_time:
        start_time = datetime.now(timezone.utc).replace(tzinfo=None)

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # If the trade is brand new (less than 15 seconds old), let it run
    if (now - start_time).total_seconds() < 15:
        record.status = "RUNNING"
        db_session.add(record)
        return "RUNNING"

    age_seconds = (now - start_time).total_seconds()
    if age_seconds < 86400:  # < 24 hours
        interval = "1m"
    elif age_seconds < 86400 * 7:  # < 7 days
        interval = "5m"
    elif age_seconds < 86400 * 30:  # < 30 days
        interval = "15m"
    else:
        interval = "1h"

    try:
        ticker = record.ticker.upper().strip()
        stock = yf.Ticker(ticker)

        start_str = start_time.strftime("%Y-%m-%d")
        end_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None,
            lambda: stock.history(start=start_str, end=end_str, interval=interval)
        )

        if df.empty:
            df = await loop.run_in_executor(
                None,
                lambda: stock.history(period="5d", interval=interval)
            )

        if df.empty:
            record.status = "RUNNING"
            db_session.add(record)
            return "RUNNING"

        # Standardize DataFrame time index to UTC for matching
        if df.index.tz is not None:
            df.index = df.index.tz_convert('UTC')
        else:
            df.index = df.index.tz_localize('UTC')

        # Slice DataFrame to only keep candles starting from the trade's exact creation timestamp
        trade_time_utc = pd.to_datetime(start_time).tz_localize('UTC')
        df = df[df.index >= trade_time_utc]

        is_buy = record.action in ("BUY", "STRONG BUY")
        status = "RUNNING"

        for _, row in df.iterrows():
            low = float(row['Low'])
            high = float(row['High'])

            if is_buy:
                # Long position targets: hits Stop Loss first or Take Profit first
                if low <= sl:
                    status = "LOSS"
                    break
                elif high >= tp:
                    status = "PROFIT"
                    break
            else:
                # Short position targets: hits Stop Loss first or Take Profit first
                if high >= sl:
                    status = "LOSS"
                    break
                elif low <= tp:
                    status = "PROFIT"
                    break

        record.status = status
        db_session.add(record)
        return status

    except Exception as e:
        print(f"⚠️ [Audit Engine Notice] Failed to resolve status for record {record.id}: {e}")
        if not record.status:
            record.status = "RUNNING"
            db_session.add(record)
        return record.status
