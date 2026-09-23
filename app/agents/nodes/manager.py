from agents import Agent
from app.agents.client import get_gemini_model
from app.agents.prompts.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from app.agents.nodes.analyst import create_analyst_agent
from app.agents.nodes.risk import create_risk_agent
from app.agents.tools.agent_tools import get_analyst_tool, get_risk_tool

def create_manager_agent(model=None, analyst_agent=None, risk_agent=None) -> Agent:
    """
    Instantiates the Master Trading Desk Manager (Orchestrator).
    Role: Strategy Orchestrator & State Initiator.
    Boundaries: Delegates data analysis to Analyst Tool and compliance to Risk Tool.
    """
    llm = model or get_gemini_model()
    analyst = analyst_agent or create_analyst_agent(model=llm)
    risk = risk_agent or create_risk_agent(model=llm)

    analyst_tool = get_analyst_tool(analyst)
    risk_tool = get_risk_tool(risk)

    return Agent(
        name="Trading Desk Manager",
        instructions=ORCHESTRATOR_SYSTEM_PROMPT,
        tools=[analyst_tool, risk_tool],
        model=llm
    )
