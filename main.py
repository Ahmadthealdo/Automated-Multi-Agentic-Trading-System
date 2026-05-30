import asyncio
import os
import json
from dotenv import load_dotenv, find_dotenv
from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI
from tools import fetch_market_data
from schemas import FinalTradingDecision

# Observability and Telemetry Integration
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
from langfuse import get_client

# Asynchronous Database and Session Imports
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone
from agents.extensions.memory.sqlalchemy_session import SQLAlchemySession

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
    take_profit = Column(String)
    stop_loss = Column(String)
    justification = Column(Text)

# ---------------------------------------------------------
# Load environment and configure
# ---------------------------------------------------------
load_dotenv(find_dotenv())  # Load local .env file

# Instrumentation setup
OpenAIAgentsInstrumentor().instrument()

# Load environment variables
os.getenv("LANGFUSE_PUBLIC_KEY")
os.getenv("LANGFUSE_SECRET_KEY")
os.getenv("LANGFUSE_HOST")

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
# Define Specialized Subagents
# ---------------------------------------------------------

# Agent 1: The Specialized Data Analyst
# Ingests market history and calculates indicators, returning technical summaries
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
# Audits the trade recommendations based on strict risk criteria and computes position sizing
risk_agent = Agent(
    name="Risk Manager Agent",
    instructions=(
        "You are the ultimate guardrail of the system. Your primary objective is to audit "
        "the Trading Desk Manager's signal and compute the exact monetary Position Size using strict portfolio rules.\n"
        "1. CAPTURE TOTAL STABLE LIQUIDITY:\n"
        "   Identify the available stable cash account balance (default to $10,000.00 USDT if not specified). "
        "   You must ONLY consider flat fiat (USD) or stablecoins (USDT, USDC, BUSD). "
        "   Completely EXCLUDE and ignore any volatile risk assets (like existing balances of BTC, ETH, or stocks).\n"
        "2. EVALUATE PROBABILITY & COMPUTE ALLOCATION:\n"
        "   Apply a mathematical position-sizing model based on the trade signal probability tier:\n"
        "   - If signal is [STRONG BUY] or [STRONG SELL] (High Probability): Approve and recommend allocating exactly 5% of the total stable balance.\n"
        "   - If signal is [BUY] or [SELL] (Medium Probability): Approve and recommend allocating exactly 2% of the total stable balance.\n"
        "   - If signal is [HOLD] (Low Probability/No Setup): Reject/block the trade and allocate 0%.\n"
        "3. STRUCTURE THE FINANCIAL OUTPUT:\n"
        "   Return your evaluation strictly as a raw JSON block conforming to this schema:\n"
        "   {\n"
        "     \"stable_capital\": \"Current Account Stable Capital (e.g. $10,000.00 USDT)\",\n"
        "     \"risk_tier\": \"High Probability | Medium Probability | Zero Allocation\",\n"
        "     \"verdict\": \"APPROVED\" | \"REJECTED\",\n"
        "     \"action_command\": \"STRONG BUY | BUY | HOLD | SELL | STRONG SELL\",\n"
        "     \"budget_allocation\": \"Allocate X% ($Y.YY USDT)\",\n"
        "     \"justification\": \"Compliance justification explaining why this capital size matches the asset's risk profile.\"\n"
        "   }"
    ),
    model=gemini_model
)

# ---------------------------------------------------------
# Hierarchical "Agents-as-Tools" Wrapping
# ---------------------------------------------------------
# Convert sub-agents into clean tools. This allows the main manager to
# retain conversation state and bypass Gemini's simultaneous function-call + JSON limitation.
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
        "Audits a proposed trading action and ticker, returning an APPROVED or REJECTED verdict with justification."
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
        "3. Review the technical indicators (EMA crossovers, RSI levels, trend directions) and classify the trade "
        "opportunity into exactly ONE of these five strategy tiers:\n"
        "   - STRONG BUY: Extreme upward momentum, EMA9 healthily above EMA21, RSI not yet overbought.\n"
        "   - BUY: Moderate upward trend or stable support baseline established.\n"
        "   - HOLD: No clear direction, sideways movement, high uncertainty, or asset is overbought/oversold.\n"
        "   - SELL: Moderate downward trend breaking immediate support lines.\n"
        "   - STRONG SELL: Severe downward breakdown, EMA9 well below EMA21, massive structural panic.\n"
        "4. Call `evaluate_trading_risk` tool with your chosen strategy signal tier (e.g., 'STRONG BUY') and the analyst summary to audit it.\n"
        "5. If the Risk Manager Agent rejects your proposal (verdict is 'REJECTED'), you must override your decision to 'HOLD'.\n"
        "6. CALCULATE ADJUSTED TARGET EXIT BOUNDARIES (TP/SL):\n"
        "   You are strictly forbidden from guessing, assuming, or utilizing hypothetical placeholder numbers for the asset entry cost. "
        "   Look directly inside the `current_price` property field returned by the `analyze_market_data` tool handoff payload. "
        "   Use that exact live decimal float value as your entry price variable baseline to execute your arithmetic calculations "
        "   for Stop Loss and Take Profit bounds according to the strategy matrix rules:\n"
        "   - If Timeframe is '15m': Set Stop Loss at -1.0% (entry * 0.99) and Take Profit at +2.0% (entry * 1.02).\n"
        "   - If Timeframe is '1h' : Set Stop Loss at -2.5% (entry * 0.975) and Take Profit at +5.0% (entry * 1.05).\n"
        "   - If Timeframe is '4h' : Set Stop Loss at -4.0% (entry * 0.96) and Take Profit at +8.0% (entry * 1.08).\n"
        "   - If Timeframe is '1d' : Set Stop Loss at -8.0% (entry * 0.92) and Take Profit at +15.0% (entry * 1.15).\n"
        "   Both values must be calculated as plain numerical float numbers rounded to 2 decimal places. "
        "   If the final action is HOLD, SELL, or STRONG SELL, set both TAKE_PROFIT and STOP_LOSS to 0.0.\n"
        "7. Provide the final formatted package decision. It MUST be a single raw JSON block (no markdown, no backticks) conforming to this schema:\n"
        "{\n"
        "  \"ticker\": \"TICKER_SYMBOL\",\n"
        "  \"action\": \"STRONG BUY\" | \"BUY\" | \"HOLD\" | \"SELL\" | \"STRONG SELL\",\n"
        "  \"risk_status\": \"Risk Manager verdict (APPROVED or REJECTED)\",\n"
        "  \"stable_capital\": \"Available stable capital balance from Risk Manager (e.g. $10,000.00 USDT)\",\n"
        "  \"budget_allocation\": \"Exact capital allocation budget from Risk Manager (e.g. Allocate 5% ($500.00 USDT))\",\n"
        "  \"TAKE_PROFIT\": float (calculated numerical Take Profit price target, or 0.0 if not applicable),\n"
        "  \"STOP_LOSS\": float (calculated numerical Stop Loss price target, or 0.0 if not applicable),\n"
        "  \"justification\": \"Final combined reasoning explaining technical momentum, risk compliance, position allocation, and TP/SL target boundaries.\"\n"
        "}"
    ),
    tools=[analyst_tool, risk_tool],
    model=gemini_model
)

# ---------------------------------------------------------
# Execution Engine
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
        print(f"  * TAKE PROFIT TRGT : ${decision.TAKE_PROFIT:.2f}" if decision.TAKE_PROFIT > 0 else f"  * TAKE PROFIT TRGT : N/A")
        print(f"  * STOP LOSS TARGET : ${decision.STOP_LOSS:.2f}" if decision.STOP_LOSS > 0 else f"  * STOP LOSS TARGET : N/A")
        print(f"  * JUSTIFICATION    : {decision.justification}")
        print("="*70 + "\n")
        
        # Persist standard transactional outcomes using async session maker bound to database connection engine
        try:
            async_session = async_sessionmaker(engine, expire_on_commit=False)
            async with async_session() as db_session:
                new_record = TradingHistory(
                    user_name=user_name,
                    user_email=user_email,
                    user_phone=user_phone,
                    ticker=decision.ticker,
                    action=decision.action,
                    risk_status=decision.risk_status,
                    stable_capital=decision.stable_capital,
                    budget_allocation=decision.budget_allocation,
                    take_profit=str(decision.TAKE_PROFIT),
                    stop_loss=str(decision.STOP_LOSS),
                    justification=decision.justification
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
# Interactive Gateway Interface
# ---------------------------------------------------------
if __name__ == "__main__":
    # Mock the frontend login identity collection gateway at initial boot
    print("\n" + "="*75)
    print("      OPERATOR LOGIN IDENTITY MIGRATION GATEWAY (MOCK FRONTEND)")
    print("="*75)
    user_name_input = ""
    while not user_name_input:
        user_name_input = input("[Login] Enter Operator Name: ").strip()
        if not user_name_input:
            print("[Warning] Operator Name is required.")
            
    user_email_input = ""
    while not user_email_input:
        user_email_input = input("[Login] Enter Email Address: ").strip()
        if not user_email_input:
            print("[Warning] Email Address is required.")
            
    user_phone_input = ""
    while not user_phone_input:
        user_phone_input = input("[Login] Enter Phone Number: ").strip()
        if not user_phone_input:
            print("[Warning] Phone Number is required.")
    print("-"*75)
    print("Operator credentials logged successfully. Access granted.")
    print("="*75)

    # Quantitative Desk Router Greeting
    print("\n" + "="*75)
    print("      AUTOMATED MULTI-AGENTIC QUANTITATIVE TRADING DESK GATEWAY")
    print("="*75)
    print("Welcome, Operator. This is your Master Trading Desk Router.")
    print("System status: ACTIVE | Core Framework: OpenAI Agents SDK | LLM: Gemini")
    print("-"*75)
    
    # 1. GREET AND ASK FOR ASSET (With crypto check guardrail)
    while True:
        ticker = input("[Router] Enter Asset Ticker (e.g. AAPL, NVDA, BTC-USD): ").strip()
        if not ticker:
            print("[Warning] Asset ticker cannot be empty. Please enter a valid symbol.")
            continue
            
        # Crypto check guardrail
        crypto_keywords = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOT', 'DOGE', 'LTC', 'LINK', 'UNI', 'AVAX']
        clean_ticker = ticker.upper()
        
        # If user types BTC or similar without -USD
        if clean_ticker in crypto_keywords:
            print(f"\n[Polite Correction] Cryptocurrency assets must be explicitly mapped with their base currency pair.")
            print(f"To ensure yfinance compatibility, please use '{clean_ticker}-USD' instead of '{ticker}'.")
            print("-"*75)
            continue
            
        ticker = clean_ticker
        break
        
    # 2. PRESENT TIMEFRAME OPTIONS
    print("\n" + "="*55)
    print("            DYNAMIC STRATEGY TIMEFRAME SELECTOR")
    print("="*55)
    print("  INTRADAY STRATEGIES:")
    print("    [A] 15-Minute (Short-term scalp       | Fetches 7 Days of history)")
    print("    [B] 1-Hour    (Day/Swing execution    | Fetches 30 Days of history)")
    print("  SWING STRATEGIES:")
    print("    [C] 4-Hour    (Medium-term swing      | Fetches 60 Days of history)")
    print("    [D] 1-Day     (Macro trend position   | Fetches 180 Days of history)")
    print("="*55)
    
    while True:
        choice = input("[Router] Select Execution Strategy Option [A, B, C, or D]: ").strip().upper()
        if choice not in ['A', 'B', 'C', 'D']:
            print("[Warning] Invalid selection. Please choose exactly A, B, C, or D.")
            continue
        break
        
    # 3. COMPUTE LOOKBACK DATA MATRIX SILENTLY
    if choice == 'A':
        interval = "15m"
        period = "7d"
        strategy = "Intraday Scalp"
        primary_indicators = ["9-EMA", "21-EMA", "RSI(14)"]
    elif choice == 'B':
        interval = "1h"
        period = "30d"
        strategy = "Intraday Swing"
        primary_indicators = ["9-EMA", "21-EMA", "RSI(14)"]
    elif choice == 'C':
        interval = "4h"
        period = "60d"
        strategy = "Medium Swing"
        primary_indicators = ["50-MA", "MACD", "RSI(14)"]
    else: # choice == 'D'
        interval = "1d"
        period = "180d"
        strategy = "Macro Position"
        primary_indicators = ["50-MA", "200-MA", "Macro RSI"]
        
    print("\n" + "-"*75)
    print(f"[Router] Payload Locked & Compiled Successfully.")
    print(f"  * TARGET ASSET     : {ticker}")
    print(f"  * STRATEGY TYPE    : {strategy}")
    print(f"  * CANDLE INTERVAL  : {interval}")
    print(f"  * LOOKBACK WINDOW  : {period}")
    print(f"  * INDICATOR SUITE  : {', '.join(primary_indicators)}")
    print("-"*75)
    print("[Router] Executing multi-agent validation pipeline. Please stand by...")
    print("="*75)
    
    # Run the trading desk pipeline passing operator metadata down the chain
    asyncio.run(run_trading_desk(ticker, interval, period, strategy, user_name_input, user_email_input, user_phone_input))