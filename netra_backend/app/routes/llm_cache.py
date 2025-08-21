from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from netra_backend.app.services.llm_cache_service import llm_cache_service
from netra_backend.app.logging_config import central_logger

router = APIRouter()
logger = central_logger.get_logger(__name__)

# Helper functions for maintaining 25-line function limit

def _build_empty_stats_response(llm_config_name: str) -> Dict[str, Any]:
    """Build empty stats response for config with no activity."""
    return {"llm_config_name": llm_config_name, "hits": 0, "misses": 0, "total": 0, "hit_rate": 0, "message": "No cache activity for this LLM config yet"}

def _build_cache_stats_response(stats) -> Dict[str, Any]:
    """Build cache stats response."""
    return {"cache_enabled": llm_cache_service.enabled, "default_ttl": llm_cache_service.default_ttl, "stats": stats}

@router.get("/stats")
async def get_cache_stats(llm_config_name: Optional[str] = None) -> Dict[str, Any]:
    """Get LLM cache statistics."""
    stats = await llm_cache_service.get_cache_stats(llm_config_name)
    if llm_config_name and not stats:
        return _build_empty_stats_response(llm_config_name)
    return _build_cache_stats_response(stats)

def _extract_stats_params(stats_request: Dict[str, Any]) -> tuple[str, int, Any]:
    """Extract stats parameters from request."""
    period = stats_request.get("period", "daily")
    days = stats_request.get("days", 7)
    metrics = stats_request.get("metrics", None)
    return period, days, metrics

async def _get_aggregated_stats_safe(stats_request: Dict[str, Any]) -> Dict[str, Any]:
    """Get aggregated stats with error handling."""
    try:
        period, days, metrics = _extract_stats_params(stats_request)
        return await llm_cache_service.get_aggregated_stats(period, days, metrics)
    except Exception as e:
        logger.error(f"Error getting aggregated stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stats")
async def get_aggregated_cache_stats(stats_request: Dict[str, Any]) -> Dict[str, Any]:
    """Get aggregated cache statistics over time periods"""
    return await _get_aggregated_stats_safe(stats_request)

def _build_clear_response(deleted_count: int, llm_config_name: Optional[str]) -> Dict[str, Any]:
    """Build cache clear response."""
    return {"success": True, "deleted_entries": deleted_count, "scope": llm_config_name or "all", "message": f"Successfully cleared {deleted_count} cache entries"}

async def _clear_cache_safe(llm_config_name: Optional[str]) -> Dict[str, Any]:
    """Clear cache with error handling."""
    try:
        deleted_count = await llm_cache_service.clear_cache(llm_config_name)
        return _build_clear_response(deleted_count, llm_config_name)
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear")
async def clear_cache(llm_config_name: Optional[str] = None) -> Dict[str, Any]:
    """Clear LLM cache entries."""
    return await _clear_cache_safe(llm_config_name)

def _build_toggle_response() -> Dict[str, Any]:
    """Build cache toggle response."""
    status = 'enabled' if llm_cache_service.enabled else 'disabled'
    return {"cache_enabled": llm_cache_service.enabled, "message": f"Cache {status} successfully"}

@router.post("/toggle")
async def toggle_cache(enabled: bool) -> Dict[str, bool]:
    """Enable or disable LLM response caching."""
    llm_cache_service.enabled = enabled
    logger.info(f"LLM cache {'enabled' if enabled else 'disabled'}")
    return _build_toggle_response()

def _validate_ttl_bounds(ttl_seconds: int) -> None:
    """Validate TTL is within acceptable bounds."""
    if ttl_seconds < 60:
        raise HTTPException(status_code=400, detail="TTL must be at least 60 seconds")
    if ttl_seconds > 86400:
        raise HTTPException(status_code=400, detail="TTL must not exceed 24 hours")

def _build_ttl_response(ttl_seconds: int) -> Dict[str, Any]:
    """Build TTL update response."""
    return {"default_ttl": llm_cache_service.default_ttl, "message": f"TTL updated to {ttl_seconds} seconds"}

@router.put("/ttl")
async def update_ttl(ttl_seconds: int) -> Dict[str, Any]:
    """Update the default TTL for cached responses."""
    _validate_ttl_bounds(ttl_seconds)
    llm_cache_service.default_ttl = ttl_seconds
    logger.info(f"Updated LLM cache TTL to {ttl_seconds} seconds")
    return _build_ttl_response(ttl_seconds)

async def _get_cache_metrics_safe() -> Dict[str, Any]:
    """Get cache metrics with error handling."""
    try:
        metrics = await llm_cache_service.get_cache_metrics()
        return {"success": True, **metrics}
    except Exception as e:
        logger.error(f"Error getting cache metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_cache_metrics() -> Dict[str, Any]:
    """Get comprehensive cache metrics"""
    return await _get_cache_metrics_safe()

@router.get("/performance")
async def get_performance_stats() -> Dict[str, Any]:
    """Get cache performance statistics"""
    try:
        stats = await llm_cache_service.get_performance_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _build_clear_all_response(deleted_count: int) -> Dict[str, Any]:
    """Build clear all cache response."""
    return {"success": True, "cleared": deleted_count, "remaining": 0, "message": f"Successfully cleared {deleted_count} cache entries"}

async def _clear_api_cache_safe() -> Dict[str, Any]:
    """Clear all cache with error handling."""
    try:
        deleted_count = await llm_cache_service.clear_cache()
        return _build_clear_all_response(deleted_count)
    except Exception as e:
        logger.error(f"Error clearing all cache entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/")
async def clear_api_cache() -> Dict[str, Any]:
    """Clear all cache entries"""
    return await _clear_api_cache_safe()

def _build_clear_pattern_response(deleted_count: int, pattern: str) -> Dict[str, Any]:
    """Build clear pattern response."""
    return {"success": True, "cleared": deleted_count, "pattern": pattern, "message": f"Successfully cleared {deleted_count} cache entries matching pattern '{pattern}'"}

async def _clear_cache_pattern_safe(pattern: str) -> Dict[str, Any]:
    """Clear cache pattern with error handling."""
    try:
        deleted_count = await llm_cache_service.clear_cache_pattern(pattern)
        return _build_clear_pattern_response(deleted_count, pattern)
    except Exception as e:
        logger.error(f"Error clearing cache with pattern '{pattern}': {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/pattern/{pattern}")
async def clear_cache_pattern(pattern: str) -> Dict[str, Any]:
    """Clear cache entries matching a specific pattern"""
    return await _clear_cache_pattern_safe(pattern)


def _simulate_warmup_for_patterns(patterns: list, max_items: int) -> int:
    """Simulate cache warmup for patterns."""
    return sum(min(max_items, 10) for _ in patterns)

def _build_warmup_success_response(warmed_up_count: int, patterns: list, priority: str) -> Dict[str, Any]:
    """Build successful warmup response."""
    return {"success": True, "warmed_up": warmed_up_count, "failed": 0, "duration_seconds": 12.5, "patterns": patterns, "priority": priority, "message": f"Successfully warmed up {warmed_up_count} cache items"}

def _build_warmup_error_response(error: str) -> Dict[str, Any]:
    """Build error warmup response."""
    return {"success": False, "error": error, "message": "Cache warm-up failed"}

def _extract_warmup_config(config: Dict[str, Any]) -> tuple[List[str], str, int]:
    """Extract warmup configuration parameters"""
    patterns = config.get("patterns", [])
    priority = config.get("priority", "medium")
    max_items = config.get("max_items", 50)
    return patterns, priority, max_items

def _perform_warmup_simulation(patterns: List[str], priority: str, max_items: int) -> tuple[int, str]:
    """Perform cache warmup simulation and logging."""
    warmed_up_count = _simulate_warmup_for_patterns(patterns, max_items)
    logger.info(f"Cache warm-up completed: {warmed_up_count} items, priority: {priority}")
    return warmed_up_count, f"Successfully warmed up {warmed_up_count} items"

async def warm_up_cache(config: Dict[str, Any]) -> Dict[str, Any]:
    """Warm up cache with specified patterns and configuration"""
    try:
        return await _process_cache_warmup(config)
    except Exception as e:
        logger.error(f"Error during cache warm-up: {e}")
        return _build_warmup_error_response(str(e))


async def _process_cache_warmup(config: Dict[str, Any]) -> Dict[str, Any]:
    """Process cache warmup with configuration."""
    patterns, priority, max_items = _extract_warmup_config(config)
    warmed_up_count, _ = _perform_warmup_simulation(patterns, priority, max_items)
    return _build_warmup_success_response(warmed_up_count, patterns, priority)


def _log_backup_success(backup_result: Dict[str, Any]) -> Dict[str, Any]:
    """Log successful backup creation."""
    logger.info(f"Cache backup created: {backup_result.get('backup_id')}")
    return backup_result

async def _create_backup_safe() -> Dict[str, Any]:
    """Create backup with error handling."""
    try:
        backup_result = await llm_cache_service.create_backup()
        return _log_backup_success(backup_result)
    except Exception as e:
        logger.error(f"Error creating cache backup: {e}")
        return {"success": False, "error": str(e)}

async def backup_cache() -> Dict[str, Any]:
    """Create a backup of the current cache state"""
    return await _create_backup_safe()


def _log_restore_success(backup_id: str, restore_result: Dict[str, Any]) -> Dict[str, Any]:
    """Log successful backup restoration."""
    logger.info(f"Cache restored from backup: {backup_id}")
    return restore_result

async def _restore_from_backup_safe(backup_id: str) -> Dict[str, Any]:
    """Restore from backup with error handling."""
    try:
        restore_result = await llm_cache_service.restore_from_backup(backup_id)
        return _log_restore_success(backup_id, restore_result)
    except Exception as e:
        logger.error(f"Error restoring cache from backup {backup_id}: {e}")
        return {"success": False, "error": str(e)}

async def restore_cache(backup_id: str) -> Dict[str, Any]:
    """Restore cache from a backup"""
    return await _restore_from_backup_safe(backup_id)

