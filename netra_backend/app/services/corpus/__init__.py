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

from netra_backend.app.services.corpus.base import ContentSource, CorpusStatus
from netra_backend.app.services.corpus.clickhouse_operations import (
    CorpusClickHouseOperations,
)
from netra_backend.app.services.corpus.core_unified import CorpusService
from netra_backend.app.services.corpus.base_service import (
    CorpusManager,
    DocumentManager,
    ValidationManager
)
from netra_backend.app.services.corpus.search_operations import SearchOperations

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