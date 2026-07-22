MASTER IMPLEMENTATION PLAN: CONGRESS ALPHA AGENT PIPELINEEXECUTIVE SUMMARY & GOALSThe objective is to elevate the Congress Alpha Multi-Agent System into an enterprise-grade, production-ready framework. This plan addresses persistence, testing, evaluation, architectural refactoring, and automated job scheduling.Key Deliverables:BigQuery Persistence: Store trade recommendations, signal context, and entry prices for long-term multi-month tracking.Integration Test Suite: Implement pytest suites covering live execution and mocked scenario edge cases (e.g., Bear Markets, Insider Dumping).Agent Evaluation Framework: Benchmark and score prompt tweaks against saved ADK Golden Datasets (.evalset.json).Skills Framework Architecture: Restructure code into modular, isolated agent skills.Automated Weekly Scheduler: Deploy to Google Cloud Run triggered via Cloud Scheduler on a weekly cadence.PHASE 1: ARCHITECTURE REFACTORING (SKILLS FRAMEWORK)Restructure the repository to decouple tools, system prompts, schemas, and sub-agents into modular skill directories.Target Directory Layout:Plaintextcongress_trades_agent/
├── config.py
├── main.py
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
    ├── bigquery_client.py
    └── market_data.py
Action Items:Move fetch_congress_signals_tool into skills/congress_scout/tools.py.Move fetch_form4_signals_tool and fetch_lobbying_signals_tool into skills/insider_analysis/tools.py.Move check_fundamentals_tool into skills/portfolio_management/tools.py.Isolate system instructions into dedicated prompt.py files within each skill folder.PHASE 2: PERSISTENCE & PERFORMANCE TRACKING (BIGQUERY)To track recommendations over multi-month holding periods, agent outputs will be saved to a structured BigQuery dataset.BigQuery Table Schema: congress_alpha.trade_recommendationsField NameTypeModeDescriptionrecommendation_idSTRINGREQUIREDUUID for the specific recordanalysis_dateDATEREQUIREDThe target analysis date requested by user/cronexecution_timestampTIMESTAMPREQUIREDExact UTC time the agent rantickerSTRINGREQUIREDStock symbol (e.g., FN, NVDA)actionSTRINGREQUIREDSTRONG BUY | BUY | HOLD | PASSconfidenceINTEGERREQUIREDConfidence rating (1 to 10)risk_ratingSTRINGREQUIREDLow | Medium | Highmarket_regime_bullishBOOLEANREQUIREDTrue if SPY > 200 SMA on analysis dateentry_priceFLOATNULLABLEClosing price of stock on analysis datesectorSTRINGNULLABLEIndustry sectorforward_peFLOATNULLABLEValuation metricdebt_to_equityFLOATNULLABLELeverage metricform4_signalSTRINGNULLABLEStrong Buy Confluence | Warning - Insider Dumping | NeutralreasoningSTRINGREQUIREDFull rationale provided by Trader AgentAction Items:Create dataset congress_alpha and table trade_recommendations in BigQuery.Implement save_recommendations_to_bq(recommendations: List[TradeRecommendation]) helper in utils/bigquery_client.py.Attach post-execution hook in the Trader Agent to write outputs automatically.PHASE 3: INTEGRATION & MOCK TEST SUITESEstablish robust testing to prevent regressions and verify guardrails under extreme market conditions.Test Matrix:Live ADK Dataset Integration Test (tests/test_adk_eval.py):Executes AgentEvaluator.evaluate() against saved golden datasets (data/20260701_run.evalset.json).Validates tool call trajectories and semantic output match.Mock Scenario Behavioral Tests (tests/test_trader_guardrails.py):Scenario A (Bear Market Override): Mock SPY < 200 SMA. Assert action is restricted to HOLD or PASS.Scenario B (Insider Dumping Trap): Mock Form 4 tool returning 'Warning - Insider Dumping'. Assert output is PASS regardless of lobbying spend.Scenario C (Debt/Valuation Trap): Mock Forward P/E > 300 or D/E > 200. Assert output is PASS.Scenario D (Data Failure Graceful Handling): Mock check_fundamentals_tool returning error="Data Unavailable". Assert pipeline passes without throwing unhandled exceptions.PHASE 4: PROMPT EVALUATION & TUNING FRAMEWORKSystematically test variations of system prompts against golden benchmarks to optimize reasoning accuracy.Action Items:Utilize ADK’s AgentEvaluator and dataset suite in tests/data/.Track two core metrics:Tool Trajectory Score (Target: 100%): Enforces exact execution sequence across all sub-agents.Response Match Score (Target: > 80%): Measures reasoning alignment against golden outputs.Run CLI benchmark command during prompt iteration:Bashadk eval congress_trades_agent tests/data/20260701_run.evalset.json --print_detailed_results
PHASE 5: AUTOMATED SCHEDULING & CLOUD DEPLOYMENTExecution Cadence:Frequency: Weekly (Every Saturday at 08:00 AM UTC) or Monthly (1st of the Month).Rationale: Senate/House trade disclosures operate on a 30 to 45-day filing window. A weekly weekend cadence catches new disclosure batches without incurring redundant API costs.Deployment Pipeline:Containerization: Package agent workflow into Docker container using Dockerfile.Cloud Run Job: Deploy as a Google Cloud Run Job.Cloud Scheduler: Configure Cloud Scheduler cron trigger (0 8 * * 6) to call the Cloud Run execution endpoint with analysis_date = current_date().STEP-BY-STEP IMPLEMENTATION ROADMAPPlaintext  [STEP 1: Refactor to Skills Layout]
                 │
                 ▼
  [STEP 2: Setup BigQuery Schema & Persistence Client]
                 │
                 ▼
  [STEP 3: Implement ADK & Mock Pytest Suites]
                 │
                 ▼
  [STEP 4: Run Prompt Evaluation & Tuning Pass]
                 │
                 ▼
  [STEP 5: Containerize & Deploy to Cloud Run + Cloud Scheduler]
NEXT IMMEDIATE ACTIONWhich step shall we begin executing first?Step 1: Reorganizing project files into the Skills Framework structure.Step 2: Building the BigQuery table schema and persistence module.