from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

# Replace these with your actual 3 specialist agents
from congress_trades_agent.skills.congress_researcher.agent import congress_researcher
from congress_trades_agent.skills.insider_analyst.agent import insider_analyst  # your 2nd specialist
from congress_trades_agent.skills.congress_trader.agent import congress_trader

ORCHESTRATOR_INSTRUCTION = """
You are the Congress Trades Orchestrator. Coordinate the specialist agents in order:

1. **Congressional & Contract Research:** Call `congress_researcher` with the requested `analysis_date` (YYYY-MM-DD) to identify candidate tickers and congressional/government contract signals.
2. **Insider / Secondary Signal Check:** Call `insider_analyst` for the candidate ticker(s) and `analysis_date` so insider and confluence context are populated in session state.
3. **Short-Circuit Guardrail:** If no valid candidates or confluence signals are found, DO NOT call `congress_trader` and DO NOT store a trade decision. State clearly that no active confluence signals were found for that `analysis_date`.
4. **Trade Synthesis:** Only when active signals exist, call `congress_trader` to synthesize and record the trade decision for the verified candidate(s) and `analysis_date`.
"""

CONGRESS_PIPELINE = LlmAgent(
    name="congress_orchestrator",
    model=congress_trader.model,  # or your configured Gemini model string/instance
    description="Orchestrates congressional research, insider analysis, confluence gating, and trade decision synthesis.",
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[
        AgentTool(agent=congress_researcher),
        AgentTool(agent=insider_analyst),
        AgentTool(agent=congress_trader),
    ],
)