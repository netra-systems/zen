from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class ReferenceItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ReferenceGetResponse(BaseModel):
    references: List[ReferenceItem]
    total: Optional[int] = None
    offset: Optional[int] = None
    limit: Optional[int] = None

class ReferenceCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    url: Optional[str] = None

class ReferenceUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None