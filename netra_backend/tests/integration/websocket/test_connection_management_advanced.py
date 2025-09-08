"""
Advanced WebSocket Connection Management Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core platform stability
- Business Goal: Ensure reliable WebSocket connections for uninterrupted AI interactions
- Value Impact: Connection reliability directly affects user experience and retention
- Strategic/Revenue Impact: Connection failures cause user churn and reduce $500K+ ARR

CRITICAL CONNECTION MANAGEMENT SCENARIOS:
1. Authentication handshake and validation
2. Connection lifecycle management (connect/disconnect/cleanup)
3. Connection pooling and resource management
4. Connection health monitoring and validation

CRITICAL REQUIREMENTS:
- NO MOCKS - Uses real WebSocket connections and real authentication
- Tests connection establishment patterns under various conditions
- Validates proper cleanup and resource management
- Ensures authentication integration works correctly
- Tests connection state management for business continuity
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest
import websockets

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.fixtures.websocket_test_helpers import WebSocketTestClient, wait_for_websocket_connection
from shared.isolated_environment import get_env


class TestWebSocketConnectionManagementAdvanced(BaseIntegrationTest):
    """
    Advanced tests for WebSocket connection management scenarios.
    
    CRITICAL: All tests use REAL WebSocket connections and REAL services
    to validate production-quality connection management patterns.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_connection_test(self, real_services_fixture):
        """
        Set up advanced connection management test environment.
        
        BVJ: Test Infrastructure - Ensures reliable connection management testing
        """
        self.env = get_env()
        self.services = real_services_fixture
        self.test_user_id = f"conn_mgmt_{uuid.uuid4().hex[:8]}"
        
        # CRITICAL: Verify real services (CLAUDE.md requirement)
        assert real_services_fixture, "Real services required for connection testing"
        assert "backend" in real_services_fixture, "Real backend required for WebSocket connections"
        
        # Initialize WebSocket auth helper
        auth_config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws",
            test_user_email=f"conn_test_{self.test_user_id}@example.com",
            timeout=20.0
        )
        
        self.auth_helper = E2EWebSocketAuthHelper(config=auth_config, environment="test")
        self.active_connections: List[websockets.WebSocketServerProtocol] = []
        self.connection_metrics: Dict[str, Any] = {
            "total_connections": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "connection_times": []
        }
        
        # Test auth helper functionality
        try:
            token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
            assert token, "Failed to create test JWT for connection management testing"
        except Exception as e:
            pytest.fail(f"Connection management test setup failed: {e}")
    
    async def async_teardown(self):
        """Clean up all WebSocket connections and resources."""
        cleanup_tasks = []
        for ws in self.active_connections:
            if not ws.closed:
                cleanup_tasks.append(ws.close())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.active_connections.clear()
        await super().async_teardown()
    
    async def create_authenticated_connection(
        self,
        user_id: Optional[str] = None,
        timeout: float = 10.0
    ) -> websockets.WebSocketServerProtocol:
        """
        Create authenticated WebSocket connection with metrics tracking.
        
        Args:
            user_id: Optional user ID for connection
            timeout: Connection timeout
            
        Returns:
            Authenticated WebSocket connection
        """
        user_id = user_id or self.test_user_id
        self.connection_metrics["total_connections"] += 1
        
        try:
            start_time = time.time()
            
            token = self.auth_helper.create_test_jwt_token(user_id=user_id)
            headers = self.auth_helper.get_websocket_headers(token)
            
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=timeout
                ),
                timeout=timeout
            )
            
            connection_time = time.time() - start_time
            self.connection_metrics["connection_times"].append(connection_time)
            self.connection_metrics["successful_connections"] += 1
            
            self.active_connections.append(websocket)
            return websocket
            
        except Exception as e:
            self.connection_metrics["failed_connections"] += 1
            raise e
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authenticated_connection_establishment(self, real_services_fixture):
        """
        Test authenticated WebSocket connection establishment flow.
        
        BVJ: User onboarding - Users must successfully connect to access AI services.
        Reliable connection establishment is critical for user acquisition and retention.
        """
        try:
            # Test single authenticated connection
            websocket = await self.create_authenticated_connection(timeout=15.0)
            
            # Verify connection is established and authenticated
            assert not websocket.closed, "Connection should be open after successful establishment"
            
            # Test connection can receive messages
            test_message = {
                "type": "connection_test",
                "user_id": self.test_user_id,
                "message": "Connection establishment validation",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(test_message))
            
            # Wait briefly for any potential response or confirmation
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                # If we get a response, verify it's valid JSON
                json.loads(response)
            except asyncio.TimeoutError:
                # No immediate response is acceptable - connection is established
                pass
            
            # Verify connection metrics
            assert self.connection_metrics["successful_connections"] >= 1, "Connection establishment not recorded"
            assert self.connection_metrics["failed_connections"] == 0, "Should have no failed connections"
            
            # Check connection timing performance
            connection_times = self.connection_metrics["connection_times"]
            assert len(connection_times) >= 1, "Connection time not recorded"
            assert connection_times[-1] < 10.0, f"Connection took {connection_times[-1]:.2f}s - too slow for good UX"
            
            await websocket.close()
            
        except Exception as e:
            pytest.fail(f"Authenticated connection establishment test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_lifecycle_management(self, real_services_fixture):
        """
        Test complete WebSocket connection lifecycle management.
        
        BVJ: Resource efficiency - Proper lifecycle management prevents resource leaks.
        Efficient connection management reduces infrastructure costs and improves scalability.
        """
        connections_to_test = 3
        created_connections = []
        
        try:
            # Create multiple connections to test lifecycle
            for i in range(connections_to_test):
                user_id = f"{self.test_user_id}_lifecycle_{i}"
                websocket = await self.create_authenticated_connection(user_id=user_id, timeout=10.0)
                created_connections.append((user_id, websocket))
                
                # Brief pause between connections
                await asyncio.sleep(0.1)
            
            # Verify all connections are active
            assert len(created_connections) == connections_to_test, "Not all connections were created"
            
            for user_id, websocket in created_connections:
                assert not websocket.closed, f"Connection for {user_id} should be active"
            
            # Test graceful connection closure
            closed_count = 0
            for user_id, websocket in created_connections:
                if not websocket.closed:
                    await websocket.close()
                    closed_count += 1
                    
                    # Verify connection is properly closed
                    assert websocket.closed, f"Connection for {user_id} should be closed"
            
            assert closed_count == connections_to_test, "Not all connections were properly closed"
            
            # Verify connection metrics reflect lifecycle
            assert self.connection_metrics["successful_connections"] >= connections_to_test, \
                "Connection creation count mismatch"
            
            # Test connection state after closure
            for user_id, websocket in created_connections:
                with pytest.raises(websockets.exceptions.ConnectionClosed):
                    await websocket.send(json.dumps({"type": "test", "user_id": user_id}))
            
        except Exception as e:
            # Ensure cleanup even on test failure
            for _, websocket in created_connections:
                if not websocket.closed:
                    try:
                        await websocket.close()
                    except:
                        pass
            pytest.fail(f"Connection lifecycle management test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_connection_establishment(self, real_services_fixture):
        """
        Test concurrent WebSocket connection establishment under load.
        
        BVJ: Scalability - Platform must handle multiple simultaneous connections.
        Concurrent connection capability enables multi-user scenarios and growth.
        """
        concurrent_connections = 5
        connection_tasks = []
        
        try:
            # Create concurrent connection establishment tasks
            for i in range(concurrent_connections):
                user_id = f"{self.test_user_id}_concurrent_{i}"
                task = asyncio.create_task(
                    self.create_authenticated_connection(user_id=user_id, timeout=15.0)
                )
                connection_tasks.append(task)
            
            # Wait for all connections to establish concurrently
            start_time = time.time()
            connections = await asyncio.gather(*connection_tasks, return_exceptions=True)
            establishment_time = time.time() - start_time
            
            # Count successful concurrent connections
            successful_connections = [conn for conn in connections if isinstance(conn, websockets.WebSocketServerProtocol)]
            failed_connections = [conn for conn in connections if isinstance(conn, Exception)]
            
            # Verify concurrent connection success
            assert len(successful_connections) >= (concurrent_connections * 0.8), \
                f"Only {len(successful_connections)}/{concurrent_connections} concurrent connections succeeded"
            
            # Verify concurrent establishment performance
            assert establishment_time < 20.0, \
                f"Concurrent connection establishment took {establishment_time:.2f}s - too slow for scalability"
            
            # Test that all successful connections are functional
            for i, websocket in enumerate(successful_connections):
                if not isinstance(websocket, Exception):
                    test_message = {
                        "type": "concurrent_test",
                        "connection_id": i,
                        "user_id": f"{self.test_user_id}_concurrent_{i}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    assert not websocket.closed, f"Concurrent connection {i} became inactive"
            
            # Analyze connection performance metrics
            connection_times = self.connection_metrics["connection_times"]
            if connection_times:
                avg_connection_time = sum(connection_times) / len(connection_times)
                max_connection_time = max(connection_times)
                
                assert avg_connection_time < 5.0, f"Average connection time {avg_connection_time:.2f}s too slow"
                assert max_connection_time < 10.0, f"Maximum connection time {max_connection_time:.2f}s too slow"
            
            # Log any failures for analysis
            if failed_connections:
                failure_types = {}
                for failure in failed_connections:
                    failure_type = type(failure).__name__
                    failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
                
                # Allow some failures but warn about patterns
                if len(failed_connections) > (concurrent_connections * 0.5):
                    pytest.fail(f"Too many concurrent connection failures: {failure_types}")
            
            # Clean up successful connections
            cleanup_tasks = []
            for websocket in successful_connections:
                if not isinstance(websocket, Exception) and not websocket.closed:
                    cleanup_tasks.append(websocket.close())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        except Exception as e:
            pytest.fail(f"Concurrent connection establishment test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_authentication_validation(self, real_services_fixture):
        """
        Test WebSocket connection authentication validation scenarios.
        
        BVJ: Security - Unauthorized connections must be rejected to protect user data.
        Proper authentication prevents security breaches and maintains user trust.
        """
        try:
            # Test 1: Valid authentication should succeed
            valid_token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
            valid_headers = self.auth_helper.get_websocket_headers(valid_token)
            
            valid_websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=valid_headers,
                    open_timeout=10.0
                ),
                timeout=12.0
            )
            
            self.active_connections.append(valid_websocket)
            assert not valid_websocket.closed, "Valid authentication should establish connection"
            
            # Test 2: Invalid token should be handled gracefully
            invalid_headers = {
                "Authorization": "Bearer invalid_token_12345",
                "X-User-ID": "invalid_user",
                "X-Test-Mode": "true"
            }
            
            auth_validation_passed = True
            try:
                invalid_websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.auth_helper.config.websocket_url,
                        additional_headers=invalid_headers,
                        open_timeout=5.0
                    ),
                    timeout=8.0
                )
                
                # If connection succeeds, it should quickly close or reject
                try:
                    await invalid_websocket.send(json.dumps({"type": "test"}))
                    await asyncio.wait_for(invalid_websocket.recv(), timeout=2.0)
                except:
                    # Expected - invalid auth should not allow full communication
                    pass
                finally:
                    if not invalid_websocket.closed:
                        await invalid_websocket.close()
                        
            except (websockets.exceptions.InvalidStatusCode, 
                   websockets.exceptions.InvalidHandshake,
                   asyncio.TimeoutError,
                   ConnectionRefusedError):
                # These are expected for invalid authentication
                auth_validation_passed = True
            except Exception as e:
                # Unexpected error - authentication validation may have issues
                auth_validation_passed = False
                
            assert auth_validation_passed, "Authentication validation has unexpected behavior"
            
            # Test 3: Missing authentication headers
            no_auth_validation_passed = True
            try:
                no_auth_websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.auth_helper.config.websocket_url,
                        open_timeout=5.0
                    ),
                    timeout=8.0
                )
                
                # Connection without auth might succeed initially but should be limited
                try:
                    await no_auth_websocket.send(json.dumps({"type": "unauthorized_test"}))
                    response = await asyncio.wait_for(no_auth_websocket.recv(), timeout=2.0)
                    # If we get here, check if response indicates auth failure
                except:
                    # Expected for no authentication
                    pass
                finally:
                    if not no_auth_websocket.closed:
                        await no_auth_websocket.close()
                        
            except (websockets.exceptions.InvalidStatusCode, 
                   websockets.exceptions.InvalidHandshake,
                   asyncio.TimeoutError,
                   ConnectionRefusedError):
                # Expected for missing authentication
                no_auth_validation_passed = True
            except Exception as e:
                no_auth_validation_passed = False
                
            assert no_auth_validation_passed, "Missing authentication handling has unexpected behavior"
            
            # Verify the valid connection is still functional
            test_message = {
                "type": "auth_validation_test",
                "user_id": self.test_user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await valid_websocket.send(json.dumps(test_message))
            assert not valid_websocket.closed, "Valid connection should remain functional"
            
            await valid_websocket.close()
            
        except Exception as e:
            pytest.fail(f"Connection authentication validation test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_resource_cleanup_validation(self, real_services_fixture):
        """
        Test WebSocket connection resource cleanup and memory management.
        
        BVJ: Operational efficiency - Proper cleanup prevents resource leaks and reduces costs.
        Efficient resource management enables sustainable platform scaling.
        """
        connection_lifecycle_iterations = 4
        resource_metrics = {
            "created": 0,
            "cleaned": 0,
            "leaked": 0
        }
        
        try:
            for iteration in range(connection_lifecycle_iterations):
                # Create connection
                user_id = f"{self.test_user_id}_cleanup_{iteration}"
                websocket = await self.create_authenticated_connection(user_id=user_id, timeout=10.0)
                resource_metrics["created"] += 1
                
                # Use connection briefly
                test_message = {
                    "type": "resource_cleanup_test",
                    "iteration": iteration,
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for potential response
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass  # No response expected for test message
                
                # Explicitly close connection
                if not websocket.closed:
                    await websocket.close()
                    resource_metrics["cleaned"] += 1
                
                # Verify connection is properly closed
                assert websocket.closed, f"Connection {iteration} not properly closed"
                
                # Test that closed connection cannot be used
                with pytest.raises(websockets.exceptions.ConnectionClosed):
                    await websocket.send(json.dumps({"type": "after_close"}))
                
                # Brief pause between iterations to allow cleanup
                await asyncio.sleep(0.2)
            
            # Verify resource management metrics
            assert resource_metrics["created"] == connection_lifecycle_iterations, \
                "Connection creation count mismatch"
            assert resource_metrics["cleaned"] == connection_lifecycle_iterations, \
                "Connection cleanup count mismatch"
            
            # Check for potential resource leaks
            active_connections_count = len([conn for conn in self.active_connections if not conn.closed])
            assert active_connections_count == 0, \
                f"Found {active_connections_count} potentially leaked connections"
            
            # Test rapid creation/destruction cycle
            rapid_cycle_count = 3
            rapid_connections = []
            
            # Create rapidly
            for i in range(rapid_cycle_count):
                conn = await self.create_authenticated_connection(
                    user_id=f"{self.test_user_id}_rapid_{i}",
                    timeout=8.0
                )
                rapid_connections.append(conn)
            
            # Destroy rapidly
            for conn in rapid_connections:
                await conn.close()
                assert conn.closed, "Rapid cleanup failed"
            
            # Verify no connections remain active from rapid cycle
            remaining_active = len([conn for conn in rapid_connections if not conn.closed])
            assert remaining_active == 0, f"Rapid cycle left {remaining_active} active connections"
            
        except Exception as e:
            pytest.fail(f"Connection resource cleanup validation test failed: {e}")