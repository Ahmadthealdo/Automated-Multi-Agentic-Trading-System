import asyncio
import os
import json
import re
from datetime import datetime, timezone
from dotenv import load_dotenv, find_dotenv
from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI
from tools import fetch_market_data
from schemas import FinalTradingDecision, UserSignup, UserLogin

# Observability and Telemetry Integration
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
from langfuse import get_client

# Asynchronous Database and Session Imports
from sqlalchemy import Column, Integer, String, DateTime, Text, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from agents.extensions.memory.sqlalchemy_session import SQLAlchemySession

# FastAPI Web Hosting & Static Files Imports
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import bcrypt

# ---------------------------------------------------------
# Load environment and configure
# ---------------------------------------------------------
load_dotenv(find_dotenv())  # Load local .env file

# Instrumentation setup
OpenAIAgentsInstrumentor().instrument()

# Initialize Langfuse client
langfuse = get_client()

# Verify connection
try:
    if langfuse.auth_check():
        print("✅ Langfuse client is authenticated and ready!")
    else:
        print("❌ Authentication failed. Please check your credentials...")
except Exception as e:
    print(f"⚠️ Langfuse connection warning: {e}. Tracing will continue natively/locally.")

# ---------------------------------------------------------
# LLM Service Configuration
# ---------------------------------------------------------
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Missing GEMINI_API_KEY in environment or .env file.")

# Configure the Gemini Client with the standard OpenAI compatibility endpoint
client = AsyncOpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    max_retries=5  # Automatically retries rate limits (429) with exponential backoff
)

# Use models/gemini-2.5-flash for fast and cost-effective reasoning
gemini_model = OpenAIChatCompletionsModel(
    model="models/gemini-2.5-flash",
    openai_client=client
)

# ---------------------------------------------------------
# Declarative Relational Database Models
# ---------------------------------------------------------
Base = declarative_base()

class TradingHistory(Base):
    __tablename__ = 'trading_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user_name = Column(String)
    user_email = Column(String)
    user_phone = Column(String)
    ticker = Column(String)
    action = Column(String)
    risk_status = Column(String)
    stable_capital = Column(String)
    budget_allocation = Column(String)
    entry_price = Column(String)
    take_profit = Column(String)
    stop_loss = Column(String)
    justification = Column(Text)
    status = Column(String, default="RUNNING")

class SystemUser(Base):
    __tablename__ = 'system_users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    verified_phone = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# ---------------------------------------------------------
# Define Specialized Subagents
# ---------------------------------------------------------

# Agent 1: The Specialized Data Analyst
analyst_agent = Agent(
    name="Market Data Analyst",
    instructions=(
        "You are a specialized data processing agent. Your sole objective is to ingest raw asset data "
        "using your tool and return a structured analysis. Read the pricing matrix sequentially, "
        "analyze moving averages, crossovers, MACD, and RSI levels, and determine overall technical momentum. "
        "Do NOT include trading recommendations like BUY or SELL.\n"
        "Return your output as a raw JSON block conforming to this schema:\n"
        "{\n"
        "  \"current_price\": float (the absolute latest Close price value extracted from the tool report),\n"
        "  \"price_variance_pct\": float (percentage variance over the fetched period),\n"
        "  \"momentum\": \"bullish\" | \"bearish\" | \"neutral\",\n"
        "  \"summary\": \"factual analysis of the market trend and indicator signals\"\n"
        "}"
    ),
    tools=[fetch_market_data],
    model=gemini_model
)

# Agent 2: The Independent Risk Guardrail
risk_agent = Agent(
    name="Risk Manager Agent",
    instructions=(
        "You are the ultimate guardrail of the system. Your primary objective is to audit "
        "the Trading Desk Manager's proposed signal and compute the exact position sizing allocation.\n"
        "1. CAPTURE TOTAL STABLE LIQUIDITY:\n"
        "   Identify the available stable cash account balance (default to $10,000.00 USDT if not specified). "
        "   Only consider stable capital (USDT, USDC, USD).\n"
        "2. AUDIT RISK-TO-REWARD (R:R) RATIO:\n"
        "   Extract the proposed entry_price, take_profit, and stop_loss from the input.\n"
        "   Calculate the Risk-to-Reward (R:R) ratio: R:R = abs(take_profit - entry_price) / abs(entry_price - stop_loss).\n"
        "   - If the R:R ratio is less than 1.5, or if the proposed action is HOLD, you must REJECT the trade. Set verdict='REJECTED', action_command='HOLD', and budget_allocation='Allocate 0% ($0.00 USDT)'.\n"
        "   - If the R:R ratio is greater than or equal to 1.5, proceed to sizing.\n"
        "3. COMPUTE 1% CAPITAL-AT-RISK POSITION SIZING:\n"
        "   - Calculate Max Dollar Risk = Stable Capital * 0.01 (e.g., $100.00 for $10,000.00 capital).\n"
        "   - Calculate Risk per Unit = abs(entry_price - stop_loss).\n"
        "   - Calculate Position Size Quantity = Max Dollar Risk / Risk per Unit.\n"
        "   - Calculate Required Budget Allocation = Position Size Quantity * entry_price.\n"
        "   - Clamp the final budget allocation to a maximum of 10% of the stable capital to prevent concentration risk:\n"
        "     Final Budget Allocation = min(Required Budget Allocation, Stable Capital * 0.10).\n"
        "   - Calculate the percentage of stable capital this represents.\n"
        "   - Format the budget_allocation string exactly as: 'Allocate X% ($Y.YY USDT) risking 1% ($Z.ZZ USDT)' (where Z.ZZ is the Max Dollar Risk, e.g., $100.00).\n"
        "   - Set verdict='APPROVED' and action_command to the proposed action (e.g. STRONG BUY, BUY, SELL, STRONG SELL).\n"
        "4. EXPLAIN THE SAFETY MATH:\n"
        "   Provide a justification explaining the math. It must be exactly one sentence prefixing with approval status, e.g., 'Approved: R:R ratio is 1.85 (above 1.5), and allocation is limited to 4.2% ($420.00 USDT) to risk exactly 1% ($100.00 USDT) of stable capital with Stop Loss at $95.50.'\n"
        "5. Return your evaluation strictly as a raw JSON block conforming to this schema:\n"
        "   {\n"
        "     \"stable_capital\": \"Current Account Stable Capital (e.g. $10,000.00 USDT)\",\n"
        "     \"risk_tier\": \"1% Risk Sized Allocation\" | \"Zero Allocation\",\n"
        "     \"verdict\": \"APPROVED\" | \"REJECTED\",\n"
        "     \"action_command\": \"STRONG BUY | BUY | HOLD | SELL | STRONG SELL\",\n"
        "     \"budget_allocation\": \"Allocate X% ($Y.YY USDT) risking 1% ($Z.ZZ USDT)\",\n"
        "     \"justification\": \"A single sentence of quantitative justification explaining the safety math.\"\n"
        "   }"
    ),
    model=gemini_model
)

# ---------------------------------------------------------
# Hierarchical "Agents-as-Tools" Wrapping
# ---------------------------------------------------------
analyst_tool = analyst_agent.as_tool(
    tool_name="analyze_market_data",
    tool_description=(
        "Retrieves technical market data (EMA, SMA, RSI, MACD) and momentum analysis for a given asset. "
        "Expects parameters: ticker (str), period (str), and interval (str)."
    )
)

risk_tool = risk_agent.as_tool(
    tool_name="evaluate_trading_risk",
    tool_description=(
        "Audits a proposed trading action and parameters, returning an APPROVED or REJECTED verdict with justification."
    )
)

# Agent 3: The Orchestrator / Trading Desk Manager
manager_agent = Agent(
    name="Trading Desk Manager",
    instructions=(
        "You are the Trading Desk Manager (Strategy Orchestrator), responsible for generating "
        "the directional trade signal based on the report provided by the Market Data Analyst.\n"
        "1. Extract the target ticker, interval, lookback period, and strategy name from the prompt.\n"
        "2. Call `analyze_market_data` tool with the ticker, period, and interval to fetch raw pricing and indicator calculations.\n"
        "3. Review the technical indicators (EMA crossovers, RSI levels, trend directions, MACD) and classify the trade "
        "opportunity into exactly ONE of these five strategy tiers:\n"
        "   - STRONG BUY: Extreme upward momentum, EMA9 healthily above EMA21, RSI not yet overbought.\n"
        "   - BUY: Moderate upward trend or stable support baseline established.\n"
        "   - HOLD: No clear direction, sideways movement, high uncertainty, or asset is overbought/oversold.\n"
        "   - SELL: Moderate downward trend breaking immediate support lines.\n"
        "   - STRONG SELL: Severe downward breakdown, EMA9 well below EMA21, massive structural panic.\n"
        "4. CALCULATE DYNAMIC TARGET EXIT BOUNDARIES (TP/SL) using the Supply and Demand Zones and ATR (14) returned by the `analyze_market_data` tool payload. Under no circumstances use standard static percentage-based rules. Round all values to 2 decimal places.\n"
        "   - For BUY or STRONG BUY:\n"
        "     - ENTRY_PRICE = Latest Close Price\n"
        "     - TAKE_PROFIT = Nearest Supply Zone (Resistance) - 0.2 * ATR (14) (or 0.995 * Nearest Supply Zone if ATR is unavailable). Fallback if no Supply Zone is found: ENTRY_PRICE + 2.5 * ATR (14).\n"
        "     - STOP_LOSS = Nearest Demand Zone (Support) - 0.5 * ATR (14) (or 0.99 * Nearest Demand Zone if ATR is unavailable). Fallback if no Demand Zone is found: ENTRY_PRICE - 1.5 * ATR (14).\n"
        "   - For SELL or STRONG SELL:\n"
        "     - ENTRY_PRICE = Latest Close Price\n"
        "     - TAKE_PROFIT = Nearest Demand Zone (Support) + 0.2 * ATR (14) (or 1.005 * Nearest Demand Zone if ATR is unavailable). Fallback if no Demand Zone is found: ENTRY_PRICE - 2.5 * ATR (14).\n"
        "     - STOP_LOSS = Nearest Supply Zone (Resistance) + 0.5 * ATR (14) (or 1.01 * Nearest Supply Zone if ATR is unavailable). Fallback if no Supply Zone is found: ENTRY_PRICE + 1.5 * ATR (14).\n"
        "   - For HOLD:\n"
        "     - If the trend is bullish/neutral, calculate TP/SL using the BUY rules. If the trend is bearish, calculate TP/SL using the SELL rules. Do NOT set entry, TP, or SL to 0.0.\n"
        "5. Call `evaluate_trading_risk` tool with parameters: action_command (your strategy tier), entry_price, take_profit, stop_loss, and the analyst summary to audit the trade.\n"
        "6. If the Risk Manager Agent rejects your proposal (verdict is 'REJECTED'), you must override your decision to 'HOLD'.\n"
        "7. Provide the final formatted package decision. It MUST be a single raw JSON block (no markdown, no backticks) conforming to this schema:\n"
        "{\n"
        "  \"ticker\": \"TICKER_SYMBOL\",\n"
        "  \"action\": \"STRONG BUY\" | \"BUY\" | \"HOLD\" | \"SELL\" | \"STRONG SELL\",\n"
        "  \"risk_status\": \"Risk Manager verdict (APPROVED or REJECTED)\",\n"
        "  \"stable_capital\": \"Available stable capital balance from Risk Manager (e.g. $10,000.00 USDT)\",\n"
        "  \"budget_allocation\": \"Exact capital allocation budget from Risk Manager (e.g. Allocate X% ($Y.YY USDT) risking 1% ($Z.ZZ USDT))\",\n"
        "  \"ENTRY_PRICE\": float (the exact ENTRY_PRICE baseline used in calculations),\n"
        "  \"TAKE_PROFIT\": float (calculated target Take Profit price as a float, must be non-zero positive),\n"
        "  \"STOP_LOSS\": float (calculated target Stop Loss price as a float, must be non-zero positive),\n"
        "  \"justification\": \"Final combined reasoning explaining technical momentum, identified supply/demand zones, ATR volatility, risk compliance, position allocation, and TP/SL target boundaries.\"\n"
        "}"
    ),
    tools=[analyst_tool, risk_tool],
    model=gemini_model
)

# ---------------------------------------------------------
# Dynamic Trade Sizing & Outcome Auditing Logic
# ---------------------------------------------------------
async def audit_trade_status(record, db_session):
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

    import yfinance as yf
    import pandas as pd
    from datetime import datetime, timezone, timedelta
    
    start_time = record.timestamp
    if start_time.tzinfo is not None:
        start_time = start_time.astimezone(timezone.utc).replace(tzinfo=None)
        
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
        
        # Format strings for yfinance query bounds as YYYY-MM-DD
        # yfinance is highly stable when querying full day ranges, and we slice the result locally
        start_str = start_time.strftime("%Y-%m-%d")
        end_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None, 
            lambda: stock.history(start=start_str, end=end_str, interval=interval)
        )
        
        if df.empty:
            # Fallback to last 5d history
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
        
        for idx, row in df.iterrows():
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
        print(f"⚠️ [Audit Engine Warning] Failed to resolve status for record {record.id}: {e}")
        if not record.status:
            record.status = "RUNNING"
            db_session.add(record)
        return record.status

# ---------------------------------------------------------
# Execution Engine (Core Agent Runner Pipeline)
# ---------------------------------------------------------
async def run_trading_desk(ticker_input: str, interval: str, period: str, strategy: str, user_name: str, user_email: str, user_phone: str):
    engine = None
    try:
        # Load Neon connection URL dynamically from environment, fallback to literal placeholder if not specified
        env_url = os.getenv("neon_db")
        if env_url:
            # Upgrade standard protocol to async driver protocol
            if env_url.startswith("postgresql://"):
                connection_url = env_url.replace("postgresql://", "postgresql+psycopg://", 1)
            else:
                connection_url = env_url
        else:
            connection_url = "postgresql+psycopg://mr..ca:PASS@abs-pooler.us-east-2.aws.neon.tech/test-sess?sslmode=require&channel_binding=require"
            
        # Instantiate a durable async connection client referencing our target Neon connection URL
        engine = create_async_engine(connection_url, echo=False)
        
        # Ensure our custom declarative tables are created in the database
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Initialize the SQLAlchemySession module wrapper with a unique user-bound conversational tracking session string
        session = SQLAlchemySession(
            session_id=f"session_{user_email}",
            engine=engine,
            create_tables=True
        )
        
        result = await Runner.run(
            manager_agent, 
            input=(
                f"Process trade opportunity for asset: '{ticker_input}' using strategy '{strategy}'. "
                f"Please fetch market data using interval='{interval}' and lookback period='{period}'."
            ),
            session=session
        )
        
        # Strip markdown backticks if model generated them
        text = result.final_output.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
            
        data = json.loads(text)
        decision = FinalTradingDecision(**data)
        
        print("\n" + "="*70)
        print("                 FINAL QUANTITATIVE SYSTEM DECISION")
        print("="*70)
        print(f"  * ASSET TICKER     : {decision.ticker}")
        print(f"  * SYSTEM ACTION    : {decision.action}")
        print(f"  * RISK COMPLIANCE  : {decision.risk_status}")
        print(f"  * STABLE CAPITAL   : {decision.stable_capital}")
        print(f"  * BUDGET ALLOCATION: {decision.budget_allocation}")
        print(f"  * POSITION ENTRY   : ${decision.ENTRY_PRICE:.2f}" if decision.ENTRY_PRICE > 0 else f"  * POSITION ENTRY   : N/A")
        print(f"  * TAKE PROFIT TRGT : ${decision.TAKE_PROFIT:.2f}" if decision.TAKE_PROFIT > 0 else f"  * TAKE PROFIT TRGT : N/A")
        print(f"  * STOP LOSS TARGET : ${decision.STOP_LOSS:.2f}" if decision.STOP_LOSS > 0 else f"  * STOP LOSS TARGET : N/A")
        print(f"  * JUSTIFICATION    : {decision.justification}")
        print("="*70 + "\n")
        
        # Persist standard transactional outcomes using async session maker bound to database connection engine
        try:
            async_session = async_sessionmaker(engine, expire_on_commit=False)
            async with async_session() as db_session:
                status_init = "INACTIVE"
                if decision.risk_status == "APPROVED" and decision.action in ("BUY", "STRONG BUY", "SELL", "STRONG SELL"):
                    status_init = "RUNNING"

                new_record = TradingHistory(
                    user_name=user_name,
                    user_email=user_email,
                    user_phone=user_phone,
                    ticker=decision.ticker,
                    action=decision.action,
                    risk_status=decision.risk_status,
                    stable_capital=decision.stable_capital,
                    budget_allocation=decision.budget_allocation,
                    entry_price=str(decision.ENTRY_PRICE),
                    take_profit=str(decision.TAKE_PROFIT),
                    stop_loss=str(decision.STOP_LOSS),
                    justification=decision.justification,
                    status=status_init
                )
                db_session.add(new_record)
                await db_session.commit()
                print("✅ [Database] Trading history record successfully persisted to Neon PostgreSQL.")
        except Exception as db_err:
            print(f"❌ [Database Error] Failed to persist trading record: {db_err}")
            
        return decision
        
    except Exception as e:
        print(f"\n[Error] Failed to parse final decision JSON or execution crashed: {e}")
        if 'result' in locals() and hasattr(result, 'final_output'):
            print("Raw Agent response was:")
            print(result.final_output)
    finally:
        # Ensure that await engine.dispose() executes cleanly on loop closure
        if engine:
            try:
                await engine.dispose()
                print("🔌 [Database] Asynchronous database connection engine disposed cleanly.")
            except Exception as dispose_err:
                print(f"🔌 [Database] Asynchronous database connection engine disposed with warning: {dispose_err}")

# ---------------------------------------------------------
# FastAPI Application & Hashing Context
# ---------------------------------------------------------
app = FastAPI(
    title="Automated-Multi-Agentic-Trading-System Dashboard Server",
    description="FastAPI Web Interface Wrapper with Pydantic Auth layers and autonomous trading loops"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mount separate custom CSS & JS static folder (MODULAR SERVING)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Password hashing configuration (Native Modern Bcrypt Implementation)
def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')
    
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

# Helper to verify DB connection
def get_db_engine():
    connection_url = os.getenv("neon_db")
    if connection_url:
        if connection_url.startswith("postgresql://"):
            connection_url = connection_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return create_async_engine(connection_url, echo=False)
    raise ValueError("Missing database connection URL (neon_db) in environment.")

# Database Migrations on Startup
@app.on_event("startup")
async def startup_event():
    try:
        engine = get_db_engine()
        
        # 1. Run RENAME and ADD COLUMN inside separate, independent transaction blocks
        async with engine.connect() as conn:
            async with conn.begin() as transaction:
                try:
                    await conn.execute(text("ALTER TABLE system_users RENAME COLUMN mobile_number TO verified_phone;"))
                    await transaction.commit()
                    print("🚀 [Database Migration] Successfully renamed column mobile_number to verified_phone in system_users table.")
                except Exception:
                    await transaction.rollback()
                    # Column might already be renamed, or table does not exist yet
                    pass
            
            async with conn.begin() as transaction:
                try:
                    await conn.execute(text("ALTER TABLE trading_history ADD COLUMN IF NOT EXISTS entry_price VARCHAR;"))
                    await transaction.commit()
                    print("🚀 [Database Migration] Successfully verified/added entry_price column to trading_history table.")
                except Exception:
                    await transaction.rollback()
                    pass
            
            async with conn.begin() as transaction:
                try:
                    await conn.execute(text("ALTER TABLE trading_history ADD COLUMN IF NOT EXISTS status VARCHAR;"))
                    await transaction.commit()
                    print("🚀 [Database Migration] Successfully verified/added status column to trading_history table.")
                except Exception:
                    await transaction.rollback()
                    pass
        
        # 2. Run metadata creation in a clean, separate transaction block
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        await engine.dispose()
        print("🚀 [FastAPI Startup] Relational schemas successfully verified and updated on Neon PostgreSQL.")
    except Exception as err:
        print(f"⚠️ [FastAPI Startup Warning] Automated schema verification failed: {err}")

# ---------------------------------------------------------
# Authentication & Historical Registry API Routes
# ---------------------------------------------------------
@app.post("/api/signup")
async def api_signup(user: UserSignup):
    try:
        engine = get_db_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Database connection setup failed: {err}")
        
    try:
        async with async_session() as db_session:
            from sqlalchemy import select
            stmt = select(SystemUser).where(SystemUser.email == user.email)
            result = await db_session.execute(stmt)
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
            db_session.add(new_user)
            await db_session.commit()
            return {"status": "success", "message": "Operator registered successfully. Please proceed to login."}
    finally:
        await engine.dispose()

@app.post("/api/login")
async def api_login(user: UserLogin):
    try:
        engine = get_db_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Database connection setup failed: {err}")
        
    try:
        async with async_session() as db_session:
            from sqlalchemy import select
            stmt = select(SystemUser).where(SystemUser.email == user.email)
            result = await db_session.execute(stmt)
            db_user = result.scalars().first()
            
            if not db_user or not verify_password(user.password, db_user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid operational credentials. Access Denied."
                )
                
            return {
                "status": "success",
                "operator": {
                    "full_name": db_user.full_name,
                    "email": db_user.email,
                    "mobile_number": db_user.verified_phone
                }
            }
    finally:
        await engine.dispose()

@app.get("/api/price-chart")
async def api_get_price_chart(ticker: str, period: str = "7d", interval: str = "15m"):
    clean_ticker = ticker.upper().strip()
    try:
        import yfinance as yf
        stock = yf.Ticker(clean_ticker)
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, lambda: stock.history(period=period, interval=interval))
        
        if df.empty:
            raise HTTPException(status_code=400, detail=f"No data found for ticker '{clean_ticker}'")
            
        latest_close = float(df['Close'].iloc[-1])
        open_price = float(df['Open'].iloc[-1])
        high_price = float(df['High'].iloc[-1])
        low_price = float(df['Low'].iloc[-1])
        volume = int(df['Volume'].iloc[-1])
        
        candles = []
        df_last = df.tail(24)
        for timestamp, row in df_last.iterrows():
            candles.append({
                "time": timestamp.strftime("%Y-%m-%d %H:%M:%S") if hasattr(timestamp, "strftime") else str(timestamp),
                "open": round(float(row['Open']), 2),
                "high": round(float(row['High']), 2),
                "low": round(float(row['Low']), 2),
                "close": round(float(row['Close']), 2),
                "volume": int(row['Volume'])
            })
            
        start_price = float(df['Close'].iloc[0])
        pct_change = ((latest_close - start_price) / start_price) * 100
        
        return {
            "status": "success",
            "ticker": clean_ticker,
            "current_price": round(latest_close, 2),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "volume": volume,
            "price_change_pct": round(pct_change, 2),
            "candles": candles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch market data: {str(e)}")

@app.get("/api/history")
async def api_get_history():
    try:
        engine = get_db_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Database connection setup failed: {err}")
        
    try:
        async with async_session() as db_session:
            from sqlalchemy import select
            stmt = select(TradingHistory).order_by(TradingHistory.timestamp.desc()).limit(15)
            result = await db_session.execute(stmt)
            records = result.scalars().all()
            
            # Audit trade status dynamically for any running or unassigned records
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
                } for r in records
            ]
    finally:
        await engine.dispose()

@app.post("/api/trade")
async def api_execute_trade(request: Request):
    payload = await request.json()
    ticker = payload.get("ticker")
    interval = payload.get("interval")
    period = payload.get("period")
    strategy = payload.get("strategy")
    user_name = payload.get("user_name")
    user_email = payload.get("user_email")
    user_phone = payload.get("user_phone")
    
    if not all([ticker, interval, period, strategy, user_name, user_email, user_phone]):
        raise HTTPException(status_code=400, detail="Missing required parameters for operational execution.")
        
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
        return decision.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# Premium UI Portal Dynamic HTML Loader
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

# ---------------------------------------------------------
# Interactive Gateway Interface (FastAPI Web Hosting Boot)
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*75)
    print("      AUTOMATED MULTI-AGENTIC QUANTITATIVE TRADING DESK GATEWAY")
    print("="*75)
    print("Booting Asynchronous FastAPI Web Server & Neon PostgreSQL schemas monitor...")
    print("Access the Premium UI Dashboard at: http://127.0.0.1:8000")
    print("="*75 + "\n")
    
    # Run the uvicorn web server instance cleanly
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False, log_level="info")