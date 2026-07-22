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