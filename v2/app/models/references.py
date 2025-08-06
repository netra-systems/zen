
from pydantic import BaseModel
from typing import List, Dict, Any

class ReferenceItem(BaseModel):
    """
    Represents a single @reference item that can be used in the chat.
    """
    name: str
    type: str
    value: Any

class ReferenceGetResponse(BaseModel):
    """
    The response model for the GET /references endpoint.
    """
    references: List[ReferenceItem]
