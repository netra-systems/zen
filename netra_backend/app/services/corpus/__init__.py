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

# NOTE: Singleton corpus_service removed to support user context isolation.
# Create CorpusService instances with user_context for WebSocket notifications:
#   corpus_service = CorpusService(user_context=user_execution_context)
# Or without for logging-only mode:
#   corpus_service = CorpusService()

def get_corpus_service(user_context=None):
    """Factory function to create corpus service with optional user context.
    
    Args:
        user_context: Optional UserExecutionContext for WebSocket isolation.
                     If provided, enables WebSocket notifications.
                     If None, notifications are logged only.
    
    Returns:
        CorpusService instance configured with the given context.
    """
    return CorpusService(user_context=user_context)

__all__ = [
    "CorpusService",
    "DocumentManager", 
    "SearchOperations",
    "ValidationManager",
    "CorpusClickHouseOperations",
    "CorpusManager",
    "CorpusStatus",
    "ContentSource",
    "get_corpus_service"
]