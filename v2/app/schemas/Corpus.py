from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class CorpusBase(BaseModel):
    name: str
    description: Optional[str] = None

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

class Corpus(CorpusInDBBase):
    pass
