from google.adk.agents import LlmAgent, SequentialAgent  
from short_selling_agent.stage_tools import (
    tool_fetch_bq_candidates, 
    tool_stage_news, 
    tool_stage_insiders, 
    tool_read_full_dossier
)

# ---------------------------------------------------------
# AGENT 1: BigQuery Ingestion
# ---------------------------------------------------------
BQ_INGESTION_AGENT = LlmAgent(
    name="BQIngestionAgent", 
    model="gemini-1.5-pro",
    tools=[tool_fetch_bq_candidates],
    system_instruction="""
You are Step 1: the BigQuery Ingestion Agent.

The user will always say:
  "Run the short-selling pipeline for YYYY-MM-DD."

1. Extract that exact date (e.g. “2023-06-01”) from the user’s message.  
2. Call your tool **once**, exactly like this:
     tool_fetch_bq_candidates(
       as_of_date="YYYY-MM-DD",
       limit=3
     )
3. Do not output anything else.  Your **only** assistant message must be that tool invocation.
""".strip()
)

# ---------------------------------------------------------
# AGENT 2: News Analyst
# ---------------------------------------------------------
NEWS_ANALYST_AGENT = LlmAgent(
    name="NewsAnalystAgent",
    model="gemini-1.5-pro",
    tools=[tool_stage_news],
    system_instruction="""
You are Step 2: the News Analyst Agent.

The conversation so far:
  • User:  "Run the short-selling pipeline for YYYY-MM-DD."  
  • Agent1: tool_fetch_bq_candidates(...) → "Tickers loaded: AAPL, TSLA, XYZ"

1. Re-extract the same date (YYYY-MM-DD) from the **user** message.  
2. You have the list of tickers from Agent1’s output.  For **each** ticker call:
     tool_stage_news(
       ticker="<TICKER>",
       as_of_date="YYYY-MM-DD"
     )
3. Do not output anything else until **all** calls succeed.  
4. Finally return **exactly**:
     "News is staged. The tickers to analyze are: AAPL, TSLA, XYZ"
""".strip()
)

# ---------------------------------------------------------
# AGENT 3: Insider Analyst
# ---------------------------------------------------------
INSIDER_ANALYST_AGENT = LlmAgent(
    name="InsiderAnalystAgent",
    model="gemini-1.5-pro",
    tools=[tool_stage_insiders],
    system_instruction="""
You are Step 3: the Insider Analyst Agent.

The conversation:
  • User:  "Run the short-selling pipeline for YYYY-MM-DD."  
  • Agent1: "Tickers loaded: AAPL, TSLA, XYZ"  
  • Agent2: "News is staged. The tickers to analyze are: AAPL, TSLA, XYZ"

1. Re-extract the same date (YYYY-MM-DD) from the **user** message.  
2. For **each** ticker, call:
     tool_stage_insiders(
       ticker="<TICKER>",
       as_of_date="YYYY-MM-DD"
     )
3. Wait until all calls finish.  
4. Return **exactly**:
     "Insiders are staged. The tickers are ready for the Quant Coordinator."
""".strip()
)

# ---------------------------------------------------------
# AGENT 4: Quant Coordinator (Final Decision)
# ---------------------------------------------------------
QUANT_COORDINATOR_AGENT = LlmAgent(
    name="LeadQuantTrader",
    model="gemini-1.5-pro",
    tools=[tool_read_full_dossier],
    system_instruction="""
You are Step 4: the Lead Quant Trader.

The conversation:
  • User:  "Run the short-selling pipeline for YYYY-MM-DD."  
  • Agent1/2/3 have staged market, news, and insider data for that date.

1. Call your only tool:
     tool_read_full_dossier()
2. You will receive the full JSON dossier.  Synthesize that data.
3. For each ticker in the dossier, produce:
     • conviction_score (1–10)
     • action: SHORT, AVOID, or COVER
     • brief reasoning
4. Output a JSON object with a "final_decisions" array, e.g.:
  {
    "final_decisions": [
      { "ticker":"AAPL", "conviction_score":8, "action":"SHORT", "reasoning":"..." },
      …
    ]
  }
""".strip()
)

# ---------------------------------------------------------
# BUILD THE PIPELINE
# ---------------------------------------------------------
SHORT_SELLING_PIPELINE = SequentialAgent(
    name="ShortSellingPipeline_V1",
    sub_agents=[
        BQ_INGESTION_AGENT,          
        NEWS_ANALYST_AGENT,          
        INSIDER_ANALYST_AGENT,       
        QUANT_COORDINATOR_AGENT      
    ]
)