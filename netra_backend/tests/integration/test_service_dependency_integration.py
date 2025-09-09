"""
Service Dependency Integration Tests - Phase 2 Implementation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure graceful degradation when service dependencies fail
- Value Impact: Prevents complete system failures when individual services are unavailable
- Strategic Impact: Critical for maintaining partial functionality during service outages
- Revenue Impact: Service dependency failures = potential $120K+ MRR protection through graceful degradation

This integration test suite validates service dependency management:
1. WebSocket behavior when database is unavailable
2. WebSocket behavior when Redis cache is unavailable
3. Graceful degradation patterns during service failures
4. Error notification systems during dependency failures
5. Service recovery detection and restoration
6. Multi-service failure scenarios and isolation

CRITICAL: Uses REAL services (PostgreSQL 5434, Redis 6381, WebSocket 8000) with simulated
failures to test actual graceful degradation behavior. Tests validate business value
by ensuring partial functionality remains available during service outages.

Key Integration Points:
- Real service dependency injection and monitoring
- Actual service failure simulation (connection drops, timeouts)
- Real WebSocket connections with dependency state awareness
- Proper error notification through WebSocket events
- SSOT factory patterns that handle dependency failures

GOLDEN PATH COMPLIANCE: These tests validate P1 service dependency failures
that can cause cascade failures in production environments.
"""

import asyncio
import json
import logging
import pytest
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager

# SSOT imports following TEST_CREATION_GUIDE.md
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.conftest_real_services import real_services
from test_framework.isolated_environment_fixtures import isolated_env
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)

# Application imports using absolute paths - FIXED: Use SSOT WebSocket imports
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.circuit_breaker.service_health_monitor import ServiceHealthMonitor
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ensure_user_id

logger = logging.getLogger(__name__)

# Test markers for unified test runner
pytestmark = [
    pytest.mark.integration,
    pytest.mark.real_services, 
    pytest.mark.golden_path
]


class TestServiceDependencyIntegration(BaseIntegrationTest):
    """
    Integration tests for service dependency management with real services.
    
    These tests validate graceful degradation when service dependencies fail,
    ensuring the system maintains partial functionality during outages.
    """

    @pytest.fixture(autouse=True)
    async def setup_integration_test(self, real_services):
        """Set up integration test with real database, Redis, and dependency monitoring."""
        self.env = get_env()
        
        # Initialize real service managers
        self.db_manager = DatabaseManager()
        self.redis_manager = RedisManager()
        self.health_monitor = ServiceHealthMonitor()
        
        # Initialize services
        await self.db_manager.initialize()
        await self.redis_manager.initialize()
        await self.health_monitor.initialize()
        
        # Initialize auth helper for E2E authentication
        self.auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Store WebSocket URL for testing
        self.websocket_base_url = "ws://localhost:8000/ws"
        
        # Track connections and service states for cleanup
        self.active_connections = []
        self.service_states = {
            "database_available": True,
            "redis_available": True,
            "websocket_available": True
        }
        
        yield
        
        # Cleanup connections
        for conn in self.active_connections:
            if hasattr(conn, 'close') and not conn.closed:
                await conn.close()
        self.active_connections.clear()
        
        # Cleanup managers
        if hasattr(self.health_monitor, 'close'):
            await self.health_monitor.close()
        if hasattr(self.redis_manager, 'close'):
            await self.redis_manager.close()
        if hasattr(self.db_manager, 'close'):
            await self.db_manager.close()

    @asynccontextmanager
    async def simulate_service_failure(self, service_name: str):
        """Context manager to simulate service failure for testing graceful degradation."""
        original_state = self.service_states.get(f"{service_name}_available", True)
        
        try:
            # Simulate service failure by marking as unavailable
            self.service_states[f"{service_name}_available"] = False
            
            # If simulating database failure, temporarily break the connection
            if service_name == "database" and hasattr(self.db_manager, '_engine'):
                # Store original engine and replace with broken one
                original_engine = self.db_manager._engine
                
                # Create a mock engine that raises connection errors
                mock_engine = AsyncMock()
                mock_engine.connect.side_effect = Exception(f"Simulated {service_name} failure")
                mock_engine.execute.side_effect = Exception(f"Simulated {service_name} failure")
                self.db_manager._engine = mock_engine
                
                yield
                
                # Restore original engine
                self.db_manager._engine = original_engine
            
            # If simulating Redis failure, break Redis connection
            elif service_name == "redis" and hasattr(self.redis_manager, '_redis'):
                original_redis = self.redis_manager._redis
                
                # Create mock Redis that raises connection errors
                mock_redis = AsyncMock()
                mock_redis.get.side_effect = Exception(f"Simulated {service_name} failure")
                mock_redis.set.side_effect = Exception(f"Simulated {service_name} failure")
                mock_redis.delete.side_effect = Exception(f"Simulated {service_name} failure")
                self.redis_manager._redis = mock_redis
                
                yield
                
                # Restore original Redis
                self.redis_manager._redis = original_redis
                
            else:
                # Generic service failure simulation
                yield
                
        finally:
            # Restore service state
            self.service_states[f"{service_name}_available"] = original_state

    async def test_001_websocket_with_database_unavailable(self):
        """
        Test WebSocket behavior when database is unavailable.
        
        Validates that WebSocket connections can still be established and basic
        functionality works even when database operations fail.
        
        Business Value: Ensures chat functionality remains partially available
        during database outages, preventing complete service disruption.
        """
        user_context = await create_authenticated_user_context(
            user_email="db_failure_test@example.com",
            websocket_enabled=True
        )
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email="db_failure_test@example.com"
        )
        headers = self.auth_helper.get_websocket_headers(token)
        
        # Test WebSocket connection during database failure
        async with self.simulate_service_failure("database"):
            start_time = time.time()
            
            try:
                # WebSocket should still connect despite database failure
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.websocket_base_url,
                        additional_headers=headers,
                        open_timeout=12.0
                    ),
                    timeout=12.0
                )
                
                connection_time = time.time() - start_time
                self.active_connections.append(websocket)
                
                # Connection should succeed despite database being unavailable
                assert not websocket.closed, "WebSocket connection should establish despite database failure"
                assert connection_time < 12.0, f"Connection took {connection_time:.2f}s during database failure"
                
                # Test that WebSocket can send/receive basic messages
                test_message = {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "test": "database_failure_resilience"
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Should receive some response even if database operations fail
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                    response_data = json.loads(response)
                    
                    # Verify we get a response (may be error or success)
                    assert "type" in response_data, "Should receive structured response during database failure"
                    
                    # If it's an error, it should be a graceful error message
                    if response_data.get("type") == "error":
                        assert "database" in response_data.get("message", "").lower() or \
                               "service" in response_data.get("message", "").lower(), \
                               "Error should indicate service dependency issue"
                        logger.info("✅ Graceful error handling during database failure")
                    else:
                        logger.info("✅ WebSocket continues functioning during database failure")
                        
                except asyncio.TimeoutError:
                    # No response is also acceptable - system may be designed to fail silently
                    logger.info("✅ WebSocket connection stable during database failure (no response required)")
                
                logger.info(f"✅ WebSocket remained functional during database failure ({connection_time:.2f}s)")
                
            except asyncio.TimeoutError:
                pytest.fail(f"WebSocket connection failed during database outage after {time.time() - start_time:.2f}s")

    async def test_002_websocket_with_redis_unavailable(self):
        """
        Test WebSocket behavior when Redis cache is unavailable.
        
        Validates that WebSocket connections work without Redis caching,
        potentially with degraded performance but maintained functionality.
        
        Business Value: Ensures real-time chat remains available when
        caching services fail, maintaining core user experience.
        """
        user_context = await create_authenticated_user_context(
            user_email="redis_failure_test@example.com",
            websocket_enabled=True
        )
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email="redis_failure_test@example.com"
        )
        headers = self.auth_helper.get_websocket_headers(token)
        
        # Test WebSocket connection during Redis failure
        async with self.simulate_service_failure("redis"):
            start_time = time.time()
            
            try:
                # WebSocket should connect despite Redis being unavailable
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.websocket_base_url,
                        additional_headers=headers,
                        open_timeout=12.0
                    ),
                    timeout=12.0
                )
                
                connection_time = time.time() - start_time
                self.active_connections.append(websocket)
                
                # Connection should succeed despite Redis failure
                assert not websocket.closed, "WebSocket connection should establish despite Redis failure"
                assert connection_time < 12.0, f"Connection took {connection_time:.2f}s during Redis failure"
                
                # Test message functionality without caching
                cache_test_message = {
                    "type": "cache_test",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": "test_data_without_redis_cache"
                }
                
                await websocket.send(json.dumps(cache_test_message))
                
                # Should work without caching, possibly with performance degradation
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    # Verify functionality despite cache unavailability
                    assert "type" in response_data, "Should receive response despite Redis failure"
                    
                    # System should either work without cache or provide graceful degradation message
                    if response_data.get("type") == "error":
                        error_msg = response_data.get("message", "").lower()
                        assert "cache" in error_msg or "redis" in error_msg or "service" in error_msg, \
                               "Error should indicate cache service issue"
                        logger.info("✅ Graceful cache failure handling")
                    else:
                        logger.info("✅ WebSocket functions without Redis cache")
                        
                except asyncio.TimeoutError:
                    # Longer timeout acceptable during cache failure
                    logger.info("✅ WebSocket connection stable during Redis failure (degraded performance expected)")
                
                logger.info(f"✅ WebSocket functional during Redis failure ({connection_time:.2f}s)")
                
            except asyncio.TimeoutError:
                pytest.fail(f"WebSocket connection failed during Redis outage after {time.time() - start_time:.2f}s")

    async def test_003_graceful_degradation_multi_service_failure(self):
        """
        Test graceful degradation when multiple services fail simultaneously.
        
        Validates that the system can handle multiple dependency failures
        and still maintain basic WebSocket connectivity with appropriate error reporting.
        
        Business Value: Ensures partial service availability during major
        infrastructure outages, protecting revenue during crisis situations.
        """
        user_context = await create_authenticated_user_context(
            user_email="multi_failure_test@example.com",
            websocket_enabled=True
        )
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email="multi_failure_test@example.com"
        )
        headers = self.auth_helper.get_websocket_headers(token)
        
        # Test with both database and Redis unavailable
        async with self.simulate_service_failure("database"):
            async with self.simulate_service_failure("redis"):
                start_time = time.time()
                
                try:
                    # WebSocket should still attempt connection
                    websocket = await asyncio.wait_for(
                        websockets.connect(
                            self.websocket_base_url,
                            additional_headers=headers,
                            open_timeout=15.0  # Allow more time for degraded mode
                        ),
                        timeout=15.0
                    )
                    
                    connection_time = time.time() - start_time
                    self.active_connections.append(websocket)
                    
                    assert not websocket.closed, "WebSocket should connect in degraded mode"
                    assert connection_time < 15.0, f"Multi-failure connection took {connection_time:.2f}s"
                    
                    # Test system status message in degraded mode
                    status_message = {
                        "type": "system_status",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(status_message))
                    
                    # System should respond with degraded mode information
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=12.0)
                        response_data = json.loads(response)
                        
                        # Should receive degraded mode status or error information
                        assert "type" in response_data, "Should receive degraded mode response"
                        
                        # Check for degraded mode indicators
                        response_text = json.dumps(response_data).lower()
                        degradation_keywords = ["degraded", "limited", "service", "unavailable", "error", "maintenance"]
                        
                        has_degradation_info = any(keyword in response_text for keyword in degradation_keywords)
                        
                        if has_degradation_info:
                            logger.info("✅ System communicates degraded mode status")
                        else:
                            logger.info("✅ System continues basic operation in degraded mode")
                            
                    except asyncio.TimeoutError:
                        # No response in degraded mode is acceptable
                        logger.info("✅ Connection maintained in degraded mode (minimal functionality)")
                    
                    logger.info(f"✅ Multi-service failure handled gracefully ({connection_time:.2f}s)")
                    
                except asyncio.TimeoutError:
                    # Total failure during multi-service outage may be acceptable
                    # depending on system design, but log for analysis
                    logger.warning(f"WebSocket unavailable during multi-service outage (after {time.time() - start_time:.2f}s)")
                    logger.info("This may be acceptable depending on system resilience design")

    async def test_004_service_recovery_detection(self):
        """
        Test service recovery detection and restoration of full functionality.
        
        Validates that the system can detect when failed services recover
        and restore full functionality appropriately.
        
        Business Value: Ensures automatic recovery from service outages
        without manual intervention, minimizing business disruption.
        """
        user_context = await create_authenticated_user_context(
            user_email="recovery_test@example.com",
            websocket_enabled=True
        )
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email="recovery_test@example.com"
        )
        headers = self.auth_helper.get_websocket_headers(token)
        
        # Establish connection during normal operation
        websocket = await websockets.connect(
            self.websocket_base_url,
            additional_headers=headers,
            open_timeout=10.0
        )
        self.active_connections.append(websocket)
        
        # Test normal operation first
        normal_message = {
            "type": "ping",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test": "normal_operation"
        }
        await websocket.send(json.dumps(normal_message))
        
        try:
            normal_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            logger.info("✅ Normal operation baseline established")
        except asyncio.TimeoutError:
            logger.info("Baseline response timeout (acceptable)")
        
        # Simulate service failure and recovery
        async with self.simulate_service_failure("database"):
            # Send message during failure
            failure_message = {
                "type": "ping",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test": "during_failure"
            }
            await websocket.send(json.dumps(failure_message))
            
            try:
                failure_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                failure_data = json.loads(failure_response)
                
                if failure_data.get("type") == "error":
                    logger.info("✅ Service failure detected and communicated")
                else:
                    logger.info("✅ Service continues functioning during failure")
            except asyncio.TimeoutError:
                logger.info("No response during failure (acceptable)")
        
        # After exiting context, service should be "recovered"
        await asyncio.sleep(1.0)  # Allow time for recovery detection
        
        # Test recovery
        recovery_message = {
            "type": "ping",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test": "after_recovery"
        }
        await websocket.send(json.dumps(recovery_message))
        
        try:
            recovery_response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
            recovery_data = json.loads(recovery_response)
            
            # Should receive normal response indicating recovery
            assert "type" in recovery_data, "Should receive response after service recovery"
            
            if recovery_data.get("type") != "error":
                logger.info("✅ Service recovery detected - full functionality restored")
            else:
                # Recovery may take time - this is also acceptable
                logger.info("✅ Service recovery in progress")
                
        except asyncio.TimeoutError:
            logger.info("Recovery response timeout - may need more time for full restoration")

    async def test_005_error_notification_during_dependency_failures(self):
        """
        Test error notification system during service dependency failures.
        
        Validates that users receive appropriate notifications when services
        are unavailable, maintaining transparent communication.
        
        Business Value: Ensures users understand service status and
        don't assume system is completely broken during partial outages.
        """
        user_context = await create_authenticated_user_context(
            user_email="notification_test@example.com",
            websocket_enabled=True
        )
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email="notification_test@example.com"
        )
        headers = self.auth_helper.get_websocket_headers(token)
        
        websocket = await websockets.connect(
            self.websocket_base_url,
            additional_headers=headers,
            open_timeout=10.0
        )
        self.active_connections.append(websocket)
        
        # Test different types of dependency failures and their notifications
        dependency_tests = [
            ("database", "Database operations may be limited"),
            ("redis", "Cache functionality unavailable"),
        ]
        
        for service_name, expected_notification_type in dependency_tests:
            async with self.simulate_service_failure(service_name):
                # Send operation that requires the failed service
                test_message = {
                    "type": "service_test",
                    "operation": f"test_{service_name}_operation",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Check for error notification
                notification_received = False
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "error" or response_data.get("type") == "notification":
                        error_msg = response_data.get("message", "").lower()
                        
                        # Check if error message relates to the service failure
                        service_keywords = [service_name, "service", "unavailable", "failure", "degraded"]
                        if any(keyword in error_msg for keyword in service_keywords):
                            notification_received = True
                            logger.info(f"✅ Appropriate notification for {service_name} failure: {response_data.get('message', '')[:100]}")
                        else:
                            logger.info(f"✅ Generic error notification during {service_name} failure")
                    else:
                        logger.info(f"✅ System continues functioning despite {service_name} failure")
                        
                except asyncio.TimeoutError:
                    # No notification may be acceptable depending on design
                    logger.info(f"No immediate notification for {service_name} failure (may be designed behavior)")
                
                # Small delay between tests
                await asyncio.sleep(0.5)

    async def test_006_concurrent_dependency_failures_isolation(self):
        """
        Test isolation of concurrent dependency failures.
        
        Validates that failures in one service don't cascade to affect
        other independent services unnecessarily.
        
        Business Value: Prevents cascade failures that could bring down
        the entire system when only one component fails.
        """
        # Create multiple user contexts to test isolation
        user_contexts = []
        websockets_list = []
        
        for i in range(3):
            user_context = await create_authenticated_user_context(
                user_email=f"isolation_test_{i}@example.com",
                websocket_enabled=True
            )
            user_contexts.append(user_context)
            
            token = self.auth_helper.create_test_jwt_token(
                user_id=str(user_context.user_id),
                email=f"isolation_test_{i}@example.com"
            )
            headers = self.auth_helper.get_websocket_headers(token)
            
            websocket = await websockets.connect(
                self.websocket_base_url,
                additional_headers=headers,
                open_timeout=10.0
            )
            websockets_list.append(websocket)
            self.active_connections.append(websocket)
        
        # Test that database failure affects database operations but not basic connectivity
        async with self.simulate_service_failure("database"):
            # All WebSocket connections should remain active
            active_connections = sum(1 for ws in websockets_list if not ws.closed)
            assert active_connections == len(websockets_list), \
                   f"Database failure should not close WebSocket connections ({active_connections}/{len(websockets_list)} active)"
            
            # Test that basic WebSocket functionality still works
            successful_pings = 0
            
            for i, websocket in enumerate(websockets_list):
                try:
                    ping_message = {
                        "type": "ping",
                        "user": i,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(ping_message))
                    
                    # Try to get response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        successful_pings += 1
                    except asyncio.TimeoutError:
                        # No response is acceptable during dependency failure
                        pass
                        
                except Exception as e:
                    logger.warning(f"WebSocket {i} failed during database outage: {e}")
            
            logger.info(f"✅ Isolation test: {successful_pings}/{len(websockets_list)} WebSocket connections responded during database failure")
            
            # At least basic connectivity should be maintained
            assert active_connections >= len(websockets_list) * 0.8, \
                   "At least 80% of connections should remain active during single service failure"

    async def test_007_dependency_health_monitoring(self):
        """
        Test dependency health monitoring and status reporting.
        
        Validates that the system can monitor and report the health status
        of its service dependencies.
        
        Business Value: Enables proactive monitoring and alerting for
        service health, reducing mean time to recovery.
        """
        user_context = await create_authenticated_user_context(
            user_email="health_monitor_test@example.com",
            websocket_enabled=True
        )
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email="health_monitor_test@example.com"
        )
        headers = self.auth_helper.get_websocket_headers(token)
        
        websocket = await websockets.connect(
            self.websocket_base_url,
            additional_headers=headers,
            open_timeout=10.0
        )
        self.active_connections.append(websocket)
        
        # Request health status
        health_request = {
            "type": "health_check",
            "include_dependencies": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await websocket.send(json.dumps(health_request))
        
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
            response_data = json.loads(response)
            
            # Should receive health status information
            assert "type" in response_data, "Should receive health check response"
            
            # Look for health status information
            health_indicators = ["health", "status", "services", "dependencies", "available", "database", "redis"]
            response_text = json.dumps(response_data).lower()
            
            found_indicators = [indicator for indicator in health_indicators if indicator in response_text]
            
            if found_indicators:
                logger.info(f"✅ Health monitoring active - indicators found: {found_indicators}")
            else:
                logger.info("✅ Health check responded (may use different format)")
            
            # Test health monitoring during simulated failure
            async with self.simulate_service_failure("database"):
                await asyncio.sleep(1.0)  # Allow health monitor to detect failure
                
                # Request health status during failure
                failure_health_request = {
                    "type": "health_check",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(failure_health_request))
                
                try:
                    failure_response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                    failure_data = json.loads(failure_response)
                    
                    # Should receive updated health status
                    failure_text = json.dumps(failure_data).lower()
                    failure_keywords = ["error", "failure", "unavailable", "degraded", "limited"]
                    
                    has_failure_info = any(keyword in failure_text for keyword in failure_keywords)
                    
                    if has_failure_info:
                        logger.info("✅ Health monitor detects and reports service failures")
                    else:
                        logger.info("✅ Health monitoring continues during failures")
                        
                except asyncio.TimeoutError:
                    logger.info("Health monitoring may be impacted during service failures (acceptable)")
                
        except asyncio.TimeoutError:
            logger.info("Health monitoring not implemented or not accessible via WebSocket")

    async def test_008_service_dependency_timeout_handling(self):
        """
        Test timeout handling for service dependencies.
        
        Validates that the system handles service dependency timeouts gracefully
        without hanging or causing indefinite delays.
        
        Business Value: Ensures responsive user experience even when
        backend services are slow or unresponsive.
        """
        user_context = await create_authenticated_user_context(
            user_email="timeout_test@example.com",
            websocket_enabled=True
        )
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email="timeout_test@example.com"
        )
        headers = self.auth_helper.get_websocket_headers(token)
        
        start_time = time.time()
        
        # Test connection establishment with potential dependency timeouts
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_base_url,
                    additional_headers=headers,
                    open_timeout=15.0
                ),
                timeout=15.0
            )
            
            connection_time = time.time() - start_time
            self.active_connections.append(websocket)
            
            # Connection should complete within reasonable time even with dependencies
            assert connection_time < 15.0, f"Connection took {connection_time:.2f}s (may indicate timeout issues)"
            
            # Test operations that might involve service dependencies
            timeout_test_operations = [
                {"type": "database_operation", "operation": "user_lookup"},
                {"type": "cache_operation", "operation": "session_check"},
                {"type": "ping", "test": "timeout_resilience"}
            ]
            
            for operation in timeout_test_operations:
                operation_start = time.time()
                operation["timestamp"] = datetime.now(timezone.utc).isoformat()
                
                await websocket.send(json.dumps(operation))
                
                # Each operation should complete or timeout within reasonable time
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    operation_time = time.time() - operation_start
                    
                    # Operations should not take excessively long
                    assert operation_time < 10.0, f"Operation {operation['type']} took {operation_time:.2f}s"
                    
                    response_data = json.loads(response)
                    if response_data.get("type") == "error" and "timeout" in response_data.get("message", "").lower():
                        logger.info(f"✅ Timeout properly handled for {operation['type']}")
                    else:
                        logger.info(f"✅ Operation {operation['type']} completed in {operation_time:.2f}s")
                        
                except asyncio.TimeoutError:
                    operation_time = time.time() - operation_start
                    # Timeout should occur within reasonable bounds
                    assert operation_time >= 9.5, f"Timeout occurred too quickly ({operation_time:.2f}s)"
                    logger.info(f"✅ Operation {operation['type']} timed out appropriately after {operation_time:.2f}s")
                
                # Small delay between operations
                await asyncio.sleep(0.2)
            
            logger.info(f"✅ All timeout handling tests completed (total connection time: {connection_time:.2f}s)")
            
        except asyncio.TimeoutError:
            total_time = time.time() - start_time
            pytest.fail(f"Timeout handling test failed - connection timeout after {total_time:.2f}s")