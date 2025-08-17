"""
Database Cache Management Routes
"""
from typing import Dict, Any
from fastapi import HTTPException, Query
from app.db.query_cache import query_cache
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


async def get_cache_metrics_handler() -> Dict[str, Any]:
    """Get query cache metrics."""
    try:
        return query_cache.get_metrics()
        
    except Exception as e:
        logger.error(f"Error getting cache metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache metrics: {str(e)}"
        )


async def invalidate_cache_by_tag_handler(tag: str) -> Dict[str, Any]:
    """Invalidate cache entries by tag."""
    try:
        invalidated_count = await query_cache.invalidate_by_tag(tag)
        
        return {
            "success": True,
            "message": f"Invalidated {invalidated_count} cache entries with tag '{tag}'",
            "invalidated_count": invalidated_count
        }
        
    except Exception as e:
        logger.error(f"Error invalidating cache by tag: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


async def invalidate_cache_by_pattern_handler(pattern: str) -> Dict[str, Any]:
    """Invalidate cache entries by pattern."""
    try:
        invalidated_count = await query_cache.invalidate_pattern(pattern)
        
        return {
            "success": True,
            "message": f"Invalidated {invalidated_count} cache entries matching pattern '{pattern}'",
            "invalidated_count": invalidated_count
        }
        
    except Exception as e:
        logger.error(f"Error invalidating cache by pattern: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


async def clear_all_cache_handler() -> Dict[str, Any]:
    """Clear all cached entries."""
    try:
        cleared_count = await query_cache.clear_all()
        
        return {
            "success": True,
            "message": f"Cleared {cleared_count} cache entries",
            "cleared_count": cleared_count
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )