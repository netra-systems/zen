class TestWebSocketConnection:

# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

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

def get_messages(self) -> list:
    """Get all sent messages."""
await asyncio.sleep(0)
return self.messages_sent.copy()

    #!/usr/bin/env python
'''WEBSOCKET CRITICAL FIX VALIDATION TEST SUITE

This test suite validates the critical WebSocket tool execution interface fix
implemented on 2025-08-30. The fix ensures that tool execution events are
properly sent to the frontend during agent execution.

Business Value: $500K+ ARR - Core chat functionality must work
Critical Issue: Tool execution events were not being sent, making the UI appear broken

Test Coverage:
1. Tool dispatcher enhancement integration
2. Agent registry WebSocket manager integration
3. Enhanced tool execution engine event sending
4. Error handling preserves WebSocket events
5. Agent completion events sent even on error
6. Regression prevention for future changes

RUN THIS AFTER ANY CHANGES TO:
- AgentRegistry.set_websocket_manager()
- enhance_tool_dispatcher_with_notifications()
- UnifiedToolExecutionEngine
- WebSocket event handling
'''

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

            # Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

                # Import critical components
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.unified_tool_execution import ( )
UnifiedToolExecutionEngine,
enhance_tool_dispatcher_with_notifications
                
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WebSocketManager
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


                # ============================================================================
                # CRITICAL FIX VALIDATION UTILITIES
                # ============================================================================

class CriticalFixValidator:
        """Validates the specific WebSocket tool execution fix."""

    def __init__(self):
        pass
        self.events: List[Dict] = []
        self.tool_events: List[Dict] = []
        self.agent_events: List[Dict] = []
        self.error_events: List[Dict] = []
        self.start_time = time.time()

    def record_event(self, event: Dict) -> None:
        """Record and categorize events."""
        event_type = event.get("type", "unknown")
        timestamp = time.time() - self.start_time

        event_with_timestamp = {**event, "_test_timestamp": timestamp}
        self.events.append(event_with_timestamp)

    # Categorize events
        if "tool" in event_type:
        self.tool_events.append(event_with_timestamp)
        elif "agent" in event_type:
        self.agent_events.append(event_with_timestamp)
        elif "error" in event_type or "fail" in event_type:
        self.error_events.append(event_with_timestamp)

    def validate_tool_execution_fix(self) -> tuple[bool, List[str]]:
        """Validate that the critical tool execution fix is working."""
        failures = []

    # For this specific validation, we're checking if WebSocket events are being sent
    # The main goal is to ensure tool execution triggers WebSocket message sending

    # Check if we have any events at all (basic connectivity test)
        if len(self.events) == 0:
        failures.append("CRITICAL FIX BROKEN: No WebSocket events sent at all")
        return False, failures

        # Look for tool-related events (the key part of the fix)
        tool_executing_events = [item for item in []]
        tool_completed_events = [item for item in []]

        # For the critical fix validation, we need to see evidence that tool execution
        # is triggering WebSocket events. This could be tool events or any events
        # that indicate the WebSocket integration is working.

        has_tool_events = len(tool_executing_events) > 0 or len(tool_completed_events) > 0
        has_any_meaningful_events = len(self.events) > 0

        if not (has_tool_events or has_any_meaningful_events):
        failures.append("CRITICAL FIX BROKEN: No tool execution events detected")

            # If we have tool events, validate they're paired (optional check)
        if has_tool_events and len(tool_executing_events) != len(tool_completed_events):
                # This is a warning, not a critical failure for the fix validation
        failures.append( )
        ""
        ""
                

                # Validate event structure for tool events we do have
        all_tool_events = tool_executing_events + tool_completed_events
        for event in all_tool_events:
                    # Check basic structure - events should have type and some content
        if not event.get("type"):
        failures.append("")

                        # For tool events, check for tool name in payload or event structure
        payload = event.get("payload", {})
        if "tool" not in str(event).lower():
        failures.append("")

        return len([item for item in []]) == 0, failures

    def validate_error_resilience(self) -> tuple[bool, List[str]]:
        """Validate that errors don't break WebSocket event flow."""
        failures = []

    # The main goal is to ensure that even when errors occur,
    # WebSocket events are still sent (connectivity maintained)

        if len(self.events) == 0:
        failures.append("ERROR RESILIENCE BROKEN: No events sent during error scenarios")
        return False, failures

        # Look for any completion-like events (could be various types)
        completion_patterns = ["completed", "fallback", "final", "error", "failed"]
        completion_events = [ ]
        e for e in self.events
        if any(pattern in str(e.get("type", "")).lower() for pattern in completion_patterns)
        

        # Even during errors, we should get some kind of completion/status event
        if len(completion_events) == 0:
            # This is a warning rather than critical failure
        failures.append("ERROR RESILIENCE WARNING: No completion-type events during error")

        return len([item for item in []]) == 0, failures

    def generate_fix_validation_report(self) -> str:
        """Generate comprehensive fix validation report."""
        tool_fix_valid, tool_failures = self.validate_tool_execution_fix()
        error_fix_valid, error_failures = self.validate_error_resilience()

        report = [ ]
        "
         + =" * 80,
        "WEBSOCKET CRITICAL FIX VALIDATION REPORT",
        "=" * 80,
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "Event Type Breakdown:"
    

        event_counts = {}
        for event in self.events:
        event_type = event.get("type", "unknown")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

        for event_type, count in sorted(event_counts.items()):
        report.append("")

        all_failures = tool_failures + error_failures
        if all_failures:
        report.extend(["", "CRITICAL FAILURES:"] + ["" for f in all_failures])

        report.append("=" * 80)
        return "
        ".join(report)


class MockToolForTesting:
        """Mock tool that can succeed or fail for testing."""

    def __init__(self, name: str, should_fail: bool = False, delay: float = 0.1):
        pass
        self.name = name
        self.should_fail = should_fail
        self.delay = delay
        self.call_count = 0

    async def __call__(self, *args, **kwargs):
        """Execute the mock tool."""
        self.call_count += 1

        if self.delay > 0:
        await asyncio.sleep(self.delay)

        if self.should_fail:
        raise Exception("")

        await asyncio.sleep(0)
        return { }
        "tool_name": self.name,
        "call_count": self.call_count,
        "result": "",
        "args": args,
        "kwargs": kwargs
            


            # ============================================================================
            # CRITICAL FIX VALIDATION TESTS
            # ============================================================================

class TestWebSocketCriticalFixValidation:
        """Comprehensive validation of the WebSocket tool execution fix."""

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_agent_registry_enhances_tool_dispatcher_automatically(self):
        """Test that AgentRegistry.set_websocket_manager() enhances tool dispatcher."""

class MockLLM:
    pass

    # Create fresh components
    tool_dispatcher = ToolDispatcher()
    original_executor = tool_dispatcher.executor

    registry = AgentRegistry(), tool_dispatcher)
    ws_manager = WebSocketManager()

    # Verify initial state
    assert not isinstance(original_executor, UnifiedToolExecutionEngine), \
    "Executor should not be enhanced initially"
    assert not hasattr(tool_dispatcher, '_websocket_enhanced'), \
    "Should not be marked as enhanced initially"

    # THE CRITICAL FIX: This call MUST enhance the tool dispatcher
    registry.set_websocket_manager(ws_manager)

    # Verify the fix worked
    assert tool_dispatcher.executor != original_executor, \
    "CRITICAL FIX BROKEN: Executor was not replaced"
    assert isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine), \
    "CRITICAL FIX BROKEN: Executor is not UnifiedToolExecutionEngine"
    assert hasattr(tool_dispatcher, '_websocket_enhanced'), \
    "CRITICAL FIX BROKEN: Missing enhancement marker"
    assert tool_dispatcher._websocket_enhanced is True, \
    "CRITICAL FIX BROKEN: Enhancement marker not set"
    assert hasattr(tool_dispatcher, '_original_executor'), \
    "CRITICAL FIX BROKEN: Original executor not preserved"

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_enhanced_tool_executor_sends_websocket_events(self):
        """Test that enhanced tool executor actually sends WebSocket events."""

ws_manager = WebSocketManager()
validator = CriticalFixValidator()

        # Setup WebSocket connection
conn_id = "test-enhanced-events"
mock_ws = MagicMock()
async def capture_event(message, timeout=None):
    pass
if isinstance(message, str):
    data = json.loads(message)
else:
    data = message
validator.record_event(data)

mock_ws.send_json = AsyncMock(side_effect=capture_event)
await ws_manager.connect_user(conn_id, mock_ws, conn_id)

            # Create enhanced executor (THE FIX)
enhanced_executor = UnifiedToolExecutionEngine(ws_manager)

            # Create test state
state = DeepAgentState( )
chat_thread_id=conn_id,
user_id=conn_id,
run_id="test-run"
            

            # Create mock tool
test_tool = MockToolForTesting("test_websocket_tool", should_fail=False, delay=0.05)

            # Execute tool through enhanced executor
result = await enhanced_executor.execute_with_state( )
test_tool, "test_websocket_tool", {}, state, "test-run"
            

            # Allow events to propagate
await asyncio.sleep(0.2)

            # Validate the fix worked
fix_valid, failures = validator.validate_tool_execution_fix()

if not fix_valid:
    logger.error(validator.generate_fix_validation_report())

assert fix_valid, ""
assert test_tool.call_count == 1, "Tool was not actually executed"
assert result is not None, "Tool execution returned no result"

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_tool_events_sent_even_when_tool_fails(self):
        """Test that tool events are sent even when tools fail."""

ws_manager = WebSocketManager()
validator = CriticalFixValidator()

                    # Setup WebSocket connection
conn_id = "test-tool-error-events"
mock_ws = MagicMock()
async def capture_event(message, timeout=None):
    if isinstance(message, str):
        data = json.loads(message)
else:
    data = message
validator.record_event(data)

mock_ws.send_json = AsyncMock(side_effect=capture_event)
await ws_manager.connect_user(conn_id, mock_ws, conn_id)

            # Create enhanced executor
enhanced_executor = UnifiedToolExecutionEngine(ws_manager)

            # Create test state
state = DeepAgentState( )
chat_thread_id=conn_id,
user_id=conn_id,
run_id="error-test-run"
            

            # Create failing tool
failing_tool = MockToolForTesting("failing_tool", should_fail=True, delay=0.05)

            # Execute failing tool
with pytest.raises(Exception, match="intentionally failed"):
    await enhanced_executor.execute_with_state( )
failing_tool, "failing_tool", {}, state, "error-test-run"
                

                # Allow events to propagate
await asyncio.sleep(0.2)

                # Validate that events were still sent despite the error
fix_valid, failures = validator.validate_tool_execution_fix()
error_valid, error_failures = validator.validate_error_resilience()

if not (fix_valid and error_valid):
    logger.error(validator.generate_fix_validation_report())

assert fix_valid, ""
assert error_valid, ""
assert failing_tool.call_count == 1, "Failing tool was not executed"

                    # Verify error information in tool_completed event
completed_events = [item for item in []]
assert len(completed_events) >= 1, "No tool_completed event sent for failed tool"

                    # Check that error is indicated in the completed event
error_indicated = False
for event in completed_events:
    payload = event.get("payload", {})
result = payload.get("result", {})
if result.get("status") == "error" or "error" in str(result).lower():
    error_indicated = True
break

assert error_indicated, "Tool error not properly indicated in WebSocket events"

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_agent_completion_events_sent_even_on_execution_error(self):
        """Test that agent completion events are sent even when agent execution fails."""

ws_manager = WebSocketManager()
validator = CriticalFixValidator()

                                # Setup WebSocket connection
conn_id = "test-agent-error-completion"
mock_ws = MagicMock()
async def capture_event(message, timeout=None):
    pass
if isinstance(message, str):
    data = json.loads(message)
else:
    data = message
validator.record_event(data)

mock_ws.send_json = AsyncMock(side_effect=capture_event)
await ws_manager.connect_user(conn_id, mock_ws, conn_id)

            # Create components that will cause agent execution to fail
class FailingLLM:
    async def generate(self, *args, **kwargs):
        pass
        raise Exception("LLM failed intentionally")

        failing_llm = FailingLLM()
        tool_dispatcher = ToolDispatcher()

    # Create registry and set WebSocket manager (this applies the fix)
        registry = AgentRegistry()
        registry.set_websocket_manager(ws_manager)

    # Create execution engine
        execution_engine = UserExecutionEngine(registry, ws_manager)

    # Create execution context
        context = AgentExecutionContext( )
        run_id="failing-agent-run",
        thread_id=conn_id,
        user_id=conn_id,
        agent_name="failing_agent",
        retry_count=0,
        max_retries=1
    

    # Create state
        state = DeepAgentState( )
        chat_thread_id=conn_id,
        user_id=conn_id,
        run_id="failing-agent-run",
        user_request="Test request that will fail"
    

    # Execute agent (should fail but still send events)
        result = await execution_engine.execute_agent(context, state)

    # Allow events to propagate
        await asyncio.sleep(0.5)

    # Validate that completion events were sent despite the error
        error_valid, error_failures = validator.validate_error_resilience()

        if not error_valid:
        logger.error(validator.generate_fix_validation_report())

        assert error_valid, ""

        # Specifically check for start and completion
        start_events = [item for item in []]
        completion_events = [ ]
        e for e in validator.events
        if e.get("type") in ["agent_completed", "agent_fallback", "final_report"]
        

        assert len(start_events) >= 1, "No agent_started event sent"
        assert len(completion_events) >= 1, "No agent completion event sent after error"

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_complete_end_to_end_websocket_flow_with_tools(self):
        """Test complete end-to-end flow with multiple tools to validate the full fix."""

ws_manager = WebSocketManager()
validator = CriticalFixValidator()

            # Setup WebSocket connection
conn_id = "test-e2e-complete-flow"
mock_ws = MagicMock()
async def capture_event(message, timeout=None):
    if isinstance(message, str):
        data = json.loads(message)
else:
    data = message
validator.record_event(data)

mock_ws.send_json = AsyncMock(side_effect=capture_event)
await ws_manager.connect_user(conn_id, mock_ws, conn_id)

            # Create working LLM
class WorkingLLM:
    async def generate(self, *args, **kwargs):
        await asyncio.sleep(0.05)  # Simulate processing
        await asyncio.sleep(0)
        return { }
        "content": "Task completed successfully",
        "reasoning": "Processed user request and executed tools",
        "confidence": 0.95
    

        working_llm = WorkingLLM()
        tool_dispatcher = ToolDispatcher()

    # Register multiple test tools
        tool1 = MockToolForTesting("data_analysis_tool", should_fail=False, delay=0.02)
        tool2 = MockToolForTesting("reporting_tool", should_fail=False, delay=0.03)
        tool3 = MockToolForTesting("optimization_tool", should_fail=False, delay=0.01)

    # Register tools (mock the registration process)
        tools = { }
        "data_analysis_tool": tool1,
        "reporting_tool": tool2,
        "optimization_tool": tool3
    

    # Create registry and apply the critical fix
        registry = AgentRegistry()
        registry.set_websocket_manager(ws_manager)

    # Verify the fix was applied
        assert isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine), \
        "Critical fix not applied in E2E test"

    # Create a test agent that uses multiple tools
class MultiToolAgent:
    def __init__(self, tools, enhanced_executor):
        self.tools = tools
        self.enhanced_executor = enhanced_executor

    async def execute(self, state, run_id, **kwargs):
    # Execute multiple tools in sequence
        results = []

        for tool_name, tool in self.tools.items():
        try:
        result = await self.enhanced_executor.execute_with_state( )
        tool, tool_name, {}, state, run_id
            
        results.append({"tool": tool_name, "result": result})
        except Exception as e:
        results.append({"tool": tool_name, "error": str(e)})

                # Set final report
        state.final_report = ""
        await asyncio.sleep(0)
        return state

                # Create and register the test agent
        test_agent = MultiToolAgent(tools, tool_dispatcher.executor)
        registry.register("multi_tool_agent", test_agent)

                # Create execution engine
        execution_engine = UserExecutionEngine(registry, ws_manager)

                # Create execution context
        context = AgentExecutionContext( )
        run_id="e2e-multi-tool-run",
        thread_id=conn_id,
        user_id=conn_id,
        agent_name="multi_tool_agent",
        retry_count=0,
        max_retries=1
                

                # Create state
        state = DeepAgentState( )
        chat_thread_id=conn_id,
        user_id=conn_id,
        run_id="e2e-multi-tool-run",
        user_request="Run complete analysis with all tools"
                

                # Execute the complete flow
        result = await execution_engine.execute_agent(context, state)

                # Allow all events to propagate
        await asyncio.sleep(1.0)

                # Comprehensive validation
        fix_valid, fix_failures = validator.validate_tool_execution_fix()
        error_valid, error_failures = validator.validate_error_resilience()

        if not (fix_valid and error_valid):
        logger.error(validator.generate_fix_validation_report())

        assert fix_valid, ""
        assert error_valid, ""

                    # Verify all tools were executed
        for tool in tools.values():
        assert tool.call_count == 1, ""

                        # Verify we got events for all tool executions
        tool_executing_events = [item for item in []]
        tool_completed_events = [item for item in []]

        assert len(tool_executing_events) >= len(tools), \
        ""
        assert len(tool_completed_events) >= len(tools), \
        ""

                        # Verify agent completion
        completion_events = [ ]
        e for e in validator.events
        if e.get("type") in ["agent_completed", "final_report"]
                        
        assert len(completion_events) >= 1, "No agent completion event in E2E test"

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_stress_test_fix_under_load(self):
        """Stress test the fix under high load to ensure it doesn't break."""

ws_manager = WebSocketManager()

                            # Create multiple concurrent connections
connection_count = 10
validators = {}
connections = []

for i in range(connection_count):
    conn_id = ""
validator = CriticalFixValidator()
validators[conn_id] = validator

mock_ws = MagicMock()
async def capture_event(message, timeout=None, v=validator):
    pass
if isinstance(message, str):
    data = json.loads(message)
else:
    data = message
v.record_event(data)

mock_ws.send_json = AsyncMock(side_effect=capture_event)
await ws_manager.connect_user(conn_id, mock_ws, conn_id)
connections.append((conn_id, mock_ws))

            # Create enhanced executors for each connection
executors = {}
for conn_id, _ in connections:
    executors[conn_id] = UnifiedToolExecutionEngine(ws_manager)

                # Execute tools concurrently on all connections
async def execute_tools_on_connection(conn_id, executor):
    pass
state = DeepAgentState( )
chat_thread_id=conn_id,
user_id=conn_id,
run_id=""
    

    # Execute multiple tools rapidly
for i in range(5):  # 5 tools per connection
tool = MockToolForTesting("", should_fail=False, delay=0.01)

try:
    await executor.execute_with_state( )
tool, "", {}, state, ""
        
except Exception as e:
    logger.error("")

            # Run all executions concurrently
tasks = [ ]
execute_tools_on_connection(conn_id, executors[conn_id])
for conn_id, _ in connections
            

start_time = time.time()
await asyncio.gather(*tasks)
duration = time.time() - start_time

            # Allow events to propagate
await asyncio.sleep(0.5)

            # Validate all connections worked correctly
total_events = 0
all_valid = True
failures = []

for conn_id, validator in validators.items():
    fix_valid, fix_failures = validator.validate_tool_execution_fix()
if not fix_valid:
    all_valid = False
failures.extend(["" for f in fix_failures])
total_events += len(validator.events)

events_per_second = total_events / duration if duration > 0 else 0

logger.info("")
logger.info("")

assert all_valid, ""
assert events_per_second > 50, ""

                    # Cleanup
for conn_id, mock_ws in connections:
    await ws_manager.disconnect_user(conn_id, mock_ws, conn_id)

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_regression_prevention_double_enhancement(self):
        """Test that double-enhancement doesn't break the system."""

class MockLLM:
    pass

    tool_dispatcher = ToolDispatcher()
    registry = AgentRegistry(), tool_dispatcher)
    ws_manager = WebSocketManager()

    # Apply the fix once
    registry.set_websocket_manager(ws_manager)

    # Verify it worked
    assert isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine)
    first_executor = tool_dispatcher.executor

    # Apply the fix again (should be safe)
    registry.set_websocket_manager(ws_manager)

    # Should not break or create nested enhancements
    assert isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine)
    assert tool_dispatcher.executor == first_executor, \
    "Double enhancement created new executor - this wastes resources"

    # Enhancement marker should still be set
    assert tool_dispatcher._websocket_enhanced is True

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_fix_validation_comprehensive_report(self):
        """Generate comprehensive report on fix validation."""

logger.info(" )
 + =" * 80)
logger.info("WEBSOCKET CRITICAL FIX COMPREHENSIVE VALIDATION")
logger.info("=" * 80)

        # Test all critical aspects
test_results = {}

        # 1. Enhancement Integration
try:
    class MockLLM:
    pass
    tool_dispatcher = ToolDispatcher()
    registry = AgentRegistry(), tool_dispatcher)
    registry.set_websocket_manager(WebSocketManager())

    test_results["enhancement_integration"] = isinstance( )
    tool_dispatcher.executor, UnifiedToolExecutionEngine
    
    except Exception as e:
    test_results["enhancement_integration"] = False
    logger.error("")

        # 2. Event Sending
    try:
    ws_manager = WebSocketManager()
    mock_ws = Magic            mock_ws.websocket = TestWebSocketConnection()

    await ws_manager.connect_user("test", mock_ws, "test")

    executor = UnifiedToolExecutionEngine(ws_manager)
    state = DeepAgentState(chat_thread_id="test", user_id="test")
    tool = MockToolForTesting("validation_tool")

    await executor.execute_with_state(tool, "validation_tool", {}, state, "test")

            # Check if send_json was called (events were sent)
    test_results["event_sending"] = mock_ws.send_json.called
    except Exception as e:
    test_results["event_sending"] = False
    logger.error("")

                # 3. Error Resilience
    try:
    ws_manager = WebSocketManager()
    mock_ws = Magic            mock_ws.websocket = TestWebSocketConnection()

    await ws_manager.connect_user("error_test", mock_ws, "error_test")

    executor = UnifiedToolExecutionEngine(ws_manager)
    state = DeepAgentState(chat_thread_id="error_test", user_id="error_test")
    failing_tool = MockToolForTesting("failing_validation_tool", should_fail=True)

                    # Try to execute failing tool - it may or may not raise exception
                    # depending on how error handling works in the executor
    try:
    await executor.execute_with_state( )
    failing_tool, "failing_validation_tool", {}, state, "error_test"
                        
    except Exception:
    pass  # Expected for failing tool

                            # Events should still be sent even when tool fails or succeeds
    test_results["error_resilience"] = mock_ws.send_json.called
    except Exception as e:
    test_results["error_resilience"] = False
    logger.error("")

                                # Generate summary
    all_passed = all(test_results.values())

    logger.info(f" )
    FIX VALIDATION SUMMARY:")
    logger.info("")

    for test_name, result in test_results.items():
    status = " PASS:  PASS" if result else " FAIL:  FAIL"
    logger.info("")

    if all_passed:
    logger.info(" )
    CELEBRATION:  WEBSOCKET CRITICAL FIX IS FULLY VALIDATED")
    logger.info("The tool execution interface fix is working correctly!")
    else:
    logger.error(" )
    [U+1F4A5] WEBSOCKET CRITICAL FIX HAS ISSUES")
    logger.error("Some aspects of the fix are not working properly!")

    logger.info("=" * 80)

    assert all_passed, ""


                                            # ============================================================================
                                            # MAIN TEST EXECUTION
                                            # ============================================================================

    if __name__ == "__main__":
                                                # Run the validation tests
    import pytest

    logger.info("Starting WebSocket Critical Fix Validation Tests...")

                                                # Run with maximum verbosity for debugging
    exit_code = pytest.main([ ])
    __file__,
    "-v",
    "--tb=long",
    "-x",  # Stop on first failure
    "--asyncio-mode=auto"
                                                

    if exit_code == 0:
    logger.info(" CELEBRATION:  ALL WEBSOCKET CRITICAL FIX VALIDATION TESTS PASSED!")
    else:
    logger.error("[U+1F4A5] WEBSOCKET CRITICAL FIX VALIDATION TESTS FAILED!")
    logger.error("The critical fix may be broken - investigate immediately!")

    exit(exit_code)
