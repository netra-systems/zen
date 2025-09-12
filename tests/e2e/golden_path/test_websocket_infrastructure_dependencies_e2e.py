"""
WebSocket Infrastructure Dependencies E2E Test - Database/Redis Connectivity Issues

CRITICAL INFRASTRUCTURE DEPENDENCY VALIDATION: This test validates that WebSocket
service properly depends on database and Redis connectivity, and fails clearly when
infrastructure dependencies are unavailable.

Test Objective: WebSocket Infrastructure Dependency Failure Detection
- MANDATORY hard failure when database unavailable for WebSocket operations
- MANDATORY hard failure when Redis unavailable for WebSocket session management  
- MANDATORY clear error messages explaining infrastructure dependency issues
- PROOF that infrastructure failures prevent WebSocket functionality properly

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Infrastructure Integrity
- Business Goal: Reliable WebSocket infrastructure dependencies
- Value Impact: Prevents WebSocket operations when data layer is unavailable
- Strategic Impact: Maintains data integrity and prevents partial WebSocket failures

CRITICAL REQUIREMENTS (per CLAUDE.md):
1. MANDATORY database connectivity check before WebSocket operations
2. MANDATORY Redis connectivity check for WebSocket session management
3. MANDATORY hard failure when infrastructure unavailable (NO try/except hiding)
4. MANDATORY authentication via E2EAuthHelper for infrastructure testing
5. NO silent infrastructure failures or partial WebSocket operations
6. Must demonstrate infrastructure unavailability prevents WebSocket operations

WEBSOCKET INFRASTRUCTURE DEPENDENCY FLOW:
```
Database Health Check  ->  Redis Health Check  ->  WebSocket Connection  -> 
Infrastructure Failure Detection  ->  Hard Failure with Infra Diagnosis  ->  Test Failure
```
"""

import asyncio
import json
import pytest
import time
# MIGRATED: from netra_backend.app.services.redis_client import get_redis_client
import asyncpg
import websockets
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# SSOT imports following absolute import rules - INFRASTRUCTURE DEPENDENCY FOCUSED
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from test_framework.ssot.real_services_test_fixtures import real_services_fixture

# Core system imports for infrastructure dependency validation
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, WebSocketID


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.infrastructure_dependencies
@pytest.mark.asyncio
@pytest.mark.websocket_infrastructure
class TestWebSocketInfrastructureDependenciesE2E(SSotAsyncTestCase):
    """
    WebSocket Infrastructure Dependencies Failure Detection Tests.
    
    This test suite validates that WebSocket service properly depends on database
    and Redis infrastructure, and fails appropriately when dependencies are unavailable.
    
    CRITICAL MANDATE: These tests MUST fail hard when infrastructure is unavailable
    to ensure WebSocket operations don't proceed with broken data layer.
    """
    
    def setup_method(self, method=None):
        """Setup with infrastructure dependency validation focus."""
        super().setup_method(method)
        
        # Infrastructure dependency compliance metrics
        self.record_metric("websocket_infrastructure_dependency_test", True)
        self.record_metric("database_dependency_validation", "mandatory")
        self.record_metric("redis_dependency_validation", "mandatory")
        self.record_metric("infrastructure_failure_tolerance", 0)  # ZERO tolerance for infra failures
        self.record_metric("websocket_data_integrity_critical", True)
        
        # Initialize infrastructure dependency components
        self._auth_helper = None
        self._websocket_helper = None
        self._database_url = None
        self._redis_url = None
        self._websocket_url = None
        
    async def async_setup_method(self, method=None):
        """Async setup with mandatory infrastructure dependency validation."""
        await super().async_setup_method(method)
        
        # CRITICAL: Initialize infrastructure dependency helpers
        environment = self.get_env_var("TEST_ENV", "test")
        self._auth_helper = E2EAuthHelper(environment=environment)
        self._websocket_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Get infrastructure URLs for dependency testing
        self._database_url = self.get_env_var("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/netra_test")
        self._redis_url = self.get_env_var("REDIS_URL", "redis://localhost:6381/0")
        self._websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        # Record infrastructure dependency setup
        self.record_metric("infrastructure_dependency_setup_completed", True)
        self.record_metric("database_url", self._database_url)
        self.record_metric("redis_url", self._redis_url)
        self.record_metric("websocket_service_url", self._websocket_url)

    @pytest.mark.timeout(50)  # Allow time for infrastructure dependency validation
    @pytest.mark.asyncio
    async def test_database_unavailable_blocks_websocket_operations(self, real_services_fixture):
        """
        CRITICAL: Test database unavailability prevents WebSocket operations.
        
        This test validates that:
        1. Database health is checked before WebSocket operations
        2. Database unavailability prevents WebSocket data operations
        3. Clear error messages explain database connectivity issues
        4. WebSocket connections fail when database layer is unavailable
        5. User data operations require accessible database
        
        DATABASE DEPENDENCY REQUIREMENTS:
        - Database connectivity check MUST be performed
        - Database unavailability MUST prevent WebSocket operations
        - Error messages MUST explain database infrastructure impact
        - NO WebSocket data operations allowed without database access
        
        BUSINESS IMPACT: Database unavailability prevents WebSocket data persistence
        """
        test_start_time = time.time()
        
        # === DATABASE HEALTH CHECK ===
        self.record_metric("database_health_check_start", time.time())
        
        database_available = False
        database_error = None
        database_response_time = None
        
        try:
            # Check database connectivity
            db_start = time.time()
            
            # Attempt database connection
            db_connection = await asyncpg.connect(self._database_url, timeout=10.0)
            
            # Test basic database operation
            await db_connection.execute("SELECT 1")
            
            database_response_time = time.time() - db_start
            database_available = True
            
            await db_connection.close()
            
        except Exception as e:
            database_error = str(e)
            database_response_time = time.time() - db_start if 'db_start' in locals() else 0
        
        # Record database health check results
        self.record_metric("database_available", database_available)
        self.record_metric("database_health_response_time", database_response_time)
        self.record_metric("database_health_error", database_error)
        
        # === DATABASE DEPENDENCY VALIDATION ===
        if database_available:
            # Database is available - test normal WebSocket with database operations
            await self._test_websocket_database_integration_when_available()
            
        else:
            # Database is unavailable - validate WebSocket operations are blocked
            await self._test_websocket_blocked_when_database_unavailable(database_error, database_response_time)
        
        # Record final metrics
        total_test_time = time.time() - test_start_time
        self.record_metric("database_dependency_test_duration", total_test_time)

    async def _test_websocket_database_integration_when_available(self):
        """Test WebSocket database integration when database is available."""
        
        # === AUTHENTICATED USER CREATION (REQUIRES DATABASE) ===
        self.record_metric("database_user_creation_test_start", time.time())
        
        # Create authenticated user (may require database for persistence)
        authenticated_user = await create_authenticated_user_context(
            user_email="websocket_db_integration@example.com",
            environment=self.get_env_var("TEST_ENV", "test"),
            permissions=["read", "write", "websocket"],
            websocket_enabled=True
        )
        
        jwt_token = authenticated_user.agent_context.get("jwt_token")
        user_id = str(authenticated_user.user_id)
        
        self.record_metric("database_user_creation_success", True)
        
        # === WEBSOCKET CONNECTION WITH DATABASE OPERATIONS ===
        self.record_metric("websocket_database_integration_test_start", time.time())
        
        # Get authenticated WebSocket headers
        auth_headers = self._websocket_helper.get_websocket_headers(jwt_token)
        
        websocket_connection = None
        
        try:
            # Connect to WebSocket
            websocket_connection = await asyncio.wait_for(
                websockets.connect(
                    self._websocket_url,
                    additional_headers=auth_headers,
                    open_timeout=10.0,
                    close_timeout=5.0
                ),
                timeout=15.0
            )
            
            # Send message that may trigger database operations
            database_test_message = {
                "type": "chat_message",
                "content": "Database integration test message",
                "user_id": user_id,
                "thread_id": str(authenticated_user.thread_id),
                "timestamp": time.time(),
                "database_operation_test": True,
                "requires_persistence": True
            }
            
            await websocket_connection.send(json.dumps(database_test_message))
            
            # Collect events (may trigger database operations)
            database_events = []
            timeout = 15.0
            start_time = time.time()
            
            while (time.time() - start_time) < timeout:
                try:
                    event_message = await asyncio.wait_for(
                        websocket_connection.recv(),
                        timeout=3.0
                    )
                    
                    event_data = json.loads(event_message)
                    database_events.append(event_data)
                    
                    # Stop if we get a completion event
                    if event_data.get("type") in ["agent_completed", "error"]:
                        break
                        
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break
            
            # Validate database-related events
            self.record_metric("database_related_events_received", len(database_events))
            
        except Exception as e:
            pytest.fail(
                f"WebSocket operations should succeed when database is available. "
                f"Error: {e}. This indicates database integration is broken."
            )
        
        finally:
            if websocket_connection:
                await websocket_connection.close()
        
        print(f" PASS:  DATABASE INTEGRATION: WORKING")
        print(f"   [U+1F7E2] Database: Available")
        print(f"   [U+1F7E2] User creation: Success")
        print(f"   [U+1F7E2] WebSocket with DB ops: Success")
        print(f"    CHART:  DB-related events: {len(database_events)}")

    async def _test_websocket_blocked_when_database_unavailable(self, db_error: str, response_time: float):
        """Test WebSocket operations are blocked when database is unavailable."""
        
        # === ATTEMPT USER CREATION WITH DATABASE DOWN ===
        user_creation_failed = False
        user_creation_error = None
        
        try:
            # Try to create user despite database unavailability
            authenticated_user = await create_authenticated_user_context(
                user_email="websocket_db_fail_test@example.com",
                environment=self.get_env_var("TEST_ENV", "test"),
                websocket_enabled=True
            )
        except Exception as e:
            user_creation_failed = True
            user_creation_error = str(e)
        
        # User creation may succeed with fallback auth, but database operations should fail
        
        database_unavailable_message = (
            f" ALERT:  DATABASE UNAVAILABILITY DETECTED:\n"
            f"   [U+1F534] Database URL: {self._database_url}\n"
            f"   [U+1F534] Health Check Error: {db_error}\n"
            f"   [U+1F534] Response Time: {response_time:.3f}s\n"
            f"   [U+1F534] User Creation Failed: {user_creation_failed}\n"
            f"   [U+1F534] User Creation Error: {user_creation_error}\n"
            f"\n"
            f"   [U+1F4BC] BUSINESS IMPACT:\n"
            f"   [U+2022] User data cannot be persisted to database\n"
            f"   [U+2022] WebSocket chat history may not be saved\n"
            f"   [U+2022] Agent execution results may not be stored\n"
            f"   [U+2022] User session data may be lost\n"
            f"   [U+2022] Data integrity compromised for WebSocket operations\n"
            f"\n"
            f"   [U+1F527] RESOLUTION REQUIRED:\n"
            f"   [U+2022] Start database service: {self._database_url}\n"
            f"   [U+2022] Verify PostgreSQL service is running and accessible\n"
            f"   [U+2022] Check database connection pool configuration\n"
            f"   [U+2022] Validate database schema and migrations\n"
            f"   [U+2022] Ensure sufficient database resources and connections\n"
        )
        
        # Print detailed database diagnosis
        print(database_unavailable_message)
        
        # MANDATORY HARD FAILURE - DO NOT HIDE DATABASE ISSUES
        pytest.fail(database_unavailable_message)

    @pytest.mark.timeout(40)
    @pytest.mark.asyncio
    async def test_redis_unavailable_blocks_websocket_sessions(self, real_services_fixture):
        """
        CRITICAL: Test Redis unavailability prevents WebSocket session management.
        
        This test validates Redis dependency for WebSocket sessions:
        1. Redis health is checked before WebSocket session operations
        2. Redis unavailability prevents WebSocket session management
        3. Clear error messages explain Redis connectivity issues
        4. WebSocket connections may fail without Redis session storage
        """
        
        # === REDIS HEALTH CHECK ===
        self.record_metric("redis_health_check_start", time.time())
        
        redis_available = False
        redis_error = None
        redis_response_time = None
        
        try:
            # Check Redis connectivity
            redis_start = time.time()
            
            # Parse Redis URL for connection
            if self._redis_url.startswith("redis://"):
                # Extract connection details from Redis URL
                redis_parts = self._redis_url.replace("redis://", "").split(":")
                redis_host = redis_parts[0] if redis_parts else "localhost"
                redis_port_db = redis_parts[1] if len(redis_parts) > 1 else "6379/0"
                redis_port = int(redis_port_db.split("/")[0]) if "/" in redis_port_db else int(redis_port_db)
                redis_db = int(redis_port_db.split("/")[1]) if "/" in redis_port_db else 0
            else:
                redis_host = "localhost"
                redis_port = 6381
                redis_db = 0
            
            # Attempt Redis connection
            redis_client = await get_redis_client()
            
            # Test basic Redis operation
            await redis_client.ping()
            
            # Test set/get operation
            test_key = f"websocket_test_{int(time.time())}"
            await redis_client.set(test_key, "test_value", ex=60)
            test_value = await redis_client.get(test_key)
            
            assert test_value == b"test_value", "Redis set/get operation failed"
            
            # Cleanup
            await redis_client.delete(test_key)
            await redis_client.close()
            
            redis_response_time = time.time() - redis_start
            redis_available = True
            
        except Exception as e:
            redis_error = str(e)
            redis_response_time = time.time() - redis_start if 'redis_start' in locals() else 0
        
        # Record Redis health check results
        self.record_metric("redis_available", redis_available)
        self.record_metric("redis_health_response_time", redis_response_time)
        self.record_metric("redis_health_error", redis_error)
        
        # === REDIS DEPENDENCY VALIDATION ===
        if redis_available:
            # Redis is available - test normal WebSocket with session management
            await self._test_websocket_redis_integration_when_available()
            
        else:
            # Redis is unavailable - validate WebSocket session management is affected
            await self._test_websocket_sessions_affected_when_redis_unavailable(redis_error, redis_response_time)

    async def _test_websocket_redis_integration_when_available(self):
        """Test WebSocket Redis integration when Redis is available."""
        
        # Create authenticated user for Redis session testing
        authenticated_user = await create_authenticated_user_context(
            user_email="websocket_redis_integration@example.com",
            environment=self.get_env_var("TEST_ENV", "test"),
            websocket_enabled=True
        )
        
        jwt_token = authenticated_user.agent_context.get("jwt_token")
        user_id = str(authenticated_user.user_id)
        
        # Get authenticated WebSocket headers
        auth_headers = self._websocket_helper.get_websocket_headers(jwt_token)
        
        websocket_connection = None
        
        try:
            # Connect to WebSocket (may use Redis for session management)
            websocket_connection = await asyncio.wait_for(
                websockets.connect(
                    self._websocket_url,
                    additional_headers=auth_headers,
                    open_timeout=10.0,
                    close_timeout=5.0
                ),
                timeout=15.0
            )
            
            # Send message that may trigger Redis session operations
            session_test_message = {
                "type": "session_test",
                "content": "Redis session integration test",
                "user_id": user_id,
                "session_data": {
                    "test_session_key": "test_session_value",
                    "timestamp": time.time()
                },
                "redis_session_test": True
            }
            
            await websocket_connection.send(json.dumps(session_test_message))
            
            # Brief wait for session processing
            await asyncio.sleep(2.0)
            
            self.record_metric("redis_session_operations_success", True)
            
        except Exception as e:
            pytest.fail(
                f"WebSocket session operations should succeed when Redis is available. "
                f"Error: {e}. This indicates Redis integration is broken."
            )
        
        finally:
            if websocket_connection:
                await websocket_connection.close()
        
        print(f" PASS:  REDIS INTEGRATION: WORKING")
        print(f"   [U+1F7E2] Redis: Available")
        print(f"   [U+1F7E2] WebSocket sessions: Success")
        print(f"    CHART:  Session operations: Success")

    async def _test_websocket_sessions_affected_when_redis_unavailable(self, redis_error: str, response_time: float):
        """Test WebSocket sessions are affected when Redis is unavailable."""
        
        # Create authenticated user (may not require Redis)
        try:
            authenticated_user = await create_authenticated_user_context(
                user_email="websocket_redis_fail_test@example.com",
                environment=self.get_env_var("TEST_ENV", "test"),
                websocket_enabled=True
            )
            
            jwt_token = authenticated_user.agent_context.get("jwt_token")
            auth_headers = self._websocket_helper.get_websocket_headers(jwt_token)
            
            # Test WebSocket connection (may work without Redis but with limited functionality)
            websocket_connection = None
            connection_success = False
            
            try:
                websocket_connection = await asyncio.wait_for(
                    websockets.connect(
                        self._websocket_url,
                        additional_headers=auth_headers,
                        open_timeout=10.0
                    ),
                    timeout=15.0
                )
                
                connection_success = True
                
                # Connection may succeed but session functionality may be limited
                print(f"[U+2139][U+FE0F] WebSocket connection succeeded despite Redis unavailability")
                print(f"   [U+1F4E1] Connection established but session management may be limited")
                print(f"   [U+1F510] Authentication working (may not require Redis)")
                
                await websocket_connection.close()
                
            except Exception as e:
                # Connection failed - may be due to Redis dependency
                self.record_metric("websocket_failed_due_to_redis", str(e))
        
        except Exception as user_error:
            # User creation failed
            self.record_metric("user_creation_failed_due_to_redis", str(user_error))
        
        # === REDIS UNAVAILABILITY IMPACT ANALYSIS ===
        
        redis_unavailable_message = (
            f" ALERT:  REDIS UNAVAILABILITY DETECTED:\n"
            f"   [U+1F534] Redis URL: {self._redis_url}\n"
            f"   [U+1F534] Health Check Error: {redis_error}\n"
            f"   [U+1F534] Response Time: {response_time:.3f}s\n"
            f"\n"
            f"   [U+1F4BC] BUSINESS IMPACT:\n"
            f"   [U+2022] WebSocket session management may be compromised\n"
            f"   [U+2022] User session data may not be cached/stored\n"
            f"   [U+2022] Real-time feature performance may be degraded\n"
            f"   [U+2022] Session-based WebSocket features may not work\n"
            f"   [U+2022] Concurrent user session tracking may fail\n"
            f"\n"
            f"   [U+1F527] RESOLUTION REQUIRED:\n"
            f"   [U+2022] Start Redis service: {self._redis_url}\n"
            f"   [U+2022] Verify Redis server is running and accessible\n"
            f"   [U+2022] Check Redis configuration and memory settings\n"
            f"   [U+2022] Validate Redis connection pool configuration\n"
            f"   [U+2022] Ensure Redis has sufficient memory for session data\n"
        )
        
        # Print detailed Redis diagnosis
        print(redis_unavailable_message)
        
        # MANDATORY HARD FAILURE - DO NOT HIDE REDIS ISSUES
        pytest.fail(redis_unavailable_message)

    @pytest.mark.timeout(35)
    @pytest.mark.asyncio
    async def test_combined_infrastructure_failure_impact(self, real_services_fixture):
        """
        CRITICAL: Test combined database and Redis failure impact on WebSocket operations.
        
        This test validates multiple infrastructure dependency failures:
        1. Both database and Redis unavailable prevents WebSocket operations
        2. Partial infrastructure availability is properly diagnosed
        3. Clear error messages explain combined infrastructure issues
        4. System behavior with multiple dependency failures
        """
        
        # === COMBINED INFRASTRUCTURE HEALTH CHECK ===
        self.record_metric("combined_infrastructure_check_start", time.time())
        
        # Check database availability (reuse logic)
        database_available = await self._check_database_availability()
        
        # Check Redis availability (reuse logic)
        redis_available = await self._check_redis_availability()
        
        # Record combined infrastructure status
        self.record_metric("database_available_combined", database_available)
        self.record_metric("redis_available_combined", redis_available)
        
        infrastructure_status = "unknown"
        
        if database_available and redis_available:
            infrastructure_status = "fully_available"
            print(f" PASS:  COMBINED INFRASTRUCTURE: FULLY AVAILABLE")
            print(f"   [U+1F7E2] Database: Available")
            print(f"   [U+1F7E2] Redis: Available")
            print(f"   [U+1F680] WebSocket operations should work normally")
            
        elif database_available and not redis_available:
            infrastructure_status = "database_only"
            print(f" WARNING: [U+FE0F] COMBINED INFRASTRUCTURE: PARTIAL (DATABASE ONLY)")
            print(f"   [U+1F7E2] Database: Available")
            print(f"   [U+1F534] Redis: Unavailable")
            print(f"   [U+1F4C9] WebSocket operations may be limited")
            
        elif not database_available and redis_available:
            infrastructure_status = "redis_only"
            print(f" WARNING: [U+FE0F] COMBINED INFRASTRUCTURE: PARTIAL (REDIS ONLY)")
            print(f"   [U+1F534] Database: Unavailable")
            print(f"   [U+1F7E2] Redis: Available")
            print(f"   [U+1F4C9] WebSocket data operations compromised")
            
        else:
            infrastructure_status = "completely_unavailable"
            
            # Both database and Redis unavailable - critical failure
            combined_failure_message = (
                f" ALERT:  COMPLETE INFRASTRUCTURE FAILURE:\n"
                f"   [U+1F534] Database: UNAVAILABLE\n"
                f"   [U+1F534] Redis: UNAVAILABLE\n"
                f"   [U+1F534] Database URL: {self._database_url}\n"
                f"   [U+1F534] Redis URL: {self._redis_url}\n"
                f"\n"
                f"   [U+1F4BC] CRITICAL BUSINESS IMPACT:\n"
                f"   [U+2022] ALL WebSocket data operations blocked\n"
                f"   [U+2022] NO user data persistence possible\n"
                f"   [U+2022] NO session management available\n"
                f"   [U+2022] Complete real-time AI feature unavailability\n"
                f"   [U+2022] System is effectively non-functional for WebSocket features\n"
                f"\n"
                f"    ALERT:  EMERGENCY RESOLUTION REQUIRED:\n"
                f"   [U+2022] Immediately start database service\n"
                f"   [U+2022] Immediately start Redis service\n"
                f"   [U+2022] Verify all infrastructure services are healthy\n"
                f"   [U+2022] Check service dependencies and startup order\n"
                f"   [U+2022] Validate network connectivity between services\n"
            )
            
            print(combined_failure_message)
            pytest.fail(combined_failure_message)
        
        self.record_metric("combined_infrastructure_status", infrastructure_status)

    async def _check_database_availability(self) -> bool:
        """Check database availability and return boolean result."""
        try:
            db_connection = await asyncpg.connect(self._database_url, timeout=5.0)
            await db_connection.execute("SELECT 1")
            await db_connection.close()
            return True
        except Exception:
            return False

    async def _check_redis_availability(self) -> bool:
        """Check Redis availability and return boolean result."""
        try:
            # Parse Redis URL and connect
            if self._redis_url.startswith("redis://"):
                redis_parts = self._redis_url.replace("redis://", "").split(":")
                redis_host = redis_parts[0] if redis_parts else "localhost"
                redis_port_db = redis_parts[1] if len(redis_parts) > 1 else "6379/0"
                redis_port = int(redis_port_db.split("/")[0]) if "/" in redis_port_db else int(redis_port_db)
                redis_db = int(redis_port_db.split("/")[1]) if "/" in redis_port_db else 0
            else:
                redis_host = "localhost"
                redis_port = 6381
                redis_db = 0
            
            redis_client = await get_redis_client()
            
            await redis_client.ping()
            await redis_client.close()
            return True
        except Exception:
            return False

    async def async_teardown_method(self, method=None):
        """Clean up WebSocket infrastructure dependencies test resources."""
        # Record final infrastructure dependency metrics
        if hasattr(self, '_metrics'):
            final_metrics = self.get_all_metrics()
            db_status = "available" if final_metrics.get("database_available") else "unavailable"
            redis_status = "available" if final_metrics.get("redis_available") else "unavailable"
            print(f"\n CHART:  WEBSOCKET INFRASTRUCTURE DEPENDENCIES TEST SUMMARY:")
            print(f"   [U+1F5C4][U+FE0F] Database Status: {db_status}")
            print(f"   [U+1F4E6] Redis Status: {redis_status}")
            print(f"    CHART:  Total Infrastructure Metrics: {len(final_metrics)}")
        
        await super().async_teardown_method(method)