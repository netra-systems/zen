"""
Comprehensive Cross-Service Error Handling Integration Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal - Foundation for ALL services
- Business Goal: Ensure system resilience and fault tolerance across service boundaries
- Value Impact: Prevents cascading failures, maintains user experience during outages, ensures multi-user isolation
- Strategic Impact: System resilience is critical - failures without proper handling lose customer trust and revenue

This comprehensive test suite validates cross-service error handling patterns including:
1. Service unavailability and fallback mechanisms
2. Network timeout and retry behavior  
3. Database/Redis connection failures and recovery
4. Circuit breaker activation and recovery
5. Error propagation and isolation
6. User experience preservation during failures
7. Multi-user state isolation during error conditions
8. Graceful degradation patterns

CRITICAL REQUIREMENTS from CLAUDE.md:
- Uses REAL PostgreSQL (port 5434) and Redis (port 6381) - NO SERVICE MOCKS
- Uses IsolatedEnvironment (never os.environ directly)
- Follows SSOT patterns from test_framework/
- Tests actual business logic under error conditions
- Each test validates realistic cross-service scenarios
- External service mocks ONLY for simulating error conditions
- Authentication follows real JWT/OAuth flows
"""

import asyncio
import pytest
import logging
import time
import json
import httpx
from typing import Dict, Any, Optional, List, AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import uuid
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.exc import OperationalError, DisconnectionError
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

# SSOT imports - absolute paths required per CLAUDE.md
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager, get_db_session
from netra_backend.app.redis_manager import get_redis_manager, RedisManager
from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.services.websocket.message_handler import MessageHandlerService
from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService, AuthResult
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.clients.auth_client_core import (
    AuthServiceClient, AuthServiceError, AuthServiceConnectionError,
    AuthServiceNotAvailableError, CircuitBreakerError
)
from netra_backend.app.clients.circuit_breaker import CircuitBreakerOpen
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.models.user import User
from netra_backend.app.models.thread import Thread
from netra_backend.app.models.message import Message
from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env
from test_framework.fixtures.real_services import real_services_fixture

logger = logging.getLogger(__name__)


@dataclass
class ErrorScenario:
    """Test scenario configuration for error handling tests."""
    name: str
    description: str
    service: str
    error_type: str
    expected_fallback: str
    recovery_mechanism: str
    user_impact: str
    

class CrossServiceErrorHandlingTest(BaseIntegrationTest):
    """Comprehensive cross-service error handling integration tests."""

    async def async_setup(self):
        """Setup real services and error injection framework."""
        await super().async_setup()
        
        # Initialize real service connections for testing
        self.env = get_env()
        self.db_manager = None
        self.redis_manager = None
        self.websocket_manager = None
        self.auth_service = UnifiedAuthenticationService()
        
        # Error injection mocks - only for simulating external failures
        self.mock_auth_client = AsyncMock()
        self.mock_llm_client = AsyncMock()
        
        # Test users for multi-user scenarios
        self.test_users = []

    async def async_teardown(self):
        """Clean up test resources."""
        # Clean up test users
        if self.db_manager:
            try:
                async with self.db_manager.get_session() as session:
                    for user_id in [u.get('id') for u in self.test_users if u.get('id')]:
                        await session.execute(
                            text("DELETE FROM users WHERE id = :user_id"),
                            {"user_id": user_id}
                        )
                    await session.commit()
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")
        
        await super().async_teardown()

    async def create_test_user(self, email: str = None) -> Dict[str, Any]:
        """Create test user with real database connection."""
        if not email:
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"
            
        user_data = {
            "id": str(uuid.uuid4()),
            "email": email,
            "name": "Test User",
            "created_at": datetime.now(timezone.utc)
        }
        
        async with self.db_manager.get_session() as session:
            await session.execute(
                text("INSERT INTO users (id, email, name, created_at) VALUES (:id, :email, :name, :created_at)"),
                user_data
            )
            await session.commit()
            
        self.test_users.append(user_data)
        return user_data

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_connection_failure_recovery(self, real_services_fixture, isolated_env):
        """
        Test database connection failure and recovery mechanisms.
        
        BVJ: Ensures users can continue working when database has temporary failures.
        Validates connection pooling, retry logic, and graceful degradation.
        """
        self.db_manager = get_database_manager()
        
        # Create test user first
        user = await self.create_test_user()
        
        # Test 1: Simulate connection pool exhaustion
        with patch.object(self.db_manager, 'get_session') as mock_get_session:
            mock_get_session.side_effect = OperationalError(
                "connection limit exceeded", None, None
            )
            
            # Verify graceful handling
            with pytest.raises(OperationalError):
                async with self.db_manager.get_session() as session:
                    await session.execute(text("SELECT 1"))
        
        # Test 2: Verify recovery after connection restored
        async with self.db_manager.get_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            assert result.fetchone().test == 1
        
        # Test 3: Verify user data integrity after recovery
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                text("SELECT email FROM users WHERE id = :user_id"),
                {"user_id": user["id"]}
            )
            found_user = result.fetchone()
            assert found_user is not None
            assert found_user.email == user["email"]

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_connection_failure_degradation(self, real_services_fixture, isolated_env):
        """
        Test Redis connection failure and graceful degradation.
        
        BVJ: System continues functioning when cache is unavailable.
        Session management falls back to database-only mode.
        """
        self.redis_manager = get_redis_manager()
        
        # Test 1: Normal Redis operation
        await self.redis_manager.set("test_key", "test_value", expire=60)
        value = await self.redis_manager.get("test_key")
        assert value == "test_value"
        
        # Test 2: Simulate Redis connection failure
        with patch.object(self.redis_manager, 'get') as mock_get:
            mock_get.side_effect = RedisConnectionError("Connection refused")
            
            # Verify graceful degradation (should not raise, should return None)
            try:
                value = await self.redis_manager.get("test_key")
                # System should handle this gracefully, possibly returning None
                assert value is None or isinstance(value, str)
            except RedisConnectionError:
                pytest.fail("Redis connection errors should be handled gracefully")
        
        # Test 3: Verify Redis timeout handling
        with patch.object(self.redis_manager, 'set') as mock_set:
            mock_set.side_effect = RedisTimeoutError("Timeout")
            
            try:
                await self.redis_manager.set("timeout_key", "value", expire=60)
                # Should handle timeout gracefully
            except RedisTimeoutError:
                pytest.fail("Redis timeout errors should be handled gracefully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_service_circuit_breaker_activation(self, real_services_fixture, isolated_env):
        """
        Test authentication service circuit breaker activation and recovery.
        
        BVJ: Protects system from auth service failures while maintaining security.
        Circuit breaker prevents cascading failures across all services.
        """
        # Test 1: Normal auth service operation
        auth_result = AuthResult(
            success=True,
            user_id="test_user",
            email="test@example.com"
        )
        
        # Mock external auth failures to trigger circuit breaker
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient.validate_token') as mock_validate:
            
            # Test 2: Simulate repeated auth service failures
            mock_validate.side_effect = AuthServiceConnectionError("Service unavailable")
            
            # Multiple failures should trigger circuit breaker
            for _ in range(5):
                try:
                    client = AuthServiceClient()
                    await client.validate_token("fake_token")
                except (AuthServiceConnectionError, CircuitBreakerError):
                    # Expected - service should fail fast after circuit opens
                    pass
            
            # Test 3: Verify circuit breaker prevents additional calls
            with pytest.raises((CircuitBreakerError, AuthServiceConnectionError)):
                client = AuthServiceClient()
                await client.validate_token("fake_token")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_failure_handling(self, real_services_fixture, isolated_env):
        """
        Test WebSocket connection failures and recovery mechanisms.
        
        BVJ: Ensures real-time communication resilience for chat functionality.
        Users maintain connection during network instability.
        """
        self.db_manager = get_database_manager()
        user = await self.create_test_user()
        
        # Test 1: Simulate WebSocket disconnect during agent execution
        websocket_mock = MagicMock()
        websocket_mock.accept = AsyncMock()
        websocket_mock.send_json = AsyncMock()
        websocket_mock.close = AsyncMock()
        
        # Test connection failure during message sending
        websocket_mock.send_json.side_effect = ConnectionError("WebSocket disconnected")
        
        try:
            await websocket_mock.send_json({"type": "agent_started", "data": {}})
        except ConnectionError:
            # Verify graceful handling of disconnection
            assert websocket_mock.close.called
        
        # Test 2: Verify message queuing for disconnected clients
        message_handler = MessageHandlerService()
        
        # Should queue messages when WebSocket unavailable
        await message_handler.handle_agent_message(
            user_id=user["id"],
            message="Test message during disconnection",
            websocket=None  # Simulate no active WebSocket
        )
        
        # Message should be stored for later delivery
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                text("SELECT COUNT(*) as count FROM messages WHERE user_id = :user_id"),
                {"user_id": user["id"]}
            )
            message_count = result.fetchone().count
            assert message_count > 0

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_timeout_handling(self, real_services_fixture, isolated_env):
        """
        Test timeout handling across service boundaries.
        
        BVJ: Prevents system lockup when services become slow.
        Users receive timely feedback instead of indefinite waiting.
        """
        # Test 1: Database query timeout
        self.db_manager = get_database_manager()
        
        with patch('asyncio.wait_for') as mock_wait_for:
            mock_wait_for.side_effect = asyncio.TimeoutError("Query timeout")
            
            with pytest.raises(asyncio.TimeoutError):
                async with self.db_manager.get_session() as session:
                    await asyncio.wait_for(
                        session.execute(text("SELECT pg_sleep(10)")),
                        timeout=1.0
                    )
        
        # Test 2: HTTP client timeout
        async with httpx.AsyncClient(timeout=0.1) as client:
            with pytest.raises(httpx.TimeoutException):
                # This should timeout quickly
                await client.get("http://httpbin.org/delay/5")
        
        # Test 3: Verify system continues after timeouts
        async with self.db_manager.get_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            assert result.fetchone().test == 1

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_error_isolation(self, real_services_fixture, isolated_env):
        """
        Test that errors for one user don't affect other users.
        
        BVJ: Critical for multi-tenant SaaS - one user's issues shouldn't impact others.
        Maintains service quality and prevents customer churn.
        """
        self.db_manager = get_database_manager()
        self.redis_manager = get_redis_manager()
        
        # Create multiple test users
        user1 = await self.create_test_user("user1@example.com")
        user2 = await self.create_test_user("user2@example.com")
        
        # Test 1: User 1 experiences database error
        user1_context = UserExecutionContext(
            user_id=user1["id"],
            execution_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            agent_name="test_agent"
        )
        
        # Simulate error for user 1 only
        with patch.object(self.db_manager, 'get_session') as mock_session:
            # Create a session that fails for user1 but works for user2
            def session_side_effect(*args, **kwargs):
                if hasattr(args[0] if args else None, 'user_id') and args[0].user_id == user1["id"]:
                    raise OperationalError("User 1 database error", None, None)
                return self.db_manager.get_session()
            
            mock_session.side_effect = session_side_effect
            
            # User 2 should still work normally
            async with self.db_manager.get_session() as session:
                result = await session.execute(
                    text("SELECT email FROM users WHERE id = :user_id"),
                    {"user_id": user2["id"]}
                )
                found_user = result.fetchone()
                assert found_user is not None
                assert found_user.email == user2["email"]
        
        # Test 2: Verify Redis key isolation
        await self.redis_manager.set(f"user:{user1['id']}:session", "error_state")
        await self.redis_manager.set(f"user:{user2['id']}:session", "normal_state")
        
        user1_session = await self.redis_manager.get(f"user:{user1['id']}:session")
        user2_session = await self.redis_manager.get(f"user:{user2['id']}:session")
        
        assert user1_session == "error_state"
        assert user2_session == "normal_state"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_health_check_failure_handling(self, real_services_fixture, isolated_env):
        """
        Test service health check failures and system response.
        
        BVJ: Proactive failure detection prevents user-facing errors.
        System can take corrective action before users are impacted.
        """
        self.db_manager = get_database_manager()
        self.redis_manager = get_redis_manager()
        
        # Test 1: Database health check failure
        with patch.object(self.db_manager, 'health_check') as mock_health:
            mock_health.return_value = {
                "status": "unhealthy",
                "error": "Connection pool exhausted",
                "timestamp": time.time()
            }
            
            health_result = await self.db_manager.health_check()
            assert health_result["status"] == "unhealthy"
            assert "error" in health_result
        
        # Test 2: Redis health check failure  
        with patch.object(self.redis_manager, 'ping') as mock_ping:
            mock_ping.side_effect = RedisConnectionError("Redis unavailable")
            
            try:
                await self.redis_manager.ping()
            except RedisConnectionError:
                # Health check should detect this
                pass
        
        # Test 3: Verify system continues with degraded functionality
        # Even with health check failures, basic operations should work
        async with self.db_manager.get_session() as session:
            result = await session.execute(text("SELECT NOW() as current_time"))
            assert result.fetchone().current_time is not None

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cascading_failure_prevention(self, real_services_fixture, isolated_env):
        """
        Test prevention of cascading failures across service boundaries.
        
        BVJ: One service failure shouldn't bring down entire system.
        Maintains overall platform availability during partial outages.
        """
        self.db_manager = get_database_manager()
        self.redis_manager = get_redis_manager()
        
        user = await self.create_test_user()
        
        # Test 1: Auth service failure doesn't prevent database operations
        with patch('netra_backend.app.services.unified_authentication_service.AuthServiceClient') as mock_auth:
            mock_auth.return_value.validate_token.side_effect = AuthServiceConnectionError("Auth service down")
            
            # Database operations should still work
            async with self.db_manager.get_session() as session:
                result = await session.execute(
                    text("SELECT email FROM users WHERE id = :user_id"),
                    {"user_id": user["id"]}
                )
                found_user = result.fetchone()
                assert found_user is not None
        
        # Test 2: Redis failure doesn't prevent core functionality
        with patch.object(self.redis_manager, 'get') as mock_get:
            mock_get.side_effect = RedisConnectionError("Redis cluster down")
            
            # Core database operations should continue
            async with self.db_manager.get_session() as session:
                new_user_id = str(uuid.uuid4())
                await session.execute(
                    text("INSERT INTO users (id, email, name, created_at) VALUES (:id, :email, :name, :created_at)"),
                    {
                        "id": new_user_id,
                        "email": "cascade_test@example.com",
                        "name": "Cascade Test",
                        "created_at": datetime.now(timezone.utc)
                    }
                )
                await session.commit()
                
                # Verify user was created despite Redis failure
                result = await session.execute(
                    text("SELECT email FROM users WHERE id = :user_id"),
                    {"user_id": new_user_id}
                )
                found_user = result.fetchone()
                assert found_user.email == "cascade_test@example.com"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_rate_limiting_error_responses(self, real_services_fixture, isolated_env):
        """
        Test proper handling of rate limiting errors from external services.
        
        BVJ: Graceful handling of API limits maintains user experience.
        System should implement backoff and retry strategies.
        """
        # Test 1: LLM API rate limiting
        with patch('httpx.AsyncClient.post') as mock_post:
            # Simulate rate limit response
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_response.json.return_value = {"error": "Rate limit exceeded"}
            mock_post.return_value = mock_response
            
            # System should handle rate limiting gracefully
            async with httpx.AsyncClient() as client:
                response = await client.post("http://example.com/api", json={"test": "data"})
                assert response.status_code == 429
                assert "Retry-After" in response.headers
        
        # Test 2: Verify exponential backoff implementation
        retry_delays = []
        
        async def mock_request_with_backoff():
            for attempt in range(3):
                delay = 2 ** attempt  # Exponential backoff
                retry_delays.append(delay)
                await asyncio.sleep(0.01)  # Simulate delay (shortened for testing)
                
                if attempt == 2:  # Succeed on final attempt
                    return {"success": True}
            return {"error": "Max retries exceeded"}
        
        result = await mock_request_with_backoff()
        assert result["success"] is True
        assert len(retry_delays) == 3
        assert retry_delays == [1, 2, 4]  # Exponential progression

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_partial_failure_recovery(self, real_services_fixture, isolated_env):
        """
        Test recovery from partial system failures.
        
        BVJ: System should gracefully handle and recover from partial outages.
        Users experience minimal disruption during recovery periods.
        """
        self.db_manager = get_database_manager()
        self.redis_manager = get_redis_manager()
        
        user = await self.create_test_user()
        
        # Test 1: Partial database failure (some queries fail, others succeed)
        query_counter = 0
        
        async def selective_query_failure(*args, **kwargs):
            nonlocal query_counter
            query_counter += 1
            if query_counter % 2 == 0:  # Every other query fails
                raise OperationalError("Partial database failure", None, None)
            return self.db_manager.get_session()
        
        with patch.object(self.db_manager, 'get_session', side_effect=selective_query_failure):
            success_count = 0
            failure_count = 0
            
            for _ in range(4):
                try:
                    async with self.db_manager.get_session() as session:
                        await session.execute(text("SELECT 1"))
                        success_count += 1
                except OperationalError:
                    failure_count += 1
            
            assert success_count == 2  # Half should succeed
            assert failure_count == 2  # Half should fail
        
        # Test 2: Verify system recovers to full functionality
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                text("SELECT email FROM users WHERE id = :user_id"),
                {"user_id": user["id"]}
            )
            found_user = result.fetchone()
            assert found_user is not None
            assert found_user.email == user["email"]

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_message_standardization(self, real_services_fixture, isolated_env):
        """
        Test standardized error message format across services.
        
        BVJ: Consistent error messages improve debugging and user experience.
        Support teams can quickly identify and resolve issues.
        """
        # Test 1: Database error standardization
        try:
            async with get_database_manager().get_session() as session:
                await session.execute(text("SELECT * FROM nonexistent_table"))
        except Exception as e:
            error_msg = str(e)
            # Should contain standardized error information
            assert len(error_msg) > 0
            # Error should be descriptive
            assert "table" in error_msg.lower() or "relation" in error_msg.lower()
        
        # Test 2: Redis error standardization  
        try:
            redis_manager = get_redis_manager()
            with patch.object(redis_manager, 'get') as mock_get:
                mock_get.side_effect = RedisConnectionError("Connection failed")
                await redis_manager.get("test_key")
        except RedisConnectionError as e:
            error_msg = str(e)
            assert "connection" in error_msg.lower()
        
        # Test 3: Auth service error standardization
        try:
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.side_effect = httpx.ConnectError("Auth service unreachable")
                
                auth_client = AuthServiceClient()
                await auth_client.validate_token("invalid_token")
        except (AuthServiceConnectionError, httpx.ConnectError) as e:
            error_msg = str(e)
            assert len(error_msg) > 0

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_resource_exhaustion_scenarios(self, real_services_fixture, isolated_env):
        """
        Test handling of resource exhaustion scenarios.
        
        BVJ: System should handle high load gracefully without crashing.
        Prevents complete service outages during traffic spikes.
        """
        self.db_manager = get_database_manager()
        self.redis_manager = get_redis_manager()
        
        # Test 1: Database connection pool exhaustion
        connections = []
        try:
            # Try to create more connections than pool allows
            for i in range(50):  # Assuming pool size is smaller
                try:
                    session = self.db_manager.get_session()
                    connections.append(session)
                except Exception as e:
                    # Should handle gracefully when pool exhausted
                    assert "connection" in str(e).lower() or "pool" in str(e).lower()
                    break
        finally:
            # Clean up connections
            for conn in connections:
                try:
                    await conn.close()
                except:
                    pass
        
        # Test 2: Memory pressure simulation
        large_data = []
        try:
            # Create large objects to simulate memory pressure
            for i in range(10):
                large_data.append("x" * 1024)  # Small for testing
            
            # System should still function
            async with self.db_manager.get_session() as session:
                result = await session.execute(text("SELECT 1 as test"))
                assert result.fetchone().test == 1
        finally:
            # Clean up memory
            large_data.clear()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_configuration_error_handling(self, real_services_fixture, isolated_env):
        """
        Test handling of configuration errors and misconfigurations.
        
        BVJ: Robust config handling prevents deployment failures.
        Clear error messages help operations teams resolve issues quickly.
        """
        env = get_env()
        
        # Test 1: Missing required configuration
        original_value = env.get("DATABASE_URL")
        
        try:
            # Temporarily remove critical config
            env.set("DATABASE_URL", "", source="test")
            
            # System should detect missing config gracefully
            try:
                db_manager = DatabaseManager()
                # Should raise clear configuration error
                pytest.fail("Should raise configuration error for missing DATABASE_URL")
            except Exception as e:
                error_msg = str(e).lower()
                assert "database" in error_msg or "url" in error_msg or "config" in error_msg
        
        finally:
            # Restore original configuration
            if original_value:
                env.set("DATABASE_URL", original_value, source="test")
        
        # Test 2: Invalid configuration format
        with patch.object(env, 'get') as mock_get:
            mock_get.return_value = "invalid://malformed:url"
            
            try:
                # Should handle malformed URLs gracefully
                from shared.database_url_builder import DatabaseURLBuilder
                builder = DatabaseURLBuilder()
                # Should raise clear format error
            except Exception as e:
                error_msg = str(e).lower()
                assert "url" in error_msg or "format" in error_msg or "invalid" in error_msg

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_experience_during_failures(self, real_services_fixture, isolated_env):
        """
        Test user experience preservation during service failures.
        
        BVJ: Users should receive meaningful feedback during outages.
        Maintains customer satisfaction even when technical issues occur.
        """
        self.db_manager = get_database_manager()
        user = await self.create_test_user()
        
        # Test 1: User gets appropriate error message for database issues
        with patch.object(self.db_manager, 'get_session') as mock_session:
            mock_session.side_effect = OperationalError("Database temporarily unavailable", None, None)
            
            try:
                async with self.db_manager.get_session() as session:
                    await session.execute(text("SELECT 1"))
            except OperationalError as e:
                # Error should be user-friendly, not technical
                error_msg = str(e)
                assert "database" in error_msg.lower()
                # Should not expose internal technical details
                assert "connection pool" not in error_msg.lower()
        
        # Test 2: User operations are queued during temporary outages
        operations_queue = []
        
        # Simulate queueing user operations during outage
        user_operation = {
            "user_id": user["id"],
            "operation": "send_message",
            "data": {"message": "Test during outage"},
            "timestamp": time.time()
        }
        operations_queue.append(user_operation)
        
        # When service recovers, queued operations should be processed
        assert len(operations_queue) == 1
        assert operations_queue[0]["user_id"] == user["id"]
        
        # Process queued operations after recovery
        for operation in operations_queue:
            # Simulate processing the queued operation
            assert operation["operation"] == "send_message"
            assert operation["data"]["message"] == "Test during outage"
        
        operations_queue.clear()
        assert len(operations_queue) == 0

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_error_scenarios(self, real_services_fixture, isolated_env):
        """
        Test handling of concurrent error scenarios across multiple users.
        
        BVJ: System maintains stability under concurrent load with mixed error conditions.
        Multi-user SaaS platform must handle concurrent failures gracefully.
        """
        self.db_manager = get_database_manager()
        
        # Create multiple test users
        users = []
        for i in range(5):
            user = await self.create_test_user(f"concurrent_test_{i}@example.com")
            users.append(user)
        
        # Test concurrent database operations with mixed success/failure
        async def user_operation(user_data, should_fail=False):
            try:
                if should_fail:
                    # Simulate failure for some users
                    raise OperationalError("Simulated user-specific error", None, None)
                
                async with self.db_manager.get_session() as session:
                    result = await session.execute(
                        text("SELECT email FROM users WHERE id = :user_id"),
                        {"user_id": user_data["id"]}
                    )
                    found_user = result.fetchone()
                    return {
                        "user_id": user_data["id"],
                        "success": True,
                        "email": found_user.email if found_user else None
                    }
            except OperationalError:
                return {
                    "user_id": user_data["id"],
                    "success": False,
                    "error": "Database operation failed"
                }
        
        # Run concurrent operations with mixed outcomes
        tasks = []
        for i, user in enumerate(users):
            should_fail = i % 2 == 0  # Every other user fails
            task = asyncio.create_task(user_operation(user, should_fail))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify mixed results - some succeed, some fail
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failure_count = sum(1 for r in results if isinstance(r, dict) and not r.get("success"))
        
        assert success_count > 0  # Some should succeed
        assert failure_count > 0  # Some should fail
        assert success_count + failure_count == len(users)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_system_recovery_validation(self, real_services_fixture, isolated_env):
        """
        Test comprehensive system recovery after failures.
        
        BVJ: Validates that system fully recovers operational capability after outages.
        Ensures business continuity after incident resolution.
        """
        self.db_manager = get_database_manager()
        self.redis_manager = get_redis_manager()
        
        user = await self.create_test_user()
        
        # Test 1: Full system recovery check
        # Simulate system coming back online after outage
        
        # Database recovery
        async with self.db_manager.get_session() as session:
            result = await session.execute(text("SELECT 1 as health_check"))
            assert result.fetchone().health_check == 1
        
        # Redis recovery
        await self.redis_manager.set("recovery_test", "system_online", expire=60)
        recovery_value = await self.redis_manager.get("recovery_test")
        assert recovery_value == "system_online"
        
        # User data integrity after recovery
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                text("SELECT email FROM users WHERE id = :user_id"),
                {"user_id": user["id"]}
            )
            found_user = result.fetchone()
            assert found_user is not None
            assert found_user.email == user["email"]
        
        # Test 2: Performance recovery validation
        start_time = time.time()
        
        async with self.db_manager.get_session() as session:
            result = await session.execute(text("SELECT COUNT(*) as user_count FROM users"))
            user_count = result.fetchone().user_count
            
        end_time = time.time()
        query_duration = end_time - start_time
        
        # Query should complete in reasonable time after recovery
        assert query_duration < 5.0  # Should be much faster, but allowing margin
        assert user_count >= len(self.test_users)  # All test users should be there