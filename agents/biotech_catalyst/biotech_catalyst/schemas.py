from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ClinicalSignalRecord(BaseModel):
    scraped_at: datetime = Field(description="Timestamp when the clinical trial status was scraped")
    nct_id: str = Field(description="ClinicalTrials.gov identifier (e.g., NCT01234567)")
    sponsor: str = Field(description="Organization or individual sponsoring the clinical trial")
    title: str = Field(description="Official title of the clinical trial study")
    status: str = Field(description="Current trial status, filtered for TERMINATED or SUSPENDED")
    negative_reason: Optional[str] = Field(None, description="Detailed explanation for termination or suspension")

    class Config:
        frozen = True