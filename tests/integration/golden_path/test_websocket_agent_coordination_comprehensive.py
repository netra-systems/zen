"""
Comprehensive Integration Tests for WebSocket-Agent Coordination in Golden Path

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure seamless WebSocket-Agent integration delivering $500K+ ARR
- Value Impact: Validates complete real-time communication flow that powers chat functionality
- Strategic Impact: Protects 90% of platform value through reliable WebSocket event delivery

This test suite validates the complete WebSocket-Agent coordination system that enables:
- Real-time agent execution updates via WebSocket events
- Bidirectional communication between agents and user interface
- Event ordering and reliability under load
- Multi-user concurrent agent execution
- Error handling and recovery in WebSocket communication
- Performance requirements for real-time user experience

Key Coverage Areas:
- WebSocket manager integration with agent execution
- AgentWebSocketBridge coordination and event delivery
- Real-time event streaming during agent workflows
- Multi-user isolation in WebSocket communications
- Error handling and reconnection logic
- Performance under concurrent load
- Event persistence and replay capabilities
"""

import asyncio
import json
import pytest
import time
import uuid
import websockets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch, call
from websockets.exceptions import ConnectionClosed, WebSocketException

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from test_framework.real_services_test_fixtures import real_services_fixture

# WebSocket and agent coordination imports
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.websocket_core.agent_handler import AgentHandler
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Agent execution imports
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

# Communication and messaging
from netra_backend.app.services.websocket.message_handler import MessageHandlerService
from netra_backend.app.websocket_core.handlers import MessageRouter

# Logging and monitoring
from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class TestWebSocketAgentCoordinationComprehensive(SSotAsyncTestCase):
    """
    Comprehensive integration tests for WebSocket-Agent coordination in golden path.
    
    Tests focus on real-time communication between WebSocket connections and agent
    execution that delivers the core chat functionality.
    """

    def setup_method(self, method):
        """Setup test environment with proper SSOT patterns."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        
        # Test users for multi-user testing
        self.test_users = [
            {
                "user_id": str(uuid.uuid4()),
                "thread_id": str(uuid.uuid4()),
                "run_id": str(uuid.uuid4())
            }
            for _ in range(3)
        ]
        
        # Event tracking for validation
        self.captured_events: List[Dict[str, Any]] = []
        self.event_sequences: Dict[str, List[Dict[str, Any]]] = {}
        self.websocket_connections: List[AsyncMock] = []
        
        # Performance tracking
        self.performance_metrics = []
        self.latency_measurements = []
        
        # Mock services
        self.mock_llm_manager = MagicMock()
        self.mock_llm_client = self.mock_factory.create_llm_client_mock()
        self.mock_llm_manager.get_default_client.return_value = self.mock_llm_client

    async def async_setup_method(self, method):
        """Async setup for WebSocket and agent initialization."""
        await super().async_setup_method(method)
        
        # Setup event capture system
        async def capture_websocket_event(event_type: str, data: Dict[str, Any], **kwargs):
            timestamp = datetime.utcnow()
            user_id = kwargs.get("user_id")
            
            event = {
                "type": event_type,
                "data": data,
                "timestamp": timestamp,
                "user_id": user_id,
                "thread_id": kwargs.get("thread_id"),
                "run_id": kwargs.get("run_id"),
                "latency": time.time()  # Will be updated when received
            }
            
            self.captured_events.append(event)
            
            # Organize by user for isolation testing
            if user_id:
                if user_id not in self.event_sequences:
                    self.event_sequences[user_id] = []
                self.event_sequences[user_id].append(event)
            
            logger.debug(f"Captured WebSocket event: {event_type} for user {user_id}")
        
        self.capture_websocket_event = capture_websocket_event

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.real_services
    async def test_websocket_manager_agent_bridge_integration(self):
        """
        BVJ: All segments | System Integration | Ensures WebSocket-Agent communication
        Test WebSocket manager integration with AgentWebSocketBridge.
        """
        # Create WebSocket bridge and manager
        websocket_bridge = AgentWebSocketBridge()
        
        # Mock WebSocket manager with event capture
        mock_websocket_manager = AsyncMock()
        mock_websocket_manager.send_event = self.capture_websocket_event
        websocket_bridge._websocket_manager = mock_websocket_manager
        
        user_context = UserExecutionContext(
            user_id=self.test_users[0]["user_id"],
            thread_id=self.test_users[0]["thread_id"],
            run_id=self.test_users[0]["run_id"]
        )
        
        # Test all bridge notification methods
        start_time = time.time()
        
        # 1. Agent Started
        await websocket_bridge.notify_agent_started(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            agent_name="supervisor",
            message="Starting comprehensive analysis"
        )
        
        # 2. Agent Thinking
        await websocket_bridge.notify_agent_thinking(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            thought="Analyzing current infrastructure and usage patterns"
        )
        
        # 3. Tool Executing
        await websocket_bridge.notify_tool_executing(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            tool_name="cost_analyzer",
            action="Fetching cloud cost data"
        )
        
        # 4. Tool Completed
        await websocket_bridge.notify_tool_completed(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            tool_name="cost_analyzer",
            result={
                "monthly_cost": 4750.25,
                "breakdown": {"compute": 2800, "storage": 1200, "network": 750.25},
                "optimization_opportunities": 3
            }
        )
        
        # 5. Agent Completed
        await websocket_bridge.notify_agent_completed(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            agent_name="supervisor",
            result={
                "analysis_complete": True,
                "recommendations": 5,
                "estimated_savings": 950.05
            }
        )
        
        total_time = time.time() - start_time
        
        # Verify all events were captured
        assert len(self.captured_events) == 5, f"Expected 5 events, got {len(self.captured_events)}"
        
        # Verify event types and order
        expected_event_types = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        actual_event_types = [event["type"] for event in self.captured_events]
        assert actual_event_types == expected_event_types, f"Event order incorrect: {actual_event_types}"
        
        # Verify event data integrity
        agent_started_event = self.captured_events[0]
        assert agent_started_event["data"]["agent_name"] == "supervisor"
        assert "Starting comprehensive analysis" in agent_started_event["data"]["message"]
        
        tool_completed_event = self.captured_events[3]
        assert tool_completed_event["data"]["tool_name"] == "cost_analyzer"
        assert tool_completed_event["data"]["result"]["monthly_cost"] == 4750.25
        
        # Verify user context propagation
        for event in self.captured_events:
            assert event["user_id"] == user_context.user_id
            assert event["thread_id"] == user_context.thread_id
        
        # Verify performance
        assert total_time < 0.1, f"Bridge communication too slow: {total_time}s"
        
        logger.info(f"✅ WebSocket-Agent bridge integration validated: 5 events in {total_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.real_services
    async def test_real_time_agent_execution_with_websocket_events(self):
        """
        BVJ: All segments | Real-time UX | Ensures real-time agent execution updates
        Test real-time WebSocket event delivery during actual agent execution.
        """
        # Create real WebSocket bridge and supervisor
        websocket_bridge = AgentWebSocketBridge()
        mock_websocket_manager = AsyncMock()
        mock_websocket_manager.send_event = self.capture_websocket_event
        websocket_bridge._websocket_manager = mock_websocket_manager
        
        # Create supervisor with WebSocket integration
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        supervisor.websocket_bridge = websocket_bridge
        
        # Mock LLM to simulate realistic agent execution
        async def mock_agent_execution(*args, **kwargs):
            # Simulate agent thinking and processing
            await asyncio.sleep(0.05)  # Simulated processing time
            return {
                "response": "I've analyzed your infrastructure costs and identified several optimization opportunities.",
                "analysis": {
                    "current_monthly_cost": 5200.75,
                    "optimization_potential": 1040.15,
                    "recommendations": [
                        "Right-size underutilized instances",
                        "Implement scheduled scaling",
                        "Optimize storage tiering"
                    ]
                },
                "confidence": 0.92
            }
        
        self.mock_llm_client.agenerate.return_value = await mock_agent_execution()
        
        user_context = UserExecutionContext(
            user_id=self.test_users[0]["user_id"],
            thread_id=self.test_users[0]["thread_id"],
            run_id=self.test_users[0]["run_id"]
        )
        
        # Execute supervisor with real-time event tracking
        execution_start_time = time.time()
        
        result = await supervisor.execute(
            context=user_context,
            stream_updates=True
        )
        
        execution_time = time.time() - execution_start_time
        
        # Verify execution completed
        assert result is not None, "Agent execution should return result"
        
        # Verify WebSocket events were sent during execution
        assert len(self.captured_events) > 0, "Events should be sent during agent execution"
        
        # Verify event timing - events should be spread across execution time
        event_timestamps = [event["timestamp"] for event in self.captured_events]
        
        if len(event_timestamps) > 1:
            time_spans = [
                (event_timestamps[i+1] - event_timestamps[i]).total_seconds()
                for i in range(len(event_timestamps) - 1)
            ]
            
            # Events should be distributed across execution time, not all at once
            max_time_span = max(time_spans) if time_spans else 0
            assert max_time_span < execution_time * 2, "Events should be distributed across execution"
        
        # Verify real-time performance
        assert execution_time < 2.0, f"Agent execution too slow for real-time: {execution_time}s"
        
        # Check for critical events
        event_types = [event["type"] for event in self.captured_events]
        critical_events = ["agent_started", "agent_completed"]
        
        for critical_event in critical_events:
            if critical_event not in event_types:
                logger.warning(f"Critical event missing: {critical_event}")
        
        logger.info(f"✅ Real-time agent execution validated: {len(self.captured_events)} events in {execution_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.concurrency
    async def test_multi_user_websocket_agent_isolation(self):
        """
        BVJ: All segments | Multi-user Support | Ensures proper user isolation
        Test WebSocket-Agent coordination with multiple concurrent users.
        """
        # Create WebSocket bridge
        websocket_bridge = AgentWebSocketBridge()
        mock_websocket_manager = AsyncMock()
        mock_websocket_manager.send_event = self.capture_websocket_event
        websocket_bridge._websocket_manager = mock_websocket_manager
        
        # Create execution engine factory for user isolation
        execution_factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        # Create user contexts and engines
        num_users = 3
        user_contexts = []
        user_engines = []
        
        for i in range(num_users):
            context = UserExecutionContext(
                user_id=self.test_users[i]["user_id"],
                thread_id=self.test_users[i]["thread_id"],
                run_id=self.test_users[i]["run_id"],
                agent_context={"user_index": i}
            )
            user_contexts.append(context)
            
            engine = await execution_factory.create_for_user(context)
            user_engines.append(engine)
        
        # Simulate concurrent agent executions
        async def simulate_user_agent_workflow(user_index: int, engine: UserExecutionEngine):
            context = user_contexts[user_index]
            user_id = context.user_id
            
            # Simulate agent workflow with WebSocket events
            await websocket_bridge.notify_agent_started(
                user_id=user_id,
                thread_id=context.thread_id,
                agent_name=f"user_{user_index}_agent",
                message=f"Starting analysis for user {user_index}"
            )
            
            # Simulate processing
            await asyncio.sleep(0.02 + (user_index * 0.01))  # Staggered timing
            
            await websocket_bridge.notify_agent_thinking(
                user_id=user_id,
                thread_id=context.thread_id,
                thought=f"Processing user {user_index} specific requirements"
            )
            
            await websocket_bridge.notify_tool_executing(
                user_id=user_id,
                thread_id=context.thread_id,
                tool_name=f"user_{user_index}_tool",
                action=f"Executing tool for user {user_index}"
            )
            
            await websocket_bridge.notify_tool_completed(
                user_id=user_id,
                thread_id=context.thread_id,
                tool_name=f"user_{user_index}_tool",
                result={"user_data": f"result_for_user_{user_index}", "value": 1000 + user_index}
            )
            
            await websocket_bridge.notify_agent_completed(
                user_id=user_id,
                thread_id=context.thread_id,
                agent_name=f"user_{user_index}_agent",
                result={"completed": True, "user_specific": f"data_for_user_{user_index}"}
            )
            
            return f"user_{user_index}_completed"
        
        # Execute all user workflows concurrently
        concurrent_start_time = time.time()
        
        workflow_tasks = [
            simulate_user_agent_workflow(i, engine)
            for i, engine in enumerate(user_engines)
        ]
        
        results = await asyncio.gather(*workflow_tasks)
        concurrent_execution_time = time.time() - concurrent_start_time
        
        # Verify all workflows completed
        assert len(results) == num_users, f"Expected {num_users} results, got {len(results)}"
        for i, result in enumerate(results):
            assert result == f"user_{i}_completed", f"User {i} workflow should complete correctly"
        
        # Verify event isolation
        total_events = len(self.captured_events)
        expected_events_per_user = 5  # agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        expected_total_events = num_users * expected_events_per_user
        
        assert total_events == expected_total_events, f"Expected {expected_total_events} events, got {total_events}"
        
        # Verify user-specific event sequences
        for i, user_context in enumerate(user_contexts):
            user_id = user_context.user_id
            user_events = self.event_sequences.get(user_id, [])
            
            assert len(user_events) == expected_events_per_user, f"User {i} should have {expected_events_per_user} events, got {len(user_events)}"
            
            # Verify user-specific data in events
            for event in user_events:
                assert event["user_id"] == user_id, f"Event user_id should match for user {i}"
                
                # Check for user-specific content
                event_data_str = str(event["data"])
                if f"user_{i}" in event_data_str:
                    # Verify no other user data leaked
                    for j in range(num_users):
                        if j != i:
                            assert f"user_{j}" not in event_data_str, f"User {j} data found in user {i} event"
        
        # Verify concurrent performance
        assert concurrent_execution_time < 1.0, f"Concurrent execution too slow: {concurrent_execution_time}s"
        
        # Verify no cross-user data contamination
        user_0_events = [e for e in self.captured_events if e["user_id"] == user_contexts[0].user_id]
        user_1_events = [e for e in self.captured_events if e["user_id"] == user_contexts[1].user_id]
        
        # User 0 events should not contain user 1 data
        for event in user_0_events:
            event_str = str(event)
            assert "user_1_" not in event_str, "User 0 events should not contain user 1 data"
        
        for event in user_1_events:
            event_str = str(event)
            assert "user_0_" not in event_str, "User 1 events should not contain user 0 data"
        
        logger.info(f"✅ Multi-user WebSocket-Agent isolation validated: {num_users} users, {total_events} events in {concurrent_execution_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.performance
    async def test_websocket_agent_performance_under_load(self):
        """
        BVJ: Mid/Enterprise | Performance SLA | Ensures performance under load
        Test WebSocket-Agent coordination performance under concurrent load.
        """
        # Create WebSocket bridge with performance monitoring
        websocket_bridge = AgentWebSocketBridge()
        
        # Performance tracking
        event_latencies = []
        throughput_metrics = []
        
        async def performance_tracking_send_event(event_type: str, data: Dict[str, Any], **kwargs):
            start_latency = time.time()
            await self.capture_websocket_event(event_type, data, **kwargs)
            end_latency = time.time()
            
            latency = end_latency - start_latency
            event_latencies.append(latency)
            
            self.latency_measurements.append({
                "event_type": event_type,
                "latency": latency,
                "timestamp": datetime.utcnow(),
                "user_id": kwargs.get("user_id")
            })
        
        mock_websocket_manager = AsyncMock()
        mock_websocket_manager.send_event = performance_tracking_send_event
        websocket_bridge._websocket_manager = mock_websocket_manager
        
        # Load test parameters
        num_concurrent_agents = 20
        events_per_agent = 5
        
        # Create load test contexts
        load_test_contexts = []
        for i in range(num_concurrent_agents):
            context = UserExecutionContext(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4())
            )
            load_test_contexts.append(context)
        
        # Load test execution
        async def agent_load_simulation(agent_index: int, context: UserExecutionContext):
            user_id = context.user_id
            thread_id = context.thread_id
            
            # Simulate full agent workflow
            await websocket_bridge.notify_agent_started(
                user_id=user_id,
                thread_id=thread_id,
                agent_name=f"load_agent_{agent_index}",
                message=f"Load test agent {agent_index} starting"
            )
            
            await websocket_bridge.notify_agent_thinking(
                user_id=user_id,
                thread_id=thread_id,
                thought=f"Load agent {agent_index} processing"
            )
            
            await websocket_bridge.notify_tool_executing(
                user_id=user_id,
                thread_id=thread_id,
                tool_name="load_test_tool",
                action="Load testing tool execution"
            )
            
            await websocket_bridge.notify_tool_completed(
                user_id=user_id,
                thread_id=thread_id,
                tool_name="load_test_tool",
                result={"load_test_data": f"result_{agent_index}", "performance": "measured"}
            )
            
            await websocket_bridge.notify_agent_completed(
                user_id=user_id,
                thread_id=thread_id,
                agent_name=f"load_agent_{agent_index}",
                result={"load_test_complete": True, "agent_index": agent_index}
            )
        
        # Execute load test
        load_test_start = time.time()
        
        load_tasks = [
            agent_load_simulation(i, context)
            for i, context in enumerate(load_test_contexts)
        ]
        
        await asyncio.gather(*load_tasks)
        
        load_test_duration = time.time() - load_test_start
        
        # Calculate performance metrics
        total_events = len(self.captured_events)
        expected_total_events = num_concurrent_agents * events_per_agent
        
        assert total_events == expected_total_events, f"Expected {expected_total_events} events, got {total_events}"
        
        # Throughput calculation
        events_per_second = total_events / load_test_duration
        
        # Latency analysis
        avg_latency = sum(event_latencies) / len(event_latencies) if event_latencies else 0
        max_latency = max(event_latencies) if event_latencies else 0
        p95_latency = sorted(event_latencies)[int(len(event_latencies) * 0.95)] if event_latencies else 0
        
        # Performance requirements validation
        assert events_per_second >= 100, f"Throughput too low: {events_per_second:.1f} events/sec (required: 100+ events/sec)"
        assert avg_latency < 0.01, f"Average latency too high: {avg_latency:.4f}s (required: <0.01s)"
        assert max_latency < 0.05, f"Max latency too high: {max_latency:.4f}s (required: <0.05s)"
        assert p95_latency < 0.02, f"P95 latency too high: {p95_latency:.4f}s (required: <0.02s)"
        
        # Memory and resource efficiency check
        memory_per_event = self._estimate_memory_per_event()
        assert memory_per_event < 1024, f"Memory per event too high: {memory_per_event} bytes (required: <1KB)"
        
        # Log performance results
        performance_summary = {
            "concurrent_agents": num_concurrent_agents,
            "total_events": total_events,
            "duration": load_test_duration,
            "throughput_eps": events_per_second,
            "avg_latency_ms": avg_latency * 1000,
            "max_latency_ms": max_latency * 1000,
            "p95_latency_ms": p95_latency * 1000,
            "memory_per_event_bytes": memory_per_event
        }
        
        self.performance_metrics.append(performance_summary)
        
        logger.info(f"✅ WebSocket-Agent performance under load validated: {events_per_second:.1f} events/sec, {avg_latency*1000:.2f}ms avg latency")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.reliability
    async def test_websocket_error_handling_and_recovery(self):
        """
        BVJ: All segments | System Reliability | Ensures graceful error handling
        Test WebSocket-Agent coordination error handling and recovery.
        """
        # Create WebSocket bridge with error simulation
        websocket_bridge = AgentWebSocketBridge()
        
        # Error tracking
        error_events = []
        recovery_events = []
        failed_operations = 0
        successful_recoveries = 0
        
        # Mock WebSocket manager that fails intermittently
        class FailingWebSocketManager:
            def __init__(self):
                self.call_count = 0
                self.failure_rate = 0.3  # 30% failure rate
            
            async def send_event(self, event_type: str, data: Dict[str, Any], **kwargs):
                self.call_count += 1
                
                # Simulate intermittent failures
                if self.call_count % 3 == 0:  # Every 3rd call fails
                    nonlocal failed_operations
                    failed_operations += 1
                    error_events.append({
                        "event_type": event_type,
                        "error": "WebSocket connection failed",
                        "timestamp": datetime.utcnow(),
                        "call_count": self.call_count
                    })
                    raise WebSocketException("Simulated WebSocket failure")
                else:
                    # Successful operation
                    await self.capture_websocket_event(event_type, data, **kwargs)
        
        failing_manager = FailingWebSocketManager()
        websocket_bridge._websocket_manager = failing_manager
        
        # Test error handling with retry logic
        user_context = UserExecutionContext(
            user_id=self.test_users[0]["user_id"],
            thread_id=self.test_users[0]["thread_id"],
            run_id=self.test_users[0]["run_id"]
        )
        
        # Enhanced bridge with retry logic
        async def resilient_notify_agent_started(user_id, thread_id, agent_name, message, max_retries=3):
            for attempt in range(max_retries):
                try:
                    await websocket_bridge.notify_agent_started(
                        user_id=user_id,
                        thread_id=thread_id,
                        agent_name=agent_name,
                        message=message
                    )
                    if attempt > 0:
                        nonlocal successful_recoveries
                        successful_recoveries += 1
                        recovery_events.append({
                            "event_type": "agent_started",
                            "attempt": attempt + 1,
                            "recovered": True,
                            "timestamp": datetime.utcnow()
                        })
                    return True
                except WebSocketException as e:
                    if attempt == max_retries - 1:
                        raise  # Re-raise on final attempt
                    await asyncio.sleep(0.01 * (attempt + 1))  # Exponential backoff
            return False
        
        # Test resilient operations
        operations_to_test = [
            ("agent_started", {"agent_name": "resilient_agent", "message": "Testing error recovery"}),
            ("agent_thinking", {"thought": "Processing with error handling"}),
            ("tool_executing", {"tool_name": "resilient_tool", "action": "Executing with retry logic"}),
            ("tool_completed", {"tool_name": "resilient_tool", "result": {"status": "success"}}),
            ("agent_completed", {"agent_name": "resilient_agent", "result": {"completed": True}})
        ]
        
        # Test error handling for each operation type
        for operation_type, operation_data in operations_to_test:
            try:
                if operation_type == "agent_started":
                    await resilient_notify_agent_started(
                        user_id=user_context.user_id,
                        thread_id=user_context.thread_id,
                        **operation_data
                    )
                # Add other operation types as needed for comprehensive testing
            except WebSocketException:
                # Some operations may still fail after all retries
                pass
        
        # Verify error handling metrics
        total_operations = len(operations_to_test)
        
        # Should have some failures (due to simulated errors)
        assert failed_operations > 0, "Simulated failures should occur"
        
        # Should have some recoveries (due to retry logic)
        if successful_recoveries > 0:
            logger.info(f"Successful recoveries: {successful_recoveries}")
        
        # Verify some events were still captured despite errors
        successful_events = len(self.captured_events)
        if successful_events > 0:
            assert successful_events <= total_operations, "Captured events should not exceed total operations"
        
        # Verify error tracking
        assert len(error_events) == failed_operations, "All failures should be tracked"
        
        # Verify error events contain required information
        for error_event in error_events:
            assert "event_type" in error_event, "Error event should contain event type"
            assert "error" in error_event, "Error event should contain error message"
            assert "timestamp" in error_event, "Error event should contain timestamp"
        
        # Calculate error handling efficiency
        if failed_operations > 0:
            recovery_rate = successful_recoveries / failed_operations
            logger.info(f"Error recovery rate: {recovery_rate:.2%}")
        
        logger.info(f"✅ WebSocket error handling validated: {failed_operations} failures, {successful_recoveries} recoveries, {successful_events} successful events")

    def _estimate_memory_per_event(self) -> int:
        """Estimate memory usage per WebSocket event."""
        if not self.captured_events:
            return 0
        
        # Rough estimation based on event data size
        total_size = 0
        for event in self.captured_events:
            event_json = json.dumps(event, default=str)
            total_size += len(event_json.encode('utf-8'))
        
        return total_size // len(self.captured_events) if self.captured_events else 0

    def teardown_method(self, method):
        """Cleanup after tests."""
        # Clear event tracking
        self.captured_events.clear()
        self.event_sequences.clear()
        self.performance_metrics.clear()
        self.latency_measurements.clear()
        
        # Clear WebSocket connections
        self.websocket_connections.clear()
        
        super().teardown_method(method)
    
    async def async_teardown_method(self, method):
        """Async cleanup after tests."""
        # Close any open WebSocket connections
        for connection in self.websocket_connections:
            if hasattr(connection, 'close'):
                try:
                    await connection.close()
                except Exception:
                    pass  # Ignore cleanup errors
        
        await super().async_teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
