# Master Implementation Plan: Congress Alpha Agent Pipeline

---

## 1. Executive Summary & Goals

The objective is to elevate the **Congress Alpha Multi-Agent System** into an enterprise-grade, production-ready framework. This plan addresses persistence, unit/integration testing, programmatic evaluation without relying on `adk web` UI session recordings, architectural refactoring, and automated job scheduling.

### Key Deliverables
1. **Skills Framework Architecture:** Restructure repository into modular, isolated agent skill folders.
2. **BigQuery Persistence:** Store trade recommendations, signal context, and entry prices for long-term multi-month tracking.
3. **Pipeline Runner & Programmatic Evals:** Create a headless ADK runner wrapper (`pipeline_runner.py`) to execute prompts in code and score prompt variations using LLM-as-a-Judge / LangChain / DeepEval frameworks.
4. **Integration & Mock Test Suite:** Implement `pytest` suites covering live execution and mocked scenario edge cases (e.g., Bear Markets, Insider Dumping, high P/E ratios).
5. **Automated Weekly Scheduler:** Deploy to Google Cloud Run triggered via Cloud Scheduler on a weekly cadence.

---

## 2. Phase 1: Architecture Refactoring (Skills Framework)

Restructure the repository to decouple tools, system prompts, schemas, and sub-agents into modular skill directories.

### Target Directory Layout

```text
congress_trades_agent/
├── config.py
├── agent.py                        # ADK root_agent definition
├── skills/
│   ├── congress_scout/
│   │   ├── __init__.py
│   │   ├── prompt.py
│   │   └── tools.py
│   ├── insider_analysis/
│   │   ├── __init__.py
│   │   ├── prompt.py
│   │   └── tools.py
│   └── portfolio_management/
│       ├── __init__.py
│       ├── prompt.py
│       └── tools.py
├── schemas/
│   ├── __init__.py
│   ├── inputs.py
│   └── outputs.py
└── utils/
    ├── pipeline_runner.py          # Programmatic ADK InMemoryRunner wrapper
    ├── bigquery_client.py          # BigQuery persistence helper
    └── market_data.py



[STEP 1: Refactor to Skills Framework Layout]
                        │
                        ▼
  [STEP 2: Build Pipeline Runner (pipeline_runner.py)]
                        │
                        ▼
  [STEP 3: Setup BigQuery Schema & Persistence Client]
                        │
                        ▼
  [STEP 4: Implement Pytest Suite & Programmatic Evals]
                        │
                        ▼
  [STEP 5: Deploy to Cloud Run + Cloud Scheduler]



========================== CURRENT SETUP
congress_agents
  |
  |__ congress_researcher  (political context)
         |__ fetch_congress_signals_tool  
  |__  insider_analyst   (political_and_insider_context)
         |__ fetch_lobbying_signals_tool 
         |__ fetch_form4_signals_tool
  |__  congress_trader  # <-- Checks P/E, Debt, and makes final decision
         |__ check_fundamentals_tool

tools available:

tools.py
  |__  fetch_congress_signals_tool(analysis_date: str) -> CongressSignalsResponse:
  |__  check_fundamentals_tool
  |__  fetch_form4_signals_tool
  |__  fetch_lobbying_signals_tool

asymmetric_tools
  |__  check_gov_contracts_tool  

=== Tests
test_congress_researcher_new
- test_fetch_congress_signals_end_to_end_wiring
test_congress_researcher_executio
- test_congress_researcher_skill_tool_sequence mock an execution
test_congress_researcher_agents.py
 - test skills migration
- test_congress_resaearcher_eval evaluate response

====================== Query to find data ====================
WITH candidate_dates AS (
  -- Extract distinct filing/action dates from your core signal tables
  SELECT DISTINCT action_date AS signal_date FROM `datascience-projects.gcp_shareloader.contract_signals` WHERE action_date IS NOT NULL
  UNION DISTINCT
  SELECT DISTINCT AS_OF_DATE AS signal_date FROM `datascience-projects.gcp_shareloader.senate_disclosures` WHERE AS_OF_DATE IS NOT NULL
  UNION DISTINCT
  SELECT DISTINCT filing_date AS signal_date FROM `datascience-projects.gcp_shareloader.form4_master` WHERE filing_date IS NOT NULL
  UNION DISTINCT
  SELECT DISTINCT filing_date AS signal_date FROM `datascience-projects.gcp_shareloader.lobbying_signals` WHERE filing_date IS NOT NULL
),
scored_dates AS (
  SELECT 
    d.signal_date,
    -- Count how many signals/filings happened on or around this date
    (SELECT COUNT(*) FROM `datascience-projects.gcp_shareloader.senate_disclosures` WHERE AS_OF_DATE = d.signal_date) AS senate_count,
    (SELECT COUNT(*) FROM `datascience-projects.gcp_shareloader.form4_master` WHERE filing_date = d.signal_date) AS insider_count,
    (SELECT COUNT(*) FROM `datascience-projects.gcp_shareloader.contract_signals` WHERE action_date = d.signal_date) AS contract_count,
    (SELECT COUNT(*) FROM `datascience-projects.gcp_shareloader.lobbying_signals` WHERE filing_date = d.signal_date) AS lobbying_count
  FROM candidate_dates d
  WHERE d.signal_date >= '2024-01-01'  -- Adjust window as needed (e.g., last 1-2 years)
)
SELECT 
  signal_date,
  senate_count,
  insider_count,
  contract_count,
  lobbying_count,
  (senate_count + insider_count + contract_count + lobbying_count) AS total_activity_score
FROM scored_dates
WHERE (senate_count > 0 OR insider_count > 0)  -- Ensure at least congress or insider data is present
ORDER BY total_activity_score DESC
LIMIT 15;


Top Recommended Test Dates
Comprehensive Multi-Signal Date (Best Overall for Full Integration):

Date: 2025-04-01

Why: Excellent multi-pillar coverage with 9 Senate disclosures, 3,645 insider filings, 19 contract signals, and 9 lobbying signals. This will thoroughly test the CongressTrader agent's ability to synthesize a crowded multi-signal environment.

High Congressional + Insider Density Date:

Date: 2025-05-15

Why: Features a massive spike in Senate activity (284 disclosures) alongside robust insider trading volume (2,644 filings) and contracts. Perfect for testing high-conviction congressional filtering.

Recent 2026 Test Case:

Date: 2026-03-02

Why: Gives you a clean recent date with 45 Senate disclosures, 3,739 insider filings, and contract activity to verify your tools against the latest data schema.





====================================================================

  ==== 3/11
  added integ test for congress trader
  added eval tests. but they fail due to a missing import