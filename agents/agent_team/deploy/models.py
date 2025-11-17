from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- Pydantic Models for ADK Response ---

class Part(BaseModel):
    """Represents a single part within the message content."""
    text: Optional[str] = None # The primary text response
    # We ignore other fields like functionCall/functionResponse for simplicity
    
class Content(BaseModel):
    """Represents the main message content block."""
    parts: List[Part] = Field(default_factory=list)
    role: str

class AgentResponseModel(BaseModel):
    """The root model for the final ADK run_sse response payload."""
    content: Content
    author: Optional[str] = None
    invocationId: Optional[str] = None
    # We ignore other metadata fields (usageMetadata, actions, etc.)