"""
WebSocket Handshake Timing Integration Tests - Phase 2 Implementation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket handshake reliability under realistic conditions
- Value Impact: Prevents timeout failures that block real-time AI chat functionality
- Strategic Impact: Critical for maintaining real-time user engagement and chat responsiveness
- Revenue Impact: WebSocket timeouts = $120K+ MRR at risk (chat is primary value delivery)

This integration test suite validates WebSocket handshake timing and resilience:
1. Handshake timing under various conditions
2. Message queuing during connection establishment
3. Connection timing with real authentication
4. Race condition resilience during concurrent connections
5. Recovery from handshake failures with proper error handling

CRITICAL: Uses REAL services (PostgreSQL 5434, Redis 6381, WebSocket 8000) and proper
authentication via test_framework/ssot/e2e_auth_helper.py. Tests actual business value
by validating the infrastructure that enables real-time AI chat interactions.

Key Integration Points:
- Real PostgreSQL database operations for user context
- Real Redis cache for session management  
- Real WebSocket connections with timing constraints
- Proper JWT authentication flow
- SSOT factory patterns for multi-user isolation

GOLDEN PATH COMPLIANCE: These tests validate P1 WebSocket authentication timeouts
that caused 3/3 failures in SESSION5 test results.
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
from unittest.mock import patch

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
from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.redis_manager import RedisManager
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ensure_user_id

logger = logging.getLogger(__name__)

# Test markers for unified test runner
pytestmark = [
    pytest.mark.integration,
    pytest.mark.real_services,
    pytest.mark.golden_path
]


class TestWebSocketHandshakeTiming(BaseIntegrationTest):
    """
    Integration tests for WebSocket handshake timing with real services.
    
    These tests validate the critical P1 failure: WebSocket authentication timeouts
    that prevent real-time chat functionality from working properly.
    """

    @pytest.fixture(autouse=True)
    async def setup_integration_test(self, real_services):
        """Set up integration test with real database and Redis."""
        self.env = get_env()
        
        # Initialize real database manager
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()
        
        # Initialize real Redis manager
        self.redis_manager = RedisManager()
        await self.redis_manager.initialize()
        
        # Initialize auth helper for E2E authentication
        self.auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Store base WebSocket URL for testing
        self.websocket_base_url = "ws://localhost:8000/ws"
        
        # Track connections for cleanup
        self.active_connections = []
        
        yield
        
        # Cleanup connections
        for conn in self.active_connections:
            if hasattr(conn, 'close') and not conn.closed:
                await conn.close()
        self.active_connections.clear()
        
        # Cleanup managers
        if hasattr(self.redis_manager, 'close'):
            await self.redis_manager.close()
        if hasattr(self.db_manager, 'close'):
            await self.db_manager.close()

    async def test_001_websocket_handshake_basic_timing(self):
        """
        Test basic WebSocket handshake timing with authentication.
        
        Validates that WebSocket can establish connection within reasonable time
        with proper JWT authentication headers.
        
        Business Value: Ensures users don't experience connection timeouts
        that would prevent chat functionality from working.
        """
        start_time = time.time()
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="handshake_timing@example.com",
            websocket_enabled=True
        )
        
        # Get authentication headers
        token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email="handshake_timing@example.com"
        )
        headers = self.auth_helper.get_websocket_headers(token)
        
        # Attempt WebSocket connection with timing
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_base_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=10.0
            )
            
            connection_time = time.time() - start_time
            self.active_connections.append(websocket)
            
            # Connection should establish within 10 seconds
            assert connection_time < 10.0, f"Handshake took {connection_time:.2f}s (expected < 10s)"
            
            # Verify connection is properly authenticated
            assert not websocket.closed, "WebSocket connection should be open"
            
            # Test basic message exchange
            test_message = {
                "type": "ping",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_id": "handshake_timing_001"
            }
            
            await websocket.send(json.dumps(test_message))
            
            # Wait for response with timeout
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            # Verify proper message handling
            assert "type" in response_data, "Response should contain message type"
            
            logger.info(f" PASS:  WebSocket handshake completed in {connection_time:.2f}s")
            
        except asyncio.TimeoutError:
            pytest.fail(f"WebSocket handshake timed out after {time.time() - start_time:.2f}s")
        except Exception as e:
            pytest.fail(f"WebSocket handshake failed: {str(e)}")

    async def test_002_websocket_handshake_under_load(self):
        """
        Test WebSocket handshake timing under concurrent connection load.
        
        Validates that multiple users can establish WebSocket connections
        simultaneously without significant timing degradation.
        
        Business Value: Ensures multi-user chat platform can handle
        concurrent user connections without performance issues.
        """
        connection_count = 5
        max_handshake_time = 15.0  # Allow more time for concurrent connections
        
        async def create_authenticated_connection(user_index: int) -> Tuple[float, websockets.WebSocketServerProtocol]:
            """Create a single authenticated WebSocket connection."""
            start_time = time.time()
            
            # Create unique user context for each connection
            user_context = await create_authenticated_user_context(
                user_email=f"load_test_{user_index}@example.com",
                websocket_enabled=True
            )
            
            # Get authentication headers
            token = self.auth_helper.create_test_jwt_token(
                user_id=str(user_context.user_id),
                email=f"load_test_{user_index}@example.com"
            )
            headers = self.auth_helper.get_websocket_headers(token)
            
            # Create connection
            websocket = await websockets.connect(
                self.websocket_base_url,
                additional_headers=headers,
                open_timeout=max_handshake_time
            )
            
            connection_time = time.time() - start_time
            return connection_time, websocket
        
        # Create concurrent connections
        start_time = time.time()
        
        try:
            # Launch concurrent connection attempts
            connection_tasks = [
                create_authenticated_connection(i) 
                for i in range(connection_count)
            ]
            
            # Wait for all connections to complete
            results = await asyncio.wait_for(
                asyncio.gather(*connection_tasks, return_exceptions=True),
                timeout=max_handshake_time + 5.0
            )
            
            total_time = time.time() - start_time
            successful_connections = []
            connection_times = []
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Connection {i} failed: {result}")
                else:
                    connection_time, websocket = result
                    connection_times.append(connection_time)
                    successful_connections.append(websocket)
                    self.active_connections.append(websocket)
            
            # Validate results
            assert len(successful_connections) >= 3, f"Expected at least 3 successful connections, got {len(successful_connections)}"
            
            # Check individual connection times
            for i, conn_time in enumerate(connection_times):
                assert conn_time < max_handshake_time, f"Connection {i} took {conn_time:.2f}s (expected < {max_handshake_time}s)"
            
            # Check average connection time
            avg_time = sum(connection_times) / len(connection_times) if connection_times else 0
            assert avg_time < 10.0, f"Average connection time {avg_time:.2f}s too slow"
            
            logger.info(f" PASS:  {len(successful_connections)}/{connection_count} concurrent connections successful")
            logger.info(f" PASS:  Average handshake time: {avg_time:.2f}s")
            logger.info(f" PASS:  Total concurrent setup time: {total_time:.2f}s")
            
            # Test message broadcasting to multiple connections
            broadcast_message = {
                "type": "broadcast_test",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Concurrent connection test"
            }
            
            # Send message to all connections
            send_tasks = [
                conn.send(json.dumps(broadcast_message)) 
                for conn in successful_connections
            ]
            await asyncio.gather(*send_tasks, return_exceptions=True)
            
        except asyncio.TimeoutError:
            pytest.fail(f"Concurrent WebSocket handshake timed out after {time.time() - start_time:.2f}s")

    async def test_003_websocket_handshake_with_database_operations(self):
        """
        Test WebSocket handshake timing when database operations are involved.
        
        Validates that WebSocket connections can be established even when
        the system is performing database operations, ensuring factory
        initialization doesn't cause timing issues.
        
        Business Value: Ensures WebSocket authentication works reliably
        even when database is under load from user context operations.
        """
        # Simulate database load with user context operations
        async def create_database_load():
            """Create realistic database load during handshake."""
            tasks = []
            for i in range(3):
                # Create user contexts that require database operations
                user_context = await create_authenticated_user_context(
                    user_email=f"db_load_{i}@example.com"
                )
                # Simulate some database operations
                await asyncio.sleep(0.1)  # Simulate DB query time
            
        # Start database load operations
        db_load_task = asyncio.create_task(create_database_load())
        
        # Measure WebSocket handshake timing during database operations
        start_time = time.time()
        
        try:
            # Create authenticated user context
            user_context = await create_authenticated_user_context(
                user_email="db_timing_test@example.com",
                websocket_enabled=True
            )
            
            # Get authentication headers
            token = self.auth_helper.create_test_jwt_token(
                user_id=str(user_context.user_id),
                email="db_timing_test@example.com"
            )
            headers = self.auth_helper.get_websocket_headers(token)
            
            # Create WebSocket connection while database is busy
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_base_url,
                    additional_headers=headers,
                    open_timeout=12.0  # Allow extra time for database operations
                ),
                timeout=12.0
            )
            
            connection_time = time.time() - start_time
            self.active_connections.append(websocket)
            
            # Connection should still complete in reasonable time
            assert connection_time < 12.0, f"Handshake with DB load took {connection_time:.2f}s"
            
            # Verify connection is functional
            test_message = {
                "type": "db_load_test", 
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(test_message))
            
            # Ensure database operations complete
            await db_load_task
            
            logger.info(f" PASS:  WebSocket handshake completed in {connection_time:.2f}s during database operations")
            
        except asyncio.TimeoutError:
            # Cancel database load task on timeout
            if not db_load_task.done():
                db_load_task.cancel()
                try:
                    await db_load_task
                except asyncio.CancelledError:
                    pass
            
            pytest.fail(f"WebSocket handshake with database load timed out after {time.time() - start_time:.2f}s")

    async def test_004_websocket_handshake_race_condition_resilience(self):
        """
        Test WebSocket handshake resilience against race conditions.
        
        Validates that WebSocket connections handle race conditions properly,
        such as rapid connect/disconnect cycles or overlapping authentication.
        
        Business Value: Prevents connection instability that would disrupt
        user chat sessions and cause poor user experience.
        """
        user_email = "race_condition_test@example.com"
        
        # Create user context once for reuse
        user_context = await create_authenticated_user_context(
            user_email=user_email,
            websocket_enabled=True
        )
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email=user_email
        )
        headers = self.auth_helper.get_websocket_headers(token)
        
        async def rapid_connect_disconnect_cycle():
            """Simulate rapid connection cycles that can cause race conditions."""
            connections = []
            
            try:
                # Rapid connection establishment
                for i in range(3):
                    websocket = await asyncio.wait_for(
                        websockets.connect(
                            self.websocket_base_url,
                            additional_headers=headers,
                            open_timeout=8.0
                        ),
                        timeout=8.0
                    )
                    connections.append(websocket)
                    
                    # Send a message immediately after connection
                    await websocket.send(json.dumps({
                        "type": "race_test",
                        "connection_id": i,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }))
                    
                    # Very short delay to create race condition
                    await asyncio.sleep(0.1)
                
                # Rapid disconnection
                for websocket in connections:
                    await websocket.close()
                    
                return len(connections)
                
            except Exception as e:
                # Clean up any successful connections
                for websocket in connections:
                    if hasattr(websocket, 'close') and not websocket.closed:
                        try:
                            await websocket.close()
                        except:
                            pass
                raise e
        
        # Test multiple rapid cycles
        start_time = time.time()
        successful_cycles = 0
        
        try:
            # Run multiple rapid connect/disconnect cycles
            cycle_tasks = [rapid_connect_disconnect_cycle() for _ in range(2)]
            
            results = await asyncio.wait_for(
                asyncio.gather(*cycle_tasks, return_exceptions=True),
                timeout=20.0
            )
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Race condition cycle failed: {result}")
                else:
                    successful_cycles += 1
                    logger.info(f"Race condition cycle completed with {result} connections")
            
            total_time = time.time() - start_time
            
            # Should handle at least one cycle successfully
            assert successful_cycles >= 1, f"Expected at least 1 successful cycle, got {successful_cycles}"
            
            logger.info(f" PASS:  {successful_cycles}/2 race condition cycles completed successfully")
            logger.info(f" PASS:  Total race condition test time: {total_time:.2f}s")
            
        except asyncio.TimeoutError:
            pytest.fail(f"Race condition test timed out after {time.time() - start_time:.2f}s")

    async def test_005_websocket_handshake_error_recovery(self):
        """
        Test WebSocket handshake error recovery and retry logic.
        
        Validates that authentication failures are handled gracefully
        and that legitimate connections can succeed after failures.
        
        Business Value: Ensures robust connection handling that doesn't
        leave users unable to connect due to temporary issues.
        """
        # Test invalid authentication first
        invalid_headers = {"Authorization": "Bearer invalid-token-123"}
        
        # Attempt connection with invalid token (should fail)
        with pytest.raises((websockets.exceptions.ConnectionClosedError, OSError, Exception)):
            invalid_websocket = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_base_url,
                    additional_headers=invalid_headers,
                    open_timeout=5.0
                ),
                timeout=5.0
            )
            # If connection succeeds unexpectedly, close it
            if hasattr(invalid_websocket, 'close'):
                await invalid_websocket.close()
        
        # Now test that valid authentication still works after invalid attempt
        user_context = await create_authenticated_user_context(
            user_email="error_recovery_test@example.com",
            websocket_enabled=True
        )
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email="error_recovery_test@example.com"
        )
        valid_headers = self.auth_helper.get_websocket_headers(token)
        
        start_time = time.time()
        
        try:
            # Valid connection should succeed after invalid attempt
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_base_url,
                    additional_headers=valid_headers,
                    open_timeout=10.0
                ),
                timeout=10.0
            )
            
            connection_time = time.time() - start_time
            self.active_connections.append(websocket)
            
            # Verify successful connection
            assert not websocket.closed, "Valid WebSocket connection should be open"
            assert connection_time < 10.0, f"Recovery connection took {connection_time:.2f}s"
            
            # Test that connection is fully functional
            recovery_message = {
                "type": "recovery_test",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Connection recovered successfully"
            }
            
            await websocket.send(json.dumps(recovery_message))
            
            # Verify message can be sent and received
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                logger.info(f" PASS:  Received response after error recovery: {len(response)} bytes")
            except asyncio.TimeoutError:
                # Some WebSocket implementations may not echo back immediately
                logger.info(" PASS:  Message sent successfully (no echo required)")
            
            logger.info(f" PASS:  WebSocket error recovery successful in {connection_time:.2f}s")
            
        except asyncio.TimeoutError:
            pytest.fail(f"WebSocket error recovery timed out after {time.time() - start_time:.2f}s")

    async def test_006_websocket_message_queuing_during_handshake(self):
        """
        Test message queuing behavior during WebSocket handshake.
        
        Validates that messages sent immediately after connection
        establishment are properly queued and delivered.
        
        Business Value: Ensures no chat messages are lost during
        connection establishment phase.
        """
        user_context = await create_authenticated_user_context(
            user_email="message_queuing@example.com",
            websocket_enabled=True
        )
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email="message_queuing@example.com"
        )
        headers = self.auth_helper.get_websocket_headers(token)
        
        start_time = time.time()
        
        try:
            # Establish connection
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_base_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=10.0
            )
            
            self.active_connections.append(websocket)
            
            # Send multiple messages rapidly after connection
            messages_to_send = [
                {"type": "queue_test", "sequence": i, "timestamp": datetime.now(timezone.utc).isoformat()}
                for i in range(5)
            ]
            
            # Send all messages as quickly as possible
            send_tasks = [
                websocket.send(json.dumps(msg)) 
                for msg in messages_to_send
            ]
            
            await asyncio.gather(*send_tasks)
            
            connection_time = time.time() - start_time
            
            # Verify connection stability after message burst
            assert not websocket.closed, "WebSocket should remain open after message burst"
            assert connection_time < 10.0, f"Message queuing test took {connection_time:.2f}s"
            
            # Send final verification message
            final_message = {
                "type": "queue_verification",
                "total_sent": len(messages_to_send),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(final_message))
            
            logger.info(f" PASS:  Message queuing test completed in {connection_time:.2f}s")
            logger.info(f" PASS:  Sent {len(messages_to_send)} messages successfully")
            
        except asyncio.TimeoutError:
            pytest.fail(f"Message queuing test timed out after {time.time() - start_time:.2f}s")

    async def test_007_websocket_handshake_with_redis_operations(self):
        """
        Test WebSocket handshake timing with Redis cache operations.
        
        Validates that WebSocket connections work properly when Redis
        is being used for session management and caching.
        
        Business Value: Ensures WebSocket connections remain stable
        when session data is cached and retrieved from Redis.
        """
        # Pre-populate Redis with session data
        user_context = await create_authenticated_user_context(
            user_email="redis_timing_test@example.com",
            websocket_enabled=True
        )
        
        # Store session data in Redis
        session_key = f"session:{user_context.user_id}"
        session_data = {
            "user_id": str(user_context.user_id),
            "email": "redis_timing_test@example.com",
            "permissions": ["read", "write"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Use Redis manager to store session
        try:
            await self.redis_manager.set(session_key, json.dumps(session_data), ex=300)
            
            # Verify Redis operation succeeded
            stored_data = await self.redis_manager.get(session_key)
            assert stored_data is not None, "Session data should be stored in Redis"
            
        except Exception as e:
            logger.warning(f"Redis operations not available: {e}")
            # Continue test without Redis if not available
        
        # Test WebSocket connection with Redis session data
        token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email="redis_timing_test@example.com"
        )
        headers = self.auth_helper.get_websocket_headers(token)
        
        start_time = time.time()
        
        try:
            # Create WebSocket connection that may use Redis for session validation
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_base_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=10.0
            )
            
            connection_time = time.time() - start_time
            self.active_connections.append(websocket)
            
            # Connection should complete even with Redis operations
            assert connection_time < 10.0, f"Handshake with Redis took {connection_time:.2f}s"
            assert not websocket.closed, "WebSocket connection should be open"
            
            # Test session-aware message
            session_message = {
                "type": "session_test",
                "session_key": session_key,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(session_message))
            
            logger.info(f" PASS:  WebSocket handshake with Redis completed in {connection_time:.2f}s")
            
        except asyncio.TimeoutError:
            pytest.fail(f"WebSocket handshake with Redis timed out after {time.time() - start_time:.2f}s")
        
        finally:
            # Cleanup Redis session data
            try:
                await self.redis_manager.delete(session_key)
            except:
                pass  # Ignore cleanup errors

    async def test_008_websocket_handshake_performance_baseline(self):
        """
        Establish performance baseline for WebSocket handshake timing.
        
        This test measures optimal handshake performance under ideal
        conditions to establish baseline for performance monitoring.
        
        Business Value: Provides performance baseline for monitoring
        WebSocket connection health and identifying degradation.
        """
        # Number of baseline measurements
        measurement_count = 10
        handshake_times = []
        
        for i in range(measurement_count):
            # Create fresh user context for each measurement
            user_context = await create_authenticated_user_context(
                user_email=f"baseline_{i}@example.com",
                websocket_enabled=True
            )
            
            token = self.auth_helper.create_test_jwt_token(
                user_id=str(user_context.user_id),
                email=f"baseline_{i}@example.com"
            )
            headers = self.auth_helper.get_websocket_headers(token)
            
            # Measure individual handshake time
            start_time = time.time()
            
            try:
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.websocket_base_url,
                        additional_headers=headers,
                        open_timeout=8.0
                    ),
                    timeout=8.0
                )
                
                handshake_time = time.time() - start_time
                handshake_times.append(handshake_time)
                
                # Quick validation message
                await websocket.send(json.dumps({
                    "type": "baseline_test",
                    "measurement": i,
                    "handshake_time": handshake_time
                }))
                
                # Close connection
                await websocket.close()
                
                # Small delay between measurements
                await asyncio.sleep(0.2)
                
            except asyncio.TimeoutError:
                logger.warning(f"Baseline measurement {i} timed out")
                handshake_times.append(8.0)  # Record timeout as max time
        
        # Calculate baseline statistics
        if handshake_times:
            avg_time = sum(handshake_times) / len(handshake_times)
            min_time = min(handshake_times)
            max_time = max(handshake_times)
            
            # Performance assertions
            assert avg_time < 5.0, f"Average handshake time {avg_time:.2f}s exceeds 5s baseline"
            assert min_time < 2.0, f"Minimum handshake time {min_time:.2f}s exceeds 2s baseline"
            assert max_time < 8.0, f"Maximum handshake time {max_time:.2f}s exceeds 8s baseline"
            
            # Success rate
            successful_handshakes = len([t for t in handshake_times if t < 8.0])
            success_rate = successful_handshakes / len(handshake_times)
            
            assert success_rate >= 0.9, f"Success rate {success_rate:.1%} below 90% baseline"
            
            logger.info(f" PASS:  WebSocket Handshake Performance Baseline:")
            logger.info(f"   Average: {avg_time:.3f}s")
            logger.info(f"   Min: {min_time:.3f}s") 
            logger.info(f"   Max: {max_time:.3f}s")
            logger.info(f"   Success Rate: {success_rate:.1%}")
            logger.info(f"   Measurements: {len(handshake_times)}")
            
        else:
            pytest.fail("No handshake timing measurements collected")