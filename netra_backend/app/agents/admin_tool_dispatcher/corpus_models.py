"""
Corpus Admin Tool Models

Data structures for corpus admin tools including enums, request/response models.
All functions maintain 25-line limit with single responsibility.
"""

from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


class CorpusToolType(str, Enum):
    """Types of corpus admin tools"""
    CREATE = "create_corpus"
    GENERATE = "generate_synthetic"
    OPTIMIZE = "optimize_corpus"
    EXPORT = "export_corpus"
    VALIDATE = "validate_corpus"
    DELETE = "delete_corpus"
    UPDATE = "update_corpus"
    ANALYZE = "analyze_corpus"


class CorpusToolRequest(BaseModel):
    """Request model for corpus tool execution"""
    tool_type: CorpusToolType
    corpus_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    options: Dict[str, Any] = Field(default_factory=dict)


class CorpusToolResponse(BaseModel):
    """Response model for corpus tool execution"""
    success: bool
    tool_type: CorpusToolType
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)