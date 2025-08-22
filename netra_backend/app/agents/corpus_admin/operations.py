"""
Corpus Operation Handler - Legacy Module

This module maintains backward compatibility while delegating to modular
implementations. All functionality has been split into focused modules
under 300 lines each.
"""

# Import from modular implementations
from netra_backend.app.agents.corpus_admin.operations_handler import (
    CorpusOperationHandler,
)

# Export for backward compatibility
__all__ = ["CorpusOperationHandler"]