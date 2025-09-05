"""Thread error handling utilities."""
from typing import Dict, List, Optional


def _get_basic_context_mappings() -> Dict[str, str]:
    """Get basic context mappings."""
    return {"creating thread": "create thread", "deleting thread": "delete thread"}

def _get_extended_context_mappings() -> Dict[str, str]:
    """Get extended context mappings."""
    return {"listing threads": "list threads", "updating thread": "update thread", "auto-renaming thread": "auto-rename thread"}

def get_context_mappings() -> Dict[str, str]:
    """Get context mapping dictionary."""
    basic = _get_basic_context_mappings()
    extended = _get_extended_context_mappings()
    return {**basic, **extended}


def check_thread_pattern(clean_context: str, pattern: str, replacement: str) -> Optional[str]:
    """Check if context matches pattern and return replacement."""
    return replacement if clean_context.startswith(pattern) else None


def _get_basic_thread_patterns() -> List[tuple]:
    """Get basic thread patterns."""
    return [("getting thread ", "get thread"), ("getting messages for thread ", "get thread messages")]

def _get_action_thread_patterns() -> List[tuple]:
    """Get action thread patterns."""
    return [("auto-renaming thread ", "auto-rename thread"), ("updating thread ", "update thread"), ("deleting thread ", "delete thread")]

def get_thread_pattern_mappings() -> List[tuple]:
    """Get thread pattern mappings."""
    basic = _get_basic_thread_patterns()
    actions = _get_action_thread_patterns()
    return basic + actions


def apply_thread_pattern_mappings(clean_context: str) -> str:
    """Apply thread-specific pattern mappings."""
    for pattern, replacement in get_thread_pattern_mappings():
        result = check_thread_pattern(clean_context, pattern, replacement)
        if result:
            return result
    return clean_context


def clean_thread_specific_context(clean_context: str) -> str:
    """Clean thread-specific context patterns."""
    return apply_thread_pattern_mappings(clean_context)


def resolve_clean_context(error_context: str) -> str:
    """Resolve clean context from error context."""
    clean_context = error_context.lower()
    context_mappings = get_context_mappings()
    clean_context = clean_thread_specific_context(clean_context)
    return context_mappings.get(clean_context, clean_context)


def should_log_exc_info(error_context: str) -> bool:
    """Determine if exception info should be logged."""
    return "creating" in error_context


def _log_route_error(error_context: str, e: Exception) -> None:
    """Log route error with context."""
    from netra_backend.app.logging_config import central_logger
    logger = central_logger.get_logger(__name__)
    logger.error(f"Error {error_context}: {e}", exc_info=should_log_exc_info(error_context))

def _raise_http_error(error_context: str) -> None:
    """Raise HTTP error with clean context."""
    from fastapi import HTTPException
    clean_context = resolve_clean_context(error_context)
    raise HTTPException(status_code=500, detail=f"Failed to {clean_context}")

async def handle_route_with_error_logging(handler_func, error_context: str):
    """Handle route with standardized error logging."""
    from fastapi import HTTPException
    from netra_backend.app.config import get_config
    
    try:
        return await handler_func()
    except HTTPException:
        raise
    except Exception as e:
        # Get config to check environment
        config = get_config()
        
        # Log with full stack trace
        from netra_backend.app.logging_config import central_logger
        logger = central_logger.get_logger(__name__)
        
        # In staging/development, log full exception details
        if config.environment in ["development", "staging"]:
            logger.error(f"Error {error_context}: {e}", exc_info=True)
        else:
            logger.error(f"Error {error_context}: {e}")
        
        # Provide more detailed error message in non-production
        if config.environment in ["development", "staging"]:
            clean_context = resolve_clean_context(error_context)
            error_detail = f"Failed to {clean_context}. Error: {str(e)}"
        else:
            clean_context = resolve_clean_context(error_context)
            error_detail = f"Failed to {clean_context}"
        
        raise HTTPException(status_code=500, detail=error_detail)