from datetime import datetime
from typing import Optional
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

    class ConfigDict:
        frozen = True


