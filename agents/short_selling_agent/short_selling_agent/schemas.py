from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import requests
import os
import logging

# --- MODELS FOR FINVIZ BLACKLIST ---
class BlacklistReport(BaseModel):
    tickers: List[str] = Field(description="List of highly shorted ticker symbols to avoid.")
    error_message: Optional[str] = Field(default=None, description="Error message if fetch failed.")

# --- MODELS FOR FMP LOSERS ---
class MarketLoser(BaseModel):
    ticker: str = Field(description="Stock ticker symbol")
    price: float = Field(description="Current price")
    change_pct: float = Field(description="Percentage drop today")

class BiggestLosersReport(BaseModel):
    losers: List[MarketLoser] = Field(description="List of the biggest market losers today.")
    error_message: Optional[str] = Field(default=None)

# --- MODELS FOR FMP NEWS ---
class NewsArticle(BaseModel):
    date: str = Field(description="Publication date of the article")
    title: str = Field(description="Headline of the article")

class StockNewsReport(BaseModel):
    ticker: str = Field(description="The stock ticker symbol")
    articles: List[NewsArticle] = Field(description="Chronological list of recent news articles")
    error_message: Optional[str] = Field(default=None)

# --- MODELS FOR FORM 4 INSIDER DATA ---
class InsiderTrade(BaseModel):
    date: str = Field(description="Date the transaction occurred")
    name: str = Field(description="Name of the executive")
    title: str = Field(description="Corporate title (e.g., CEO, CFO)")
    value_sold: float = Field(description="Total dollar value of the stock sold")

class InsiderTradingReport(BaseModel):
    ticker: str = Field(description="The stock ticker symbol")
    total_dollars_dumped: float = Field(description="Aggregate dollar amount sold by C-Suite in the time window")
    significant_sales: List[InsiderTrade] = Field(description="List of major individual sale transactions")
    error_message: Optional[str] = Field(default=None)