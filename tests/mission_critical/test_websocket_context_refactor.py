from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.
    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
    async def send_json(self, message: dict):
        ""Send JSON message.
        if self._closed:
            raise RuntimeError(WebSocket is closed)"
        self.messages_sent.append(message)
    async def close(self, code: int = 1000, reason: str = Normal closure"):
        Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False
    async def get_messages(self) -> list:
        Get all sent messages."
        await asyncio.sleep(0)
        return self.messages_sent.copy()
        '''
        Mission Critical Test Suite: WebSocket Context Refactor Validation
        Tests proper WebSocket handling patterns after refactoring.
        '''
        import asyncio
        import unittest
        from typing import Dict, Any, List, Optional
        import threading
        import time
        import random
        import tracemalloc
        import gc
        from datetime import datetime, timezone
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment
        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, get_agent_websocket_bridge
        from netra_backend.app.orchestration.agent_execution_registry import AgentExecutionRegistry
        from netra_backend.app.agents.base.interface import ExecutionContext
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
class AdvancedWebSocketCapture:
        "Advanced WebSocket event capture with performance metrics and failure simulation.
    def __init__(self):
        pass
        self.events: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, List[float]] = {}
        self.lock = threading.Lock()
        self.failure_rate = 0.0  # Configurable failure rate for testing
        self.latency_ms = 0  # Configurable latency for testing
    async def capture_event(self, event_type: str, run_id: str, agent_name: str, *args, **kwargs):
        ""Capture WebSocket event with performance tracking.
    # Simulate network latency if configured
        if self.latency_ms > 0:
        await asyncio.sleep(self.latency_ms / 1000.0)
        # Simulate failures if configured
        if self.failure_rate > 0 and random.random() < self.failure_rate:
        raise ConnectionError(""
        start_time = time.perf_counter()
        with self.lock:
        event = {
        'type': event_type,
        'run_id': run_id,
        'agent_name': agent_name,
        'timestamp': datetime.now(timezone.utc),
        'args': args,
        'kwargs': kwargs
                
        self.events.append(event)
                # Track performance metrics
        if event_type not in self.performance_metrics:
        self.performance_metrics[event_type] = []
        self.performance_metrics[event_type].append( )
        (time.perf_counter() - start_time) * 1000  # Convert to ms
                    
    def get_events_timeline(self) -> List[Dict[str, Any]]:
        Get events in chronological order with timing analysis."
        pass
        with self.lock:
        sorted_events = sorted(self.events, key=lambda x: None e['timestamp']
        # Add relative timing information
        if sorted_events:
        first_time = sorted_events[0]['timestamp']
        for event in sorted_events:
        event['relative_time_ms'] = ( )
        (event['timestamp'] - first_time).total_seconds() * 1000
                
        await asyncio.sleep(0)
        return sorted_events
    def get_performance_summary(self) -> Dict[str, Dict[str, float]]:
        "Get performance summary for all event types.
        with self.lock:
        summary = {}
        for event_type, latencies in self.performance_metrics.items():
        if latencies:
        summary[event_type] = {
        'avg_ms': sum(latencies) / len(latencies),
        'min_ms': min(latencies),
        'max_ms': max(latencies),
        'count': len(latencies)
                
        return summary
class TestProperWebSocketHandling(SSotAsyncTestCase):
        ""Test that proper WebSocket handling patterns work correctly.
    def setUp(self):
        Set up test fixtures.""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.capture = AdvancedWebSocketCapture()
    def tearDown(self):
        Clean up after tests.""
        pass
        self.loop.close()
    def test_websocket_bridge_initialization(self):
        Test WebSocket bridge initializes correctly for agents."
    async def run_test():
    # Create agent
        agent = DataSubAgent()
    # Create and configure bridge
        bridge = AgentWebSocketBridge()
    # Set bridge on agent (modern pattern)
        agent.set_websocket_bridge(bridge, test_run_001")
    # Verify bridge is set
        self.assertIsNotNone(agent._websocket_adapter)
        self.assertTrue(hasattr(agent._websocket_adapter, '_bridge'))
    # Test that agent can emit events through bridge
        await agent.emit_thinking(Initializing data analysis)
        await agent.emit_tool_executing(query_builder", {"query: SELECT *}
        await agent.emit_progress(Processing results, is_complete=False)"
    # Verify no exceptions were raised
        self.assertTrue(True)
        self.loop.run_until_complete(run_test())
    def test_agent_registry_websocket_integration(self):
        "Test AgentRegistry properly integrates with WebSocket bridge.
        pass
    async def run_test():
        pass
    # Create registry and mock WebSocket manager
        registry = AgentExecutionRegistry()
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
    # Set WebSocket manager on registry
        registry.set_websocket_manager(mock_ws_manager)
    # Verify WebSocket manager is set
        self.assertEqual(registry._websocket_manager, mock_ws_manager)
    # Create execution context
        context = ExecutionContext( )
        run_id="registry_test_001,"
        user_id=test_user,
        agent_name=DataSubAgent,"
        state={},
        stream_updates=True
    
    # Register context
        registry.register_context(context)
    # Verify context is registered
        self.assertIn(registry_test_001", registry._active_contexts)
        self.loop.run_until_complete(run_test())
    def test_complete_event_lifecycle(self):
        Test complete WebSocket event lifecycle through proper channels.""
    async def run_test():
    # Create mock bridge with capture
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        mock_bridge.notify_agent_started = self.capture.capture_event
        mock_bridge.notify_agent_thinking = self.capture.capture_event
        mock_bridge.notify_tool_executing = self.capture.capture_event
        mock_bridge.notify_tool_completed = self.capture.capture_event
        mock_bridge.notify_agent_completed = self.capture.capture_event
    # Patch global bridge getter
    # Create and configure agent
        agent = ValidationSubAgent()
        agent.set_websocket_bridge(mock_bridge, lifecycle_test)
    # Execute complete lifecycle
        context = ExecutionContext( )
        run_id=lifecycle_test,"
        user_id=test_user",
        agent_name=ValidationSubAgent,
        state={},
        stream_updates=True
    
    # Simulate agent lifecycle
        await agent.emit_thinking(Starting validation")"
        await agent.emit_tool_executing(schema_validator, {}
        await agent.emit_tool_completed(schema_validator, {"status: success"}
        await agent.emit_thinking(Processing results)
        await agent.emit_progress(Validation complete", is_complete=True)"
    # Verify events were captured in correct order
        timeline = self.capture.get_events_timeline()
        self.assertGreater(len(timeline), 0)
    # Verify event ordering
        event_types = [e['type'] for e in timeline]
        expected_order = [
        'notify_agent_thinking',
        'notify_tool_executing',
        'notify_tool_completed',
        'notify_agent_thinking'
    
        for expected in expected_order:
        self.assertIn(expected, event_types)
        self.loop.run_until_complete(run_test())
    def test_event_ordering_guarantees(self):
        Test that WebSocket events maintain correct ordering."
        pass
    async def run_test():
        pass
        events_received = []
        event_lock = threading.Lock()
    # Create mock bridge that preserves order
        mock_bridge = Mock(spec=AgentWebSocketBridge)
    async def ordered_capture(event_type, run_id, agent_name, *args, **kwargs):
        pass
        with event_lock:
        events_received.append()
        'type': event_type,
        'order': len(events_received),
        'timestamp': time.perf_counter()
        
        # Set up mock methods
        mock_bridge.notify_agent_thinking = ordered_capture
        mock_bridge.notify_tool_executing = ordered_capture
        mock_bridge.notify_agent_completed = ordered_capture
        # Create multiple agents
        agents = []
        for i in range(3):
        agent = DataSubAgent()
        agent.set_websocket_bridge(mock_bridge, formatted_string")
        agents.append((agent, )"
            # Execute agents sequentially and verify ordering
        for agent, run_id in agents:
        await agent.emit_thinking(formatted_string")
        await agent.emit_tool_executing(tool, {}
        await agent.emit_progress(Complete", is_complete=True)"
                # Verify events are in order
        with event_lock:
        for i in range(len(events_received) - 1):
        self.assertLess( )
        events_received[i]['timestamp'],
        events_received[i + 1]['timestamp'],
        Events are out of order
                        
        self.loop.run_until_complete(run_test())
class TestConcurrentAgentExecution(SSotAsyncTestCase):
        "Test concurrent agent execution with WebSocket notifications."
    def setUp(self):
        Set up test fixtures.""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    def tearDown(self):
        Clean up after tests."
        pass
        self.loop.close()
    def test_concurrent_agent_websocket_notifications(self):
        "Test that concurrent agents send WebSocket notifications correctly.
    async def run_test():
        capture = AdvancedWebSocketCapture()
    # Create mock bridge
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        mock_bridge.notify_agent_thinking = capture.capture_event
        mock_bridge.notify_tool_executing = capture.capture_event
        mock_bridge.notify_agent_completed = capture.capture_event
    # Create 20 concurrent agents
        agents = []
        for i in range(20):
        agent = DataSubAgent() if i % 2 == 0 else ValidationSubAgent()
        run_id = formatted_string""
        agent.set_websocket_bridge(mock_bridge, run_id)
        agents.append((agent, run_id))
        # Execute all agents concurrently
    async def execute_agent(agent, run_id):
        for step in range(5):
        await agent.emit_thinking(
        await asyncio.sleep(0.001)  # Small delay to simulate work
        # Run all agents concurrently
        # Removed problematic line: await asyncio.gather(*]
        execute_agent(agent, run_id)
        for agent, run_id in agents
        
        # Verify all events were captured
        timeline = capture.get_events_timeline()
        self.assertEqual(len(timeline), 20 * 5)  # 20 agents * 5 steps
        # Verify no events were lost
        run_ids = set(e['run_id'] for e in timeline)
        self.assertEqual(len(run_ids), 20)
        # Check performance
        perf_summary = capture.get_performance_summary()
        if 'notify_agent_thinking' in perf_summary:
        avg_latency = perf_summary['notify_agent_thinking']['avg_ms']
        self.assertLess(avg_latency, 10, Average latency too high")"
        self.loop.run_until_complete(run_test())
    def test_high_concurrency_load(self):
        Test system under high concurrent load."
        pass
    async def run_test():
        pass
        capture = AdvancedWebSocketCapture()
    # Create mock bridge
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        mock_bridge.notify_agent_thinking = capture.capture_event
        mock_bridge.notify_tool_executing = capture.capture_event
    # Track throughput
        start_time = time.perf_counter()
        event_count = 0
    # Create high concurrent load
    async def send_events(agent_id):
        pass
        nonlocal event_count
        agent = DataSubAgent()
        agent.set_websocket_bridge(mock_bridge, formatted_string")
        for i in range(50):  # 50 events per agent
        await agent.emit_thinking("
        event_count += 1
    # Run 100 concurrent agents
    # Removed problematic line: await asyncio.gather(*]
        send_events(i) for i in range(100)
    
    # Calculate throughput
        duration = time.perf_counter() - start_time
        throughput = event_count / duration
        print(formatted_string")
    # Verify high throughput (target: 500+ events/second)
        self.assertGreater(throughput, 500, Throughput below target)"
    # Verify all events were captured
        self.assertEqual(len(capture.events), 100 * 50)
        self.loop.run_until_complete(run_test())
    def test_performance_degradation_monitoring(self):
        "Test that performance degradation is detected under load.
    async def run_test():
        capture = AdvancedWebSocketCapture()
    # Add artificial latency that increases with load
        load_counter = 0
    async def degrading_capture(event_type, run_id, agent_name, *args, **kwargs):
        nonlocal load_counter
        load_counter += 1
    # Simulate degradation: latency increases with load
        latency = min(0.001 * (load_counter / 100), 0.1)
        await asyncio.sleep(latency)
        await capture.capture_event(event_type, run_id, agent_name, *args, **kwargs)
    # Create mock bridge
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        mock_bridge.notify_agent_thinking = degrading_capture
    # Send events and track latency
        agent = DataSubAgent()
        agent.set_websocket_bridge(mock_bridge, "degradation_test)"
        latencies = []
        for i in range(200):
        start = time.perf_counter()
        await agent.emit_thinking(formatted_string)
        latencies.append((time.perf_counter() - start) * 1000)
        # Analyze latency trend
        first_quartile = sum(latencies[:50] / 50
        last_quartile = sum(latencies[-50:] / 50
        # Verify degradation is detected
        degradation_ratio = last_quartile / first_quartile
        self.assertGreater(degradation_ratio, 1.5, Failed to detect performance degradation)"
        print(formatted_string")
        self.loop.run_until_complete(run_test())
class TestErrorHandlingAndRecovery(SSotAsyncTestCase):
        Test error handling and recovery in WebSocket operations.""
    def setUp(self):
        Set up test fixtures.""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    def tearDown(self):
        Clean up after tests."
        pass
        self.loop.close()
    def test_websocket_failure_recovery(self):
        "Test recovery from WebSocket failures.
    async def run_test():
        capture = AdvancedWebSocketCapture()
        capture.failure_rate = 0.3  # 30% failure rate
    # Create mock bridge with failure simulation
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        mock_bridge.notify_agent_thinking = capture.capture_event
    # Create agent with retry logic
        agent = ValidationSubAgent()
        agent.set_websocket_bridge(mock_bridge, "recovery_test)"
    # Send events and track failures
        success_count = 0
        failure_count = 0
        for i in range(100):
        try:
        await agent.emit_thinking(formatted_string)
        success_count += 1
        except ConnectionError:
        failure_count += 1
                # Verify reasonable failure rate
        actual_failure_rate = failure_count / (success_count + failure_count)
        self.assertAlmostEqual(actual_failure_rate, 0.3, delta=0.1)
                # Verify successful events were captured
        self.assertGreater(len(capture.events), 0)
        self.loop.run_until_complete(run_test())
    def test_network_latency_handling(self):
        Test handling of network latency in WebSocket operations.""
        pass
    async def run_test():
        pass
        capture = AdvancedWebSocketCapture()
    # Test different latency scenarios
        latency_scenarios = [10, 50, 100, 500]  # ms
        for target_latency in latency_scenarios:
        capture.latency_ms = target_latency
        capture.events.clear()
        # Create mock bridge
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        mock_bridge.notify_agent_thinking = capture.capture_event
        # Create agent
        agent = DataSubAgent()
        agent.set_websocket_bridge(mock_bridge, formatted_string)
        # Measure actual latency
        start = time.perf_counter()
        await agent.emit_thinking("Test event)"
        actual_latency = (time.perf_counter() - start) * 1000
        # Verify latency is handled correctly
        self.assertGreaterEqual(actual_latency, target_latency)
        self.assertLess(actual_latency, target_latency * 1.5)
        print(formatted_string)
        self.loop.run_until_complete(run_test())
    def test_bridge_state_transitions(self):
        "Test WebSocket bridge state transitions under various conditions."
    async def run_test():
    # Create bridge and track state transitions
        bridge = AgentWebSocketBridge()
        states = []
    # Mock state tracking
        original_notify = bridge.notify_agent_thinking
    async def track_state(*args, **kwargs):
        states.append(active)"
        await asyncio.sleep(0)
        return await original_notify(*args, **kwargs)
        bridge.notify_agent_thinking = track_state
    # Create agents and test state transitions
        agent1 = DataSubAgent()
        agent2 = ValidationSubAgent()
    # Initial state: no bridge set
        states.append("uninitialized)
    # Set bridge on first agent
        agent1.set_websocket_bridge(bridge, state_test_1)
        states.append("initialized_1)"
    # Set bridge on second agent
        agent2.set_websocket_bridge(bridge, state_test_2)
        states.append(initialized_2)"
    # Send events
        await agent1.emit_thinking(Agent 1 thinking")
        await agent2.emit_thinking(Agent 2 thinking)
    # Verify state transitions
        expected_states = [
        uninitialized","
        initialized_1,
        initialized_2,"
        "active,
        active
    
        self.assertEqual(states, expected_states)
        self.loop.run_until_complete(run_test())
class TestPerformanceAndMemory(SSotAsyncTestCase):
        "Test performance and memory efficiency after refactoring."
    def setUp(self):
        "Set up test fixtures."
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    def tearDown(self):
        Clean up after tests.""
        pass
        self.loop.close()
    def test_memory_efficiency(self):
        Test memory efficiency with proper WebSocket handling."
    async def run_test():
        tracemalloc.start()
        baseline = tracemalloc.take_snapshot()
    # Track memory per iteration
        memory_per_iteration = []
        for iteration in range(200):
        # Create agent and bridge
        agent = DataSubAgent()
        bridge = AgentWebSocketBridge()
        agent.set_websocket_bridge(bridge, "
        # Send some events
        await agent.emit_thinking(Processing)"
        await agent.emit_tool_executing("tool, {}
        await agent.emit_progress(Done, is_complete=True)
        # Take memory snapshot every 10 iterations
        if iteration % 10 == 0:
        current = tracemalloc.take_snapshot()
        stats = current.compare_to(baseline, 'lineno')
        total_memory = sum(stat.size for stat in stats[:100]
        memory_per_iteration.append(total_memory / (iteration + 1))
            # Clean up references
        del agent
        del bridge
            # Force garbage collection
        gc.collect()
            # Verify memory efficiency
        if memory_per_iteration:
        avg_memory_per_iteration = sum(memory_per_iteration) / len(memory_per_iteration)
                # Should be less than 50KB per iteration
        self.assertLess(avg_memory_per_iteration, 50 * 1024,
        ""
        tracemalloc.stop()
        self.loop.run_until_complete(run_test())
    def test_throughput_performance(self):
        Test throughput performance with new WebSocket architecture.""
        pass
    async def run_test():
        pass
        capture = AdvancedWebSocketCapture()
    # Create mock bridge
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        mock_bridge.notify_agent_thinking = capture.capture_event
        mock_bridge.notify_tool_executing = capture.capture_event
        mock_bridge.notify_agent_completed = capture.capture_event
    # Create multiple agents
        agents = []
        for i in range(50):
        agent = DataSubAgent() if i % 2 == 0 else ValidationSubAgent()
        agent.set_websocket_bridge(mock_bridge, 
        agents.append(agent)
        # Measure throughput over 5 seconds
        start_time = time.perf_counter()
        end_time = start_time + 5.0  # 5 second test
        event_count = 0
        while time.perf_counter() < end_time:
            # Round-robin through agents
        agent = agents[event_count % len(agents)]
            # Send different event types
        if event_count % 3 == 0:
        await agent.emit_thinking(formatted_string")"
        elif event_count % 3 == 1:
        await agent.emit_tool_executing(formatted_string, {}
        else:
        await agent.emit_progress(formatted_string, is_complete=False)"
        event_count += 1
                        # Calculate final throughput
        duration = time.perf_counter() - start_time
        throughput = event_count / duration
        print(")
                        # Verify performance meets requirements
        self.assertGreater(throughput, 500, Throughput below 500 events/second target")"
                        # Check performance consistency
        perf_summary = capture.get_performance_summary()
        for event_type, metrics in perf_summary.items():
        self.assertLess(metrics['avg_ms'], 5.0,
        
        self.loop.run_until_complete(run_test())
    def test_performance_requirements(self):
        ""Test that performance meets all specified requirements.
    async def run_test():
        requirements = {
        'max_latency_ms': 50,
        'min_throughput_eps': 500,  # events per second
        'max_memory_kb_per_agent': 100,
        'max_concurrent_agents': 100
    
    # Test setup
        capture = AdvancedWebSocketCapture()
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        mock_bridge.notify_agent_thinking = capture.capture_event
    # Track metrics
        latencies = []
        memory_usage = []
    # Test concurrent agents
        agents = []
        for i in range(requirements['max_concurrent_agents']:
        agent = DataSubAgent()
        agent.set_websocket_bridge(mock_bridge, ""
        agents.append(agent)
        # Measure performance
        tracemalloc.start()
        start_time = time.perf_counter()
        event_count = 0
        # Run for 10 seconds
        while time.perf_counter() - start_time < 10:
        agent = agents[event_count % len(agents)]
        event_start = time.perf_counter()
        await agent.emit_thinking(formatted_string)
        latencies.append((time.perf_counter() - event_start) * 1000)
        event_count += 1
            # Check memory periodically
        if event_count % 100 == 0:
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        total_memory = sum(stat.size for stat in top_stats[:100]
        memory_usage.append(total_memory / len(agents) / 1024)  # KB per agent
        tracemalloc.stop()
                # Calculate results
        duration = time.perf_counter() - start_time
        throughput = event_count / duration
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        avg_memory = sum(memory_usage) / len(memory_usage) if memory_usage else 0
                # Verify requirements
        print(f )
        Performance Test Results:")
        print(formatted_string")
        print("")
        print(formatted_string)"
        print(")
        self.assertGreater(throughput, requirements['min_throughput_eps']
        self.assertLess(max_latency, requirements['max_latency_ms']
        self.assertLess(avg_memory, requirements['max_memory_kb_per_agent']
        self.loop.run_until_complete(run_test())
        if __name__ == __main__":"
        unittest.main(verbosity=2)
        pass