# state.py
from pydantic import BaseModel
from typing import List
from short_selling_agent.schemas import MarketLoser, StockNewsReport, InsiderTradingReport,\
        PipelineDossier# ------------------------------
# 5. STATE MANAGER
# ------------------------------
class StateManager:
    """Global state that persists across tools and agents."""
    def __init__(self):
        self.dossier = PipelineDossier()

    def reset(self):
        self.dossier = PipelineDossier()

# Export single instance
CURRENT_RUN_STATE = StateManager()