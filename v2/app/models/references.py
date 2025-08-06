from pydantic import BaseModel
from typing import List, Dict, Any

class ReferenceItem(BaseModel):
    id: int
    name: str
    friendly_name: str
    description: str | None = None
    type: str
    value: str
    version: str

    class Config:
        orm_mode = True

class ReferenceGetResponse(BaseModel):
    """
    The response model for the GET /references endpoint.
    """
    references: List[ReferenceItem]

class ReferenceCreateRequest(BaseModel):
    """
    The request model for creating a new reference.
    """
    name: str
    friendly_name: str
    description: str | None = None
    type: str
    value: str
    version: str

class ReferenceUpdateRequest(BaseModel):
    """
    The request model for updating a reference.
    """
    name: str | None = None
    friendly_name: str | None = None
    description: str | None = None
    type: str | None = None
    value: str | None = None
    version: str | None = None
