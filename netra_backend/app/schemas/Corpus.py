import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


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

    model_config = ConfigDict(from_attributes=True, extra="allow")

class Corpus(CorpusInDBBase):
    pass

class ContentCorpus(BaseModel):
    record_id: uuid.UUID
    workload_type: str
    prompt: str
    response: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="allow")

class DocumentBase(BaseModel):
    title: str
    content: str
    metadata: Optional[dict] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(DocumentBase):
    title: Optional[str] = None
    content: Optional[str] = None

class Document(DocumentBase):
    id: str
    corpus_id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True, extra="allow")