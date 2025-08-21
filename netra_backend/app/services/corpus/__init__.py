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

from netra_backend.app.base import CorpusStatus, ContentSource
from netra_backend.app.core_unified import CorpusService
from netra_backend.app.document_manager import DocumentManager
from netra_backend.app.search_operations import SearchOperations
from netra_backend.app.validation import ValidationManager
from netra_backend.app.clickhouse_operations import CorpusClickHouseOperations
from netra_backend.app.corpus_manager import CorpusManager

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