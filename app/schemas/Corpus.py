from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import uuid

class CorpusBase(BaseModel):
    name: str
    description: Optional[str] = None
    domain: Optional[str] = "general"

class CorpusCreate(CorpusBase):
    pass

class CorpusUpdate(CorpusBase):
    pass

class CorpusInDBBase(CorpusBase):
    id: str
    status: str
    created_by_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        extra = "allow"

class Corpus(CorpusInDBBase):
    pass

class ContentCorpus(BaseModel):
    record_id: uuid.UUID
    workload_type: str
    prompt: str
    response: str
    created_at: datetime

    class Config:
        from_attributes = True
        extra = "allow"