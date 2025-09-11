# 🚨 Three-Tier Storage Architecture Comprehensive Test Plan

**Date**: 2025-01-09  
**Issue**: #1 - Broken Three-Tier Storage Architecture in Message Handling  
**Priority**: P0 - Mission Critical  
**Business Impact**: Severe UX degradation and architectural violations  

## Executive Summary

This test plan creates comprehensive **FAILING TESTS** to expose the critical architectural gaps in the current message handling system. The tests will demonstrate that:

1. `StateCacheManager` uses in-memory dict instead of Redis
2. `handle_send_message_request()` bypasses Redis entirely
3. No three-tier failover chain implementation
4. Missing WebSocket notifications for real-time user feedback
5. Performance violations (>500ms message delays vs <100ms target)

## 📋 Architecture Gap Analysis 

### Current Reality (BROKEN)
```python
# handle_send_message_request() - WRONG IMPLEMENTATION
message_repo = MessageRepository()
await message_repo.create(db, **message_data)  # ❌ Direct PostgreSQL
await db.commit()                               # ❌ Blocking commit ~500ms
return response                                 # ❌ User waits for database
```

### Expected Architecture (FROM SPEC)
```python
# Should be 3-tier flow:
# 1. Redis (PRIMARY) - Store for <100ms access
# 2. PostgreSQL (SECONDARY) - Durable checkpoints 
# 3. ClickHouse (TERTIARY) - Analytics archive
# + WebSocket notifications for immediate user feedback
```

## 🎯 Test Strategy

All tests are designed to **FAIL WITH CURRENT IMPLEMENTATION** and pass once the three-tier architecture is properly implemented. This follows the principle that failing tests clearly demonstrate system gaps.

## 📁 Test File Structure & Locations

Following `reports/testing/TEST_CREATION_GUIDE.md` SSOT patterns:

```
netra_backend/tests/
├── unit/
│   ├── services/
│   │   ├── test_state_cache_manager_redis_integration_unit.py    # FAILING TESTS
│   │   └── test_message_three_tier_storage_unit.py               # FAILING TESTS
│   └── routes/
│       └── test_thread_handlers_three_tier_integration_unit.py   # FAILING TESTS
├── integration/
│   ├── services/
│   │   ├── test_three_tier_message_flow_integration.py           # FAILING TESTS  
│   │   └── test_redis_postgresql_failover_integration.py         # FAILING TESTS
│   └── websocket/
│       └── test_message_websocket_notification_integration.py    # FAILING TESTS
└── e2e/
    ├── test_three_tier_message_performance_e2e.py                # FAILING TESTS
    └── test_message_failover_scenarios_e2e.py                    # FAILING TESTS

tests/mission_critical/
└── test_three_tier_storage_compliance.py                         # FAILING TESTS
```

## 🔧 Unit Tests (No Docker Required)

### 1. StateCacheManager Redis Integration
**File**: `netra_backend/tests/unit/services/test_state_cache_manager_redis_integration_unit.py`

**Business Value**: Ensures Redis is actually used instead of in-memory dict

```python
"""
Test StateCacheManager Redis Integration - DESIGNED TO FAIL

These tests expose that StateCacheManager uses in-memory dict instead of Redis.
They will FAIL until proper Redis integration is implemented.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: System Performance & Reliability
- Value Impact: Sub-100ms message access via Redis caching
- Strategic Impact: Foundation for scalable message architecture
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from netra_backend.app.services.state_persistence import StateCacheManager, state_cache_manager
from netra_backend.app.redis_manager import redis_manager

class TestStateCacheManagerRedisIntegration:
    """Unit tests for StateCacheManager Redis integration - FAILING TESTS."""
    
    @pytest.mark.unit
    async def test_state_cache_manager_uses_redis_not_memory_dict(self):
        """FAILING TEST: StateCacheManager should use Redis, not in-memory dict."""
        # This test WILL FAIL because StateCacheManager uses self._cache: Dict[str, Any] = {}
        
        cache_manager = StateCacheManager()
        
        # TEST WILL FAIL: StateCacheManager doesn't use RedisManager
        assert hasattr(cache_manager, 'redis_manager'), "StateCacheManager should use RedisManager"
        assert cache_manager.redis_manager is not None, "Redis manager should be initialized"
        
        # TEST WILL FAIL: Current implementation uses in-memory dict
        assert not hasattr(cache_manager, '_cache'), "Should not use in-memory dict when Redis available"
    
    @pytest.mark.unit
    async def test_save_primary_state_calls_redis_set(self):
        """FAILING TEST: save_primary_state should call redis.set(), not dict assignment."""
        cache_manager = StateCacheManager()
        
        # Mock request
        mock_request = MagicMock()
        mock_request.run_id = "test-run-123"
        mock_request.state_data = {"message": "test message", "status": "pending"}
        
        with patch.object(redis_manager, 'set', new_callable=AsyncMock) as mock_redis_set:
            mock_redis_set.return_value = True
            
            result = await cache_manager.save_primary_state(mock_request)
            
            # TEST WILL FAIL: Current implementation doesn't call Redis
            mock_redis_set.assert_called_once_with(
                f"state:primary:{mock_request.run_id}",
                json.dumps(mock_request.state_data),
                ex=3600  # 1 hour TTL
            )
            assert result is True

    @pytest.mark.unit
    async def test_load_primary_state_calls_redis_get(self):
        """FAILING TEST: load_primary_state should call redis.get(), not dict lookup.""" 
        cache_manager = StateCacheManager()
        run_id = "test-run-456"
        expected_data = {"message": "cached message", "status": "completed"}
        
        with patch.object(redis_manager, 'get', new_callable=AsyncMock) as mock_redis_get:
            mock_redis_get.return_value = json.dumps(expected_data)
            
            result = await cache_manager.load_primary_state(run_id)
            
            # TEST WILL FAIL: Current implementation doesn't call Redis
            mock_redis_get.assert_called_once_with(f"state:primary:{run_id}")
            assert result == expected_data

    @pytest.mark.unit
    async def test_cache_state_in_redis_actually_uses_redis(self):
        """FAILING TEST: cache_state_in_redis should use Redis, not memory dict."""
        cache_manager = StateCacheManager()
        
        mock_request = MagicMock()
        mock_request.run_id = "redis-test-789"
        mock_request.state_data = {"tier": "redis", "performance": "sub-100ms"}
        
        with patch.object(redis_manager, 'set', new_callable=AsyncMock) as mock_redis_set:
            mock_redis_set.return_value = True
            
            result = await cache_manager.cache_state_in_redis(mock_request)
            
            # TEST WILL FAIL: Method just calls save_primary_state (which uses dict)
            mock_redis_set.assert_called_once()
            assert result is True
```

### 2. Message Three-Tier Storage Flow
**File**: `netra_backend/tests/unit/services/test_message_three_tier_storage_unit.py`

**Business Value**: Validates the complete three-tier storage architecture

```python
"""
Test Message Three-Tier Storage Flow - DESIGNED TO FAIL

These tests expose missing three-tier storage architecture for message handling.
They will FAIL until proper Redis -> PostgreSQL -> ClickHouse flow is implemented.

Business Value Justification (BVJ):
- Segment: Enterprise ($25K+ MRR)
- Business Goal: Zero data loss + Sub-100ms performance  
- Value Impact: Mission-critical AI workloads with disaster recovery
- Strategic Impact: $9.4M protection value per spec
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from netra_backend.app.routes.utils.thread_handlers import handle_send_message_request
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.services.database.message_repository import MessageRepository

class TestMessageThreeTierStorage:
    """Unit tests for three-tier message storage - FAILING TESTS."""
    
    @pytest.mark.unit 
    async def test_handle_send_message_saves_to_redis_first(self):
        """FAILING TEST: Messages should save to Redis (Tier 1) before PostgreSQL."""
        # Current implementation ONLY saves to PostgreSQL
        
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_request.message = "Test message for Redis"
        mock_request.metadata = {}
        
        with patch.object(redis_manager, 'set', new_callable=AsyncMock) as mock_redis_set, \
             patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation', new_callable=AsyncMock) as mock_validation:
            
            mock_validation.return_value = MagicMock(id="thread-123")
            mock_redis_set.return_value = True
            
            # Call the function
            await handle_send_message_request(mock_db, "thread-123", mock_request, "user-456")
            
            # TEST WILL FAIL: Current implementation doesn't call Redis
            mock_redis_set.assert_called_once()
            
            # Verify Redis key format follows SPEC
            call_args = mock_redis_set.call_args[0]
            redis_key = call_args[0]
            assert redis_key.startswith("message:active:"), "Should use message:active: prefix for active messages"

    @pytest.mark.unit
    async def test_message_three_tier_failover_chain(self):
        """FAILING TEST: Should implement Redis -> PostgreSQL -> ClickHouse failover."""
        # This will expose that no failover chain exists
        
        with patch('netra_backend.app.services.UnifiedMessageStorageService') as mock_storage:
            mock_storage_instance = AsyncMock()
            mock_storage.return_value = mock_storage_instance
            
            # Simulate Redis failure
            mock_storage_instance.save_to_redis.side_effect = Exception("Redis connection failed")
            mock_storage_instance.save_to_postgresql.return_value = True
            mock_storage_instance.save_to_clickhouse.return_value = True
            
            message_data = {
                'id': 'msg-789',
                'thread_id': 'thread-123', 
                'content': 'Test failover message',
                'role': 'user'
            }
            
            # TEST WILL FAIL: UnifiedMessageStorageService doesn't exist
            result = await mock_storage_instance.save_with_failover(message_data)
            
            # Should fallback to PostgreSQL when Redis fails
            mock_storage_instance.save_to_postgresql.assert_called_once_with(message_data)
            assert result['tier_used'] == 'postgresql'
            assert result['failover_reason'] == 'redis_failure'

    @pytest.mark.unit
    async def test_message_retrieval_performance_tiers(self):
        """FAILING TEST: Message retrieval should try Redis first for <100ms performance."""
        
        message_id = "msg-performance-test"
        expected_message = {
            'id': message_id,
            'content': 'Performance test message',
            'created_at': 1641555200
        }
        
        with patch('netra_backend.app.services.UnifiedMessageRetrievalService') as mock_retrieval:
            mock_retrieval_instance = AsyncMock()
            mock_retrieval.return_value = mock_retrieval_instance
            
            # Redis hit scenario (fast path)
            mock_retrieval_instance.get_from_redis.return_value = expected_message
            
            # TEST WILL FAIL: UnifiedMessageRetrievalService doesn't exist
            result = await mock_retrieval_instance.get_message_with_performance_tiers(message_id)
            
            # Should try Redis first
            mock_retrieval_instance.get_from_redis.assert_called_once_with(message_id)
            
            # Should not call PostgreSQL when Redis has data
            mock_retrieval_instance.get_from_postgresql.assert_not_called()
            
            assert result == expected_message
            assert result['retrieval_tier'] == 'redis'
            assert result['latency_ms'] < 100  # Performance target
```

### 3. Thread Handlers Integration
**File**: `netra_backend/tests/unit/routes/test_thread_handlers_three_tier_integration_unit.py`

**Business Value**: Ensures thread handlers use three-tier architecture

```python
"""
Test Thread Handlers Three-Tier Integration - DESIGNED TO FAIL

These tests expose that handle_send_message_request bypasses three-tier architecture.
They will FAIL until proper integration is implemented.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Improve Chat UX & System Reliability
- Value Impact: Fast message confirmation + background persistence
- Strategic Impact: Core chat functionality performance
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import time
from netra_backend.app.routes.utils.thread_handlers import handle_send_message_request

class TestThreadHandlersThreeTierIntegration:
    """Unit tests for thread handlers three-tier integration - FAILING TESTS."""
    
    @pytest.mark.unit
    async def test_send_message_returns_immediately_after_redis_cache(self):
        """FAILING TEST: Should return to user immediately after Redis cache, not after PostgreSQL commit."""
        # Current implementation waits for PostgreSQL commit (~500ms)
        # Should return after Redis cache (~50ms) with background PostgreSQL
        
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_request.message = "Test immediate response"
        mock_request.metadata = {}
        
        start_time = time.time()
        
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation', new_callable=AsyncMock) as mock_validation, \
             patch('netra_backend.app.routes.utils.thread_handlers.UnifiedMessageStorageService') as mock_storage, \
             patch('netra_backend.app.routes.utils.thread_handlers.asyncio.create_task') as mock_create_task:
            
            mock_validation.return_value = MagicMock(id="thread-immediate")
            
            mock_storage_instance = AsyncMock()
            mock_storage.return_value = mock_storage_instance
            mock_storage_instance.save_to_redis.return_value = True
            
            # Call function 
            result = await handle_send_message_request(mock_db, "thread-immediate", mock_request, "user-immediate")
            
            end_time = time.time()
            execution_time_ms = (end_time - start_time) * 1000
            
            # TEST WILL FAIL: Current implementation is synchronous with PostgreSQL
            assert execution_time_ms < 100, f"Should return in <100ms, took {execution_time_ms}ms"
            
            # Should create background task for PostgreSQL
            mock_create_task.assert_called_once()
            
            # Should return message immediately after Redis cache
            assert result['id'] is not None
            assert result['thread_id'] == "thread-immediate"

    @pytest.mark.unit
    async def test_websocket_notification_sent_immediately(self):
        """FAILING TEST: Should send WebSocket notification immediately when message received."""
        # Current implementation has no WebSocket integration
        
        mock_db = AsyncMock() 
        mock_request = MagicMock()
        mock_request.message = "Test WebSocket notification"
        mock_request.metadata = {}
        
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation', new_callable=AsyncMock) as mock_validation, \
             patch('netra_backend.app.routes.utils.thread_handlers.WebSocketNotificationService') as mock_websocket:
            
            mock_validation.return_value = MagicMock(id="thread-ws")
            
            mock_websocket_instance = AsyncMock()
            mock_websocket.return_value = mock_websocket_instance
            
            # Call function
            await handle_send_message_request(mock_db, "thread-ws", mock_request, "user-ws")
            
            # TEST WILL FAIL: WebSocketNotificationService doesn't exist 
            mock_websocket_instance.send_message_received_notification.assert_called_once()
            
            # Verify notification payload
            call_args = mock_websocket_instance.send_message_received_notification.call_args[0]
            notification = call_args[0]
            
            assert notification['type'] == 'message_received'
            assert notification['thread_id'] == 'thread-ws'
            assert notification['user_id'] == 'user-ws'
```

## 🔗 Integration Tests (Real Database Required)

### 1. Three-Tier Message Flow Integration
**File**: `netra_backend/tests/integration/services/test_three_tier_message_flow_integration.py`

**Business Value**: Tests complete message flow through all three tiers

```python
"""
Test Three-Tier Message Flow Integration - DESIGNED TO FAIL

These tests verify complete message flow through Redis -> PostgreSQL -> ClickHouse.
They will FAIL until proper three-tier integration is implemented.

Requires: Real PostgreSQL and Redis (no mocks)
"""

import pytest
import asyncio
import time
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture

class TestThreeTierMessageFlowIntegration(BaseIntegrationTest):
    """Integration tests for three-tier message flow - FAILING TESTS."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_saved_to_all_three_tiers(self, real_services_fixture):
        """FAILING TEST: Message should eventually exist in all three storage tiers."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create test message
        message_data = {
            'id': 'integration-msg-123',
            'thread_id': 'integration-thread-123', 
            'role': 'user',
            'content': 'Integration test message for three tiers',
            'created_at': int(time.time())
        }
        
        # This will expose missing UnifiedMessageStorageService
        from netra_backend.app.services.unified_message_storage_service import UnifiedMessageStorageService
        
        # TEST WILL FAIL: Import will fail - service doesn't exist
        storage_service = UnifiedMessageStorageService(db, redis)
        await storage_service.save_message_with_three_tier_flow(message_data)
        
        # Verify immediate Redis storage
        redis_key = f"message:active:{message_data['id']}"
        cached_message = await redis.get(redis_key)
        assert cached_message is not None, "Message should be immediately available in Redis"
        
        # Wait for background PostgreSQL persistence
        await asyncio.sleep(1)
        
        # Verify PostgreSQL checkpoint
        pg_result = await db.execute("SELECT * FROM messages WHERE id = :id", {"id": message_data['id']})
        pg_message = pg_result.fetchone()
        assert pg_message is not None, "Message should be persisted to PostgreSQL"
        
        # For completed messages, should migrate to ClickHouse
        # (This will be implemented as part of the architecture fix)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_postgresql_consistency_check(self, real_services_fixture):
        """FAILING TEST: Data should be consistent between Redis and PostgreSQL after sync."""
        db = real_services_fixture["db"] 
        redis = real_services_fixture["redis"]
        
        message_id = "consistency-test-456"
        
        # This test will expose missing consistency validation
        from netra_backend.app.services.three_tier_consistency_checker import ThreeTierConsistencyChecker
        
        # TEST WILL FAIL: Import will fail - service doesn't exist
        consistency_checker = ThreeTierConsistencyChecker(redis, db)
        
        # Create message in Redis first
        redis_message = {
            'id': message_id,
            'content': 'Consistency test message',
            'version': 1
        }
        await redis.set(f"message:active:{message_id}", json.dumps(redis_message))
        
        # Simulate background sync to PostgreSQL
        await consistency_checker.sync_redis_to_postgresql(message_id)
        
        # Verify consistency
        consistency_report = await consistency_checker.validate_message_consistency(message_id)
        
        assert consistency_report['redis_exists'] is True
        assert consistency_report['postgresql_exists'] is True  
        assert consistency_report['data_matches'] is True
        assert consistency_report['version_synced'] is True

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_message_retrieval_performance_tiers(self, real_services_fixture):
        """FAILING TEST: Message retrieval should use performance-optimized tier selection."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"] 
        
        message_id = "perf-retrieval-789"
        
        # This will expose missing performance-optimized retrieval
        from netra_backend.app.services.unified_message_retrieval_service import UnifiedMessageRetrievalService
        
        # TEST WILL FAIL: Import will fail - service doesn't exist
        retrieval_service = UnifiedMessageRetrievalService(redis, db)
        
        # Test Redis hit (fastest path)
        start_time = time.time()
        message = await retrieval_service.get_message_optimized(message_id)
        redis_time = (time.time() - start_time) * 1000
        
        assert redis_time < 50, f"Redis retrieval should be <50ms, took {redis_time}ms"
        assert message is not None
        assert message['retrieval_source'] == 'redis'
        
        # Test PostgreSQL fallback when Redis miss
        await redis.delete(f"message:active:{message_id}")
        
        start_time = time.time()
        message = await retrieval_service.get_message_optimized(message_id)  
        postgresql_time = (time.time() - start_time) * 1000
        
        assert postgresql_time < 500, f"PostgreSQL retrieval should be <500ms, took {postgresql_time}ms"
        assert message is not None
        assert message['retrieval_source'] == 'postgresql'
```

### 2. Redis PostgreSQL Failover Integration
**File**: `netra_backend/tests/integration/services/test_redis_postgresql_failover_integration.py`

**Business Value**: Validates failover mechanisms between storage tiers

```python
"""
Test Redis PostgreSQL Failover Integration - DESIGNED TO FAIL

These tests verify failover behavior when Redis is unavailable.
They will FAIL until proper failover mechanisms are implemented.
"""

import pytest
import asyncio
from unittest.mock import patch
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture

class TestRedisPostgreSQLFailoverIntegration(BaseIntegrationTest):
    """Integration tests for Redis-PostgreSQL failover - FAILING TESTS."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_save_falls_back_to_postgresql_when_redis_fails(self, real_services_fixture):
        """FAILING TEST: Should gracefully fallback to PostgreSQL when Redis is unavailable."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # This will expose missing failover service
        from netra_backend.app.services.message_failover_service import MessageFailoverService
        
        # TEST WILL FAIL: Import will fail - service doesn't exist  
        failover_service = MessageFailoverService(redis, db)
        
        message_data = {
            'id': 'failover-msg-123',
            'thread_id': 'failover-thread-123',
            'content': 'Test failover to PostgreSQL',
            'role': 'user'
        }
        
        # Simulate Redis failure
        with patch.object(redis, 'set', side_effect=Exception("Redis connection lost")):
            
            result = await failover_service.save_message_with_failover(message_data)
            
            # Should succeed despite Redis failure
            assert result['success'] is True
            assert result['tier_used'] == 'postgresql'
            assert result['failover_reason'] == 'redis_unavailable'
            
            # Message should be in PostgreSQL
            pg_result = await db.execute("SELECT * FROM messages WHERE id = :id", {"id": message_data['id']})
            pg_message = pg_result.fetchone()
            assert pg_message is not None
            
            # Should not be in Redis
            redis_message = await redis.get(f"message:active:{message_data['id']}")
            assert redis_message is None

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_redis_recovery_backfill_from_postgresql(self, real_services_fixture):
        """FAILING TEST: Should backfill Redis from PostgreSQL when Redis recovers."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # This will expose missing recovery service
        from netra_backend.app.services.redis_recovery_service import RedisRecoveryService
        
        # TEST WILL FAIL: Import will fail - service doesn't exist
        recovery_service = RedisRecoveryService(redis, db)
        
        # Create message in PostgreSQL (simulating Redis was down)
        message_data = {
            'id': 'recovery-msg-456', 
            'thread_id': 'recovery-thread-456',
            'content': 'Recovery test message',
            'role': 'user'
        }
        
        await db.execute("""
            INSERT INTO messages (id, thread_id, content, role, created_at)
            VALUES (:id, :thread_id, :content, :role, NOW())
        """, message_data)
        await db.commit()
        
        # Redis is empty initially
        redis_message = await redis.get(f"message:active:{message_data['id']}")
        assert redis_message is None
        
        # Trigger recovery backfill
        recovery_result = await recovery_service.backfill_redis_from_postgresql(
            thread_id=message_data['thread_id']
        )
        
        # Should backfill to Redis
        assert recovery_result['messages_backfilled'] == 1
        assert recovery_result['success'] is True
        
        # Message should now be in Redis
        redis_message = await redis.get(f"message:active:{message_data['id']}")
        assert redis_message is not None
        
        redis_data = json.loads(redis_message)
        assert redis_data['id'] == message_data['id']
        assert redis_data['content'] == message_data['content']
```

## 🌐 End-to-End Tests (Full Stack + Authentication)

### 1. Three-Tier Message Performance E2E
**File**: `tests/e2e/test_three_tier_message_performance_e2e.py`

**Business Value**: Validates end-to-end performance meets business requirements

```python
"""
Test Three-Tier Message Performance E2E - DESIGNED TO FAIL

These tests verify end-to-end message performance meets business requirements.
They will FAIL until three-tier architecture delivers target performance.

CRITICAL: Uses real authentication as per CLAUDE.md requirements.
"""

import pytest
import time
import asyncio
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.websocket_helpers import WebSocketTestClient

class TestThreeTierMessagePerformanceE2E(BaseE2ETest):
    """E2E tests for three-tier message performance - FAILING TESTS."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_message_confirmation_under_100ms(self, real_services_fixture):
        """FAILING TEST: User should receive message confirmation in <100ms (Redis tier)."""
        # Current implementation takes ~500ms due to PostgreSQL blocking
        
        # CRITICAL: Use real authentication as required by CLAUDE.md
        auth_helper = E2EAuthHelper()
        auth_result = await auth_helper.create_authenticated_test_user()
        
        assert auth_result.success, "E2E test requires real authentication"
        user_token = auth_result.jwt_token
        
        backend_url = real_services_fixture["backend_url"]
        
        async with WebSocketTestClient(token=user_token, base_url=backend_url) as ws_client:
            # Send message and measure confirmation time
            start_time = time.time()
            
            await ws_client.send_json({
                "type": "send_message",
                "thread_id": "perf-thread-123",
                "message": "Performance test message - should be confirmed quickly",
                "metadata": {"test_type": "performance", "tier": "redis"}
            })
            
            # Wait for immediate confirmation (should come from Redis tier)
            confirmation = await ws_client.receive_json()
            confirmation_time = (time.time() - start_time) * 1000
            
            # TEST WILL FAIL: Current implementation waits for PostgreSQL commit
            assert confirmation_time < 100, f"Message confirmation took {confirmation_time}ms, should be <100ms"
            
            assert confirmation["type"] == "message_confirmed"
            assert confirmation["tier_used"] == "redis"
            assert "message_id" in confirmation
            
            # Background PostgreSQL persistence should happen separately
            await asyncio.sleep(1)  # Allow background persistence
            
            # Verify message was eventually persisted
            persisted_notification = await ws_client.receive_json()
            assert persisted_notification["type"] == "message_persisted"
            assert persisted_notification["tier_used"] == "postgresql"

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_message_retrieval_performance_by_tier(self, real_services_fixture):
        """FAILING TEST: Message retrieval performance should vary by storage tier."""
        
        auth_helper = E2EAuthHelper()
        auth_result = await auth_helper.create_authenticated_test_user()
        user_token = auth_result.jwt_token
        
        backend_url = real_services_fixture["backend_url"]
        
        # Create messages in different tiers
        test_messages = [
            {"id": "redis-msg-1", "tier": "redis", "content": "Active Redis message"},
            {"id": "pg-msg-1", "tier": "postgresql", "content": "PostgreSQL checkpoint message"},  
            {"id": "ch-msg-1", "tier": "clickhouse", "content": "ClickHouse archived message"}
        ]
        
        async with aiohttp.ClientSession() as session:
            # Create messages
            for msg in test_messages:
                await session.post(
                    f"{backend_url}/api/threads/test-thread/messages",
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={"message": msg["content"], "metadata": {"target_tier": msg["tier"]}}
                )
                
                # Allow tier placement
                await asyncio.sleep(0.1)
            
            # Test retrieval performance by tier
            performance_results = {}
            
            for msg in test_messages:
                start_time = time.time()
                
                response = await session.get(
                    f"{backend_url}/api/messages/{msg['id']}",
                    headers={"Authorization": f"Bearer {user_token}"}
                )
                
                retrieval_time = (time.time() - start_time) * 1000
                performance_results[msg["tier"]] = retrieval_time
                
                assert response.status == 200
                data = await response.json()
                assert data["id"] == msg["id"]
                
            # TEST WILL FAIL: All retrievals currently use PostgreSQL
            # Performance should differ by tier:
            assert performance_results["redis"] < 50, f"Redis retrieval should be <50ms, was {performance_results['redis']}ms"
            assert performance_results["postgresql"] < 500, f"PostgreSQL retrieval should be <500ms, was {performance_results['postgresql']}ms" 
            assert performance_results["clickhouse"] < 2000, f"ClickHouse retrieval should be <2000ms, was {performance_results['clickhouse']}ms"
            
            # Redis should be fastest
            assert performance_results["redis"] < performance_results["postgresql"]
            assert performance_results["postgresql"] < performance_results["clickhouse"]

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_concurrent_message_handling_with_three_tiers(self, real_services_fixture):
        """FAILING TEST: System should handle concurrent messages efficiently using all tiers."""
        
        auth_helper = E2EAuthHelper()
        auth_result = await auth_helper.create_authenticated_test_user()
        user_token = auth_result.jwt_token
        
        backend_url = real_services_fixture["backend_url"]
        
        # Send 10 concurrent messages
        concurrent_messages = 10
        send_tasks = []
        
        async def send_concurrent_message(session, msg_index):
            start_time = time.time()
            
            response = await session.post(
                f"{backend_url}/api/threads/concurrent-thread/messages",
                headers={"Authorization": f"Bearer {user_token}"},
                json={
                    "message": f"Concurrent message {msg_index}",
                    "metadata": {"concurrency_test": True, "index": msg_index}
                }
            )
            
            end_time = time.time()
            return {
                "index": msg_index,
                "response_time": (end_time - start_time) * 1000,
                "status": response.status,
                "data": await response.json() if response.status == 200 else None
            }
        
        async with aiohttp.ClientSession() as session:
            # Launch concurrent sends
            for i in range(concurrent_messages):
                task = asyncio.create_task(send_concurrent_message(session, i))
                send_tasks.append(task)
            
            # Wait for all sends to complete
            results = await asyncio.gather(*send_tasks)
            
            # Analyze performance
            response_times = [r["response_time"] for r in results]
            success_count = len([r for r in results if r["status"] == 200])
            
            # TEST WILL FAIL: Current PostgreSQL-only implementation will be slow and may have conflicts
            assert success_count == concurrent_messages, f"Only {success_count}/{concurrent_messages} messages succeeded"
            
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            # With three-tier architecture, should handle concurrency well
            assert avg_response_time < 200, f"Average response time {avg_response_time}ms should be <200ms with Redis tier"
            assert max_response_time < 500, f"Max response time {max_response_time}ms should be <500ms even under load"
            
            # All messages should have unique IDs (no conflicts)
            message_ids = {r["data"]["id"] for r in results if r["data"]}
            assert len(message_ids) == concurrent_messages, "Should have unique message IDs (no transaction conflicts)"
```

### 2. Message Failover Scenarios E2E
**File**: `tests/e2e/test_message_failover_scenarios_e2e.py`

**Business Value**: Ensures system resilience during infrastructure failures

```python
"""
Test Message Failover Scenarios E2E - DESIGNED TO FAIL

These tests verify system behavior during infrastructure failures.
They will FAIL until proper failover mechanisms are implemented.

CRITICAL: Uses real authentication and simulates realistic failure scenarios.
"""

import pytest
import asyncio
import time
from unittest.mock import patch
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

class TestMessageFailoverScenariosE2E(BaseE2ETest):
    """E2E tests for message failover scenarios - FAILING TESTS."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_redis_outage_transparent_failover(self, real_services_fixture):
        """FAILING TEST: Messages should still be saved/retrieved when Redis is down."""
        
        auth_helper = E2EAuthHelper()
        auth_result = await auth_helper.create_authenticated_test_user()
        user_token = auth_result.jwt_token
        
        backend_url = real_services_fixture["backend_url"]
        
        # First, send a message when Redis is working
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                f"{backend_url}/api/threads/failover-thread/messages",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"message": "Message before Redis outage", "metadata": {"scenario": "pre_outage"}}
            )
            
            assert response.status == 200
            pre_outage_msg = await response.json()
            
            # Simulate Redis outage
            with patch('netra_backend.app.redis_manager.redis_manager.get', side_effect=Exception("Redis is down")), \
                 patch('netra_backend.app.redis_manager.redis_manager.set', side_effect=Exception("Redis is down")):
                
                # Send message during Redis outage
                start_time = time.time()
                
                response = await session.post(
                    f"{backend_url}/api/threads/failover-thread/messages", 
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={"message": "Message during Redis outage", "metadata": {"scenario": "during_outage"}}
                )
                
                failover_time = (time.time() - start_time) * 1000
                
                # TEST WILL FAIL: Current implementation will probably fail completely when Redis is down
                assert response.status == 200, "Should succeed despite Redis outage"
                
                during_outage_msg = await response.json() 
                
                # Should take longer but still complete (using PostgreSQL directly)
                assert failover_time > 100, "Should take longer during Redis outage"
                assert failover_time < 2000, "But should still complete in reasonable time"
                
                # Response should indicate failover occurred
                assert during_outage_msg.get("tier_used") == "postgresql"
                assert during_outage_msg.get("failover_reason") == "redis_unavailable"
                
                # Try to retrieve messages during outage
                retrieve_response = await session.get(
                    f"{backend_url}/api/threads/failover-thread/messages",
                    headers={"Authorization": f"Bearer {user_token}"}
                )
                
                # TEST WILL FAIL: Retrieval might fail if system doesn't handle Redis outage
                assert retrieve_response.status == 200, "Should be able to retrieve messages despite Redis outage"
                
                messages_data = await retrieve_response.json()
                message_contents = [msg["content"] for msg in messages_data["messages"]]
                
                assert "Message before Redis outage" in message_contents
                assert "Message during Redis outage" in message_contents

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_postgresql_outage_graceful_degradation(self, real_services_fixture):
        """FAILING TEST: Should gracefully handle PostgreSQL outage with appropriate user feedback."""
        
        auth_helper = E2EAuthHelper()
        auth_result = await auth_helper.create_authenticated_test_user()  
        user_token = auth_result.jwt_token
        
        backend_url = real_services_fixture["backend_url"]
        
        # Simulate PostgreSQL outage
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_session', side_effect=Exception("PostgreSQL connection failed")):
            
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    f"{backend_url}/api/threads/pg-outage-thread/messages",
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={
                        "message": "Message during PostgreSQL outage", 
                        "metadata": {"scenario": "postgresql_outage"}
                    }
                )
                
                # TEST WILL FAIL: Current implementation will fail hard without graceful degradation
                # With proper three-tier architecture:
                if response.status == 200:
                    # Should succeed with Redis-only storage and warn about degraded mode
                    data = await response.json()
                    assert data.get("tier_used") == "redis"
                    assert data.get("warning") == "degraded_mode_postgresql_unavailable"
                    assert data.get("message_id") is not None
                    
                elif response.status == 503:
                    # Acceptable alternative: Service unavailable with clear message
                    error_data = await response.json()
                    assert "postgresql_unavailable" in error_data.get("detail", "").lower()
                    assert "temporary" in error_data.get("detail", "").lower()
                
                else:
                    # Unacceptable: Generic errors that don't explain the situation
                    pytest.fail(f"Should have either succeeded with degraded mode (200) or returned clear service unavailable (503), got {response.status}")

    @pytest.mark.e2e 
    @pytest.mark.real_services
    async def test_full_recovery_after_outage(self, real_services_fixture):
        """FAILING TEST: System should fully recover and backfill data after infrastructure outage."""
        
        auth_helper = E2EAuthHelper()
        auth_result = await auth_helper.create_authenticated_test_user()
        user_token = auth_result.jwt_token
        
        backend_url = real_services_fixture["backend_url"]
        
        # This test will expose missing recovery mechanisms
        async with aiohttp.ClientSession() as session:
            
            # Phase 1: Normal operation
            normal_response = await session.post(
                f"{backend_url}/api/threads/recovery-thread/messages",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"message": "Normal operation message", "metadata": {"phase": "normal"}}
            )
            assert normal_response.status == 200
            
            # Phase 2: Simulate outage and recovery
            with patch('netra_backend.app.redis_manager.redis_manager.get', side_effect=Exception("Redis outage")):
                
                # Send message during outage (should fallback to PostgreSQL)
                outage_response = await session.post(
                    f"{backend_url}/api/threads/recovery-thread/messages",
                    headers={"Authorization": f"Bearer {user_token}"},  
                    json={"message": "Message during Redis outage", "metadata": {"phase": "outage"}}
                )
                
                # Should still work (PostgreSQL fallback)
                if outage_response.status == 200:
                    outage_data = await outage_response.json()
                    outage_message_id = outage_data["id"]
            
            # Phase 3: After recovery, trigger backfill
            recovery_response = await session.post(
                f"{backend_url}/api/admin/recover-redis-cache",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"thread_id": "recovery-thread", "backfill_missing": True}
            )
            
            # TEST WILL FAIL: Recovery endpoint doesn't exist
            assert recovery_response.status == 200, "Should have recovery endpoint"
            
            recovery_data = await recovery_response.json()
            assert recovery_data["backfilled_messages"] >= 1
            assert recovery_data["recovery_success"] is True
            
            # Verify all messages are now accessible at high speed (from Redis)
            start_time = time.time()
            
            messages_response = await session.get(
                f"{backend_url}/api/threads/recovery-thread/messages",
                headers={"Authorization": f"Bearer {user_token}"}
            )
            
            retrieval_time = (time.time() - start_time) * 1000
            
            assert messages_response.status == 200
            messages_data = await messages_response.json()
            
            # Should be fast now (Redis serving)
            assert retrieval_time < 100, f"Post-recovery retrieval should be fast, took {retrieval_time}ms"
            
            # All messages should be present
            message_contents = [msg["content"] for msg in messages_data["messages"]]
            assert "Normal operation message" in message_contents
            assert "Message during Redis outage" in message_contents
```

## 🚀 Mission Critical Tests

### Mission Critical Three-Tier Storage Compliance
**File**: `tests/mission_critical/test_three_tier_storage_compliance.py`

**Business Value**: Validates compliance with business-critical performance requirements

```python
"""
Test Three-Tier Storage Compliance - DESIGNED TO FAIL

Mission critical tests that MUST pass for production deployment.
These tests validate compliance with business performance requirements.

NEVER SKIP THESE TESTS - They represent core business value delivery.
"""

import pytest
import time
import asyncio
from tests.mission_critical.base import MissionCriticalTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

class TestThreeTierStorageCompliance(MissionCriticalTest):
    """Mission critical compliance tests - FAILING TESTS."""
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_sub_100ms_message_confirmation_target(self):
        """MISSION CRITICAL: Message confirmation MUST be <100ms for business value."""
        # This is a hard requirement from the business for chat responsiveness
        
        auth_helper = E2EAuthHelper()
        auth_result = await auth_helper.create_authenticated_test_user()
        user_token = auth_result.jwt_token
        
        # Test with realistic message load
        confirmation_times = []
        
        async with aiohttp.ClientSession() as session:
            for i in range(10):  # Test multiple messages
                start_time = time.time()
                
                response = await session.post(
                    f"{self.backend_url}/api/threads/mission-critical-thread/messages",
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={
                        "message": f"Mission critical message {i}",
                        "metadata": {"business_critical": True}
                    }
                )
                
                confirmation_time = (time.time() - start_time) * 1000
                confirmation_times.append(confirmation_time)
                
                # TEST WILL FAIL: Current PostgreSQL-blocking implementation exceeds 100ms
                assert response.status == 200, f"Message {i} failed to send"
                
                # HARD BUSINESS REQUIREMENT: <100ms
                assert confirmation_time < 100, f"Message {i} confirmation took {confirmation_time}ms, MUST be <100ms"
        
        # Statistical analysis
        avg_time = sum(confirmation_times) / len(confirmation_times)
        max_time = max(confirmation_times)
        p95_time = sorted(confirmation_times)[int(0.95 * len(confirmation_times))]
        
        # Business SLA requirements
        assert avg_time < 50, f"Average confirmation time {avg_time}ms MUST be <50ms"
        assert max_time < 100, f"Maximum confirmation time {max_time}ms MUST be <100ms"  
        assert p95_time < 75, f"P95 confirmation time {p95_time}ms MUST be <75ms"

    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_zero_data_loss_guarantee(self):
        """MISSION CRITICAL: Zero data loss guarantee for Enterprise customers."""
        # $25K+ MRR customers require zero data loss guarantee
        
        auth_helper = E2EAuthHelper()
        auth_result = await auth_helper.create_authenticated_test_user(subscription="enterprise")
        user_token = auth_result.jwt_token
        
        # Send 100 messages rapidly to stress test
        sent_message_ids = []
        
        async with aiohttp.ClientSession() as session:
            send_tasks = []
            
            for i in range(100):
                task = asyncio.create_task(
                    session.post(
                        f"{self.backend_url}/api/threads/zero-loss-thread/messages",
                        headers={"Authorization": f"Bearer {user_token}"},
                        json={
                            "message": f"Enterprise message {i} - critical data",
                            "metadata": {"enterprise": True, "sequence": i}
                        }
                    )
                )
                send_tasks.append(task)
            
            responses = await asyncio.gather(*send_tasks, return_exceptions=True)
            
            # Collect successful message IDs
            for i, response in enumerate(responses):
                if not isinstance(response, Exception) and response.status == 200:
                    data = await response.json()
                    sent_message_ids.append(data["id"])
                else:
                    pytest.fail(f"Message {i} failed to send - violates zero data loss guarantee")
            
            # Verify ALL messages were persisted
            await asyncio.sleep(5)  # Allow background persistence
            
            retrieve_response = await session.get(
                f"{self.backend_url}/api/threads/zero-loss-thread/messages?limit=100",
                headers={"Authorization": f"Bearer {user_token}"}
            )
            
            assert retrieve_response.status == 200
            retrieved_data = await retrieve_response.json()
            retrieved_ids = {msg["id"] for msg in retrieved_data["messages"]}
            
            # ZERO DATA LOSS: All sent messages must be retrievable
            missing_messages = set(sent_message_ids) - retrieved_ids
            assert len(missing_messages) == 0, f"ZERO DATA LOSS VIOLATED: {len(missing_messages)} messages lost: {missing_messages}"
            
            # Verify message integrity
            for msg in retrieved_data["messages"]:
                if "Enterprise message" in msg["content"]:
                    assert msg["metadata"]["enterprise"] is True
                    assert "sequence" in msg["metadata"]

    @pytest.mark.mission_critical  
    @pytest.mark.no_skip
    async def test_disaster_recovery_rto_5_minutes(self):
        """MISSION CRITICAL: Recovery Time Objective (RTO) must be <5 minutes."""
        # Enterprise requirement for disaster recovery
        
        # This test will expose missing disaster recovery mechanisms
        auth_helper = E2EAuthHelper()
        auth_result = await auth_helper.create_authenticated_test_user(subscription="enterprise")
        user_token = auth_result.jwt_token
        
        # Create baseline data
        async with aiohttp.ClientSession() as session:
            baseline_response = await session.post(
                f"{self.backend_url}/api/threads/disaster-recovery-thread/messages",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"message": "Baseline message before disaster", "metadata": {"pre_disaster": True}}
            )
            assert baseline_response.status == 200
            baseline_data = await baseline_response.json()
            baseline_message_id = baseline_data["id"]
            
            # Allow data to propagate to all tiers
            await asyncio.sleep(2)
            
            # Simulate disaster scenario (both Redis and PostgreSQL primary fail)
            disaster_start_time = time.time()
            
            # TEST WILL FAIL: No disaster recovery service exists
            disaster_response = await session.post(
                f"{self.backend_url}/api/admin/simulate-disaster",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"scenario": "redis_postgresql_failure", "duration_seconds": 60}
            )
            
            assert disaster_response.status == 200, "Should be able to simulate disaster"
            
            # Trigger recovery
            recovery_response = await session.post(
                f"{self.backend_url}/api/admin/initiate-disaster-recovery",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"recovery_tier": "clickhouse", "target_rto_seconds": 300}
            )
            
            assert recovery_response.status == 200, "Should be able to initiate disaster recovery"
            
            # Wait for recovery completion
            recovery_complete = False
            max_wait_time = 300  # 5 minutes max
            check_interval = 10   # Check every 10 seconds
            
            for attempt in range(max_wait_time // check_interval):
                status_response = await session.get(
                    f"{self.backend_url}/api/admin/disaster-recovery-status",
                    headers={"Authorization": f"Bearer {user_token}"}
                )
                
                if status_response.status == 200:
                    status_data = await status_response.json()
                    if status_data.get("recovery_complete") is True:
                        recovery_complete = True
                        recovery_time = time.time() - disaster_start_time
                        break
                
                await asyncio.sleep(check_interval)
            
            # MISSION CRITICAL: RTO <5 minutes
            assert recovery_complete, "Disaster recovery did not complete within 5 minutes"
            assert recovery_time < 300, f"Recovery took {recovery_time}s, MUST be <300s (5 minutes)"
            
            # Verify data accessibility after recovery
            verify_response = await session.get(
                f"{self.backend_url}/api/messages/{baseline_message_id}",
                headers={"Authorization": f"Bearer {user_token}"}
            )
            
            assert verify_response.status == 200, "Baseline message should be accessible after disaster recovery"
            
            recovered_data = await verify_response.json()
            assert recovered_data["id"] == baseline_message_id
            assert recovered_data["content"] == "Baseline message before disaster"

    @pytest.mark.mission_critical
    @pytest.mark.no_skip  
    async def test_performance_degradation_monitoring(self):
        """MISSION CRITICAL: System must detect and alert on performance degradation."""
        
        # This will expose missing performance monitoring
        auth_helper = E2EAuthHelper() 
        auth_result = await auth_helper.create_authenticated_test_user()
        user_token = auth_result.jwt_token
        
        baseline_times = []
        degraded_times = []
        
        async with aiohttp.ClientSession() as session:
            
            # Establish baseline performance (normal operation)
            for i in range(10):
                start_time = time.time()
                
                response = await session.post(
                    f"{self.backend_url}/api/threads/monitoring-thread/messages",
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={"message": f"Baseline message {i}", "metadata": {"phase": "baseline"}}
                )
                
                response_time = (time.time() - start_time) * 1000
                baseline_times.append(response_time)
                
                assert response.status == 200
                await asyncio.sleep(0.1)
            
            baseline_avg = sum(baseline_times) / len(baseline_times)
            
            # Simulate degraded performance (overload Redis with large data)
            # TEST WILL FAIL: No performance monitoring service exists
            degrade_response = await session.post(
                f"{self.backend_url}/api/admin/simulate-performance-degradation",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"scenario": "redis_overload", "intensity": "moderate"}
            )
            
            assert degrade_response.status == 200, "Should be able to simulate performance degradation"
            
            # Measure performance during degradation
            for i in range(10):
                start_time = time.time()
                
                response = await session.post(
                    f"{self.backend_url}/api/threads/monitoring-thread/messages",
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={"message": f"Degraded message {i}", "metadata": {"phase": "degraded"}}
                )
                
                response_time = (time.time() - start_time) * 1000
                degraded_times.append(response_time)
                
                assert response.status == 200
                await asyncio.sleep(0.1)
            
            degraded_avg = sum(degraded_times) / len(degraded_times)
            
            # Check monitoring alerts
            alerts_response = await session.get(
                f"{self.backend_url}/api/admin/performance-alerts",
                headers={"Authorization": f"Bearer {user_token}"}
            )
            
            assert alerts_response.status == 200
            alerts_data = await alerts_response.json()
            
            # Should detect degradation
            assert len(alerts_data["active_alerts"]) > 0, "Should detect performance degradation"
            
            degradation_alert = next((alert for alert in alerts_data["active_alerts"] 
                                    if alert["type"] == "performance_degradation"), None)
            assert degradation_alert is not None, "Should have performance degradation alert"
            
            # Verify degradation metrics
            assert degradation_alert["baseline_avg_ms"] == pytest.approx(baseline_avg, rel=0.1)
            assert degradation_alert["current_avg_ms"] == pytest.approx(degraded_avg, rel=0.1)
            assert degradation_alert["degradation_percent"] > 0
```

## 🔐 Authentication Requirements

All E2E tests MUST use real authentication as per CLAUDE.md requirements:

```python
# CRITICAL: Every E2E test must use this pattern
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

async def test_some_e2e_scenario():
    # REQUIRED: Real authentication for ALL E2E tests  
    auth_helper = E2EAuthHelper()
    auth_result = await auth_helper.create_authenticated_test_user()
    
    assert auth_result.success, "E2E test requires real authentication"
    user_token = auth_result.jwt_token
    
    # Use user_token in all API calls and WebSocket connections
    headers = {"Authorization": f"Bearer {user_token}"}
    # ... rest of test
```

**NEVER SKIP AUTH**: The only exception is tests that specifically validate the auth system itself.

## 📊 Test Difficulty Levels & Execution Approach

### **EASY** Tests (Unit Tests)
- **Execution Time**: 2-5 seconds each
- **Dependencies**: None (use mocks for external services)  
- **Difficulty**: ⭐⭐ (Straightforward mocking and assertions)
- **Purpose**: Expose architectural gaps through failed assertions

### **MEDIUM** Tests (Integration Tests)
- **Execution Time**: 10-30 seconds each
- **Dependencies**: Real PostgreSQL + Redis (Docker managed)
- **Difficulty**: ⭐⭐⭐ (Requires real service setup)
- **Purpose**: Validate cross-service interactions and performance

### **HARD** Tests (E2E Tests)
- **Execution Time**: 30-60 seconds each
- **Dependencies**: Full Docker stack + Real auth + WebSocket
- **Difficulty**: ⭐⭐⭐⭐ (Complex setup with multiple services)
- **Purpose**: End-to-end business value validation

### **EXPERT** Tests (Mission Critical)
- **Execution Time**: 60-300 seconds each  
- **Dependencies**: Production-like environment + Monitoring
- **Difficulty**: ⭐⭐⭐⭐⭐ (Enterprise scenarios with disaster simulation)
- **Purpose**: Business-critical compliance validation

## 🚀 Execution Commands

```bash
# Run unit tests (FAILING - expose architectural gaps)
python tests/unified_test_runner.py --category unit --pattern "*three_tier*" --fast-fail

# Run integration tests (FAILING - need real Redis integration)
python tests/unified_test_runner.py --category integration --pattern "*three_tier*" --real-services

# Run E2E tests (FAILING - missing performance architecture)  
python tests/unified_test_runner.py --category e2e --pattern "*three_tier*" --real-services --real-llm

# Run mission critical tests (FAILING - business requirements not met)
python tests/mission_critical/test_three_tier_storage_compliance.py

# Run ALL three-tier tests to see complete failure picture
python tests/unified_test_runner.py --pattern "*three_tier*" --real-services --coverage
```

## 📈 Expected Test Results (Before Architecture Fix)

### ❌ UNIT TESTS: 15+ Failures
- `StateCacheManager` using in-memory dict instead of Redis
- No `UnifiedMessageStorageService` imports
- No three-tier failover logic
- Missing WebSocket notification services

### ❌ INTEGRATION TESTS: 10+ Failures  
- No Redis-first message storage
- No cross-tier consistency validation
- Missing failover mechanisms
- No performance tier optimization

### ❌ E2E TESTS: 8+ Failures
- Message confirmation >500ms (target <100ms)
- No graceful degradation during outages
- Missing disaster recovery endpoints
- No performance monitoring

### ❌ MISSION CRITICAL: 4/4 Failures
- Sub-100ms requirement violated
- Zero data loss not guaranteed
- RTO >5 minutes not possible
- No performance degradation monitoring

## 🎯 Success Criteria (After Architecture Implementation)

### ✅ ALL TESTS PASS when:
1. `StateCacheManager` uses Redis instead of in-memory dict
2. `handle_send_message_request()` implements three-tier flow
3. Message confirmation <100ms via Redis tier  
4. Background PostgreSQL persistence with WebSocket notifications
5. Failover chain: Redis → PostgreSQL → ClickHouse
6. Disaster recovery with <5 minute RTO
7. Performance monitoring and alerting

## 📝 SSOT Integration Points

### Test Framework Usage:
- `test_framework/ssot/e2e_auth_helper.py` - Authentication 
- `test_framework/real_services_test_fixtures.py` - Real services
- `test_framework/base_integration_test.py` - Integration base
- `test_framework/websocket_helpers.py` - WebSocket testing

### Configuration:
- Uses `shared/isolated_environment.py` for environment access
- Follows `TEST_PORTS` constants from test framework
- Alpine Docker containers for 50% faster execution

### Business Value Alignment:
Every test includes Business Value Justification (BVJ) explaining:
- **Segment**: Which customer tiers benefit
- **Business Goal**: Strategic objective supported  
- **Value Impact**: How it improves customer operations
- **Strategic Impact**: Revenue/retention implications

## 🚨 Critical Implementation Notes

1. **ALL TESTS DESIGNED TO FAIL**: These tests expose current architectural gaps
2. **NO MOCKS IN E2E**: Real services only, following CLAUDE.md principles
3. **MANDATORY AUTH**: All E2E tests use real JWT authentication
4. **PERFORMANCE FOCUSED**: Tests validate actual business performance requirements
5. **ZERO DATA LOSS**: Enterprise customers require guarantees
6. **DISASTER RECOVERY**: RTO <5 minutes is business requirement

This comprehensive test suite will clearly demonstrate the need for three-tier storage architecture and provide the validation framework for the implementation.

---

**Next Steps**: 
1. Create failing test files as documented above
2. Run tests to confirm they expose architectural gaps
3. Implement three-tier storage architecture to make tests pass
4. Validate business performance requirements are met

**Estimated Effort**: 
- Test Creation: 4-6 hours
- Architecture Implementation: 12-16 hours  
- Validation & Refinement: 2-4 hours
- **Total**: ~20 hours for complete three-tier architecture with validation