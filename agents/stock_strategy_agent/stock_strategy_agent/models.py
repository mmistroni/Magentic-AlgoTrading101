from pydantic import BaseModel, Field

from typing import List, Dict, Any
from google.cloud import bigquery
from pydantic import BaseModel, Field

# ----------------------------------------------
# 1. Pydantic Schemas for Tool I/O
# ----------------------------------------------

class GetSchemaInput(BaseModel):
    """Input schema for the tool that fetches table field information."""
    table_id: str = Field(..., description="The full BigQuery table ID (project.dataset.table) to retrieve the schema from.")

class FieldInfo(BaseModel):
    """Represents a single field's name and BigQuery type."""
    field_name: str = Field(..., description="The name of the column/field.")
    bigquery_type: str = Field(..., description="The BigQuery data type (e.g., STRING, FLOAT, TIMESTAMP).")

class GetSchemaOutput(BaseModel):
    """Output schema returning a list of all fields and their types."""
    fields: List[FieldInfo] = Field(..., description="A list of all fields and their corresponding BigQuery types available in the table.")

