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