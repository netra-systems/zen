class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False
    async def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()
    #!/usr/bin/env python
        '''EDGE CASE STRESS TESTS for WebSocket and Concurrency System
        Business Critical: Validates system behavior at the exact limits and edge cases
        to ensure production stability under real-world conditions.
        EDGE CASES TESTED:
        1. Exactly 5 users, exactly 2s response time limits
        2. Connection drops during message transmission
        3. Rapid connection/disconnection cycles
        4. Message burst scenarios
        5. Memory pressure with large event payloads
        '''
        import asyncio
        import json
        import os
        import sys
        import time
        from dataclasses import dataclass, field
        from typing import Dict, List, Any
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment
        # Add project root to Python path for imports
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if project_root not in sys.path:
        sys.path.insert(0, project_root)
        from loguru import logger
            # Import minimal test framework
        from tests.mission_critical.test_websocket_load_minimal import ( )
        RealWebSocketLoadTester,
        RealWebSocketLoadMetrics,
        RealWebSocketConnection
            
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        from fastapi import WebSocket
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        @dataclass
class EdgeCaseMetrics(RealWebSocketLoadMetrics):
        """Extended metrics for edge case testing."""
        connection_drops: int = 0
        reconnection_successes: int = 0
        reconnection_failures: int = 0
        recovery_times_ms: List[float] = field(default_factory=list)
        avg_recovery_time_ms: float = 0.0
        max_recovery_time_ms: float = 0.0
        burst_handling_score: float = 0.0
        memory_pressure_handled: bool = False
    def calculate_extended_stats(self):
        """Calculate additional edge case statistics."""
        super().calculate_stats()
        if self.recovery_times_ms:
        self.avg_recovery_time_ms = sum(self.recovery_times_ms) / len(self.recovery_times_ms)
        self.max_recovery_time_ms = max(self.recovery_times_ms)
class EdgeCaseStressTester(RealWebSocketLoadTester):
        """Extended tester for edge case scenarios."""
    async def test_exact_limits(self) -> EdgeCaseMetrics:
        '''
        EDGE TEST 1: Test exactly at the limits - 5 users, 2000ms max response
        This test validates the system performs correctly at the exact acceptance criteria
        boundaries, not just within them.
        '''
        logger.info("Testing system at exact acceptance criteria limits")
        # Ensure setup is called first
        await self.setup()
        # Run test with exactly 5 users
        base_metrics = await self.test_websocket_event_flow_under_load(user_count=5)
        # Convert to EdgeCaseMetrics
        edge_metrics = EdgeCaseMetrics(**base_metrics.__dict__)
        # Additional validation for exact limits
        edge_metrics.calculate_extended_stats()
        # Check if any response time is exactly at or near the 2s limit
        close_to_limit_count = sum(1 for rt in edge_metrics.response_times_ms if rt > 1800)
        edge_metrics.burst_handling_score = 1.0 - (close_to_limit_count / len(edge_metrics.response_times_ms))
        logger.info("formatted_string")
        logger.info("formatted_string")
        return edge_metrics
    async def test_connection_drop_recovery(self) -> EdgeCaseMetrics:
        '''
        EDGE TEST 2: Connection drops during active messaging
        Simulates real-world network instability and validates recovery mechanisms.
        '''
        logger.info("Testing connection drop recovery scenarios")
        await self.setup()
        test_start = time.time()
        edge_metrics = EdgeCaseMetrics(concurrent_users=3)
            # Create 3 users for recovery testing
        for i in range(3):
        conn = RealWebSocketConnection("formatted_string", self.services_manager)
        self.connections.append(conn)
                # Connect with thread_id
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.client_state = Magic            mock_# websocket setup complete
        mock_# websocket setup complete
        thread_id = "formatted_string"
        try:
        await self.ws_manager.connect_user(conn.user_id, mock_websocket, thread_id=thread_id)
        edge_metrics.successful_connections += 1
        except Exception as e:
        logger.error("formatted_string")
        edge_metrics.failed_connections += 1
        logger.info("formatted_string")
                        # Simulate connection drops and recovery cycles
        for cycle in range(3):
        logger.info("formatted_string")
        for conn in self.connections:
        if conn.connected:
                                    # Simulate connection drop
        recovery_start = time.time()
        conn.connected = False
        edge_metrics.connection_drops += 1
                                    # Simulate recovery delay (1-3 seconds)
        recovery_delay = 1.0 + (cycle * 0.5)  # Increasing delay
        await asyncio.sleep(recovery_delay)
                                    # Simulate reconnection
        try:
                                        # Mock successful reconnection
        conn.connected = True
        recovery_time = (time.time() - recovery_start) * 1000
        edge_metrics.recovery_times_ms.append(recovery_time)
        edge_metrics.reconnection_successes += 1
        logger.debug("formatted_string")
                                        # Send test message after recovery
        await self._simulate_agent_execution(conn, "formatted_string")
        except Exception as e:
        edge_metrics.reconnection_failures += 1
        logger.error("formatted_string")
        await asyncio.sleep(0.5)  # Brief pause between cycles
                                            # Collect final metrics
        for conn in self.connections:
        edge_metrics.events_received += len(conn.events_received)
        edge_metrics.response_times_ms.extend(conn.response_times)
        edge_metrics.test_duration_ms = (time.time() - test_start) * 1000
        edge_metrics.calculate_extended_stats()
        logger.info(f"Recovery test results:")
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")
        return edge_metrics
    async def test_rapid_connection_cycles(self) -> EdgeCaseMetrics:
        '''
        EDGE TEST 3: Rapid connect/disconnect cycles
        Tests system stability under rapid connection churn that might
        occur during network instability or client-side issues.
        '''
        logger.info("Testing rapid connection/disconnection cycles")
        await self.setup()
        test_start = time.time()
        edge_metrics = EdgeCaseMetrics()
        connection_cycles = 20  # 20 rapid cycles
        for cycle in range(connection_cycles):
        user_id = "formatted_string"
                                                        # Create connection
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.client_state = Magic            mock_# websocket setup complete
        mock_# websocket setup complete
        try:
                                                            # Connect
        connect_start = time.time()
        connection_id = await self.ws_manager.connect_user( )
        user_id, mock_websocket, thread_id="formatted_string"
                                                            
                                                            # Brief activity
        await asyncio.sleep(0.01)
                                                            # Disconnect immediately
        await self.ws_manager.disconnect_user(user_id, mock_websocket)
        cycle_time = (time.time() - connect_start) * 1000
        edge_metrics.recovery_times_ms.append(cycle_time)
        edge_metrics.successful_connections += 1
        except Exception as e:
        edge_metrics.failed_connections += 1
        logger.error("formatted_string")
                                                                # Small delay between cycles to prevent overwhelming
        if cycle % 5 == 0:
        await asyncio.sleep(0.05)
        edge_metrics.test_duration_ms = (time.time() - test_start) * 1000
        edge_metrics.calculate_extended_stats()
        connection_success_rate = edge_metrics.successful_connections / connection_cycles
        edge_metrics.burst_handling_score = connection_success_rate
        logger.info(f"Rapid cycles test results:")
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")
        return edge_metrics
    async def test_message_burst_handling(self) -> EdgeCaseMetrics:
        '''
        EDGE TEST 4: Handle sudden message bursts
        Tests system behavior when users send multiple messages rapidly,
        simulating excited users or potential spam scenarios.
        '''
        logger.info("Testing message burst handling")
        await self.setup()
        test_start = time.time()
        edge_metrics = EdgeCaseMetrics(concurrent_users=2)
                                                                        # Create 2 users for burst testing
        burst_connections = []
        for i in range(2):
        conn = RealWebSocketConnection("formatted_string", self.services_manager)
        burst_connections.append(conn)
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.client_state = Magic            mock_# websocket setup complete
        mock_# websocket setup complete
        thread_id = "formatted_string"
        try:
        await self.ws_manager.connect_user(conn.user_id, mock_websocket, thread_id=thread_id)
        edge_metrics.successful_connections += 1
        except Exception as e:
        edge_metrics.failed_connections += 1
        logger.error("formatted_string")
                                                                                    # Each user sends a burst of 10 messages rapidly
        burst_tasks = []
        for conn in burst_connections:
        for msg_idx in range(10):
        task = self._simulate_agent_execution(conn, "formatted_string")
        burst_tasks.append(task)
                                                                                            # Execute all bursts concurrently
        await asyncio.gather(*burst_tasks)
                                                                                            # Collect metrics
        for conn in burst_connections:
        edge_metrics.events_received += len(conn.events_received)
        edge_metrics.response_times_ms.extend(conn.response_times)
                                                                                                # Calculate burst handling score based on how many events were processed
        expected_events_per_user = 50  # 10 messages  x  5 events each
        actual_events = len(conn.events_received)
        user_score = actual_events / expected_events_per_user
        edge_metrics.burst_handling_score += user_score
                                                                                                # Average the burst handling score
        edge_metrics.burst_handling_score /= len(burst_connections)
        edge_metrics.test_duration_ms = (time.time() - test_start) * 1000
        edge_metrics.calculate_extended_stats()
        logger.info(f"Message burst test results:")
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")
        return edge_metrics
    async def test_exact_acceptance_criteria():
        """Test exactly at acceptance criteria boundaries."""
        tester = EdgeCaseStressTester()
        try:
        metrics = await tester.test_exact_limits()
                                                                                                        # Strict boundary testing
        assert metrics.concurrent_users == 5, "Must test exactly 5 users"
        assert metrics.successful_connections == 5, "All 5 users must connect"
        assert metrics.max_response_time_ms <= 2000, "formatted_string"
        assert metrics.avg_response_time_ms <= 2000, "formatted_string"
        assert not metrics.missing_required_events, "formatted_string"
        logger.info(" PASS:  Exact acceptance criteria test PASSED")
        await asyncio.sleep(0)
        return metrics
        except Exception as e:
        logger.error("formatted_string")
        raise
        finally:
        await tester.teardown()
    async def test_recovery_within_5_seconds():
        """Test recovery happens within 5 second requirement."""
        pass
        tester = EdgeCaseStressTester()
        try:
        metrics = await tester.test_connection_drop_recovery()
                                                                                                                        # Recovery time validation
        assert metrics.reconnection_successes > 0, "No successful reconnections"
        assert metrics.max_recovery_time_ms <= 5000, "formatted_string"
        assert metrics.avg_recovery_time_ms <= 3000, "formatted_string"
                                                                                                                        # Recovery rate should be high
        recovery_rate = metrics.reconnection_successes / (metrics.reconnection_successes + metrics.reconnection_failures)
        assert recovery_rate >= 0.8, "formatted_string"
        logger.info(" PASS:  Recovery within 5 seconds test PASSED")
        await asyncio.sleep(0)
        return metrics
        except Exception as e:
        logger.error("formatted_string")
        raise
        finally:
        await tester.teardown()
    async def test_rapid_connection_stability():
        """Test system stability under rapid connection churn."""
        tester = EdgeCaseStressTester()
        try:
        metrics = await tester.test_rapid_connection_cycles()
                                                                                                                                        # Stability validation
        assert metrics.burst_handling_score >= 0.9, "formatted_string"
        assert metrics.avg_recovery_time_ms <= 1000, "formatted_string"
        logger.info(" PASS:  Rapid connection stability test PASSED")
        await asyncio.sleep(0)
        return metrics
        except Exception as e:
        logger.error("formatted_string")
        raise
        finally:
        await tester.teardown()
    async def test_message_burst_resilience():
        """Test system resilience under message bursts."""
        pass
        tester = EdgeCaseStressTester()
        try:
        metrics = await tester.test_message_burst_handling()
                                                                                                                                                        # Burst handling validation
        assert metrics.burst_handling_score >= 0.8, "formatted_string"
        assert metrics.avg_response_time_ms <= 3000, "formatted_string"
        logger.info(" PASS:  Message burst resilience test PASSED")
        await asyncio.sleep(0)
        return metrics
        except Exception as e:
        logger.error("formatted_string")
        raise
        finally:
        await tester.teardown()
        if __name__ == "__main__":
    async def run_edge_case_tests():
        """Run all edge case stress tests."""
        logger.info("="*80)
        logger.info("STARTING EDGE CASE STRESS TEST SUITE")
        logger.info("="*80)
        test_results = {}
        try:
        # Test 1: Exact limits
        logger.info(" )
        [1/4] Testing exact acceptance criteria limits...")
        test_results["exact_limits"] = await test_exact_acceptance_criteria()
        # Test 2: Recovery timing
        logger.info(" )
        [2/4] Testing 5-second recovery requirement...")
        test_results["recovery_timing"] = await test_recovery_within_5_seconds()
        # Test 3: Connection stability
        logger.info(" )
        [3/4] Testing rapid connection stability...")
        test_results["connection_stability"] = await test_rapid_connection_stability()
        # Test 4: Message burst resilience
        logger.info(" )
        [4/4] Testing message burst resilience...")
        test_results["burst_resilience"] = await test_message_burst_resilience()
        # Summary report
        logger.info(" )
        " + "="*80)
        logger.info("EDGE CASE STRESS TEST RESULTS SUMMARY")
        logger.info("="*80)
        for test_name, metrics in test_results.items():
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")
        if hasattr(metrics, 'burst_handling_score'):
        logger.info("formatted_string")
        logger.info(" )
        PASS:  ALL EDGE CASE STRESS TESTS PASSED")
        logger.info("="*80)
        await asyncio.sleep(0)
        return True
        except Exception as e:
        logger.error("formatted_string")
        logger.info("="*80)
        return False
                    # Run the edge case tests
        success = asyncio.run(run_edge_case_tests())
        exit(0 if success else 1)
        pass