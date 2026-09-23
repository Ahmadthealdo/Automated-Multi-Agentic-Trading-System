from agents import Agent
from app.agents.client import get_gemini_model
from app.agents.prompts.analyst import ANALYST_SYSTEM_PROMPT
from app.agents.tools.market_data import fetch_market_data

def create_analyst_agent(model=None) -> Agent:
    """
    Instantiates the Market Data Analyst agent.
    Role: Specialized Quantitative & Technical Signal Synthesizer.
    Boundaries: Zero portfolio execution authority; never emits BUY/SELL/HOLD directives.
    """
    llm = model or get_gemini_model()
    return Agent(
        name="Market Data Analyst",
        instructions=ANALYST_SYSTEM_PROMPT,
        tools=[fetch_market_data],
        model=llm
    )
