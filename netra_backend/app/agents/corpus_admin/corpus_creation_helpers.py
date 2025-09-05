"""
Corpus creation helpers module.

Provides helper functions for corpus creation operations.
This module has been removed but tests still reference it.
"""

# Configuration flag for handler availability
HANDLERS_AVAILABLE = False


def get_handlers():
    """
    Get corpus creation handlers.
    
    Returns tuple of (validation_handler, indexing_handler, upload_handler).
    All handlers are None since this functionality was removed.
    """
    if HANDLERS_AVAILABLE:
        # Handlers would be created here if available
        validation_handler = create_validation_handler()
        indexing_handler = create_indexing_handler()
        upload_handler = create_upload_handler()
        return validation_handler, indexing_handler, upload_handler
    else:
        return None, None, None


def create_validation_handler():
    """Create validation handler stub."""
    return None


def create_indexing_handler():
    """Create indexing handler stub."""
    return None


def create_upload_handler():
    """Create upload handler stub."""
    return None