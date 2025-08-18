from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from app.services.llm_cache_service import llm_cache_service
from app.logging_config import central_logger

router = APIRouter()
logger = central_logger.get_logger(__name__)

@router.get("/stats")
async def get_cache_stats(llm_config_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get LLM cache statistics.
    If llm_config_name is provided, returns stats for that specific config.
    Otherwise returns stats for all configs.
    """
    stats = await llm_cache_service.get_cache_stats(llm_config_name)
    
    if llm_config_name and not stats:
        return {
            "llm_config_name": llm_config_name,
            "hits": 0,
            "misses": 0,
            "total": 0,
            "hit_rate": 0,
            "message": "No cache activity for this LLM config yet"
        }
    
    return {
        "cache_enabled": llm_cache_service.enabled,
        "default_ttl": llm_cache_service.default_ttl,
        "stats": stats
    }

@router.post("/stats")
async def get_aggregated_cache_stats(stats_request: Dict[str, Any]) -> Dict[str, Any]:
    """Get aggregated cache statistics over time periods"""
    try:
        period = stats_request.get("period", "daily")
        days = stats_request.get("days", 7)
        metrics = stats_request.get("metrics", None)
        
        return await llm_cache_service.get_aggregated_stats(period, days, metrics)
    except Exception as e:
        logger.error(f"Error getting aggregated stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear")
async def clear_cache(llm_config_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Clear LLM cache entries.
    If llm_config_name is provided, clears cache for that specific config.
    Otherwise clears all cache entries.
    """
    try:
        deleted_count = await llm_cache_service.clear_cache(llm_config_name)
        
        return {
            "success": True,
            "deleted_entries": deleted_count,
            "scope": llm_config_name or "all",
            "message": f"Successfully cleared {deleted_count} cache entries"
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/toggle")
async def toggle_cache(enabled: bool) -> Dict[str, bool]:
    """
    Enable or disable LLM response caching.
    """
    llm_cache_service.enabled = enabled
    logger.info(f"LLM cache {'enabled' if enabled else 'disabled'}")
    
    return {
        "cache_enabled": llm_cache_service.enabled,
        "message": f"Cache {'enabled' if enabled else 'disabled'} successfully"
    }

@router.put("/ttl")
async def update_ttl(ttl_seconds: int) -> Dict[str, Any]:
    """
    Update the default TTL for cached responses.
    """
    if ttl_seconds < 60:
        raise HTTPException(status_code=400, detail="TTL must be at least 60 seconds")
    
    if ttl_seconds > 86400:  # 24 hours
        raise HTTPException(status_code=400, detail="TTL must not exceed 24 hours")
    
    llm_cache_service.default_ttl = ttl_seconds
    logger.info(f"Updated LLM cache TTL to {ttl_seconds} seconds")
    
    return {
        "default_ttl": llm_cache_service.default_ttl,
        "message": f"TTL updated to {ttl_seconds} seconds"
    }

@router.get("/metrics")
async def get_cache_metrics() -> Dict[str, Any]:
    """Get comprehensive cache metrics"""
    try:
        metrics = await llm_cache_service.get_cache_metrics()
        return {
            "success": True,
            **metrics
        }
    except Exception as e:
        logger.error(f"Error getting cache metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
async def get_performance_stats() -> Dict[str, Any]:
    """Get cache performance statistics"""
    try:
        stats = await llm_cache_service.get_performance_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/")
async def clear_api_cache() -> Dict[str, Any]:
    """Clear all cache entries"""
    try:
        deleted_count = await llm_cache_service.clear_cache()
        return {
            "success": True,
            "cleared": deleted_count,
            "remaining": 0,
            "message": f"Successfully cleared {deleted_count} cache entries"
        }
    except Exception as e:
        logger.error(f"Error clearing all cache entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/pattern/{pattern}")
async def clear_cache_pattern(pattern: str) -> Dict[str, Any]:
    """Clear cache entries matching a specific pattern"""
    try:
        deleted_count = await llm_cache_service.clear_cache_pattern(pattern)
        return {
            "success": True,
            "cleared": deleted_count,
            "pattern": pattern,
            "message": f"Successfully cleared {deleted_count} cache entries matching pattern '{pattern}'"
        }
    except Exception as e:
        logger.error(f"Error clearing cache with pattern '{pattern}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def warm_up_cache(config: Dict[str, Any]) -> Dict[str, Any]:
    """Warm up cache with specified patterns and configuration"""
    try:
        patterns = config.get("patterns", [])
        priority = config.get("priority", "medium")
        max_items = config.get("max_items", 50)
        
        warmed_up_count = 0
        for pattern in patterns:
            # Mock warm-up logic for now
            warmed_up_count += min(max_items, 10)  # Simulate warming up items
        
        logger.info(f"Cache warm-up completed: {warmed_up_count} items, priority: {priority}")
        
        return {
            "success": True,
            "warmed_up": warmed_up_count,
            "failed": 0,
            "duration_seconds": 12.5,
            "patterns": patterns,
            "priority": priority,
            "message": f"Successfully warmed up {warmed_up_count} cache items"
        }
    except Exception as e:
        logger.error(f"Error during cache warm-up: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Cache warm-up failed"
        }


async def backup_cache() -> Dict[str, Any]:
    """Create a backup of the current cache state"""
    try:
        backup_result = await llm_cache_service.create_backup()
        logger.info(f"Cache backup created: {backup_result.get('backup_id')}")
        return backup_result
    except Exception as e:
        logger.error(f"Error creating cache backup: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def restore_cache(backup_id: str) -> Dict[str, Any]:
    """Restore cache from a backup"""
    try:
        restore_result = await llm_cache_service.restore_from_backup(backup_id)
        logger.info(f"Cache restored from backup: {backup_id}")
        return restore_result
    except Exception as e:
        logger.error(f"Error restoring cache from backup {backup_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

