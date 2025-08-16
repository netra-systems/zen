"""Error handler specific to Corpus Admin Agent operations.

This module provides a unified interface to the modular corpus admin error handling system.
All core functionality has been split into focused modules for maintainability.
"""

# Import all core types and classes
from app.agents.corpus_admin.corpus_error_types import (
    CorpusAdminError,
    DocumentUploadError,
    DocumentValidationError,
    IndexingError
)

from app.agents.corpus_admin.corpus_error_compensation import (
    CorpusCleanupCompensation,
    create_corpus_compensation
)

from app.agents.corpus_admin.corpus_upload_handlers import (
    UploadErrorHandler,
    create_upload_handler
)

from app.agents.corpus_admin.corpus_validation_handlers import (
    ValidationErrorHandler,
    create_validation_handler
)

from app.agents.corpus_admin.corpus_indexing_handlers import (
    IndexingErrorHandler,
    create_indexing_handler
)

from app.agents.corpus_admin.corpus_error_handler_core import (
    CorpusAdminErrorHandler,
    create_corpus_admin_error_handler,
    corpus_admin_error_handler
)

# Export main interfaces for backward compatibility
__all__ = [
    # Error types
    'CorpusAdminError',
    'DocumentUploadError',
    'DocumentValidationError',
    'IndexingError',
    
    # Core classes
    'CorpusCleanupCompensation',
    'UploadErrorHandler',
    'ValidationErrorHandler',
    'IndexingErrorHandler',
    'CorpusAdminErrorHandler',
    
    # Factory functions
    'create_corpus_compensation',
    'create_upload_handler',
    'create_validation_handler',
    'create_indexing_handler',
    'create_corpus_admin_error_handler',
    
    # Global instance
    'corpus_admin_error_handler'
]