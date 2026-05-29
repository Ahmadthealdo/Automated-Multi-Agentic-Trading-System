import asyncio
from agents import Agent, Runner
from tools import fetch_5day_history
from schemas import MarketAnalysis, RiskEvaluation, FinalTradingDecision

# Agent 1: The Specialized Data Analyst
analyst_agent = Agent(
    name="Market Data Analyst",
    instructions=(
        "You are a specialized data processing agent. Your sole objective is to ingest raw asset data "
        "using your tool and return a structured analysis. Read the pricing matrix sequentially "
        "and determine momentum. Do NOT include trading recommendations like BUY or SELL."
    ),
    tools=[fetch_5day_history]
)

# Agent 2: The Independent Risk Guardrail
risk_agent = Agent(
    name="Risk Manager Agent",
    instructions=(
        "You are an independent automated risk control block. Audit proposed trading actions against rules:\n"
        "1. Reject 'BUY' entries if data indicates a steep, uninterrupted multi-day downward cascade (Falling Knife).\n"
        "2. Reject entries if price vectors show erratic, unpredictable spikes without support.\n"
        "Provide a strict APPROVED or REJECTED verdict."
    )
)

# Agent 3: The Orchestrator / Trading Desk Manager
manager_agent = Agent(
    name="Trading Desk Manager",
    instructions=(
        "You orchestrate the trading workflow.\n"
        "1. Extract the ticker from the user prompt.\n"
        "2. Hand off to Market Data Analyst to get an analysis schema.\n"
        "3. Formulate an initial recommendation (Strong upward -> BUY, Strong downward -> SELL, Neutral -> HOLD).\n"
        "4. Hand off to Risk Manager Agent to evaluate your proposal.\n"
        "5. If rejected, override your decision to HOLD.\n"
        "6. Provide the final formatted package decision."
    )
)

# Define clean handoff access capabilities matching your architecture
manager_agent.handoffs = [analyst_agent, risk_agent]

async def run_trading_desk(ticker_input: str):
    print(f"--- Activating Trading Desk System for: {ticker_input} ---")
    
    # We enforce a structured output target profile right at the runner level
    result = await Runner.run(
        manager_agent, 
        user_turn=f"Process asset entry for target: {ticker_input}",
        response_format=FinalTradingDecision
    )
    
    # This prints out a pure, verified JSON string ready for any web frontend
    print("\n[Final Verified System JSON Output]:")
    print(result.final_output)

if __name__ == "__main__":
    # Test the system end-to-end smoothly
    asyncio.run(run_trading_desk("AAPL"))