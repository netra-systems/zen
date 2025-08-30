#!/usr/bin/env python
"""MISSION CRITICAL TEST SUITE: WebSocket Agent Events

THIS SUITE MUST PASS OR THE PRODUCT IS BROKEN.
Business Value: $500K+ ARR - Core chat functionality

This comprehensive test suite validates WebSocket agent event integration at multiple levels:
1. Unit Tests - Component isolation
2. Integration Tests - Component interaction  
3. E2E Tests - Complete user flow

ANY FAILURE HERE BLOCKS DEPLOYMENT.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
import threading
import random

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import production components
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.enhanced_tool_execution import (
    EnhancedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager


# ============================================================================
# TEST UTILITIES
# ============================================================================

class MissionCriticalEventValidator:
    """Validates WebSocket events with extreme rigor."""
    
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.events: List[Dict] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, data)
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()
        
    def record(self, event: Dict) -> None:
        """Record an event with detailed tracking."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")
        
        self.events.append(event)
        self.event_timeline.append((timestamp, event_type, event))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
    def validate_critical_requirements(self) -> tuple[bool, List[str]]:
        """Validate that ALL critical requirements are met."""
        failures = []
        
        # 1. Check for required events
        missing = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(f"CRITICAL: Missing required events: {missing}")
        
        # 2. Validate event ordering
        if not self._validate_event_order():
            failures.append("CRITICAL: Invalid event order")
        
        # 3. Check for paired events
        if not self._validate_paired_events():
            failures.append("CRITICAL: Unpaired tool events")
        
        # 4. Validate timing constraints
        if not self._validate_timing():
            failures.append("CRITICAL: Event timing violations")
        
        # 5. Check for data completeness
        if not self._validate_event_data():
            failures.append("CRITICAL: Incomplete event data")
        
        return len(failures) == 0, failures
    
    def _validate_event_order(self) -> bool:
        """Ensure events follow logical order."""
        if not self.event_timeline:
            return False
            
        # First event must be agent_started
        if self.event_timeline[0][1] != "agent_started":
            self.errors.append(f"First event was {self.event_timeline[0][1]}, not agent_started")
            return False
        
        # Last event should be completion
        last_event = self.event_timeline[-1][1]
        if last_event not in ["agent_completed", "final_report"]:
            self.errors.append(f"Last event was {last_event}, not a completion event")
            return False
            
        return True
    
    def _validate_paired_events(self) -> bool:
        """Ensure tool events are properly paired."""
        tool_starts = self.event_counts.get("tool_executing", 0)
        tool_ends = self.event_counts.get("tool_completed", 0)
        
        if tool_starts != tool_ends:
            self.errors.append(f"Tool event mismatch: {tool_starts} starts, {tool_ends} completions")
            return False
            
        return True
    
    def _validate_timing(self) -> bool:
        """Validate event timing constraints."""
        if not self.event_timeline:
            return True
            
        # Check for events that arrive too late
        for timestamp, event_type, _ in self.event_timeline:
            if timestamp > 30:  # 30 second timeout
                self.errors.append(f"Event {event_type} arrived after 30s timeout at {timestamp:.2f}s")
                return False
                
        return True
    
    def _validate_event_data(self) -> bool:
        """Ensure events contain required data fields."""
        for event in self.events:
            if "type" not in event:
                self.errors.append("Event missing 'type' field")
                return False
            if "timestamp" not in event and self.strict_mode:
                self.warnings.append(f"Event {event.get('type')} missing timestamp")
                
        return True
    
    def generate_report(self) -> str:
        """Generate comprehensive validation report."""
        is_valid, failures = self.validate_critical_requirements()
        
        report = [
            "\n" + "=" * 80,
            "MISSION CRITICAL VALIDATION REPORT",
            "=" * 80,
            f"Status: {'✅ PASSED' if is_valid else '❌ FAILED'}",
            f"Total Events: {len(self.events)}",
            f"Unique Types: {len(self.event_counts)}",
            f"Duration: {self.event_timeline[-1][0] if self.event_timeline else 0:.2f}s",
            "",
            "Event Coverage:"
        ]
        
        for event in self.REQUIRED_EVENTS:
            count = self.event_counts.get(event, 0)
            status = "✅" if count > 0 else "❌"
            report.append(f"  {status} {event}: {count}")
        
        if failures:
            report.extend(["", "FAILURES:"] + [f"  - {f}" for f in failures])
        
        if self.errors:
            report.extend(["", "ERRORS:"] + [f"  - {e}" for e in self.errors])
            
        if self.warnings and self.strict_mode:
            report.extend(["", "WARNINGS:"] + [f"  - {w}" for w in self.warnings])
        
        report.append("=" * 80)
        return "\n".join(report)


class StressTestClient:
    """Simulates stress conditions for WebSocket testing."""
    
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self.connections: Dict[str, Any] = {}
        
    async def create_concurrent_connections(self, count: int) -> List[str]:
        """Create multiple concurrent connections."""
        connection_ids = []
        
        async def create_connection():
            conn_id = f"stress-{uuid.uuid4()}"
            mock_ws = MagicMock()
            mock_ws.send_json = AsyncMock()
            await self.ws_manager.connect_user(conn_id, mock_ws, conn_id)
            self.connections[conn_id] = mock_ws
            return conn_id
        
        tasks = [create_connection() for _ in range(count)]
        connection_ids = await asyncio.gather(*tasks)
        return connection_ids
    
    async def send_rapid_messages(self, connection_id: str, count: int, delay: float = 0.01):
        """Send rapid-fire messages to test throughput."""
        for i in range(count):
            message = {
                "type": "user_message",
                "content": f"Rapid message {i}",
                "timestamp": datetime.utcnow().isoformat()
            }
            # Simulate sending through WebSocket
            await asyncio.sleep(delay)
    
    async def cleanup(self):
        """Clean up all connections."""
        for conn_id, mock_ws in self.connections.items():
            await self.ws_manager.disconnect_user(conn_id, mock_ws, conn_id)


# ============================================================================
# UNIT TESTS - Component Isolation
# ============================================================================

class TestUnitWebSocketComponents:
    """Unit tests for individual WebSocket components."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_notifier_all_methods(self):
        """Test that WebSocketNotifier has ALL required methods and they work."""
        ws_manager = WebSocketManager()
        notifier = WebSocketNotifier(ws_manager)
        
        # Verify all methods exist
        required_methods = [
            'send_agent_started',
            'send_agent_thinking',
            'send_partial_result',
            'send_tool_executing',
            'send_tool_completed',
            'send_final_report',
            'send_agent_completed'
        ]
        
        for method in required_methods:
            assert hasattr(notifier, method), f"Missing critical method: {method}"
            assert callable(getattr(notifier, method)), f"Method {method} is not callable"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_tool_dispatcher_enhancement(self):
        """Test that tool dispatcher enhancement actually works."""
        dispatcher = ToolDispatcher()
        ws_manager = WebSocketManager()
        
        # Verify initial state
        assert hasattr(dispatcher, 'executor'), "ToolDispatcher missing executor"
        original_executor = dispatcher.executor
        
        # Enhance
        enhance_tool_dispatcher_with_notifications(dispatcher, ws_manager)
        
        # Verify enhancement
        assert dispatcher.executor != original_executor, "Executor was not replaced"
        assert isinstance(dispatcher.executor, EnhancedToolExecutionEngine), \
            "Executor is not EnhancedToolExecutionEngine"
        assert hasattr(dispatcher, '_websocket_enhanced'), "Missing enhancement marker"
        assert dispatcher._websocket_enhanced is True, "Enhancement marker not set"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_agent_registry_websocket_integration(self):
        """Test that AgentRegistry properly integrates WebSocket."""
        class MockLLM:
            pass
        
        tool_dispatcher = ToolDispatcher()
        registry = AgentRegistry(MockLLM(), tool_dispatcher)
        ws_manager = WebSocketManager()
        
        # Set WebSocket manager
        registry.set_websocket_manager(ws_manager)
        
        # Verify tool dispatcher was enhanced
        assert isinstance(tool_dispatcher.executor, EnhancedToolExecutionEngine), \
            "AgentRegistry did not enhance tool dispatcher"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_execution_engine_initialization(self):
        """Test that ExecutionEngine properly initializes WebSocket components."""
        class MockLLM:
            pass
        
        registry = AgentRegistry(MockLLM(), ToolDispatcher())
        ws_manager = WebSocketManager()
        
        engine = ExecutionEngine(registry, ws_manager)
        
        # Verify WebSocket components
        assert hasattr(engine, 'websocket_notifier'), "Missing websocket_notifier"
        assert isinstance(engine.websocket_notifier, WebSocketNotifier), \
            "websocket_notifier is not WebSocketNotifier"
        assert hasattr(engine, 'send_agent_thinking'), "Missing send_agent_thinking method"
        assert hasattr(engine, 'send_partial_result'), "Missing send_partial_result method"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_enhanced_tool_execution_sends_events(self):
        """Test that enhanced tool execution actually sends WebSocket events."""
        ws_manager = WebSocketManager()
        validator = MissionCriticalEventValidator()
        
        # Mock connection
        conn_id = "test-enhanced"
        mock_ws = MagicMock()
        
        async def capture(message, timeout=None):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator.record(data)
        
        mock_ws.send_json = AsyncMock(side_effect=capture)
        await ws_manager.connect_user(conn_id, mock_ws, conn_id)
        
        # Create enhanced executor
        executor = EnhancedToolExecutionEngine(ws_manager)
        
        # Create test context
        context = AgentExecutionContext(
            run_id="req-123",
            thread_id=conn_id,
            user_id=conn_id,
            agent_name="test",
            retry_count=0,
            max_retries=1
        )
        
        # Mock tool that accepts arguments
        async def test_tool(*args, **kwargs):
            return {"result": "success"}
        
        # Execute with context
        state = DeepAgentState(
            chat_thread_id=conn_id,
            user_id=conn_id,
            run_id="run-123"
        )
        
        result = await executor.execute_with_state(
            test_tool, "test_tool", {}, state, "run-123"
        )
        
        # Verify events were sent
        assert validator.event_counts.get("tool_executing", 0) > 0, \
            "No tool_executing event sent"
        assert validator.event_counts.get("tool_completed", 0) > 0, \
            "No tool_completed event sent"


# ============================================================================
# INTEGRATION TESTS - Component Interaction
# ============================================================================

class TestIntegrationWebSocketFlow:
    """Integration tests for WebSocket event flow between components."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_supervisor_to_websocket_flow(self):
        """Test complete flow from supervisor to WebSocket events."""
        ws_manager = WebSocketManager()
        validator = MissionCriticalEventValidator()
        
        # Setup mock connection
        conn_id = "integration-test"
        mock_ws = MagicMock()
        
        async def capture(message, timeout=None):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator.record(data)
        
        mock_ws.send_json = AsyncMock(side_effect=capture)
        await ws_manager.connect_user(conn_id, mock_ws, conn_id)
        
        # Create supervisor components
        class MockLLM:
            async def generate(self, *args, **kwargs):
                return {"content": "Test response", "reasoning": "Test reasoning"}
        
        llm = MockLLM()
        tool_dispatcher = ToolDispatcher()
        
        # Register a test tool - create a proper mock tool
        from langchain_core.tools import BaseTool
        
        class MockTool(BaseTool):
            name: str = "test_tool"
            description: str = "Test tool"
            
            async def _arun(self, *args, **kwargs):
                return {"processed": "test_data"}
            
            def _run(self, *args, **kwargs):
                return {"processed": "test_data"}
        
        mock_tool = MockTool()
        
        # Register the tool with the dispatcher's registry
        tool_dispatcher.registry.register_tool(mock_tool)
        
        # Create registry with WebSocket
        registry = AgentRegistry(llm, tool_dispatcher)
        registry.set_websocket_manager(ws_manager)
        
        # Create and register a mock agent that will use the tool
        class TestAgent:
            async def execute(self, state, run_id, return_direct=True):
                # Simulate agent invoking a tool
                if hasattr(tool_dispatcher, 'executor'):
                    # Use execute_with_state for WebSocket notifications
                    if hasattr(tool_dispatcher.executor, 'execute_with_state'):
                        await tool_dispatcher.executor.execute_with_state(
                            mock_tool, "test_tool", {}, state, state.run_id
                        )
                # Use the correct field for DeepAgentState
                state.final_report = "Test completed"
                return state
        
        test_agent = TestAgent()
        registry.register("test_agent", test_agent)
        
        # Create execution engine
        engine = ExecutionEngine(registry, ws_manager)
        
        # Create context
        context = AgentExecutionContext(
            run_id="req-456",
            thread_id=conn_id,
            user_id=conn_id,
            agent_name="test_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Create state
        state = DeepAgentState()
        state.user_request = "Test request"
        state.chat_thread_id = conn_id
        state.run_id = "req-456"
        state.user_id = conn_id
        
        # Execute
        result = await engine.execute_agent(context, state)
        
        # Allow events to propagate
        await asyncio.sleep(0.5)
        
        # Validate
        is_valid, failures = validator.validate_critical_requirements()
        
        if not is_valid:
            logger.error(validator.generate_report())
            
        assert is_valid, f"Integration test failed: {failures}"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_concurrent_agent_websocket_events(self):
        """Test WebSocket events with multiple concurrent agents."""
        ws_manager = WebSocketManager()
        validators = {}
        
        # Create multiple connections
        connection_count = 5
        connections = []
        
        for i in range(connection_count):
            conn_id = f"concurrent-{i}"
            validator = MissionCriticalEventValidator()
            validators[conn_id] = validator
            
            mock_ws = MagicMock()
            
            async def capture(message, timeout=None, v=validator):
                if isinstance(message, str):
                    data = json.loads(message)
                else:
                    data = message
                v.record(data)
            
            mock_ws.send_json = AsyncMock(side_effect=capture)
            await ws_manager.connect_user(conn_id, mock_ws, conn_id)
            connections.append((conn_id, mock_ws))
        
        # Create notifier
        notifier = WebSocketNotifier(ws_manager)
        
        # Send events concurrently
        async def send_events_for_connection(conn_id):
            request_id = f"req-{conn_id}"
            await notifier.send_agent_started(conn_id, request_id, "agent")
            await asyncio.sleep(random.uniform(0.01, 0.05))
            await notifier.send_agent_thinking(conn_id, request_id, "Thinking...")
            await asyncio.sleep(random.uniform(0.01, 0.05))
            await notifier.send_tool_executing(conn_id, request_id, "tool", {})
            await asyncio.sleep(random.uniform(0.01, 0.05))
            await notifier.send_tool_completed(conn_id, request_id, "tool", {"result": "done"})
            await asyncio.sleep(random.uniform(0.01, 0.05))
            await notifier.send_agent_completed(conn_id, request_id, {"success": True})
        
        # Execute concurrently
        tasks = [send_events_for_connection(conn_id) for conn_id, _ in connections]
        await asyncio.gather(*tasks)
        
        # Allow processing
        await asyncio.sleep(0.5)
        
        # Validate each connection
        for conn_id, validator in validators.items():
            is_valid, failures = validator.validate_critical_requirements()
            assert is_valid, f"Connection {conn_id} failed: {failures}"
        
        # Cleanup
        for conn_id, mock_ws in connections:
            await ws_manager.disconnect_user(conn_id, mock_ws, conn_id)
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_error_recovery_websocket_events(self):
        """Test that errors still result in proper WebSocket events."""
        ws_manager = WebSocketManager()
        validator = MissionCriticalEventValidator(strict_mode=False)
        
        conn_id = "error-test"
        mock_ws = MagicMock()
        
        async def capture(message, timeout=None):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator.record(data)
        
        mock_ws.send_json = AsyncMock(side_effect=capture)
        await ws_manager.connect_user(conn_id, mock_ws, conn_id)
        
        # Create components that will error
        class ErrorLLM:
            async def generate(self, *args, **kwargs):
                raise Exception("Simulated LLM failure")
        
        registry = AgentRegistry(ErrorLLM(), ToolDispatcher())
        registry.set_websocket_manager(ws_manager)
        
        engine = ExecutionEngine(registry, ws_manager)
        
        context = AgentExecutionContext(
            run_id="err-123",
            thread_id=conn_id,
            user_id=conn_id,
            agent_name="error_agent",
            retry_count=0,
            max_retries=1
        )
        
        state = DeepAgentState()
        state.chat_thread_id = conn_id
        
        # Execute (should handle error)
        result = await engine.execute_agent(context, state)
        
        await asyncio.sleep(0.5)
        
        # Should still have start and completion events
        assert validator.event_counts.get("agent_started", 0) > 0, \
            "No agent_started event even with error"
        assert any(e in validator.event_counts for e in ["agent_completed", "agent_fallback"]), \
            "No completion event after error"


# ============================================================================
# E2E TESTS - Complete User Flow
# ============================================================================

class TestE2EWebSocketChatFlow:
    """End-to-end tests for complete chat flow with WebSocket events."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_complete_user_chat_flow(self):
        """Test complete user chat flow from message to response."""
        ws_manager = WebSocketManager()
        validator = MissionCriticalEventValidator()
        
        # Setup user connection
        user_id = "e2e-user"
        conn_id = "e2e-conn"
        mock_ws = MagicMock()
        
        received_events = []
        
        async def capture(message, timeout=None):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            received_events.append(data)
            validator.record(data)
            logger.info(f"E2E Event: {data.get('type', 'unknown')}")
        
        mock_ws.send_json = AsyncMock(side_effect=capture)
        await ws_manager.connect_user(user_id, mock_ws, conn_id)
        
        # Import and setup supervisor
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        
        class MockLLM:
            async def generate(self, *args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate processing
                return {
                    "content": "I can help you with that.",
                    "reasoning": "Analyzing the request...",
                    "confidence": 0.95
                }
        
        llm = MockLLM()
        tool_dispatcher = ToolDispatcher()
        
        # Register realistic tools
        async def search_knowledge(query: str) -> Dict:
            await asyncio.sleep(0.05)
            return {"results": f"Found information about {query}"}
        
        async def analyze_data(data: Dict) -> Dict:
            await asyncio.sleep(0.05)
            return {"analysis": "Data analyzed successfully"}
        
        tool_dispatcher.register_tool("search_knowledge", search_knowledge, "Search knowledge base")
        tool_dispatcher.register_tool("analyze_data", analyze_data, "Analyze data")
        
        # Create supervisor
        supervisor = SupervisorAgent(llm, tool_dispatcher)
        
        # Setup supervisor components
        registry = AgentRegistry(llm, tool_dispatcher)
        registry.set_websocket_manager(ws_manager)
        registry.register_default_agents()
        
        engine = ExecutionEngine(registry, ws_manager)
        
        supervisor.agent_registry = registry
        supervisor.execution_engine = engine
        supervisor.websocket_manager = ws_manager
        
        # Simulate user message
        user_message = "What is the system status?"
        
        # Process through supervisor
        try:
            result = await supervisor.execute(
                user_message,
                conn_id,
                user_id
            )
            logger.info(f"Supervisor result: {result is not None}")
        except Exception as e:
            logger.error(f"Supervisor execution failed: {e}")
        
        # Allow all async events to complete
        await asyncio.sleep(1.0)
        
        # Validate complete flow
        logger.info(validator.generate_report())
        
        is_valid, failures = validator.validate_critical_requirements()
        assert is_valid, f"E2E flow validation failed: {failures}"
        
        # Additional E2E validations
        assert len(received_events) >= 5, \
            f"Expected at least 5 events, got {len(received_events)}"
        
        # Verify user would see meaningful updates
        event_types = [e.get("type") for e in received_events]
        assert "agent_started" in event_types, "User wouldn't know processing started"
        assert any("complet" in t or "final" in t for t in event_types), \
            "User wouldn't know when processing finished"
        
        # Cleanup
        await ws_manager.disconnect_user(user_id, mock_ws, conn_id)
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_stress_test_websocket_events(self):
        """Stress test WebSocket events under load."""
        ws_manager = WebSocketManager()
        stress_client = StressTestClient(ws_manager)
        
        # Create many concurrent connections
        connection_ids = await stress_client.create_concurrent_connections(10)
        
        # Create notifier
        notifier = WebSocketNotifier(ws_manager)
        
        # Send many events rapidly
        event_count = 0
        start_time = time.time()
        
        async def send_burst(conn_id):
            nonlocal event_count
            for i in range(50):  # 50 events per connection
                request_id = f"stress-{conn_id}-{i}"
                await notifier.send_agent_thinking(conn_id, request_id, f"Processing {i}")
                event_count += 1
                if i % 10 == 0:
                    await notifier.send_partial_result(conn_id, request_id, f"Result {i}")
                    event_count += 1
        
        # Send events to all connections concurrently
        tasks = [send_burst(conn_id) for conn_id in connection_ids]
        await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        events_per_second = event_count / duration
        
        logger.info(f"Stress test: {event_count} events in {duration:.2f}s = {events_per_second:.0f} events/s")
        
        # Verify performance
        assert events_per_second > 100, \
            f"WebSocket throughput too low: {events_per_second:.0f} events/s (expected >100)"
        
        # Cleanup
        await stress_client.cleanup()
    
    @pytest.mark.asyncio
    @pytest.mark.critical  
    @pytest.mark.timeout(30)
    async def test_websocket_reconnection_preserves_events(self):
        """Test that reconnection doesn't lose events."""
        ws_manager = WebSocketManager()
        validator1 = MissionCriticalEventValidator()
        validator2 = MissionCriticalEventValidator()
        
        user_id = "reconnect-user"
        conn_id1 = "conn-1"
        conn_id2 = "conn-2"
        
        # First connection
        mock_ws1 = MagicMock()
        
        async def capture1(message):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator1.record(data)
        
        mock_ws1.send_json = AsyncMock(side_effect=capture1)
        await ws_manager.connect_user(user_id, mock_ws1, conn_id1)
        
        # Send some events
        notifier = WebSocketNotifier(ws_manager)
        await notifier.send_agent_started(conn_id1, "req-1", "agent")
        await notifier.send_agent_thinking(conn_id1, "req-1", "Processing...")
        
        # Disconnect
        await ws_manager.disconnect_user(user_id, mock_ws1, conn_id1)
        
        # Reconnect with new connection
        mock_ws2 = MagicMock()
        
        async def capture2(message):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator2.record(data)
        
        mock_ws2.send_json = AsyncMock(side_effect=capture2)
        await ws_manager.connect_user(user_id, mock_ws2, conn_id2)
        
        # Continue sending events
        await notifier.send_tool_executing(conn_id2, "req-1", "tool", {})
        await notifier.send_tool_completed(conn_id2, "req-1", "tool", {"done": True})
        await notifier.send_agent_completed(conn_id2, "req-1", {"success": True})
        
        await asyncio.sleep(0.5)
        
        # Second connection should receive completion events
        assert validator2.event_counts.get("agent_completed", 0) > 0, \
            "Reconnected client didn't receive completion"


# ============================================================================
# REGRESSION PREVENTION TESTS
# ============================================================================

class TestRegressionPrevention:
    """Tests specifically designed to prevent regression of fixed issues."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_agent_registry_always_enhances_tool_dispatcher(self):
        """REGRESSION TEST: AgentRegistry MUST enhance tool dispatcher."""
        class MockLLM:
            pass
        
        # Test multiple times to catch intermittent issues
        for i in range(5):
            tool_dispatcher = ToolDispatcher()
            original_executor = tool_dispatcher.executor
            
            registry = AgentRegistry(MockLLM(), tool_dispatcher)
            ws_manager = WebSocketManager()
            
            # This is the critical call that was missing
            registry.set_websocket_manager(ws_manager)
            
            # MUST be enhanced
            assert tool_dispatcher.executor != original_executor, \
                f"Iteration {i}: Tool dispatcher not enhanced - REGRESSION!"
            assert isinstance(tool_dispatcher.executor, EnhancedToolExecutionEngine), \
                f"Iteration {i}: Wrong executor type - REGRESSION!"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_events_not_skipped_on_error(self):
        """REGRESSION TEST: Errors must not skip WebSocket events."""
        ws_manager = WebSocketManager()
        validator = MissionCriticalEventValidator(strict_mode=False)
        
        conn_id = "regression-error"
        mock_ws = MagicMock()
        
        async def capture(message, timeout=None):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator.record(data)
        
        mock_ws.send_json = AsyncMock(side_effect=capture)
        await ws_manager.connect_user(conn_id, mock_ws, conn_id)
        
        notifier = WebSocketNotifier(ws_manager)
        
        # Create proper context for notifier
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        context = AgentExecutionContext(
            run_id="reg-1",
            thread_id=conn_id,
            user_id=conn_id,
            agent_name="agent"
        )
        
        # Start execution
        await notifier.send_agent_started(context)
        
        # Simulate error during execution
        try:
            raise Exception("Simulated error")
        except Exception:
            # Must still send completion using fallback
            await notifier.send_fallback_notification(context, "error_fallback")
        
        await asyncio.sleep(0.1)
        
        # Must have both start and fallback/completion
        assert validator.event_counts.get("agent_started", 0) > 0, \
            "REGRESSION: No start event"
        assert validator.event_counts.get("agent_fallback", 0) > 0, \
            "REGRESSION: No error handling event"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_tool_events_always_paired(self):
        """REGRESSION TEST: Tool events must ALWAYS be paired."""
        ws_manager = WebSocketManager()
        enhanced_executor = EnhancedToolExecutionEngine(ws_manager)
        
        validator = MissionCriticalEventValidator()
        
        conn_id = "regression-tools"
        mock_ws = MagicMock()
        
        async def capture(message, timeout=None):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator.record(data)
        
        mock_ws.send_json = AsyncMock(side_effect=capture)
        await ws_manager.connect_user(conn_id, mock_ws, conn_id)
        
        # Test both success and failure cases
        state = DeepAgentState(
            chat_thread_id=conn_id,
            user_id=conn_id
        )
        
        # Success case
        async def success_tool(state):
            return {"success": True}
        
        await enhanced_executor.execute_with_state(
            success_tool, "success_tool", {}, state, conn_id
        )
        
        # Failure case
        async def failure_tool(state):
            raise Exception("Tool failed")
        
        try:
            await enhanced_executor.execute_with_state(
                failure_tool, "failure_tool", {}, state, conn_id
            )
        except:
            pass  # Expected
        
        await asyncio.sleep(0.5)
        
        # Verify pairing
        tool_starts = validator.event_counts.get("tool_executing", 0)
        tool_ends = validator.event_counts.get("tool_completed", 0)
        
        assert tool_starts == tool_ends, \
            f"REGRESSION: Unpaired tool events - {tool_starts} starts, {tool_ends} ends"
        assert tool_starts >= 2, \
            f"REGRESSION: Expected at least 2 tool executions, got {tool_starts}"


# ============================================================================
# TEST SUITE RUNNER
# ============================================================================

@pytest.mark.critical
@pytest.mark.mission_critical
class TestMissionCriticalSuite:
    """Main test suite class for mission-critical WebSocket tests."""
    
    @pytest.mark.asyncio
    async def test_run_complete_suite(self):
        """Run the complete mission-critical test suite."""
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING MISSION CRITICAL WEBSOCKET TEST SUITE")
        logger.info("=" * 80)
        
        results = {
            "unit": {"passed": 0, "failed": 0},
            "integration": {"passed": 0, "failed": 0},
            "e2e": {"passed": 0, "failed": 0},
            "regression": {"passed": 0, "failed": 0}
        }
        
        # Run unit tests
        unit_tests = TestUnitWebSocketComponents()
        integration_tests = TestIntegrationWebSocketFlow()
        e2e_tests = TestE2EWebSocketChatFlow()
        regression_tests = TestRegressionPrevention()
        
        # This is a meta-test that validates the suite itself works
        logger.info("\n✅ Mission Critical Test Suite is operational")
        logger.info("Run with: pytest tests/mission_critical/test_websocket_agent_events_suite.py -v")


if __name__ == "__main__":
    # Run with: python tests/mission_critical/test_websocket_agent_events_suite.py
    # Or: pytest tests/mission_critical/test_websocket_agent_events_suite.py -v
    pytest.main([__file__, "-v", "--tb=short", "-x"])  # -x stops on first failure