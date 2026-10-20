from agents import Agent

def get_analyst_tool(analyst_agent: Agent):
    """Wraps the Market Data Analyst agent into a callable tool for orchestrators."""
    return analyst_agent.as_tool(
        tool_name="analyze_market_data",
        tool_description=(
            "Retrieves technical market data (EMA, SMA, RSI, MACD, ATR) and momentum analysis for a given asset. "
            "Expects parameters: ticker (str), period (str), and interval (str)."
        )
    )

def get_risk_tool(risk_agent: Agent):
    """Wraps the Risk Manager agent into a callable tool for orchestrators."""
    return risk_agent.as_tool(
        tool_name="evaluate_trading_risk",
        tool_description=(
            "Audits a proposed trading action and parameters against 1% capital-at-risk and R:R constraints, "
            "returning an APPROVED or REJECTED verdict with justification."
        )
    )
