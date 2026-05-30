import asyncio
import os
import json
from dotenv import load_dotenv
from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI, set_tracing_disabled
from tools import fetch_5day_history
from schemas import FinalTradingDecision

# Load environment variables (such as GEMINI_API_KEY) from .env
load_dotenv()

# Disable default telemetry/tracing to avoid 401 errors when OPENAI_API_KEY is not set
set_tracing_disabled(True)

# ---------------------------------------------------------
# LLM Service Configuration
# ---------------------------------------------------------
# Set up Gemini Client using the OpenAI-compatible endpoint
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Missing GEMINI_API_KEY in environment or .env file.")

client = AsyncOpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    max_retries=5
)

# Use models/gemini-2.5-flash: Google's ultra-cheap, highly-capable Flash model.
# NOTE: In Google's OpenAI-compatible endpoint, model names require the 'models/' prefix.
gemini_model = OpenAIChatCompletionsModel(
    model="models/gemini-2.5-flash",
    openai_client=client
)

# ---------------------------------------------------------
# Define Specialized Agents
# ---------------------------------------------------------

# Agent 1: The Specialized Data Analyst
# Enforces a structured description of market trend in its instructions.
analyst_agent = Agent(
    name="Market Data Analyst",
    instructions=(
        "You are a specialized data processing agent. Your sole objective is to ingest raw asset data "
        "using your tool and return a structured analysis. Read the pricing matrix sequentially "
        "and determine momentum. Do NOT include trading recommendations like BUY or SELL.\n"
        "Return your output as a raw JSON block conforming to this schema:\n"
        "{\n"
        "  \"price_variance_pct\": float (percentage variance over 5 days),\n"
        "  \"momentum\": \"bullish\" | \"bearish\" | \"neutral\",\n"
        "  \"summary\": \"factual analysis of the 5-day market trend\"\n"
        "}"
    ),
    tools=[fetch_5day_history],
    model=gemini_model
)

# Agent 2: The Independent Risk Guardrail
# Audits the trade recommendations.
risk_agent = Agent(
    name="Risk Manager Agent",
    instructions=(
        "You are an independent automated risk control block. Audit proposed trading actions against rules:\n"
        "1. Reject 'BUY' entries if data indicates a steep, uninterrupted multi-day downward cascade (Falling Knife).\n"
        "2. Reject entries if price vectors show erratic, unpredictable spikes without support.\n"
        "Return your audit verdict as a raw JSON block conforming to this schema:\n"
        "{\n"
        "  \"verdict\": \"APPROVED\" | \"REJECTED\",\n"
        "  \"justification\": \"Single-sentence technical justification\"\n"
        "}"
    ),
    model=gemini_model
)

# ---------------------------------------------------------
# Hierarchical "Agents-as-Tools" Wrapping
# ---------------------------------------------------------
# Gemini does not support combining strict structured output (JSON mode)
# and function calling in the same request. Therefore, we use the "Agents-as-Tools"
# pattern. The main orchestrator calls specialized sub-agents as tools,
# and parses the final JSON string in Python at the end.
analyst_tool = analyst_agent.as_tool(
    tool_name="analyze_market_data",
    tool_description="Retrieves a structured 5-day market data and momentum analysis for a given stock ticker."
)

risk_tool = risk_agent.as_tool(
    tool_name="evaluate_trading_risk",
    tool_description="Audits a proposed trading action and ticker, returning an APPROVED or REJECTED verdict with justification."
)

# Agent 3: The Orchestrator / Trading Desk Manager
manager_agent = Agent(
    name="Trading Desk Manager",
    instructions=(
        "You orchestrate the trading workflow.\n"
        "1. Extract the ticker from the user prompt.\n"
        "2. Call `analyze_market_data` tool to fetch and analyze the market history.\n"
        "3. Based on the momentum from the analysis, formulate an initial recommendation "
        "(e.g., 'bullish' -> BUY, 'bearish' -> SELL, 'neutral' -> HOLD).\n"
        "4. Call `evaluate_trading_risk` tool with your proposal and ticker to audit it.\n"
        "5. If the risk verdict is REJECTED, override your decision to HOLD.\n"
        "6. Provide the final formatted package decision. It MUST be a single raw JSON block (no markdown, no backticks) conforming to this schema:\n"
        "{\n"
        "  \"ticker\": \"TICKER_SYMBOL\",\n"
        "  \"action\": \"BUY\" | \"SELL\" | \"HOLD\",\n"
        "  \"risk_status\": \"Risk Manager verdict (APPROVED or REJECTED)\",\n"
        "  \"justification\": \"Final combined reasoning explaining both the technical momentum and risk audit outcome.\"\n"
        "}"
    ),
    tools=[analyst_tool, risk_tool],
    model=gemini_model
)

# ---------------------------------------------------------
# Execution Engine
# ---------------------------------------------------------
async def run_trading_desk(ticker_input: str):
    print(f"--- Activating Trading Desk System for: {ticker_input} ---")
    
    result = await Runner.run(
        manager_agent, 
        input=f"Process asset entry for target: {ticker_input}"
    )
    
    # Clean up the output string (strip backticks if the model used markdown)
    text = result.final_output.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        
    try:
        # Parse the JSON string
        data = json.loads(text)
        # Validate using Pydantic schema
        decision = FinalTradingDecision(**data)
        
        print("\n[Final Verified System JSON Output]:")
        print(decision.model_dump_json(indent=2))
        return decision
        
    except Exception as e:
        print(f"\nError parsing/validating final decision JSON: {e}")
        print("Raw output was:")
        print(result.final_output)

if __name__ == "__main__":
    # Test the system end-to-end with AAPL (Apple) stock
    asyncio.run(run_trading_desk("AAPL"))