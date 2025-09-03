# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-13T00:00:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Refactored from triage_sub_agent_legacy.py - Cache utilities (25-line function limit)
# Git: v6 | dirty
# Change: Refactor | Scope: Component | Risk: Low
# Session: compliance-fix | Seq: 8
# Review: Pending | Score: 95
# ================================
"""Cache utilities - compliant with 25-line limit."""

import json
import re
from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.serialization.unified_json_handler import safe_json_loads
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.cache.cache_helpers import CacheHelpers


def normalize_request(request: str) -> str:
    """Normalize request for better cache hits."""
    normalized = request.lower().strip()
    return re.sub(r'\s+', ' ', normalized)


def generate_request_hash(request: str, user_context=None) -> str:
    """Generate hash for caching similar requests using canonical CacheHelpers."""
    normalized = normalize_request(request)
    
    # Use canonical cache key generation (SSOT)
    cache_helper = CacheHelpers(None)
    key_data = {"request": normalized}
    
    # Include user context for proper isolation when available
    if user_context:
        key_data["user_id"] = getattr(user_context, "user_id", None)
        key_data["thread_id"] = getattr(user_context, "thread_id", None)
    
    return cache_helper.hash_key_data(key_data)


def build_cache_key(request_hash: str) -> str:
    """Build Redis cache key."""
    return f"triage:cache:{request_hash}"


async def get_cached_result(redis_manager: Optional[RedisManager], request_hash: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached triage result if available."""
    if not redis_manager:
        return None
    return await _safe_cache_retrieval(redis_manager, request_hash)


async def _safe_cache_retrieval(redis_manager: RedisManager, request_hash: str) -> Optional[Dict[str, Any]]:
    """Safely retrieve from cache with error handling."""
    try:
        cached = await redis_manager.get(build_cache_key(request_hash))
        return _process_cached_data(cached, request_hash)
    except Exception as e:
        central_logger.warning(f"Failed to retrieve from cache: {e}")
        return None


def _process_cached_data(cached: str, request_hash: str) -> Optional[Dict[str, Any]]:
    """Process cached data if available."""
    if cached:
        central_logger.info(f"Cache hit for request hash: {request_hash}")
        return safe_json_loads(cached, {})
    return None


async def cache_result(redis_manager: Optional[RedisManager], request_hash: str, result: Dict[str, Any], ttl: int) -> None:
    """Cache triage result for future use."""
    if not redis_manager:
        return
    try:
        await redis_manager.set(build_cache_key(request_hash), json.dumps(result), ex=ttl)
        central_logger.debug(f"Cached result for request hash: {request_hash}")
    except Exception as e:
        central_logger.warning(f"Failed to cache result: {e}")