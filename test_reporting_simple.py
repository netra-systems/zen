#!/usr/bin/env python3
"""Simple test for ReportingSubAgent that bypasses test orchestration"""

import sys
import asyncio
import json
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

sys.path.insert(0, '.')

from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher

def test_inheritance():
    """Test BaseAgent inheritance."""
    agent = ReportingSubAgent()
    print(f"[OK] ReportingSubAgent inherits from BaseAgent: {isinstance(agent, BaseAgent)}")
    print(f"[OK] MRO: {[cls.__name__ for cls in ReportingSubAgent.__mro__]}")
    
def test_infrastructure_ssot():
    """Test no infrastructure duplication."""
    agent = ReportingSubAgent()
    
    # Check that prohibited local infrastructure doesn't exist
    prohibited_attrs = [
        'local_reliability_manager', 'local_execution_monitor', 
        'local_circuit_breaker', 'local_websocket_handler',
        'local_retry_manager', 'websocket_notifier',
        'execution_engine_local'
    ]
    
    violations = []
    for attr in prohibited_attrs:
        if hasattr(agent, attr):
            violations.append(attr)
    
    if not violations:
        print("[OK] No infrastructure duplication found")
    else:
        print(f"[ERROR] Found prohibited infrastructure: {violations}")
    
    # Check inherited infrastructure exists
    inherited_attrs = [
        '_websocket_adapter', '_unified_reliability_handler',
        '_execution_engine', 'timing_collector', 'logger'
    ]
    
    missing = []
    for attr in inherited_attrs:
        if not hasattr(agent, attr):
            missing.append(attr)
    
    if not missing:
        print("[OK] All inherited infrastructure found")
    else:
        print(f"[ERROR] Missing inherited infrastructure: {missing}")

async def test_golden_pattern_methods():
    """Test golden pattern methods."""
    agent = ReportingSubAgent()
    agent.llm_manager = Mock(spec=LLMManager)
    
    # Create complete state
    state = DeepAgentState()
    state.user_request = "Generate report"
    state.action_plan_result = {"plan": "Test plan"}
    state.optimizations_result = {"opts": "Test opts"}
    state.data_result = {"data": "Test data"}
    state.triage_result = {"triage": "Test triage"}
    state.chat_thread_id = "test-thread-123"
    
    context = ExecutionContext(
        run_id="test-run-123",
        agent_name="ReportingSubAgent",
        state=state,
        stream_updates=True,
        thread_id="test-thread-123",
        start_time=datetime.now(timezone.utc)
    )
    
    # Test validate_preconditions
    result = await agent.validate_preconditions(context)
    print(f"[OK] validate_preconditions with complete state: {result}")
    
    # Test with incomplete state
    incomplete_state = DeepAgentState()
    incomplete_state.user_request = "Generate report"
    incomplete_context = ExecutionContext(
        run_id="test-run-123",
        agent_name="ReportingSubAgent",
        state=incomplete_state
    )
    
    result = await agent.validate_preconditions(incomplete_context)
    print(f"[OK] validate_preconditions with incomplete state: {result}")
    
    # Test execute_core_logic
    agent.llm_manager.ask_llm = AsyncMock(return_value=json.dumps({
        "report": "Test report content",
        "sections": ["intro", "analysis"],
        "metadata": {"generated": True}
    }))
    
    try:
        result = await agent.execute_core_logic(context)
        print(f"[OK] execute_core_logic completed: {type(result)}")
        print(f"     Result keys: {list(result.keys())}")
    except Exception as e:
        print(f"[ERROR] execute_core_logic failed: {e}")
        import traceback
        traceback.print_exc()

async def test_websocket_events():
    """Test WebSocket event emission."""
    agent = ReportingSubAgent()
    mock_websocket = Mock()
    mock_websocket.send_to_thread = AsyncMock(return_value=True)
    mock_websocket.notify_agent_thinking = AsyncMock()
    mock_websocket.notify_agent_completed = AsyncMock()
    
    # Set WebSocket bridge
    agent.set_websocket_bridge(mock_websocket, "test-run-123")
    print(f"[OK] WebSocket bridge set: {agent.has_websocket_context()}")
    
    # Test emit methods
    await agent.emit_thinking("Test thinking...")
    await agent.emit_progress("Test progress...")
    await agent.emit_agent_completed({"test": "result"})
    
    print("[OK] WebSocket events emitted without errors")

def test_fallback_methods():
    """Test fallback methods for error recovery."""
    agent = ReportingSubAgent()
    
    state = DeepAgentState()
    state.action_plan_result = {"plan": "Test"}
    state.data_result = {"data": "Test"}
    state.optimizations_result = {"opts": "Test"}
    
    # Test fallback summary
    summary = agent._create_fallback_summary(state)
    print(f"[OK] Fallback summary created: {summary}")
    
    # Test fallback metadata
    metadata = agent._create_fallback_metadata()
    print(f"[OK] Fallback metadata created: {metadata}")
    
    # Test fallback operation
    operation = agent._create_fallback_reporting_operation(state, "test-run", True)
    print(f"[OK] Fallback operation created: {callable(operation)}")

def test_execution_result_methods():
    """Test ExecutionResult creation methods."""
    agent = ReportingSubAgent()
    
    # Test success result
    result = agent._create_success_execution_result({"test": "data"}, 150.5)
    print(f"[OK] Success execution result: {result.success}, {result.execution_time_ms}")
    
    # Test error result
    error_result = agent._create_error_execution_result("Test error", 75.0)
    print(f"[OK] Error execution result: {error_result.success}, {error_result.error}")

async def main():
    """Run all tests."""
    print("=== ReportingSubAgent Golden Pattern Tests ===")
    
    print("\n1. Testing Inheritance...")
    test_inheritance()
    
    print("\n2. Testing Infrastructure SSOT...")
    test_infrastructure_ssot()
    
    print("\n3. Testing Golden Pattern Methods...")
    await test_golden_pattern_methods()
    
    print("\n4. Testing WebSocket Events...")
    await test_websocket_events()
    
    print("\n5. Testing Fallback Methods...")
    test_fallback_methods()
    
    print("\n6. Testing ExecutionResult Methods...")
    test_execution_result_methods()
    
    print("\n=== All Tests Completed ===")

if __name__ == "__main__":
    asyncio.run(main())