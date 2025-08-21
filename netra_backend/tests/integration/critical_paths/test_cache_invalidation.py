"""Cache Invalidation Across Services Critical Path Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (performance-critical features)
- Business Goal: Data consistency and performance optimization
- Value Impact: Protects $6K MRR from stale data issues and cache inconsistencies
- Strategic Impact: Ensures data coherency across distributed services

Critical Path: Data update -> Cache invalidation -> Cross-service notification -> Cache refresh
Coverage: Redis cache management, service coordination, consistency validation
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
import logging
import json
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, patch, MagicMock

# Add project root to path

from netra_backend.app.services.redis_service import RedisService
from netra_backend.app.services.cache.cache_manager import CacheManager
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager
from netra_backend.app.services.notification_service import NotificationService

# Add project root to path

logger = logging.getLogger(__name__)


class CacheInvalidationManager:
    """Manages cache invalidation testing across services."""
    
    def __init__(self):
        self.redis_service = None
        self.cache_manager = None
        self.db_manager = None
        self.notification_service = None
        self.cache_operations = []
        self.invalidation_events = []
        
    async def initialize_services(self):
        """Initialize cache invalidation services."""
        self.redis_service = RedisService()
        await self.redis_service.connect()
        
        self.cache_manager = CacheManager()
        await self.cache_manager.initialize()
        
        self.db_manager = DatabaseConnectionManager()
        await self.db_manager.initialize()
        
        self.notification_service = NotificationService()
        await self.notification_service.initialize()
    
    async def create_cache_entry(self, key: str, data: Dict[str, Any], 
                               ttl: int = 300) -> Dict[str, Any]:
        """Create cache entry across services."""
        start_time = time.time()
        
        # Store in Redis
        cache_result = await self.cache_manager.set(
            key, json.dumps(data), ttl
        )
        
        # Record operation
        operation = {
            "operation": "create",
            "key": key,
            "data": data,
            "ttl": ttl,
            "success": cache_result,
            "timestamp": time.time(),
            "operation_time": time.time() - start_time
        }
        
        self.cache_operations.append(operation)
        return operation
    
    async def update_data_and_invalidate_cache(self, key: str, new_data: Dict[str, Any],
                                             affected_services: List[str]) -> Dict[str, Any]:
        """Update data and trigger cache invalidation."""
        invalidation_start = time.time()
        
        try:
            # Step 1: Update data in database
            conn = await self.db_manager.get_connection()
            
            # Simulate database update
            update_query = """
                UPDATE cache_test_data 
                SET data = $1, updated_at = $2 
                WHERE cache_key = $3
                RETURNING id
            """
            
            result = await conn.fetchrow(
                update_query,
                json.dumps(new_data),
                time.time(),
                key
            )
            
            if not result:
                # Insert if not exists
                insert_query = """
                    INSERT INTO cache_test_data (cache_key, data, updated_at)
                    VALUES ($1, $2, $3)
                    RETURNING id
                """
                result = await conn.fetchrow(
                    insert_query,
                    key,
                    json.dumps(new_data),
                    time.time()
                )
            
            await self.db_manager.return_connection(conn)
            
            # Step 2: Invalidate cache
            invalidation_result = await self.cache_manager.delete(key)
            
            # Step 3: Notify affected services
            notification_results = []
            for service in affected_services:
                notification = await self.notification_service.notify_cache_invalidation(
                    service, key, {"reason": "data_update"}
                )
                notification_results.append(notification)
            
            # Record invalidation event
            invalidation_event = {
                "key": key,
                "new_data": new_data,
                "affected_services": affected_services,
                "db_updated": result is not None,
                "cache_invalidated": invalidation_result,
                "notifications_sent": len([n for n in notification_results if n.get("success")]),
                "total_time": time.time() - invalidation_start,
                "timestamp": time.time()
            }
            
            self.invalidation_events.append(invalidation_event)
            return invalidation_event
            
        except Exception as e:
            return {
                "key": key,
                "error": str(e),
                "total_time": time.time() - invalidation_start,
                "success": False
            }
    
    async def verify_cache_consistency(self, key: str, expected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify cache consistency across services."""
        verification_start = time.time()
        
        # Check Redis cache
        cached_data = await self.cache_manager.get(key)
        
        # Check database
        conn = await self.db_manager.get_connection()
        db_result = await conn.fetchrow(
            "SELECT data FROM cache_test_data WHERE cache_key = $1", key
        )
        await self.db_manager.return_connection(conn)
        
        db_data = json.loads(db_result["data"]) if db_result else None
        cached_data_parsed = json.loads(cached_data) if cached_data else None
        
        consistency_check = {
            "key": key,
            "expected_data": expected_data,
            "cached_data": cached_data_parsed,
            "db_data": db_data,
            "cache_consistent": cached_data_parsed == expected_data if cached_data_parsed else True,  # None is consistent (invalidated)
            "db_consistent": db_data == expected_data if db_data else False,
            "verification_time": time.time() - verification_start
        }
        
        return consistency_check
    
    async def test_multi_service_cache_invalidation(self, cache_entries: List[Dict]) -> Dict[str, Any]:
        """Test cache invalidation across multiple services."""
        test_start = time.time()
        
        # Create initial cache entries
        create_results = []
        for entry in cache_entries:
            result = await self.create_cache_entry(
                entry["key"], entry["data"], entry.get("ttl", 300)
            )
            create_results.append(result)
        
        # Wait for cache to propagate
        await asyncio.sleep(0.1)
        
        # Perform invalidations
        invalidation_results = []
        for entry in cache_entries:
            result = await self.update_data_and_invalidate_cache(
                entry["key"],
                {**entry["data"], "updated": True, "version": 2},
                entry.get("affected_services", ["service_a", "service_b"])
            )
            invalidation_results.append(result)
        
        # Verify consistency after invalidation
        consistency_results = []
        for entry in cache_entries:
            consistency = await self.verify_cache_consistency(
                entry["key"],
                {**entry["data"], "updated": True, "version": 2}
            )
            consistency_results.append(consistency)
        
        return {
            "total_test_time": time.time() - test_start,
            "create_results": create_results,
            "invalidation_results": invalidation_results,
            "consistency_results": consistency_results,
            "overall_success": all(
                r.get("cache_invalidated", False) for r in invalidation_results
            )
        }
    
    async def cleanup(self):
        """Clean up cache invalidation test resources."""
        # Clear cache entries
        for operation in self.cache_operations:
            if operation["success"]:
                await self.cache_manager.delete(operation["key"])
        
        # Clear database test data
        try:
            conn = await self.db_manager.get_connection()
            for operation in self.cache_operations:
                await conn.execute(
                    "DELETE FROM cache_test_data WHERE cache_key = $1",
                    operation["key"]
                )
            await self.db_manager.return_connection(conn)
        except Exception:
            pass
        
        if self.redis_service:
            await self.redis_service.disconnect()
        if self.cache_manager:
            await self.cache_manager.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()
        if self.notification_service:
            await self.notification_service.shutdown()


@pytest.fixture
async def cache_invalidation_manager():
    """Create cache invalidation manager for testing."""
    manager = CacheInvalidationManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_single_cache_invalidation_flow(cache_invalidation_manager):
    """Test single cache invalidation flow."""
    manager = cache_invalidation_manager
    
    # Create cache entry
    cache_key = "test_user_profile"
    initial_data = {"user_id": "test_user", "name": "Test User", "version": 1}
    
    create_result = await manager.create_cache_entry(cache_key, initial_data)
    assert create_result["success"] is True
    assert create_result["operation_time"] < 0.1
    
    # Update and invalidate
    updated_data = {**initial_data, "name": "Updated User", "version": 2}
    invalidation_result = await manager.update_data_and_invalidate_cache(
        cache_key, updated_data, ["user_service", "profile_service"]
    )
    
    assert invalidation_result["db_updated"] is True
    assert invalidation_result["cache_invalidated"] is True
    assert invalidation_result["notifications_sent"] == 2
    assert invalidation_result["total_time"] < 1.0
    
    # Verify consistency
    consistency = await manager.verify_cache_consistency(cache_key, updated_data)
    assert consistency["db_consistent"] is True
    assert consistency["cache_consistent"] is True  # Should be None (invalidated) or updated


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_concurrent_cache_invalidation(cache_invalidation_manager):
    """Test concurrent cache invalidation across multiple keys."""
    manager = cache_invalidation_manager
    
    # Configure multiple cache entries
    cache_entries = [
        {"key": "user_1", "data": {"user_id": "1", "name": "User 1"}, "affected_services": ["user_service"]},
        {"key": "user_2", "data": {"user_id": "2", "name": "User 2"}, "affected_services": ["user_service"]},
        {"key": "config_1", "data": {"setting": "value1"}, "affected_services": ["config_service"]},
        {"key": "session_1", "data": {"session_id": "s1", "active": True}, "affected_services": ["session_service"]}
    ]
    
    test_result = await manager.test_multi_service_cache_invalidation(cache_entries)
    
    assert test_result["overall_success"] is True
    assert test_result["total_test_time"] < 3.0
    
    # Verify all cache operations succeeded
    assert all(r["success"] for r in test_result["create_results"])
    assert all(r.get("cache_invalidated", False) for r in test_result["invalidation_results"])


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_cache_invalidation_error_handling(cache_invalidation_manager):
    """Test cache invalidation error handling."""
    manager = cache_invalidation_manager
    
    # Test invalidation of non-existent cache entry
    non_existent_result = await manager.update_data_and_invalidate_cache(
        "non_existent_key",
        {"data": "value"},
        ["test_service"]
    )
    
    # Should handle gracefully
    assert "error" in non_existent_result or non_existent_result.get("db_updated") is True
    
    # Test with invalid service notification
    cache_key = "error_test_key"
    await manager.create_cache_entry(cache_key, {"test": "data"})
    
    error_result = await manager.update_data_and_invalidate_cache(
        cache_key,
        {"test": "updated"},
        ["invalid_service"]
    )
    
    # Should handle invalid service gracefully
    assert error_result.get("cache_invalidated") is True  # Cache part should work


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_cache_consistency_validation(cache_invalidation_manager):
    """Test cache consistency validation across services."""
    manager = cache_invalidation_manager
    
    # Create and update cache entry
    cache_key = "consistency_test"
    initial_data = {"id": "test", "value": "initial"}
    updated_data = {"id": "test", "value": "updated"}
    
    await manager.create_cache_entry(cache_key, initial_data)
    await manager.update_data_and_invalidate_cache(
        cache_key, updated_data, ["consistency_service"]
    )
    
    # Verify consistency multiple times
    consistency_checks = []
    for _ in range(3):
        consistency = await manager.verify_cache_consistency(cache_key, updated_data)
        consistency_checks.append(consistency)
        await asyncio.sleep(0.1)
    
    # All checks should be consistent with L3 validation
    assert all(c["db_consistent"] for c in consistency_checks)
    assert all(c["verification_time"] < 0.1 for c in consistency_checks)
    assert all(c["metadata_exists"] for c in consistency_checks)
    assert all(c["cache_invalidated"] for c in consistency_checks)
    
    # Verify circuit breaker state
    assert manager.circuit_breaker.failure_count < 3
    assert manager.circuit_breaker.state.value == "closed"


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_redis_circuit_breaker_integration(cache_invalidation_manager):
    """Test L3 Redis circuit breaker integration."""
    manager = cache_invalidation_manager
    
    # Test normal operation with circuit breaker
    cache_key = "circuit_breaker_test"
    test_data = {"test": "data", "timestamp": time.time()}
    
    create_result = await manager.create_cache_entry(cache_key, test_data)
    assert create_result["success"] is True
    
    # Test circuit breaker state
    initial_state = manager.circuit_breaker.state.value
    
    # Perform invalidation
    invalidation_result = await manager.update_data_and_invalidate_cache(
        cache_key, {**test_data, "updated": True}, ["test_service"]
    )
    
    assert invalidation_result["cache_invalidated"] is True
    assert manager.circuit_breaker.state.value == "closed"
    assert initial_state == "closed"