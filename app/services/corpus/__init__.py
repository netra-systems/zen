"""
Corpus service module - modular corpus management system

This module provides a refactored, modular approach to corpus management
split across logical components:

- Core service class
- Document management operations  
- Search and query operations
- Embeddings and vector operations
- Validation and preprocessing
"""

from .base import CorpusStatus, ContentSource
from .core_unified import CorpusService
from .document_manager import DocumentManager
from .search_operations import SearchOperations
from .validation import ValidationManager
from .clickhouse_operations import CorpusClickHouseOperations
from .corpus_manager import CorpusManager

# Create singleton instance
corpus_service = CorpusService()

__all__ = [
    "CorpusService",
    "DocumentManager", 
    "SearchOperations",
    "ValidationManager",
    "CorpusClickHouseOperations",
    "CorpusManager",
    "CorpusStatus",
    "ContentSource",
    "corpus_service"
]