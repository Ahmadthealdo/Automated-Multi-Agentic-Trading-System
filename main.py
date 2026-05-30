import asyncio
import os
import json
from dotenv import load_dotenv
from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI, set_tracing_disabled
from tools import fetch_market_data
from schemas import FinalTradingDecision

# Load environment variables from .env
load_dotenv()

# Disable telemetry/tracing to avoid 401 errors when OPENAI_API_KEY is not set
set_tracing_disabled(True)

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
        "   If the final system action is verified as a BUY or STRONG BUY, you must identify the active timeframe (interval) variable "
        "   and extract the exact entry bounds from the latest close price (entry price) using this strict compliance matrix:\n"
        "   - If Timeframe is '15m': Set Stop Loss at -1.0% (entry * 0.99) and Take Profit at +2.0% (entry * 1.02).\n"
        "   - If Timeframe is '1h' : Set Stop Loss at -2.5% (entry * 0.975) and Take Profit at +5.0% (entry * 1.05).\n"
        "   - If Timeframe is '4h' : Set Stop Loss at -4.0% (entry * 0.96) and Take Profit at +8.0% (entry * 1.08).\n"
        "   - If Timeframe is '1d' : Set Stop Loss at -8.0% (entry * 0.92) and Take Profit at +15.0% (entry * 1.15).\n"
        "   Format both values as a dollar amount and percentage (e.g. \"$108.00 (+8.0%)\"). "
        "   If the final action is HOLD, SELL, or STRONG SELL, set both exit targets to \"N/A\".\n"
        "7. Provide the final formatted package decision. It MUST be a single raw JSON block (no markdown, no backticks) conforming to this schema:\n"
        "{\n"
        "  \"ticker\": \"TICKER_SYMBOL\",\n"
        "  \"action\": \"STRONG BUY\" | \"BUY\" | \"HOLD\" | \"SELL\" | \"STRONG SELL\",\n"
        "  \"risk_status\": \"Risk Manager verdict (APPROVED or REJECTED)\",\n"
        "  \"stable_capital\": \"Available stable capital balance from Risk Manager (e.g. $10,000.00 USDT)\",\n"
        "  \"budget_allocation\": \"Exact capital allocation budget from Risk Manager (e.g. Allocate 5% ($500.00 USDT))\",\n"
        "  \"take_profit\": \"Calculated target Take Profit price and percentage, or N/A\",\n"
        "  \"stop_loss\": \"Calculated target Stop Loss price and percentage, or N/A\",\n"
        "  \"justification\": \"Final combined reasoning explaining technical momentum, risk compliance, position allocation, and TP/SL target boundaries.\"\n"
        "}"
    ),
    tools=[analyst_tool, risk_tool],
    model=gemini_model
)

# ---------------------------------------------------------
# Execution Engine
# ---------------------------------------------------------
async def run_trading_desk(ticker_input: str, interval: str, period: str, strategy: str):
    result = await Runner.run(
        manager_agent, 
        input=(
            f"Process trade opportunity for asset: '{ticker_input}' using strategy '{strategy}'. "
            f"Please fetch market data using interval='{interval}' and lookback period='{period}'."
        )
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
        
    try:
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
        print(f"  * TAKE PROFIT TRGT : {decision.take_profit}")
        print(f"  * STOP LOSS TARGET : {decision.stop_loss}")
        print(f"  * JUSTIFICATION    : {decision.justification}")
        print("="*70 + "\n")
        return decision
        
    except Exception as e:
        print(f"\n[Error] Failed to parse final decision JSON: {e}")
        print("Raw Agent response was:")
        print(result.final_output)

# ---------------------------------------------------------
# Interactive Gateway Interface
# ---------------------------------------------------------
if __name__ == "__main__":
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
    
    # Run the trading desk pipeline
    asyncio.run(run_trading_desk(ticker, interval, period, strategy))