from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class ClinicalSignalRecord(BaseModel):
    ticker: Optional[str] = Field(None, description="Stock ticker symbol for the sponsoring organization")
    cusip: Optional[str] = Field(None, description="CUSIP identifier for the sponsoring organization")
    sponsor: str = Field(description="Organization or individual sponsoring the clinical trial")
    failure_status: Optional[str] = Field(None, description="Status of the clinical trial failure (e.g., TERMINATED, SUSPENDED)")
    failure_post_date: Optional[datetime] = Field(None, description="Timestamp when the failure status was posted")
    nct_id: Optional[str] = Field(None, description="ClinicalTrials.gov identifier (e.g., NCT01234567)")
    trial_title: Optional[str] = Field(None, description="Official title of the clinical trial study")
    failure_reason: Optional[str] = Field(None, description="Detailed explanation for termination or suspension")

    model_config = ConfigDict(frozen=True)



class ClinicalSignalResponse(BaseModel):
    reference_date: str = Field(description="Reference timestamp used for the query cutoff")
    signals: List[ClinicalSignalItem] = Field(default_factory=list, description="List of extracted clinical trial signals")
    count: int = Field(default=0, description="Total number of signals retrieved")
    error: Optional[str] = Field(None, description="Error message if the query or processing failed")

    model_config = ConfigDict(frozen=True)