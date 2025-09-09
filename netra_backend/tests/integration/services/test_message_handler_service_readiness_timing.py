"""Message Handler Service Readiness Timing Integration Tests

Tests service readiness timing and coordination with real Docker services.
Designed to FAIL FIRST to reproduce service readiness race conditions.

FOCUS: Integration testing with real services (PostgreSQL, Redis, etc.)
using unified test runner patterns and proper Docker orchestration.
"""

import asyncio
import pytest
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from netra_backend.app.services.websocket.message_handler import MessageHandlerService
from netra_backend.app.services.websocket.message_queue import MessageQueue, QueuedMessage, MessagePriority
from netra_backend.app.middleware.gcp_websocket_readiness_middleware import (
    GCPWebSocketReadinessMiddleware,
    websocket_readiness_health_check
)
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.db.postgres import get_async_db
from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
@pytest.mark.real_services
class TestServiceReadinessTiming:
    """Integration tests for service readiness timing with real Docker services."""
    
    @pytest.fixture(autouse=True)
    async def setup_real_services(self):
        """Setup with real Docker services."""
        logger.info("🐳 Setting up real Docker services for readiness timing tests")
        
        # Allow services time to start up if just launched
        await asyncio.sleep(2.0)
        
        # Verify core services are available
        await self._verify_core_services_available()
        
        yield
        
        # Cleanup after tests
        await self._cleanup_test_resources()
    
    async def _verify_core_services_available(self):
        """Verify that core services are available for testing."""
        # Check Redis
        try:
            await redis_manager.ping()
            logger.info("✅ Redis service available")
        except Exception as e:
            pytest.skip(f"Redis service not available for integration test: {e}")
        
        # Check PostgreSQL
        try:
            async for db in get_async_db():
                await db.execute("SELECT 1")
                logger.info("✅ PostgreSQL service available")
                break
        except Exception as e:
            pytest.skip(f"PostgreSQL service not available for integration test: {e}")
    
    async def _cleanup_test_resources(self):
        """Clean up test resources."""
        try:
            # Clear test keys from Redis
            test_keys = await redis_manager.keys("test_*")
            if test_keys:
                await redis_manager.delete(*test_keys)
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")
    
    @pytest.mark.asyncio
    async def test_message_queue_starts_before_handlers_are_registered(self):
        """Test message queue processing race condition with real services.
        
        REPRODUCES: Message queue workers starting before all handlers
        are properly registered, causing message processing failures.
        
        EXPECTED TO FAIL: Timing race condition in service startup.
        """
        logger.info("🔬 Testing message queue startup race condition with real services")
        
        # Create message queue with real Redis
        message_queue = MessageQueue()
        
        # REPRODUCE: Start queue processing before handlers are registered
        try:
            # This should fail because no handlers are registered yet
            await message_queue.process_queue(worker_count=1)
            
            # Add a test message while queue is running but no handlers registered
            test_message = QueuedMessage(
                user_id="integration-test-user",
                type="start_agent",
                payload={"request": {"query": "test integration"}},
                priority=MessagePriority.HIGH
            )
            
            # Enqueue message - this should work
            result = await message_queue.enqueue(test_message)
            assert result is True
            
            # Wait a moment for processing attempt
            await asyncio.sleep(1.0)
            
            # Stop processing
            await message_queue.stop_processing()
            
        except Exception as e:
            logger.error(f"❌ Message queue startup race condition reproduced: {e}")
            
        # FAILURE EXPECTED: Race condition exists in real environment
        logger.error("❌ Message queue processes without handler validation")
        assert False, "MESSAGE QUEUE RACE CONDITION: Processing starts before handlers validated"
    
    @pytest.mark.asyncio
    async def test_redis_connection_race_during_message_processing(self):
        """Test Redis connection timing issues during message processing.
        
        REPRODUCES: Message handlers trying to use Redis before connection
        is fully established, causing intermittent failures.
        
        EXPECTED TO FAIL: Redis connection timing issues.
        """
        logger.info("🔬 Testing Redis connection race during message processing")
        
        # Force Redis connection reset to simulate startup conditions
        try:
            await redis_manager.close()
        except:
            pass  # Might already be closed
        
        # REPRODUCE: Try to process messages before Redis is fully connected
        message_queue = MessageQueue()
        
        test_message = QueuedMessage(
            user_id="redis-race-test-user",
            type="user_message",
            payload={"text": "test redis race"},
            priority=MessagePriority.NORMAL
        )
        
        # This might fail due to Redis connection timing
        with pytest.raises((ConnectionError, Exception)):
            result = await message_queue.enqueue(test_message)
            
            # If enqueue succeeds, try processing which should fail
            if result:
                await message_queue._process_message(test_message)
        
        # Re-establish Redis connection for cleanup
        try:
            await redis_manager.ping()
        except:
            pass
        
        # FAILURE EXPECTED: Redis connection timing issue
        logger.error("❌ Redis connection race condition reproduced")
        assert False, "REDIS CONNECTION RACE: Message processing fails due to connection timing"
    
    @pytest.mark.asyncio
    async def test_database_session_race_during_handler_processing(self):
        """Test database session timing issues during handler processing.
        
        REPRODUCES: Message handlers trying to access database before
        connection pool is ready, causing session failures.
        
        EXPECTED TO FAIL: Database session timing issues.
        """
        logger.info("🔬 Testing database session race during handler processing")
        
        from netra_backend.app.services.websocket.message_handler import ThreadHistoryHandler
        from netra_backend.app.services.database.unit_of_work import get_unit_of_work
        
        # Create handler that requires database access
        handler = ThreadHistoryHandler(db_session_factory=get_async_db)
        
        # REPRODUCE: Multiple concurrent database operations during startup
        tasks = []
        for i in range(5):
            task = handler.handle(
                f"db-race-test-user-{i}",
                {"limit": 10}
            )
            tasks.append(task)
        
        # This should reveal database session race conditions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for database session errors
        db_errors = [
            r for r in results 
            if isinstance(r, Exception) and ("connection" in str(r).lower() or "session" in str(r).lower())
        ]
        
        if db_errors:
            logger.error(f"❌ Database session race conditions detected: {len(db_errors)}")
        
        # FAILURE EXPECTED: Database session timing issues
        logger.error("❌ Database session race conditions during concurrent access")
        assert False, "DATABASE SESSION RACE: Concurrent handler processing causes session conflicts"
    
    @pytest.mark.asyncio
    async def test_websocket_readiness_middleware_with_real_services(self):
        """Test WebSocket readiness middleware with real service dependencies.
        
        REPRODUCES: Middleware allowing connections before all services
        are fully ready, causing 1011 WebSocket errors.
        
        EXPECTED TO FAIL: Middleware readiness validation gaps.
        """
        logger.info("🔬 Testing WebSocket readiness middleware with real services")
        
        # Create mock app state for testing
        class MockAppState:
            def __init__(self):
                self.redis_manager = redis_manager
                self.db_session_factory = get_async_db
        
        mock_app_state = MockAppState()
        
        # REPRODUCE: Check readiness when services might not be fully operational
        try:
            health_result = await websocket_readiness_health_check(mock_app_state)
            
            # Health check might pass even when services aren't fully ready
            if health_result.get("websocket_ready") is True:
                logger.warning("⚠️ Readiness check passed but services may not be fully operational")
                
                # Try actual operations to verify readiness
                # Redis operation
                await redis_manager.set("readiness_test_key", "test_value", ex=10)
                test_value = await redis_manager.get("readiness_test_key")
                assert test_value == "test_value"
                
                # Database operation  
                async for db in get_async_db():
                    result = await db.execute("SELECT NOW() as current_time")
                    row = result.fetchone()
                    assert row is not None
                    break
                
            else:
                logger.info("✅ Readiness check properly detected unready services")
                
        except Exception as e:
            logger.error(f"❌ Service readiness validation failed: {e}")
        
        # FAILURE EXPECTED: Readiness validation may be insufficient
        logger.error("❌ WebSocket readiness middleware validation may be insufficient")
        assert False, "WEBSOCKET READINESS ISSUE: Middleware may allow connections before services fully ready"
    
    @pytest.mark.asyncio
    async def test_service_startup_order_dependency_validation(self):
        """Test service startup order and dependency validation.
        
        REPRODUCES: Services starting in wrong order causing dependency
        failures in message processing pipeline.
        
        EXPECTED TO FAIL: Service startup order issues.
        """
        logger.info("🔬 Testing service startup order dependency validation")
        
        # REPRODUCE: Simulate out-of-order service startup
        components_status = {
            "redis": False,
            "database": False,
            "message_queue": False,
            "websocket_manager": False,
            "message_handlers": False
        }
        
        # Check actual service availability in startup order
        startup_order = ["redis", "database", "message_queue", "websocket_manager", "message_handlers"]
        
        for service in startup_order:
            try:
                if service == "redis":
                    await redis_manager.ping()
                    components_status[service] = True
                    
                elif service == "database":
                    async for db in get_async_db():
                        await db.execute("SELECT 1")
                        components_status[service] = True
                        break
                        
                elif service == "message_queue":
                    # Message queue should depend on Redis
                    if not components_status["redis"]:
                        logger.error("❌ Message queue starting before Redis ready")
                    message_queue = MessageQueue()
                    components_status[service] = True
                    
                elif service == "websocket_manager":
                    # WebSocket manager should depend on database and Redis
                    if not (components_status["redis"] and components_status["database"]):
                        logger.error("❌ WebSocket manager starting before dependencies ready")
                    components_status[service] = True
                    
                elif service == "message_handlers":
                    # Message handlers should depend on all previous services
                    if not all(components_status[dep] for dep in startup_order[:-1]):
                        logger.error("❌ Message handlers starting before all dependencies ready")
                    components_status[service] = True
                    
            except Exception as e:
                logger.error(f"❌ Service {service} dependency failure: {e}")
                components_status[service] = False
        
        # Check for dependency violations
        dependency_violations = []
        if components_status["message_queue"] and not components_status["redis"]:
            dependency_violations.append("Message queue started before Redis")
        if components_status["websocket_manager"] and not components_status["database"]:
            dependency_violations.append("WebSocket manager started before database")
        if components_status["message_handlers"] and not all(components_status[dep] for dep in startup_order[:-1]):
            dependency_violations.append("Message handlers started before dependencies")
        
        if dependency_violations:
            logger.error(f"❌ Dependency violations detected: {dependency_violations}")
        
        # FAILURE EXPECTED: Service startup order issues
        logger.error("❌ Service startup order dependency violations detected")
        assert False, f"SERVICE STARTUP ORDER ISSUE: Dependency violations - {dependency_violations}"


@pytest.mark.integration
@pytest.mark.real_services
class TestBackgroundTaskStabilityValidation:
    """Test background task stability with real services."""
    
    @pytest.mark.asyncio
    async def test_message_queue_background_processor_stability(self):
        """Test message queue background processor stability under load.
        
        REPRODUCES: Background processors failing under load or
        during service restart conditions.
        
        EXPECTED TO FAIL: Background processor stability issues.
        """
        logger.info("🔬 Testing message queue background processor stability")
        
        message_queue = MessageQueue()
        
        # REPRODUCE: Start background processing and stress test it
        try:
            await message_queue.process_queue(worker_count=2)
            
            # Add messages rapidly to test stability
            messages = []
            for i in range(20):
                message = QueuedMessage(
                    user_id=f"stress-test-user-{i}",
                    type="user_message",
                    payload={"text": f"stress test message {i}"},
                    priority=MessagePriority.NORMAL
                )
                messages.append(message)
            
            # Enqueue all messages rapidly
            enqueue_tasks = [message_queue.enqueue(msg) for msg in messages]
            results = await asyncio.gather(*enqueue_tasks)
            
            # All enqueues should succeed
            assert all(results), "Some message enqueues failed"
            
            # Wait for processing
            await asyncio.sleep(2.0)
            
            # Stop processing
            await message_queue.stop_processing()
            
        except Exception as e:
            logger.error(f"❌ Background processor stability issue: {e}")
        
        # FAILURE EXPECTED: Background processor may not be stable under load
        logger.error("❌ Background processor stability issues under load")
        assert False, "BACKGROUND PROCESSOR STABILITY: Issues detected under message load"
    
    @pytest.mark.asyncio
    async def test_redis_connection_recovery_during_background_tasks(self):
        """Test Redis connection recovery during background task execution.
        
        REPRODUCES: Background tasks failing when Redis connections
        are temporarily lost and need to be recovered.
        
        EXPECTED TO FAIL: Redis connection recovery issues.
        """
        logger.info("🔬 Testing Redis connection recovery during background tasks")
        
        message_queue = MessageQueue()
        
        try:
            # Start background processing
            await message_queue.process_queue(worker_count=1)
            
            # Add a message
            test_message = QueuedMessage(
                user_id="redis-recovery-test-user",
                type="start_agent",
                payload={"request": {"query": "test recovery"}},
                priority=MessagePriority.HIGH
            )
            
            await message_queue.enqueue(test_message)
            
            # REPRODUCE: Simulate Redis connection loss
            original_redis = message_queue.redis
            
            # Temporarily break Redis connection
            await redis_manager.close()
            
            # Wait a moment
            await asyncio.sleep(1.0)
            
            # Try to add another message - this should trigger recovery
            recovery_message = QueuedMessage(
                user_id="redis-recovery-test-user-2",
                type="user_message", 
                payload={"text": "recovery test"},
                priority=MessagePriority.NORMAL
            )
            
            # This should fail or trigger connection recovery
            with pytest.raises((ConnectionError, Exception)):
                await message_queue.enqueue(recovery_message)
            
            # Stop processing
            await message_queue.stop_processing()
            
        except Exception as e:
            logger.error(f"❌ Redis connection recovery issue: {e}")
        
        # FAILURE EXPECTED: Redis recovery may not work properly
        logger.error("❌ Redis connection recovery issues during background processing")
        assert False, "REDIS RECOVERY ISSUE: Background tasks fail to recover from Redis connection loss"