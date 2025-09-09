from shared.isolated_environment import get_env
"""Cache Coherence E2E Test Helpers

env = get_env()
Business Value Justification (BVJ):
1. Segment: Enterprise (40K+ MRR protection from stale data issues)
2. Business Goal: Prevent data inconsistency across distributed caches
3. Value Impact: Eliminates customer churn from stale AI optimization data
4. Revenue Impact: Protects $40K+ MRR from cache coherence failures

Architecture: <300 lines, functions <8 lines per CLAUDE.md requirements
"""

from shared.isolated_environment import get_env

env = get_env()
env.set("NETRA_ENV", "testing", "test")

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager
from tests.e2e.database_sync_fixtures import DatabaseSyncValidator
from test_framework.cypress.service_manager import ServiceDependencyManager as RealServicesManager
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient

logger = central_logger.get_logger(__name__)


@dataclass
class CacheCoherenceEvent:
    """Represents a cache coherence event for testing."""
    event_id: str
    event_type: str  # 'write', 'invalidate', 'read', 'notification'
    cache_keys: List[str]
    data_payload: Optional[Dict[str, Any]] = None
    service_origin: str = "unknown"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: Optional[int] = None


@dataclass 
class CacheCoherenceMetrics:
    """Metrics for cache coherence testing."""
    total_writes: int = 0
    successful_invalidations: int = 0
    failed_invalidations: int = 0
    notification_deliveries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    consistency_violations: int = 0
    average_invalidation_time: float = 0.0


class CacheCoherenceValidator:
    """Validates cache coherence across services and Redis."""
    
    def __init__(self):
        self.services_manager = RealServicesManager()
        self.db_validator = DatabaseSyncValidator()
        self.websocket_client: Optional[RealWebSocketClient] = None
        self.tracked_keys: Set[str] = set()
        self.metrics = CacheCoherenceMetrics()
        self.event_log: List[CacheCoherenceEvent] = []
        
    async def setup_coherence_environment(self) -> None:
        """Setup cache coherence testing environment."""
        await self.services_manager.start_all_services()
        await self._wait_for_redis_connection()
        await self._initialize_websocket_monitoring()
        await self._clear_test_cache_namespace()

    async def _wait_for_redis_connection(self) -> None:
        """Wait for Redis connection to be ready."""
        await redis_manager.connect()
        redis_client = await redis_manager.get_client()
        assert redis_client is not None, "Redis connection required for cache tests"
        
    async def _initialize_websocket_monitoring(self) -> None:
        """Initialize WebSocket for cache invalidation notifications."""
        websocket_url = "ws://localhost:8000/ws"
        self.websocket_client = RealWebSocketClient(websocket_url)
        await self.websocket_client.connect()
        
    async def _clear_test_cache_namespace(self) -> None:
        """Clear test cache keys before testing."""
        test_keys = await self._get_test_cache_keys()
        for key in test_keys:
            await redis_manager.delete(key)

    async def _get_test_cache_keys(self) -> List[str]:
        """Get all test cache keys from Redis."""
        redis_client = await redis_manager.get_client()
        if redis_client:
            return await redis_client.keys("test_cache_*")
        return []

    async def write_to_cache(self, event: CacheCoherenceEvent) -> bool:
        """Write data to cache and track the operation."""
        success = True
        for cache_key in event.cache_keys:
            self.tracked_keys.add(cache_key)
            cache_success = await self._write_single_cache_entry(cache_key, event)
            success = success and cache_success
            
        self.metrics.total_writes += len(event.cache_keys)
        self.event_log.append(event)
        return success

    async def _write_single_cache_entry(self, cache_key: str, event: CacheCoherenceEvent) -> bool:
        """Write single cache entry with optional TTL."""
        try:
            payload = json.dumps(event.data_payload) if event.data_payload else ""
            await redis_manager.set(cache_key, payload, ex=event.ttl_seconds)
            return True
        except Exception as e:
            logger.error(f"Cache write failed for key {cache_key}: {e}")
            return False

    async def invalidate_cache_keys(self, cache_keys: List[str], service_name: str) -> bool:
        """Invalidate cache keys and measure performance."""
        start_time = time.time()
        
        invalidation_event = CacheCoherenceEvent(
            event_id=f"invalidate_{int(time.time())}",
            event_type="invalidate", 
            cache_keys=cache_keys,
            service_origin=service_name
        )
        
        success = await self._execute_cache_invalidation(cache_keys)
        
        invalidation_time = time.time() - start_time
        self._update_invalidation_metrics(success, invalidation_time)
        self.event_log.append(invalidation_event)
        
        return success

    async def _execute_cache_invalidation(self, cache_keys: List[str]) -> bool:
        """Execute cache invalidation for all keys."""
        invalidation_results = []
        for cache_key in cache_keys:
            result = await redis_manager.delete(cache_key)
            invalidation_results.append(result is not None)
        return all(invalidation_results)

    def _update_invalidation_metrics(self, success: bool, invalidation_time: float) -> None:
        """Update invalidation performance metrics."""
        if success:
            self.metrics.successful_invalidations += 1
        else:
            self.metrics.failed_invalidations += 1
        
        # Update average invalidation time using running average
        total_invalidations = self.metrics.successful_invalidations + self.metrics.failed_invalidations
        current_avg = self.metrics.average_invalidation_time
        self.metrics.average_invalidation_time = (current_avg * (total_invalidations - 1) + invalidation_time) / total_invalidations

    async def verify_cache_consistency(self, expected_data: Dict[str, Any], cache_keys: List[str]) -> bool:
        """Verify cache consistency across all specified keys."""
        consistency_results = []
        
        for cache_key in cache_keys:
            is_consistent = await self._verify_single_key_consistency(cache_key, expected_data)
            consistency_results.append(is_consistent)
            
        overall_consistency = all(consistency_results)
        if not overall_consistency:
            self.metrics.consistency_violations += 1
            
        return overall_consistency

    async def _verify_single_key_consistency(self, cache_key: str, expected_data: Dict[str, Any]) -> bool:
        """Verify consistency for a single cache key."""
        cached_data = await redis_manager.get(cache_key)
        
        if cached_data is None:
            self.metrics.cache_misses += 1
            return expected_data.get(cache_key) is None
            
        self.metrics.cache_hits += 1
        
        try:
            parsed_data = json.loads(cached_data)
            return parsed_data == expected_data.get(cache_key)
        except json.JSONDecodeError:
            return cached_data == str(expected_data.get(cache_key, ""))

    async def simulate_cross_service_update(self, user_id: str) -> Dict[str, Any]:
        """Simulate cross-service cache update scenario."""
        update_scenario = {
            "user_id": user_id,
            "profile_cache_key": f"user_profile_{user_id}",
            "workspace_cache_key": f"user_workspace_{user_id}",
            "settings_cache_key": f"user_settings_{user_id}"
        }
        
        # Step 1: Write initial data to PostgreSQL
        initial_profile = await self._create_initial_profile_data(user_id)
        await self.db_validator.postgres.insert_user_profile(initial_profile)
        
        # Step 2: Cache profile data in Redis
        await self._cache_profile_data(update_scenario["profile_cache_key"], initial_profile)
        
        # Step 3: Update profile in PostgreSQL 
        updated_profile = await self._update_profile_data(initial_profile)
        await self.db_validator.postgres.update_user_profile(updated_profile)
        
        # Step 4: Invalidate cache to maintain consistency
        await self.invalidate_cache_keys([update_scenario["profile_cache_key"]], "auth_service")
        
        return update_scenario

    async def _create_initial_profile_data(self, user_id: str) -> Dict[str, Any]:
        """Create initial profile data for testing."""
        return {
            "user_id": user_id,
            "full_name": f"Test User {user_id}",
            "email": f"test_{user_id}@example.com",
            "plan_tier": "free",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    async def _cache_profile_data(self, cache_key: str, profile_data: Dict[str, Any]) -> None:
        """Cache profile data in Redis."""
        cache_event = CacheCoherenceEvent(
            event_id=f"cache_{int(time.time())}",
            event_type="write",
            cache_keys=[cache_key],
            data_payload=profile_data,
            service_origin="auth_service",
            ttl_seconds=300
        )
        await self.write_to_cache(cache_event)

    async def _update_profile_data(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update profile data for consistency testing."""
        updated_profile = profile_data.copy()
        updated_profile["plan_tier"] = "enterprise"
        updated_profile["updated_at"] = datetime.now(timezone.utc).isoformat()
        return updated_profile

    async def test_websocket_cache_notifications(self, cache_keys: List[str]) -> bool:
        """Test WebSocket notifications for cache updates."""
        if not self.websocket_client:
            return False
            
        notification_data = {
            "type": "cache_invalidated",
            "cache_keys": cache_keys,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.websocket_client.send_message(json.dumps(notification_data))
        self.metrics.notification_deliveries += 1
        
        return True

    async def simulate_cache_stampede_scenario(self, cache_key: str, concurrent_requests: int = 10) -> Dict[str, Any]:
        """Simulate cache stampede prevention scenario."""
        stampede_results = {
            "cache_key": cache_key,
            "concurrent_requests": concurrent_requests,
            "successful_writes": 0,
            "failed_writes": 0,
            "duplicate_computations": 0
        }
        
        # Simulate concurrent cache misses and regeneration
        cache_write_tasks = []
        for i in range(concurrent_requests):
            task_data = {
                "request_id": i,
                "cache_key": cache_key,
                "computed_value": f"computed_data_{i}_{int(time.time())}"
            }
            cache_write_tasks.append(self._simulate_cache_regeneration(task_data))
        
        results = await asyncio.gather(*cache_write_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                stampede_results["failed_writes"] += 1
            else:
                stampede_results["successful_writes"] += 1
                
        return stampede_results

    async def _simulate_cache_regeneration(self, task_data: Dict[str, Any]) -> bool:
        """Simulate cache regeneration with potential race conditions."""
        try:
            # Check if cache already exists (stampede prevention)
            existing_value = await redis_manager.get(task_data["cache_key"])
            if existing_value:
                return True  # Cache hit, no regeneration needed
                
            # Simulate expensive computation
            await asyncio.sleep(0.1)
            
            # Write computed value to cache
            await redis_manager.set(task_data["cache_key"], task_data["computed_value"], ex=60)
            return True
            
        except Exception as e:
            logger.error(f"Cache regeneration failed: {e}")
            return False

    def get_coherence_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache coherence metrics."""
        return {
            "total_writes": self.metrics.total_writes,
            "successful_invalidations": self.metrics.successful_invalidations,
            "failed_invalidations": self.metrics.failed_invalidations,
            "cache_hit_ratio": self._calculate_cache_hit_ratio(),
            "consistency_violations": self.metrics.consistency_violations,
            "average_invalidation_time_ms": round(self.metrics.average_invalidation_time * 1000, 2),
            "notification_deliveries": self.metrics.notification_deliveries,
            "tracked_keys_count": len(self.tracked_keys)
        }

    def _calculate_cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio percentage."""
        total_requests = self.metrics.cache_hits + self.metrics.cache_misses
        if total_requests == 0:
            return 0.0
        return round((self.metrics.cache_hits / total_requests) * 100, 2)

    async def cleanup_coherence_environment(self) -> None:
        """Cleanup cache coherence test environment."""
        await self._cleanup_tracked_cache_keys()
        if self.websocket_client:
            await self.websocket_client.disconnect()
        await self.services_manager.stop_all_services()

    async def _cleanup_tracked_cache_keys(self) -> None:
        """Cleanup all tracked cache keys."""
        for cache_key in self.tracked_keys:
            await redis_manager.delete(cache_key)
        self.tracked_keys.clear()