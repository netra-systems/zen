"""
Unified Corpus Admin Module - SSOT for all corpus management operations.

This module consolidates 30+ corpus admin files into a single unified implementation
with proper user isolation and factory pattern support.

Business Value:
- Simplified maintenance (30 files  ->  1 file)
- Improved multi-user isolation
- Thread-safe corpus operations
- Consistent metadata handling via BaseAgent SSOT methods
"""

from netra_backend.app.admin.corpus.unified_corpus_admin import (
    # Main classes
    UnifiedCorpusAdmin,
    UnifiedCorpusAdminFactory,
    
    # Context and isolation
    UserExecutionContext,
    IsolationStrategy,
    
    # Enums
    CorpusOperation,
    CorpusType,
    
    # Models
    CorpusMetadata,
    CorpusOperationRequest,
    CorpusOperationResult,
    
    # Error types
    CorpusAdminError,
    DocumentUploadError,
    DocumentValidationError,
    IndexingError,
)

# For backward compatibility during migration
from netra_backend.app.admin.corpus.compatibility import (
    CorpusAdminSubAgent,
    CorpusOperationHandler,
    CorpusCRUDOperations,
    CorpusAnalysisOperations,
    CorpusIndexingHandlers,
    CorpusUploadHandlers,
    CorpusValidationHandlers,
    CorpusAdminTools,
)

__all__ = [
    # Primary SSOT classes
    'UnifiedCorpusAdmin',
    'UnifiedCorpusAdminFactory',
    
    # Context and isolation
    'UserExecutionContext',
    'IsolationStrategy',
    
    # Enums
    'CorpusOperation',
    'CorpusType',
    
    # Models
    'CorpusMetadata',
    'CorpusOperationRequest',
    'CorpusOperationResult',
    
    # Error types
    'CorpusAdminError',
    'DocumentUploadError',
    'DocumentValidationError',
    'IndexingError',
    
    # Backward compatibility (deprecated)
    'CorpusAdminSubAgent',
    'CorpusOperationHandler',
    'CorpusCRUDOperations',
    'CorpusAnalysisOperations',
    'CorpusIndexingHandlers',
    'CorpusUploadHandlers',
    'CorpusValidationHandlers',
    'CorpusAdminTools',
]