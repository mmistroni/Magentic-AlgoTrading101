# state.py
from pydantic import BaseModel
from typing import List
from short_selling_agent.schemas import MarketLoser, StockNewsReport, InsiderTradingReport

class PipelineDossier(BaseModel):
    """The master Pydantic object that holds all pipeline data."""
    market_losers: List[MarketLoser] = []
    news_reports: List[StockNewsReport] = []
    insider_reports: List[InsiderTradingReport] = []

class StateManager:
    """A container for our global state."""
    def __init__(self):
        self.dossier = PipelineDossier()
        
    def reset(self):
        self.dossier = PipelineDossier()

# THIS IS THE MAGIC VARIABLE. 
# We create it exactly once here.
CURRENT_RUN_STATE = StateManager()