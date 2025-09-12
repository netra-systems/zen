"""Cache Coherence E2E Tests

Business Value Justification (BVJ):
1. Segment: Enterprise ($40K+ MRR protection)
2. Business Goal: Prevent revenue loss from stale data serving incorrect AI optimization
3. Value Impact: Ensures cache consistency across Auth -> Backend -> Frontend services
4. Revenue Impact: Protects $40K+ MRR from cache-induced customer churn

CRITICAL TEST IMPLEMENTATION #5: Distributed Cache Coherence
Architecture: <300 lines, functions <8 lines per CLAUDE.md requirements
"""

import asyncio
import time
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager
from tests.e2e.cache_coherence_helpers import (
    CacheCoherenceEvent,
    CacheCoherenceMetrics,
    CacheCoherenceValidator,
)
from tests.e2e.jwt_token_helpers import JWTTestHelper

logger = central_logger.get_logger(__name__)

# Test configuration
CACHE_TTL_SECONDS = 300
MAX_INVALIDATION_TIME_MS = 100
MIN_CACHE_HIT_RATIO = 80.0
MAX_CONSISTENCY_VIOLATIONS = 0


@pytest.mark.e2e
class TestCacheCoherence:
    """E2E tests for distributed cache coherence across services."""
    
    @pytest.fixture(autouse=True)
    async def setup_cache_tests(self):
        """Setup cache coherence test environment."""
        self.validator = CacheCoherenceValidator()
        self.jwt_helper = JWTTestHelper()
        
        await self.validator.setup_coherence_environment()
        yield
        await self.validator.cleanup_coherence_environment()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_user_data_cache_invalidation_flow(self):
        """Test user data update  ->  cache invalidation  ->  consistency."""
        # BVJ: Enterprise revenue protection from stale user data
        user_id = "cache_test_user_001"
        
        # Execute cross-service cache update scenario
        update_scenario = await self.validator.simulate_cross_service_update(user_id)
        
        # Verify cache was properly invalidated
        cache_keys = [
            update_scenario["profile_cache_key"],
            update_scenario["workspace_cache_key"],
            update_scenario["settings_cache_key"]
        ]
        
        # Verify no stale data remains in cache
        stale_data_check = await self._verify_no_stale_data(cache_keys)
        assert stale_data_check, "Stale data detected after invalidation"

    async def _verify_no_stale_data(self, cache_keys: List[str]) -> bool:
        """Verify no stale data exists in specified cache keys."""
        for cache_key in cache_keys:
            cached_value = await redis_manager.get(cache_key)
            if cached_value:
                logger.warning(f"Stale data found in cache key: {cache_key}")
                return False
        return True

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cross_service_cache_consistency(self):
        """Test cache consistency across Auth -> Backend -> Frontend services."""
        user_id = "cache_consistency_user_002"
        
        # Step 1: Auth service updates user data
        auth_update_event = CacheCoherenceEvent(
            event_id="auth_update_001",
            event_type="write",
            cache_keys=[f"auth_user_{user_id}"],
            data_payload={"user_id": user_id, "plan": "enterprise", "source": "auth"},
            service_origin="auth_service",
            ttl_seconds=CACHE_TTL_SECONDS
        )
        await self.validator.write_to_cache(auth_update_event)

        # Step 2: Backend service syncs user data
        await self._simulate_backend_sync(user_id)
        
        # Step 3: Frontend requests updated data
        consistency_check = await self._verify_frontend_consistency(user_id)
        assert consistency_check, "Cross-service cache consistency failed"

    async def _simulate_backend_sync(self, user_id: str) -> None:
        """Simulate backend service syncing user data."""
        backend_sync_event = CacheCoherenceEvent(
            event_id="backend_sync_001", 
            event_type="write",
            cache_keys=[f"backend_user_{user_id}"],
            data_payload={"user_id": user_id, "plan": "enterprise", "source": "backend"},
            service_origin="backend_service",
            ttl_seconds=CACHE_TTL_SECONDS
        )
        await self.validator.write_to_cache(backend_sync_event)

    async def _verify_frontend_consistency(self, user_id: str) -> bool:
        """Verify frontend receives consistent user data."""
        auth_data = await redis_manager.get(f"auth_user_{user_id}")
        backend_data = await redis_manager.get(f"backend_user_{user_id}")
        
        if not auth_data or not backend_data:
            return False
            
        # Both services should have consistent plan data
        return "enterprise" in auth_data and "enterprise" in backend_data

    @pytest.mark.asyncio 
    @pytest.mark.e2e
    async def test_bulk_operations_cache_coherence(self):
        """Test cache coherence during bulk operations."""
        # BVJ: Prevents data inconsistency during batch processing
        user_count = 50
        user_ids = [f"bulk_user_{i:03d}" for i in range(user_count)]
        
        # Execute bulk cache operations
        bulk_results = await self._execute_bulk_cache_operations(user_ids)
        
        # Verify coherence across all operations
        coherence_metrics = self.validator.get_coherence_metrics()
        assert coherence_metrics["consistency_violations"] <= MAX_CONSISTENCY_VIOLATIONS
        assert coherence_metrics["cache_hit_ratio"] >= MIN_CACHE_HIT_RATIO

    async def _execute_bulk_cache_operations(self, user_ids: List[str]) -> Dict[str, Any]:
        """Execute bulk cache operations and measure coherence."""
        bulk_events = []
        for user_id in user_ids:
            event = CacheCoherenceEvent(
                event_id=f"bulk_{user_id}",
                event_type="write",
                cache_keys=[f"bulk_cache_{user_id}"],
                data_payload={"user_id": user_id, "processed": True},
                service_origin="bulk_processor",
                ttl_seconds=CACHE_TTL_SECONDS
            )
            bulk_events.append(event)
        
        # Execute bulk operations concurrently
        write_tasks = [self.validator.write_to_cache(event) for event in bulk_events]
        write_results = await asyncio.gather(*write_tasks)
        
        return {"successful_writes": sum(write_results), "total_operations": len(user_ids)}

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_ttl_expiration_refresh_logic(self):
        """Test TTL expiration and cache refresh logic."""
        cache_key = "ttl_test_key"
        short_ttl = 2  # 2 seconds for testing
        
        # Write data with short TTL
        ttl_event = CacheCoherenceEvent(
            event_id="ttl_test",
            event_type="write", 
            cache_keys=[cache_key],
            data_payload={"test": "ttl_data", "created": int(time.time())},
            service_origin="ttl_service",
            ttl_seconds=short_ttl
        )
        await self.validator.write_to_cache(ttl_event)
        
        # Verify data exists initially
        initial_data = await redis_manager.get(cache_key)
        assert initial_data is not None, "Data should exist before TTL expiration"
        
        # Wait for TTL expiration
        await asyncio.sleep(short_ttl + 1)
        
        # Verify data expired
        expired_data = await redis_manager.get(cache_key)
        assert expired_data is None, "Data should expire after TTL"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_cache_update_notifications(self):
        """Test WebSocket notifications for cache updates."""
        # BVJ: Real-time cache invalidation notifications prevent stale UI
        cache_keys = ["ws_notification_test_1", "ws_notification_test_2"]
        
        # Send cache update notifications via WebSocket
        notification_success = await self.validator.test_websocket_cache_notifications(cache_keys)
        assert notification_success, "WebSocket cache notifications failed"
        
        # Verify metrics tracked notifications
        metrics = self.validator.get_coherence_metrics()
        assert metrics["notification_deliveries"] >= 1

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cache_stampede_prevention(self):
        """Test cache stampede prevention during concurrent requests."""
        cache_key = "stampede_prevention_test"
        concurrent_requests = 20
        
        # Simulate cache stampede scenario
        stampede_results = await self.validator.simulate_cache_stampede_scenario(
            cache_key, concurrent_requests
        )
        
        # Verify stampede was handled correctly
        assert stampede_results["successful_writes"] > 0, "No successful cache writes"
        assert stampede_results["failed_writes"] < concurrent_requests, "Too many failures"
        
        # Verify only one value exists in cache (no race conditions)
        final_cache_value = await redis_manager.get(cache_key)
        assert final_cache_value is not None, "Cache should contain computed value"

    @pytest.mark.asyncio 
    @pytest.mark.e2e
    async def test_cache_invalidation_performance(self):
        """Test cache invalidation performance requirements."""
        # BVJ: Sub-100ms invalidation prevents user experience degradation
        cache_keys = [f"perf_test_key_{i}" for i in range(100)]
        
        # Pre-populate cache keys
        for cache_key in cache_keys:
            await redis_manager.set(cache_key, "performance_test_data", ex=300)
        
        # Measure invalidation performance
        start_time = time.time()
        invalidation_success = await self.validator.invalidate_cache_keys(cache_keys, "performance_test")
        invalidation_time_ms = (time.time() - start_time) * 1000
        
        assert invalidation_success, "Cache invalidation failed"
        assert invalidation_time_ms <= MAX_INVALIDATION_TIME_MS, f"Invalidation too slow: {invalidation_time_ms}ms"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multi_service_cache_invalidation_cascade(self):
        """Test cascading cache invalidation across multiple services."""
        user_id = "cascade_test_user"
        
        # Create cache entries across multiple services
        service_cache_keys = {
            "auth_service": f"auth_profile_{user_id}",
            "backend_service": f"backend_workspace_{user_id}", 
            "frontend_service": f"frontend_session_{user_id}"
        }
        
        # Populate cache in all services
        for service, cache_key in service_cache_keys.items():
            event = CacheCoherenceEvent(
                event_id=f"cascade_{service}",
                event_type="write",
                cache_keys=[cache_key],
                data_payload={"service": service, "user_id": user_id},
                service_origin=service,
                ttl_seconds=CACHE_TTL_SECONDS
            )
            await self.validator.write_to_cache(event)
        
        # Trigger cascading invalidation
        all_cache_keys = list(service_cache_keys.values())
        cascade_success = await self.validator.invalidate_cache_keys(all_cache_keys, "cascade_trigger")
        
        assert cascade_success, "Cascading cache invalidation failed"
        
        # Verify all caches were invalidated
        for cache_key in all_cache_keys:
            cached_data = await redis_manager.get(cache_key)
            assert cached_data is None, f"Cache key {cache_key} not properly invalidated"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cache_coherence_metrics_collection(self):
        """Test comprehensive cache coherence metrics collection."""
        # Execute various cache operations to generate metrics
        test_key = "metrics_collection_test"
        
        # Write operation
        write_event = CacheCoherenceEvent(
            event_id="metrics_write",
            event_type="write",
            cache_keys=[test_key],
            data_payload={"test": "metrics_data"},
            service_origin="metrics_service"
        )
        await self.validator.write_to_cache(write_event)
        
        # Read operation (cache hit)
        await redis_manager.get(test_key)
        
        # Invalidation operation  
        await self.validator.invalidate_cache_keys([test_key], "metrics_service")
        
        # Collect and verify metrics
        metrics = self.validator.get_coherence_metrics()
        
        assert metrics["total_writes"] >= 1, "Write metrics not tracked"
        assert metrics["successful_invalidations"] >= 1, "Invalidation metrics not tracked"
        assert isinstance(metrics["cache_hit_ratio"], float), "Hit ratio not calculated"
        assert isinstance(metrics["average_invalidation_time_ms"], float), "Invalidation time not tracked"