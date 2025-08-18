"""Thread error handling utilities."""
from typing import Dict, List, Optional


def get_context_mappings() -> Dict[str, str]:
    """Get context mapping dictionary."""
    return {
        "creating thread": "create thread",
        "deleting thread": "delete thread",
        "listing threads": "list threads",
        "updating thread": "update thread",
        "auto-renaming thread": "auto-rename thread"
    }


def check_thread_pattern(clean_context: str, pattern: str, replacement: str) -> Optional[str]:
    """Check if context matches pattern and return replacement."""
    return replacement if clean_context.startswith(pattern) else None


def get_thread_pattern_mappings() -> List[tuple]:
    """Get thread pattern mappings."""
    return [
        ("getting thread ", "get thread"),
        ("getting messages for thread ", "get thread messages"),
        ("auto-renaming thread ", "auto-rename thread"),
        ("updating thread ", "update thread"),
        ("deleting thread ", "delete thread")
    ]


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


async def handle_route_with_error_logging(handler_func, error_context: str):
    """Handle route with standardized error logging."""
    from fastapi import HTTPException
    try:
        return await handler_func()
    except HTTPException:
        raise
    except Exception as e:
        from app.logging_config import central_logger
        logger = central_logger.get_logger(__name__)
        logger.error(f"Error {error_context}: {e}", exc_info=should_log_exc_info(error_context))
        clean_context = resolve_clean_context(error_context)
        raise HTTPException(status_code=500, detail=f"Failed to {clean_context}")