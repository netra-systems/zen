"""
WebSocket Handshake Race Conditions Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Validate race condition fixes work with real database and Redis
- Value Impact: Tests actual service interactions that cause race conditions  
- Strategic/Revenue Impact: Critical validation that fixes work protecting $500K+ ARR

ROOT CAUSE ADDRESSED:
- WebSocket 1011 errors due to race conditions in Cloud Run environments
- Message handling starts before WebSocket handshake completion
- Service dependencies not ready during connection establishment

CRITICAL TESTING FOCUS:
1. Real WebSocket handshake timing with PostgreSQL/Redis
2. Service dependency validation with actual services
3. Rapid connection attempts causing state confusion
4. Authentication vs event emission timing mismatches
5. Progressive delay effectiveness with real infrastructure

REAL INFRASTRUCTURE REQUIREMENTS (NO MOCKS per CLAUDE.md):
- Real PostgreSQL database connections (port 5434 for testing)  
- Real Redis cache operations (port 6381 for testing)
- Real WebSocket connections with authentication
- Real service startup timing and dependency chains

This integration test validates that race condition fixes work in realistic
environment with actual service timing and network conditions.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

import pytest
import websockets
from websockets.exceptions import ConnectionClosedError, InvalidStatusCode

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.base_integration_test import BaseIntegrationTest  
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import (
    E2EWebSocketAuthHelper,
    E2EAuthConfig,
    AuthenticatedUser,
    create_authenticated_user
)
from test_framework.websocket_helpers import WebSocketTestClient
from shared.isolated_environment import get_env

# Import existing WebSocket infrastructure
from netra_backend.app.websocket_core import (
    WebSocketManager,
    get_websocket_manager,
    is_websocket_connected,
    is_websocket_connected_and_ready,
    validate_websocket_handshake_completion
)
from netra_backend.app.websocket_core.utils import safe_websocket_send

# Real agent components for business value testing
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestWebSocketHandshakeRaceConditionsIntegration(BaseIntegrationTest):
    """
    Integration tests for WebSocket handshake race condition fixes.
    
    Tests race condition prevention with REAL services (PostgreSQL, Redis)
    and REAL WebSocket connections. NO MOCKS per CLAUDE.md requirements.
    
    CRITICAL: These tests validate that race condition fixes work with
    actual service timing, network latency, and database operations.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_integration_environment(self, real_services_fixture):
        """Set up real services environment for race condition testing."""
        self.services = real_services_fixture
        
        # Initialize authentication helper with real services
        self.auth_config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws"
        )
        self.auth_helper = E2EWebSocketAuthHelper(
            config=self.auth_config,
            environment="test"
        )
        
        # Ensure services are ready before testing
        await self._wait_for_services_ready()
        
        # Initialize race condition tracking
        self.race_condition_events: List[Dict[str, Any]] = []
        self.connection_timing_data: List[Dict[str, Any]] = []
    
    async def _wait_for_services_ready(self, max_wait_time: float = 30.0):
        """
        Wait for all required services to be ready before testing.
        
        This prevents race conditions in the tests themselves by ensuring
        infrastructure is stable before testing WebSocket race conditions.
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # Check PostgreSQL readiness
                postgres_ready = await self.services.is_postgres_ready()
                
                # Check Redis readiness  
                redis_ready = await self.services.is_redis_ready()
                
                # Check backend service readiness
                backend_ready = await self._check_backend_health()
                
                if postgres_ready and redis_ready and backend_ready:
                    return
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                await asyncio.sleep(0.5)
        
        pytest.fail(f"Services not ready after {max_wait_time}s wait")
    
    async def _check_backend_health(self) -> bool:
        """Check if backend service is ready for WebSocket connections."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8002/health") as response:
                    return response.status == 200
        except Exception:
            return False
    
    def _record_race_condition_event(self, event_type: str, details: Dict[str, Any]):
        """Record race condition event for analysis."""
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details
        }
        self.race_condition_events.append(event)
    
    def _record_connection_timing(self, operation: str, duration: float, success: bool, details: Optional[Dict] = None):
        """Record connection timing data for race condition analysis."""
        timing_data = {
            "operation": operation,
            "duration_ms": duration * 1000,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {}
        }
        self.connection_timing_data.append(timing_data)
    
    @pytest.mark.asyncio
    async def test_handshake_with_real_redis_timing(self):
        """
        Test WebSocket handshake coordination with real Redis operations.
        
        BVJ: Validates Redis readiness doesn't cause WebSocket race conditions
        Tests critical integration point between WebSocket and Redis cache
        """
        # Create authenticated user with Redis session storage
        auth_user = await self.auth_helper.create_authenticated_user()
        
        # Record baseline Redis timing  
        redis_start = time.time()
        await self.services.redis_client.set(f"test_user:{auth_user.user_id}", json.dumps({
            "user_id": auth_user.user_id,
            "session_start": datetime.now(timezone.utc).isoformat()
        }))
        redis_duration = time.time() - redis_start
        self._record_connection_timing("redis_baseline", redis_duration, True)
        
        # Test WebSocket connection with Redis integration
        connection_start = time.time()
        try:
            websocket_client = WebSocketTestClient(
                url=self.auth_config.websocket_url,
                headers=self.auth_helper.get_websocket_headers(auth_user.jwt_token)
            )
            
            async with websocket_client as ws:
                # Wait for connection ready message
                ready_message = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
                
                connection_duration = time.time() - connection_start
                self._record_connection_timing("websocket_with_redis", connection_duration, True, {
                    "redis_baseline_ms": redis_duration * 1000,
                    "ready_message": ready_message
                })
                
                # Verify connection is stable (no race conditions)
                self.assertIn("connection_ready", str(ready_message).lower())
                
                # Test Redis operations during WebSocket connection
                redis_during_ws_start = time.time()
                cached_data = await self.services.redis_client.get(f"test_user:{auth_user.user_id}")
                redis_during_ws_duration = time.time() - redis_during_ws_start
                
                self.assertIsNotNone(cached_data)
                
                # Redis operations during WebSocket should not cause race conditions
                self.assertLess(redis_during_ws_duration, 0.1, 
                              f"Redis operation during WebSocket took too long: {redis_during_ws_duration*1000:.1f}ms")
                
        except asyncio.TimeoutError:
            connection_duration = time.time() - connection_start
            self._record_connection_timing("websocket_with_redis", connection_duration, False, {
                "error": "timeout_waiting_for_ready_message"
            })
            pytest.fail("WebSocket connection timed out waiting for ready message - potential race condition")
        
        except Exception as e:
            connection_duration = time.time() - connection_start
            self._record_connection_timing("websocket_with_redis", connection_duration, False, {
                "error": str(e),
                "error_type": type(e).__name__
            })
            
            # Check if this is a race condition error
            if "1011" in str(e) or "need to call accept first" in str(e).lower():
                self._record_race_condition_event("redis_integration_race_condition", {
                    "error": str(e),
                    "redis_baseline_ms": redis_duration * 1000,
                    "connection_attempt_duration_ms": connection_duration * 1000
                })
                pytest.fail(f"Race condition detected with Redis integration: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_database_readiness_validation(self):
        """
        Test WebSocket handshake with database connection validation.
        
        BVJ: Ensures database connections don't interfere with WebSocket handshake
        Critical for user context creation and session management
        """
        # Test database baseline timing
        db_start = time.time()
        async with self.services.get_postgres_connection() as conn:
            result = await conn.fetchval("SELECT 1")
            self.assertEqual(result, 1)
        db_duration = time.time() - db_start
        self._record_connection_timing("database_baseline", db_duration, True)
        
        # Create authenticated user with database validation
        auth_user = await self.auth_helper.create_authenticated_user()
        
        # Test WebSocket connection with concurrent database operations
        ws_start = time.time()
        db_concurrent_start = time.time()
        
        try:
            async with asyncio.TaskGroup() as tg:
                # Start WebSocket connection
                ws_task = tg.create_task(self._test_websocket_connection_with_timing(auth_user))
                
                # Start concurrent database operations
                db_task = tg.create_task(self._perform_concurrent_database_operations(auth_user.user_id))
            
            ws_result, db_results = await ws_task, await db_task
            
            concurrent_duration = time.time() - db_concurrent_start
            self._record_connection_timing("websocket_with_concurrent_db", concurrent_duration, True, {
                "database_baseline_ms": db_duration * 1000,
                "websocket_success": ws_result,
                "database_operations": len(db_results)
            })
            
            # Both WebSocket and database operations should succeed
            self.assertTrue(ws_result, "WebSocket connection should succeed with concurrent database operations")
            self.assertGreater(len(db_results), 0, "Database operations should complete successfully")
            
        except Exception as e:
            concurrent_duration = time.time() - db_concurrent_start
            self._record_connection_timing("websocket_with_concurrent_db", concurrent_duration, False, {
                "error": str(e)
            })
            
            if "1011" in str(e) or "race" in str(e).lower():
                self._record_race_condition_event("database_concurrency_race_condition", {
                    "error": str(e),
                    "db_baseline_ms": db_duration * 1000
                })
                pytest.fail(f"Race condition detected with database concurrency: {e}")
            raise
    
    async def _test_websocket_connection_with_timing(self, auth_user: AuthenticatedUser) -> bool:
        """Helper to test WebSocket connection and return success status."""
        try:
            websocket_client = WebSocketTestClient(
                url=self.auth_config.websocket_url,
                headers=self.auth_helper.get_websocket_headers(auth_user.jwt_token)
            )
            
            async with websocket_client as ws:
                ready_message = await asyncio.wait_for(ws.receive_json(), timeout=3.0)
                return "connection_ready" in str(ready_message).lower()
                
        except Exception:
            return False
    
    async def _perform_concurrent_database_operations(self, user_id: str) -> List[Dict]:
        """Perform database operations concurrently with WebSocket connection."""
        results = []
        
        for i in range(5):
            async with self.services.get_postgres_connection() as conn:
                # Simulate user context queries that happen during WebSocket handshake
                result = await conn.fetchval(
                    "SELECT $1 as user_id, $2 as operation_id, NOW() as timestamp",
                    user_id, f"concurrent_op_{i}"
                )
                results.append({"operation_id": f"concurrent_op_{i}", "result": result})
                
                # Small delay to simulate realistic database timing
                await asyncio.sleep(0.01)
        
        return results
    
    @pytest.mark.asyncio  
    async def test_rapid_connection_attempts(self):
        """
        Test system behavior under rapid WebSocket connection attempts.
        
        BVJ: Validates system handles rapid user connection attempts without race conditions
        Critical for user experience when users refresh or retry connections
        """
        # Create multiple authenticated users for concurrent testing
        auth_users = []
        for i in range(5):
            user = await self.auth_helper.create_authenticated_user(
                email=f"rapid_test_{i}@example.com",
                user_id=f"rapid_user_{i}_{uuid.uuid4().hex[:8]}"
            )
            auth_users.append(user)
        
        # Test rapid successive connections
        connection_results = []
        rapid_start = time.time()
        
        try:
            # Attempt multiple connections in rapid succession
            connection_tasks = []
            for i, auth_user in enumerate(auth_users):
                task = asyncio.create_task(
                    self._attempt_rapid_connection(auth_user, connection_id=i)
                )
                connection_tasks.append(task)
                
                # Very small delay between connection attempts (simulates rapid user clicks)
                await asyncio.sleep(0.02)
            
            # Wait for all connection attempts
            connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            rapid_duration = time.time() - rapid_start
            self._record_connection_timing("rapid_connections", rapid_duration, True, {
                "connection_count": len(auth_users),
                "success_count": sum(1 for r in connection_results if r is True),
                "error_count": sum(1 for r in connection_results if isinstance(r, Exception))
            })
            
            # Analyze results for race conditions
            successful_connections = sum(1 for r in connection_results if r is True)
            race_condition_errors = sum(1 for r in connection_results 
                                      if isinstance(r, Exception) and ("1011" in str(r) or "accept first" in str(r).lower()))
            
            # At least 80% of rapid connections should succeed (allows for some network variance)
            success_rate = successful_connections / len(auth_users)
            self.assertGreaterEqual(success_rate, 0.8, 
                                  f"Rapid connection success rate too low: {success_rate:.1%}")
            
            # Zero tolerance for race condition errors
            self.assertEqual(race_condition_errors, 0, 
                           f"Race condition errors detected in rapid connections: {race_condition_errors}")
            
        except Exception as e:
            rapid_duration = time.time() - rapid_start
            self._record_connection_timing("rapid_connections", rapid_duration, False, {
                "error": str(e)
            })
            
            if "1011" in str(e):
                self._record_race_condition_event("rapid_connection_race_condition", {
                    "error": str(e),
                    "connection_count": len(auth_users),
                    "duration_ms": rapid_duration * 1000
                })
                pytest.fail(f"Race condition in rapid connections: {e}")
            raise
    
    async def _attempt_rapid_connection(self, auth_user: AuthenticatedUser, connection_id: int) -> bool:
        """Attempt a single rapid WebSocket connection."""
        try:
            websocket_client = WebSocketTestClient(
                url=self.auth_config.websocket_url,
                headers=self.auth_helper.get_websocket_headers(auth_user.jwt_token),
                timeout=2.0  # Short timeout for rapid testing
            )
            
            async with websocket_client as ws:
                # Wait for connection ready with short timeout
                ready_message = await asyncio.wait_for(ws.receive_json(), timeout=1.0)
                
                # Send a quick test message to verify connection works
                test_message = {
                    "type": "ping",
                    "connection_id": connection_id,
                    "user_id": auth_user.user_id
                }
                await ws.send_json(test_message)
                
                # Wait for response
                response = await asyncio.wait_for(ws.receive_json(), timeout=1.0)
                
                return True
                
        except asyncio.TimeoutError:
            return False
        except Exception as e:
            # Return the exception for analysis
            return e
    
    @pytest.mark.asyncio
    async def test_progressive_delay_effectiveness(self):
        """
        Test that progressive delay system reduces race condition occurrence.
        
        BVJ: Validates core race condition mitigation strategy works with real services
        Tests the actual fix implementation effectiveness  
        """
        auth_user = await self.auth_helper.create_authenticated_user()
        
        # Test connection timing with progressive delays enabled (normal mode)
        normal_timings = []
        for attempt in range(10):
            timing_start = time.time()
            try:
                websocket_client = WebSocketTestClient(
                    url=self.auth_config.websocket_url,
                    headers=self.auth_helper.get_websocket_headers(auth_user.jwt_token)
                )
                
                async with websocket_client as ws:
                    ready_message = await asyncio.wait_for(ws.receive_json(), timeout=3.0)
                    timing_duration = time.time() - timing_start
                    normal_timings.append(timing_duration)
                
                # Small delay between attempts
                await asyncio.sleep(0.1)
                
            except Exception as e:
                timing_duration = time.time() - timing_start
                normal_timings.append(None)  # Mark as failed
                
                if "1011" in str(e) or "accept first" in str(e).lower():
                    self._record_race_condition_event("progressive_delay_race_condition", {
                        "attempt": attempt,
                        "error": str(e),
                        "timing_ms": timing_duration * 1000
                    })
        
        # Analyze timing effectiveness
        successful_timings = [t for t in normal_timings if t is not None]
        failed_attempts = sum(1 for t in normal_timings if t is None)
        
        # Record overall effectiveness
        self._record_connection_timing("progressive_delay_effectiveness", 
                                     sum(successful_timings) / len(successful_timings) if successful_timings else 0,
                                     len(successful_timings) > 0, {
            "total_attempts": len(normal_timings),
            "successful_attempts": len(successful_timings),
            "failed_attempts": failed_attempts,
            "average_success_time_ms": (sum(successful_timings) / len(successful_timings) * 1000) if successful_timings else 0
        })
        
        # Progressive delays should achieve high success rate
        success_rate = len(successful_timings) / len(normal_timings)
        self.assertGreaterEqual(success_rate, 0.9, 
                              f"Progressive delay success rate too low: {success_rate:.1%}")
        
        # Zero tolerance for race condition failures
        self.assertEqual(failed_attempts, 0, 
                       f"Progressive delays failed to prevent race conditions: {failed_attempts} failures")
        
        # Connection times should be reasonable (under 500ms for test environment)
        if successful_timings:
            avg_time = sum(successful_timings) / len(successful_timings)
            self.assertLess(avg_time, 0.5, 
                          f"Progressive delays causing excessive connection time: {avg_time*1000:.1f}ms")
    
    @pytest.mark.asyncio
    async def test_service_startup_timing_race_conditions(self):
        """
        Test WebSocket behavior during service startup and initialization.
        
        BVJ: Ensures graceful handling when services are starting up
        Critical for system reliability during deployments and scaling
        """
        auth_user = await self.auth_helper.create_authenticated_user()
        
        # Test connection during simulated service startup delays
        startup_scenarios = [
            {"redis_delay": 0.1, "postgres_delay": 0.05, "description": "normal_startup"},
            {"redis_delay": 0.2, "postgres_delay": 0.15, "description": "slow_startup"},
            {"redis_delay": 0.05, "postgres_delay": 0.3, "description": "postgres_slow"},
            {"redis_delay": 0.3, "postgres_delay": 0.05, "description": "redis_slow"}
        ]
        
        for scenario in startup_scenarios:
            scenario_start = time.time()
            
            try:
                # Simulate startup delays by introducing artificial delays in test
                await asyncio.sleep(scenario["redis_delay"])
                await asyncio.sleep(scenario["postgres_delay"])
                
                # Attempt WebSocket connection during "startup"
                websocket_client = WebSocketTestClient(
                    url=self.auth_config.websocket_url,
                    headers=self.auth_helper.get_websocket_headers(auth_user.jwt_token)
                )
                
                async with websocket_client as ws:
                    ready_message = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
                    
                    scenario_duration = time.time() - scenario_start
                    self._record_connection_timing(f"startup_scenario_{scenario['description']}", 
                                                 scenario_duration, True, scenario)
                    
                    # Connection should succeed despite startup delays
                    self.assertIn("connection_ready", str(ready_message).lower(),
                                f"Connection should be ready in {scenario['description']} scenario")
                
            except Exception as e:
                scenario_duration = time.time() - scenario_start
                self._record_connection_timing(f"startup_scenario_{scenario['description']}", 
                                             scenario_duration, False, {**scenario, "error": str(e)})
                
                if "1011" in str(e) or "accept first" in str(e).lower():
                    self._record_race_condition_event("service_startup_race_condition", {
                        "scenario": scenario["description"],
                        "error": str(e),
                        "timing_ms": scenario_duration * 1000
                    })
                    pytest.fail(f"Race condition during service startup ({scenario['description']}): {e}")
                
                # Other errors should be investigated but not necessarily fail the test
                self.fail(f"Unexpected error in startup scenario {scenario['description']}: {e}")
    
    def tearDown(self):
        """Clean up and report race condition analysis."""
        super().tearDown()
        
        # Log race condition events for analysis
        if self.race_condition_events:
            print(f"\n🚨 RACE CONDITION EVENTS DETECTED: {len(self.race_condition_events)}")
            for event in self.race_condition_events:
                print(f"  - {event['event_type']}: {event['details']}")
        
        # Log connection timing summary
        successful_connections = [t for t in self.connection_timing_data if t["success"]]
        failed_connections = [t for t in self.connection_timing_data if not t["success"]]
        
        if successful_connections:
            avg_time = sum(t["duration_ms"] for t in successful_connections) / len(successful_connections)
            print(f"\n📊 CONNECTION TIMING SUMMARY:")
            print(f"  - Successful connections: {len(successful_connections)}")
            print(f"  - Failed connections: {len(failed_connections)}")
            print(f"  - Average connection time: {avg_time:.1f}ms")
        
        # Assert no race conditions were detected
        self.assertEqual(len(self.race_condition_events), 0, 
                       f"Race condition events detected: {[e['event_type'] for e in self.race_condition_events]}")


if __name__ == "__main__":
    unittest.main()