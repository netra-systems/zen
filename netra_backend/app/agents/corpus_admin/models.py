"""
Corpus Admin Data Models

Pydantic models and enums for corpus management operations.
All models follow type safety requirements under 300 lines.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CorpusOperation(str, Enum):
    """Types of corpus operations"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"
    ANALYZE = "analyze"
    EXPORT = "export"
    IMPORT = "import"
    VALIDATE = "validate"


class CorpusType(str, Enum):
    """Types of corpus data"""
    DOCUMENTATION = "documentation"
    KNOWLEDGE_BASE = "knowledge_base"
    TRAINING_DATA = "training_data"
    REFERENCE_DATA = "reference_data"
    EMBEDDINGS = "embeddings"


class CorpusMetadata(BaseModel):
    """Metadata for corpus entries"""
    corpus_id: Optional[str] = None
    corpus_name: str
    corpus_type: CorpusType
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    size_bytes: Optional[int] = None
    document_count: Optional[int] = None
    version: str = Field(default="1.0")
    access_level: str = Field(default="private")


class CorpusOperationRequest(BaseModel):
    """Request for corpus operation"""
    operation: CorpusOperation
    corpus_metadata: CorpusMetadata
    filters: Dict[str, Any] = Field(default_factory=dict)
    content: Optional[Any] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False


class CorpusOperationResult(BaseModel):
    """Result of corpus operation"""
    success: bool
    operation: CorpusOperation
    corpus_metadata: CorpusMetadata
    affected_documents: int = 0
    result_data: Optional[Any] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    requires_approval: bool = False
    approval_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CorpusStatistics(BaseModel):
    """Statistics about corpus"""
    total_corpora: int = 0
    total_documents: int = 0
    total_size_bytes: int = 0
    corpora_by_type: Dict[str, int] = Field(default_factory=dict)
    recent_operations: List[Dict[str, Any]] = Field(default_factory=list)