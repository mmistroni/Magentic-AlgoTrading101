from google_adk import LLMAgent, SequentialAgent  
# Import your other tools: get_fmp_news, get_bearish_insider_sales
from short_selling_agent.tools import get_bq_short_candidates, get_fmp_news,\
     get_bearish_insider_sales
from short_selling_agent.schemas import PipelineDossier

# ---------------------------------------------------------
# AGENT 1: BigQuery Ingestion
# -------------------------------------------------------
BQ_INGESTION_AGENT = LLMAgent(
    name="BQIngestionAgent", 
    model="gemini-1.5-pro",
    tools=[get_bq_short_candidates],
    system_instruction=(
        "You are Step 1 in the Short Selling Pipeline. "
        "Your job is to call the `get_bq_short_candidates` tool. "
        "Extract the tickers and their quantitative data (price, drop %, float, squeeze risk). "
        "Format this data clearly as a 'Daily Candidate List' and pass it to the next agent."
    )
)

# ---------------------------------------------------------
# AGENT 2: News Analyst
# ---------------------------------------------------------
NEWS_ANALYST_AGENT = LLMAgent(
    name="NewsAnalystAgent",
    model="gemini-1.5-pro",
    tools=[get_fmp_news],
    system_instruction=(
        "You are Step 2 in the Short Selling Pipeline. "
        "You will receive a 'Daily Candidate List' containing several tickers from the previous step. "
        "For EACH ticker on the list, you MUST call the `get_fmp_news` tool. "
        "Write a brief 'Catalyst Summary' for each ticker explaining why it dropped today. "
        "APPEND your news summaries to the original candidate list, and pass the combined dossier forward."
    )
)

# ---------------------------------------------------------
# AGENT 3: Insider Analyst
# ---------------------------------------------------------
INSIDER_ANALYST_AGENT = LLMAgent(
    name="InsiderAnalystAgent",
    model="gemini-1.5-pro",
    tools=[get_bearish_insider_sales],
    system_instruction=(
        "You are Step 3 in the Short Selling Pipeline. "
        "You will receive a dossier containing tickers, market data, and news catalysts. "
        "For EACH ticker in the dossier, call the `get_bearish_insider_sales` tool. "
        "Check if C-Suite executives are dumping stock. "
        "APPEND your 'Insider Conviction Summary' for each ticker to the dossier, and pass it to the Lead Quant."
    )
)

# ---------------------------------------------------------
# AGENT 4: Quant Coordinator (Final Decision)
# ---------------------------------------------------------
QUANT_COORDINATOR_AGENT = LLMAgent(
    name="LeadQuantTrader",
    model="gemini-1.5-pro",
    tools=[], # No tools needed, just reasoning
    system_instruction=(
        "You are the final step: The Lead Quant Trader. "
        "You will receive a massive dossier from your junior analysts containing: "
        "1. BQ Market Data, 2. News Catalysts, 3. Insider Dumping Data for today's worst performing stocks. "
        "Your job is to synthesize all of this. "
        "For EACH stock, write a final 'Short Report'. "
        "Assign a Conviction Score (1-10) and give a final verdict: [SHORT, AVOID, or COVER]. "
        "If 'is_squeeze_risk' is True, be highly skeptical unless the news is devastating."
    )
)

# ---------------------------------------------------------
# BUILD THE PIPELINE
# ---------------------------------------------------------
SHORT_SELLING_PIPELINE = SequentialAgent(
    name="ShortSellingPipeline_V1",
    sub_agents=[
        BQ_INGESTION_AGENT,          # Step 1: Gets tickers from BQ
        NEWS_ANALYST_AGENT,          # Step 2: Adds News for all tickers
        INSIDER_ANALYST_AGENT,       # Step 3: Adds Insiders for all tickers
        QUANT_COORDINATOR_AGENT      # Step 4: Final verdict on all tickers
    ]
)