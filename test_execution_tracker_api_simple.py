#!/usr/bin/env python3
"""
Simple test script for ExecutionTracker API compatibility (Issue #1131)

This script tests the ExecutionTracker API compatibility layer without pytest complexity.
"""

from netra_backend.app.core.execution_tracker import ExecutionTracker, ExecutionState, get_execution_tracker
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker


def test_execution_tracker_instantiation():
    """Test that ExecutionTracker can be instantiated."""
    print("Testing ExecutionTracker instantiation...")
    tracker = ExecutionTracker()
    assert isinstance(tracker, ExecutionTracker)
    assert isinstance(tracker, AgentExecutionTracker)  # Should inherit from SSOT
    print("✅ PASS: ExecutionTracker instantiation")


def test_register_execution_method():
    """Test that register_execution method exists and works."""
    print("Testing register_execution method...")
    tracker = ExecutionTracker()
    
    result = tracker.register_execution(
        agent_name="test-agent",
        thread_id="test-thread",
        user_id="test-user",
        timeout_seconds=30.0,
        metadata={"test": "value"}
    )
    
    assert result is not None, "register_execution should return an execution ID"
    assert isinstance(result, str), "Execution ID should be a string"
    print(f"✅ PASS: register_execution returned: {result}")


def test_complete_execution_method():
    """Test that complete_execution method exists and works."""
    print("Testing complete_execution method...")
    tracker = ExecutionTracker()
    
    # Create execution first
    exec_id = tracker.register_execution(
        agent_name="test-agent",
        thread_id="test-thread", 
        user_id="test-user"
    )
    
    # Test successful completion
    result = tracker.complete_execution(exec_id, success=True)
    assert result is not None, "complete_execution should return a result"
    print(f"✅ PASS: complete_execution success returned: {result}")
    
    # Test failure completion
    exec_id2 = tracker.register_execution(
        agent_name="test-agent-2",
        thread_id="test-thread",
        user_id="test-user"
    )
    result = tracker.complete_execution(exec_id2, success=False, error="Test error")
    assert result is not None, "complete_execution should return a result"
    print(f"✅ PASS: complete_execution failure returned: {result}")


def test_start_execution_method():
    """Test that start_execution method exists."""
    print("Testing start_execution method...")
    tracker = ExecutionTracker()
    
    exec_id = tracker.register_execution(
        agent_name="test-agent",
        thread_id="test-thread",
        user_id="test-user"
    )
    
    result = tracker.start_execution(exec_id)
    assert result is not None, "start_execution should return a result"
    print(f"✅ PASS: start_execution returned: {result}")


def test_update_execution_state_method():
    """Test that update_execution_state method exists."""
    print("Testing update_execution_state method...")
    tracker = ExecutionTracker()
    
    exec_id = tracker.register_execution(
        agent_name="test-agent", 
        thread_id="test-thread",
        user_id="test-user"
    )
    
    result = tracker.update_execution_state(exec_id, ExecutionState.RUNNING)
    assert result is not None, "update_execution_state should return a result"
    print(f"✅ PASS: update_execution_state returned: {result}")


def test_get_execution_tracker_function():
    """Test that get_execution_tracker function works."""
    print("Testing get_execution_tracker function...")
    tracker = get_execution_tracker()
    assert isinstance(tracker, ExecutionTracker)
    
    # Should be able to use all the expected methods
    exec_id = tracker.register_execution(
        agent_name="function-test-agent",
        thread_id="function-test-thread", 
        user_id="function-test-user"
    )
    assert exec_id is not None
    
    started = tracker.start_execution(exec_id)
    assert started is not None
    
    completed = tracker.complete_execution(exec_id, success=True)
    assert completed is not None
    
    print("✅ PASS: get_execution_tracker function works")


def test_backward_compatibility_properties():
    """Test that backward compatibility properties exist."""
    print("Testing backward compatibility properties...")
    tracker = ExecutionTracker()
    
    # These properties should exist for backward compatibility
    assert hasattr(tracker, 'executions')
    assert hasattr(tracker, 'active_executions')
    assert hasattr(tracker, 'failed_executions')
    assert hasattr(tracker, 'recovery_callbacks')
    
    # Properties should be accessible
    executions = tracker.executions
    active_executions = tracker.active_executions
    failed_executions = tracker.failed_executions
    recovery_callbacks = tracker.recovery_callbacks
    
    assert executions is not None
    assert active_executions is not None
    assert failed_executions is not None
    assert recovery_callbacks is not None
    
    print("✅ PASS: Backward compatibility properties exist")


def test_agent_execution_core_compatibility():
    """Test AgentExecutionCore compatibility with ExecutionTracker API."""
    print("Testing AgentExecutionCore compatibility...")
    
    from unittest.mock import MagicMock
    from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
    
    mock_registry = MagicMock()
    execution_core = AgentExecutionCore(registry=mock_registry)
    
    # Test execution_tracker attribute
    assert hasattr(execution_core, 'execution_tracker')
    assert execution_core.execution_tracker is not None
    
    # Test execution_tracker methods
    tracker = execution_core.execution_tracker
    assert hasattr(tracker, 'register_execution')
    assert callable(tracker.register_execution)
    assert hasattr(tracker, 'start_execution')
    assert callable(tracker.start_execution)
    assert hasattr(tracker, 'complete_execution')
    assert callable(tracker.complete_execution)
    
    # Test agent_tracker attribute
    assert hasattr(execution_core, 'agent_tracker')
    assert execution_core.agent_tracker is not None
    
    # Test agent_tracker methods
    agent_tracker = execution_core.agent_tracker
    assert hasattr(agent_tracker, 'create_execution')
    assert callable(agent_tracker.create_execution)
    assert hasattr(agent_tracker, 'start_execution')
    assert callable(agent_tracker.start_execution)
    assert hasattr(agent_tracker, 'transition_state')
    assert callable(agent_tracker.transition_state)
    
    # Test register_execution compatibility method on AgentExecutionCore
    assert hasattr(execution_core, 'register_execution')
    assert callable(execution_core.register_execution)
    
    # Test delegation works
    exec_id = execution_core.register_execution(
        agent_name="compat-test-agent",
        thread_id="compat-test-thread",
        user_id="compat-test-user"
    )
    assert exec_id is not None
    assert isinstance(exec_id, str)
    
    print("✅ PASS: AgentExecutionCore compatibility")


def run_all_tests():
    """Run all API compatibility tests."""
    print("🧪 Starting ExecutionTracker API compatibility tests (Issue #1131)")
    print("=" * 60)
    
    tests = [
        test_execution_tracker_instantiation,
        test_register_execution_method,
        test_complete_execution_method,
        test_start_execution_method,
        test_update_execution_state_method,
        test_get_execution_tracker_function,
        test_backward_compatibility_properties,
        test_agent_execution_core_compatibility,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ FAIL: {test.__name__}: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"🎯 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ ALL TESTS PASSED - ExecutionTracker API compatibility is working!")
        return True
    else:
        print("❌ SOME TESTS FAILED - ExecutionTracker API needs fixes")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)