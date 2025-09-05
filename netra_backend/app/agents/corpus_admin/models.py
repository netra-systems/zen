"""
Corpus admin models.

Data models for corpus administration operations.
"""

from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass


class CorpusType(Enum):
    """Corpus type enumeration."""
    DOCUMENTATION = "documentation"
    KNOWLEDGE_BASE = "knowledge_base"
    REFERENCE = "reference"
    CUSTOM = "custom"


class CorpusOperation(Enum):
    """Corpus operation enumeration."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    INDEX = "index"
    VALIDATE = "validate"
    SEARCH = "search"
    ANALYZE = "analyze"
    EXPORT = "export"
    IMPORT = "import"


@dataclass
class CorpusMetadata:
    """Corpus metadata model."""
    corpus_name: str
    corpus_type: CorpusType
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    document_count: Optional[int] = None


@dataclass 
class CorpusOperationRequest:
    """Corpus operation request model."""
    operation: CorpusOperation
    corpus_metadata: CorpusMetadata
    parameters: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    thread_id: Optional[str] = None


@dataclass
class CorpusOperationResult:
    """Corpus operation result model."""
    success: bool
    operation: CorpusOperation
    corpus_metadata: Optional[CorpusMetadata] = None
    affected_documents: Optional[int] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None


@dataclass
class CorpusStatistics:
    """Corpus statistics model."""
    total_documents: int = 0
    total_size_bytes: int = 0
    indexed_documents: int = 0
    processed_documents: int = 0
    failed_documents: int = 0
    last_updated: Optional[str] = None
    processing_time_seconds: Optional[float] = None