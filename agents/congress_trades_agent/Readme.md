##  Agent on Cloud Run - 
Cloud run agent to interpert congress trades
Brainstorme dusing Gemini 3 pro on outlier

Todo: agent needs to be tested locally


Every time you launch a new Codespace, run the following to authenticate:
```bash

# printf '%s' "$GCP_SA_KEY" > /workspaces/Magentic-AlgoTrading101/gcp_key.json

# 1. The most critical one: Points the code to your JSON file
export GOOGLE_APPLICATION_CREDENTIALS="/workspaces/Magentic-AlgoTrading101/gcp_key.json"

# 2. Sets the default project so you don't have to hardcode it in Python
export GOOGLE_CLOUD_PROJECT="datascience-projects"

# 3. Tells gcloud (and some libraries) which project to bill for API usage
export GOOGLE_CLOUD_QUOTA_PROJECT="datascience-projects"

Sample prompt

# The Prompt string
user_prompt = f"""
Current Analysis Date: 2026-02-01

Please execute the Congress Alpha Strategy:
1. First, research the political and legislative atmosphere for the month surrounding 2026-02-01.
2. Then, use that context to validate high-conviction Congress trades for the same date.
"""

# TEst Dates

Recommended Backtesting Dates
Since your data spans November 2024 to February 2026, and your SQL query uses a 90-day lookback, you cannot effectively backtest November 2024 (because the lookback period would be empty).

You should test these specific "Quarterly" checkpoints to see how the strategy evolves:

1. The "Ramp-Up" Date: 2025-02-01

Why: This is the first date where you have a full 90 days of history (Nov, Dec, Jan) populated in your database. The signals here will be the first "fully valid" ones.

[
  {
    "ticker": "HD",
    "action": "PASS",
    "confidence": 9,
    "risk_rating": "High",
    "reason": "Thesis: Infrastructure/Construction mentioned as a potential tailwind, but not a direct context play for Home Improvement retail. Fundamentals: P/E 25.91, Beta 1.09, Debt/Equity 544.586. Signal: Net Buy Activity 40. Verdict: Pass."
  },
  {
    "ticker": "JPM",
    "action": "BUY",
    "confidence": 8,
    "risk_rating": "Medium",
    "reason": "Thesis: Financials could see eased regulatory burdens under a Republican administration (one probable scenario). Fundamentals: P/E 13.77, Beta 1.05, Debt/Equity N/A (normal for financial sector). Signal: Net Buy Activity 39. Verdict: Buy."
  },
  {
    "ticker": "COR",
    "action": "PASS",
    "confidence": 9,
    "risk_rating": "High",
    "reason": "Thesis: Healthcare sector has mixed political outlook; potential for drug pricing headwinds under some scenarios. No clear direct context play. Fundamentals: P/E 18.38, Beta 0.69, Debt/Equity 472.584. Signal: Net Buy Activity 31. Verdict: Pass."
  },
  {
    "ticker": "FCFS",
    "action": "BUY",
    "confidence": 8,
    "risk_rating": "Medium",
    "reason": "Thesis: Financials could see eased regulatory burdens under a Republican administration (one probable scenario). Fundamentals: P/E 14.8, Beta 0.48, Debt/Equity 112.821. Signal: Net Buy Activity 30. Verdict: Buy."
  }
]





2. The "Mid-Year" Check: 2025-06-01


[
  {
    "ticker": "MKL",
    "action": "BUY",
    "confidence": 7,
    "risk_rating": "Low",
    "reason": "Thesis: No direct political context support for Financial Services (Property & Casualty Insurance). Fundamentals: P/E 17.01, Beta 0.77 (low volatility), Debt/Equity 23.042 (healthy). Signal: Net Buy Score 30 (strong insider buying activity, qualifying as an 'Insider Play'). Verdict: Buy."
  },
  {
    "ticker": "NVT",
    "action": "BUY",
    "confidence": 8,
    "risk_rating": "Medium",
    "reason": "Thesis: Supply chain resilience initiatives and 'friend-shoring' directly support US-based manufacturing and industrial equipment, aligning with nVent Electric's sector. Fundamentals: P/E 23.31, Beta 1.31 (moderate volatility), Debt/Equity 41.815 (healthy). Signal: Net Buy Score 20 (moderate insider buying, strong enough when combined with context). Verdict: Buy."
  },
  {
    "ticker": "FLT",
    "action": "PASS",
    "confidence": 3,
    "risk_rating": "High",
    "reason": "Thesis: Unknown sector, thus cannot align with political context. Fundamentals: P/E 0, Beta 1.0, Debt/Equity null (missing critical fundamental data, indicating high risk). Signal: Net Buy Score 20. Verdict: Pass (due to lack of essential fundamental information for risk assessment)."
  },
  {
    "ticker": "JLL",
    "action": "PASS",
    "confidence": 8,
    "risk_rating": "High",
    "reason": "Thesis: Commercial Real Estate (CRE) faces significant headwinds from higher interest rates and continued valuation concerns, directly impacting Real Estate Services. This strong negative political context outweighs insider buying signals. Fundamentals: P/E 16.9, Beta 1.41 (moderate-high volatility), Debt/Equity 47.732 (healthy). Signal: Net Buy Score 20. Verdict: Pass."
  },
  {
    "ticker": "IBM",
    "action": "PASS",
    "confidence": 5,
    "risk_rating": "Medium",
    "reason": "Thesis: The Technology sector faces a mixed political context with potential regulatory scrutiny on one hand and strategic importance for supply chain resilience on the other; no direct strong supportive context to warrant a 'Context Play'. Fundamentals: P/E 16.5, Beta 0.9 (low volatility), Debt/Equity 167.8. Signal: Net Buy Score 17 (does not meet the 'net_buy_activity > 20' threshold for a strong 'Insider Play'). Verdict: Pass (lacks sufficiently strong signals or direct context support)."
  }
]


Why: This captures the Spring/Summer legislative session trades.
3. The "Year-End" Check: 2025-11-01
[
  {
    "ticker": "MSDA",
    "action": "PASS",
    "confidence": 0,
    "risk_rating": "High",
    "reason": "Thesis: Political context points to specific sectors with tailwinds like Defense, Semiconductors, Industrials, AI, and Cybersecurity. Fundamentals: Sector, P/E, Beta, and Debt-to-Equity are unknown. Signal: Net Buy Score is 28. Verdict: Pass, due to insufficient fundamental data for proper risk assessment and sector alignment."
  },
  {
    "ticker": "SMCY",
    "action": "PASS",
    "confidence": 0,
    "risk_rating": "High",
    "reason": "Thesis: Political context points to specific sectors with tailwinds like Defense, Semiconductors, Industrials, AI, and Cybersecurity. Fundamentals: Sector, P/E, Beta, and Debt-to-Equity are unknown. Signal: Net Buy Score is 25. Verdict: Pass, due to insufficient fundamental data for proper risk assessment and sector alignment."
  },
  {
    "ticker": "FIG",
    "action": "BUY",
    "confidence": 8,
    "risk_rating": "Medium",
    "reason": "Thesis: The political context highlights strong tailwinds for Technology, particularly in AI, advanced computing, and cybersecurity, driven by US-China strategic competition and initiatives like the 'American Economic Resilience & Security Act.' This directly supports the Software - Application sector. Fundamentals: P/E is 102.68, Beta is 1.0, Debt-to-Equity is 4.41 (healthy). Signal: Net Buy Score is 24. Verdict: Buy."
  },
  {
    "ticker": "HLMIX",
    "action": "PASS",
    "confidence": 0,
    "risk_rating": "High",
    "reason": "Thesis: Political context points to specific sectors with tailwinds like Defense, Semiconductors, Industrials, AI, and Cybersecurity. Fundamentals: Sector, P/E, Beta, and Debt-to-Equity are unknown. Signal: Net Buy Score is 24. Verdict: Pass, due to insufficient fundamental data for proper risk assessment and sector alignment."
  }
]

Why: This gives you exactly one year of data. It captures end-of-year budget spending trades.
4. The "Final" Check: 2026-02-01

Why: This is the end of your dataset. It allows you to see if the strategy held up over the full 15-month period

[
  {
    "ticker": "CSCO",
    "action": "BUY",
    "confidence": 9,
    "risk_rating": "Low",
    "reason": "Thesis: \"Cybersecurity Infrastructure Protection Bill\" and rising state-sponsored cyber threats drive demand for network security, aligning with Cisco's offerings. Fundamentals: P/E 19.27, Beta 0.86, Debt/Equity 63.228 (healthy). Signal: Net Buy Score 21. Verdict: Buy."
  },
  {
    "ticker": "TSM",
    "action": "BUY",
    "confidence": 8,
    "risk_rating": "Medium",
    "reason": "Thesis: \"Advanced Industries Competitiveness Act\" and geopolitical risks (China-Taiwan tensions) amplify urgency for supply chain independence in Semiconductors. Fundamentals: P/E 20.11, Beta 1.27, Debt/Equity 18.187 (very healthy). Signal: Net Buy Score 17. Verdict: Buy."
  },
  {
    "ticker": "TSCO",
    "action": "PASS",
    "confidence": 3,
    "risk_rating": "High",
    "reason": "Thesis: No direct political context support. Consumer Cyclical sector faces headwinds from sticky inflation and high interest rates. Fundamentals: P/E 22.45, Beta 0.73, Debt/Equity 230.228 (high for non-utility/financial). Signal: Net Buy Score 15 (low conviction). Verdict: Pass."
  },
  {
    "ticker": "DELL",
    "action": "PASS",
    "confidence": 2,
    "risk_rating": "High",
    "reason": "Thesis: Indirect political context, not a strong \"Context Play\". Fundamentals: P/E 10.95, Beta 1.1, Debt/Equity: Unknown (critical data missing). Signal: Net Buy Score 15. Verdict: Pass."
  },
  {
    "ticker": "CSWI",
    "action": "PASS",
    "confidence": 1,
    "risk_rating": "Very High",
    "reason": "Thesis: Unable to assess political context due to unknown sector/industry. Fundamentals: P/E 0, Beta 1.0, Debt/Equity: Unknown (critical data missing). Signal: Net Buy Score 15. Verdict: Pass."
  }
]


==== FOR a Run on  25-6-26 we got
[
  {
    "ticker": "FN",
    "action": "BUY",
    "confidence": 7,
    "risk_rating": "Medium",
    "reason": "Thesis: Macro regime is BULLISH (market uptrend). Congress shows strong net buying activity (net_buy_activity: 10). There is no 'Golden Confluence' from corporate lobbying or C-Suite insider buying, but also no negative signals. Fundamentals: P/E is 30.69 (reasonable for the Technology sector). Debt-to-Equity is 0.192 (very healthy). Verdict: Buy."
  }
]



================= 20260706 - rev engineer congres strades
Agents:

congress_researcher = LlmAgent(
    name="CongressResearcher",
    model='gemini-2.5-flash',
    instruction=RESEARCHER_INSTRUCTION,
    tools=[
        FunctionTool(fetch_congress_signals_tool)  this comes directly from big query
executing this 
WITH clean_data AS (
        SELECT
        AS_OF_DATE AS trade_date,
        CASE
            WHEN DISCLOSURE LIKE '%Purchase%' THEN 'Buy'
            WHEN DISCLOSURE LIKE '%Sale%' THEN 'Sell'
            ELSE 'Other'
        END AS action,
        TRIM(REPLACE(TICKER, 'Ticker:', '')) AS ticker
        FROM `datascience-projects.gcp_shareloader.senate_disclosures`
        WHERE
        TICKER IS NOT NULL
        AND AS_OF_DATE IS NOT NULL
        AND AS_OF_DATE >= DATE_SUB(run_date, INTERVAL 90 DAY)
        AND AS_OF_DATE <= run_date
    )

    SELECT
        run_date AS signal_date,
        ticker,
        COUNTIF(action = 'Buy') AS purchase_count,
        COUNTIF(action = 'Sell') AS sale_count,
        (COUNTIF(action = 'Buy') - COUNTIF(action = 'Sell')) AS net_buy_activity,
        
        -- NEW METRIC: Count Distinct Days (The Spam Filter)
        COUNT(DISTINCT CASE WHEN action='Buy' THEN trade_date END) as buying_days_count,
        
        MAX(trade_date) AS last_trade_date
    FROM clean_data
    WHERE
        LOWER(ticker) NOT IN (
        'vti', 'spy', 'voo', 'qqq', 'ivv', 'spxl', 'spxs',
        'tqqq', 'sqqq', 'dia', 'iwm', 'dow', 'shv', 'bnd'
        )
        AND TRIM(ticker) != ''
        AND ticker IS NOT NULL
        
        -- NEW FILTERS: Remove Mutual Funds (5 chars) and weird symbols
        AND LENGTH(ticker) <= 4 
        AND NOT REGEXP_CONTAINS(ticker, r'[^a-zA-Z]') 

    GROUP BY ticker, run_date

    HAVING
        -- 1. Must be bought on at least 2 SEPARATE days (Kills 1-day spam)
        buying_days_count >= 2
        
        -- 2. Net activity must still be positive
        AND net_buy_activity >= 5
        AND last_trade_date >= DATE_SUB(run_date, INTERVAL 90 DAY)
        AND (
        COUNTIF(action = 'Sell') = 0
        OR
        (COUNTIF(action = 'Buy') * 1.0 / GREATEST(COUNTIF(action = 'Sell'), 1)) >= 2.0
        )

    ORDER BY buying_days_count DESC, net_buy_activity DESC
    LIMIT 10;
    



    ],
    output_key="political_context" 
)

# ==========================================
# AGENT 2: The Insider Analyst
# ==========================================
insider_analyst = LlmAgent(
    name="CorporateInsiderAnalyst",
    model='gemini-2.5-flash',
    instruction=INSIDER_ANALYST_INSTRUCTION,
    tools=[
        FunctionTool(fetch_lobbying_signals_tool),  ---> this too comes form big query
        
        
        
        
         # <-- Checks Lobbying on the tickers
        FunctionTool(fetch_form4_signals_tool)    --> this will come from big query  but at the moment is mocked
                      we need to replacce with real
    ],
    output_key="political_and_insider_context"
)

# ==========================================
# AGENT 3: The Trader
# ==========================================
congress_trader = LlmAgent(
    name="CongressTrader",
    model='gemini-2.5-flash',
    instruction=TRADER_INSTRUCTION,
    tools=[
        FunctionTool(check_fundamentals_tool),     # <-- Checks P/E, Debt, and makes final decision
    ],
    output_key="final_trade_plan"
)
