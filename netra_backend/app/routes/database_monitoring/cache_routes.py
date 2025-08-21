"""
Database Cache Management Routes
"""
from typing import Dict, Any
from fastapi import HTTPException, Query
from netra_backend.app.db.query_cache import query_cache
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def handle_cache_metrics_error(e: Exception) -> None:
    """Handle cache metrics retrieval error."""
    logger.error(f"Error getting cache metrics: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to get cache metrics: {str(e)}"
    )


async def get_cache_metrics_handler() -> Dict[str, Any]:
    """Get query cache metrics."""
    try:
        return query_cache.get_metrics()
    except Exception as e:
        handle_cache_metrics_error(e)


def build_tag_invalidation_response(tag: str, count: int) -> Dict[str, Any]:
    """Build tag invalidation response."""
    return {
        "success": True,
        "message": f"Invalidated {count} cache entries with tag '{tag}'",
        "invalidated_count": count
    }


def handle_tag_invalidation_error(e: Exception) -> None:
    """Handle tag invalidation error."""
    logger.error(f"Error invalidating cache by tag: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to invalidate cache: {str(e)}"
    )


async def invalidate_cache_by_tag_handler(tag: str) -> Dict[str, Any]:
    """Invalidate cache entries by tag."""
    try:
        invalidated_count = await query_cache.invalidate_by_tag(tag)
        return build_tag_invalidation_response(tag, invalidated_count)
    except Exception as e:
        handle_tag_invalidation_error(e)


def build_pattern_invalidation_response(pattern: str, count: int) -> Dict[str, Any]:
    """Build pattern invalidation response."""
    return {
        "success": True,
        "message": f"Invalidated {count} cache entries matching pattern '{pattern}'",
        "invalidated_count": count
    }


def handle_pattern_invalidation_error(e: Exception) -> None:
    """Handle pattern invalidation error."""
    logger.error(f"Error invalidating cache by pattern: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to invalidate cache: {str(e)}"
    )


async def invalidate_cache_by_pattern_handler(pattern: str) -> Dict[str, Any]:
    """Invalidate cache entries by pattern."""
    try:
        invalidated_count = await query_cache.invalidate_pattern(pattern)
        return build_pattern_invalidation_response(pattern, invalidated_count)
    except Exception as e:
        handle_pattern_invalidation_error(e)


def build_clear_cache_response(count: int) -> Dict[str, Any]:
    """Build clear cache response."""
    return {
        "success": True,
        "message": f"Cleared {count} cache entries",
        "cleared_count": count
    }


def handle_clear_cache_error(e: Exception) -> None:
    """Handle clear cache error."""
    logger.error(f"Error clearing cache: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to clear cache: {str(e)}"
    )


async def clear_all_cache_handler() -> Dict[str, Any]:
    """Clear all cached entries."""
    try:
        cleared_count = await query_cache.clear_all()
        return build_clear_cache_response(cleared_count)
    except Exception as e:
        handle_clear_cache_error(e)