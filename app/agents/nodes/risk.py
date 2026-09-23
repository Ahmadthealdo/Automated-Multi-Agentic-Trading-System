from agents import Agent
from app.agents.client import get_gemini_model
from app.agents.prompts.risk import RISK_SYSTEM_PROMPT

def create_risk_agent(model=None) -> Agent:
    """
    Instantiates the Risk Manager Guardrail agent.
    Role: Capital Preservation & Compliance Audit Guardrail.
    Boundaries: Must prefix all audits with [APPROVED] or [REJECTED] and enforce 1% risk rule.
    """
    llm = model or get_gemini_model()
    return Agent(
        name="Risk Manager Agent",
        instructions=RISK_SYSTEM_PROMPT,
        model=llm
    )
