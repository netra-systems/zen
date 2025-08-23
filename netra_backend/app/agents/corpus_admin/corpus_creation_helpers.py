#!/usr/bin/env python3
"""Helper functions for corpus creation - main coordination module."""

from typing import Any, Dict, Optional, Tuple

# Try to import handlers for advanced features
try:
    from netra_backend.app.agents.corpus_admin.corpus_indexing_handlers import create_indexing_handler
    from netra_backend.app.agents.corpus_admin.corpus_upload_handlers import create_upload_handler
    from netra_backend.app.agents.corpus_admin.corpus_validation_handlers import create_validation_handler
    HANDLERS_AVAILABLE = True
except (ImportError, ValueError):
    try:
        from corpus_indexing_handlers import create_indexing_handler
        from corpus_upload_handlers import create_upload_handler
        from corpus_validation_handlers import create_validation_handler
        HANDLERS_AVAILABLE = True
    except (ImportError, ValueError):
        HANDLERS_AVAILABLE = False

def get_handlers():
    """Get or create handlers."""
    if HANDLERS_AVAILABLE:
        v = create_validation_handler()
        i = create_indexing_handler()
        u = create_upload_handler()
        return v, i, u
    return None, None, None