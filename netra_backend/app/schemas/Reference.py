from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ReferenceItem(BaseModel):
    id: str
    name: str
    friendly_name: str
    description: Optional[str] = None
    type: str
    value: str
    version: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ReferenceGetResponse(BaseModel):
    references: List[ReferenceItem]
    total: Optional[int] = None
    offset: Optional[int] = None
    limit: Optional[int] = None

class ReferenceCreateRequest(BaseModel):
    name: str
    friendly_name: str
    description: Optional[str] = None
    type: str
    value: str
    version: Optional[str] = "1.0"

class ReferenceUpdateRequest(BaseModel):
    name: Optional[str] = None
    friendly_name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    value: Optional[str] = None
    version: Optional[str] = None