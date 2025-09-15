#!/usr/bin/env python3
"""
Mock Configuration Validation Test for Issue #1131

This script identifies and validates proper mock object configurations for agent execution tests.
"""

import asyncio
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult, AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext


async def test_mock_agent_execute_method_configuration():
    """Test that mock agents must have properly configured execute method."""
    print("Testing mock agent execute method configuration...")
    
    # PROBLEM: The original test uses MagicMock for agents that need async methods
    problematic_agent = MagicMock()
    problematic_agent.execute = MagicMock(return_value=AgentExecutionResult(success=True, agent_name="test"))
    
    # This will fail with "object MagicMock can't be used in 'await' expression"
    try:
        result = await problematic_agent.execute("user_context", "run_id", True)
        print("❌ UNEXPECTED: MagicMock execute should have failed")
        return False
    except TypeError as e:
        if "MagicMock can't be used in 'await' expression" in str(e):
            print(f"✅ CONFIRMED: MagicMock fails with await: {e}")
        else:
            print(f"❌ UNEXPECTED ERROR: {e}")
            return False
    
    # SOLUTION: Use AsyncMock for agent.execute method
    correct_agent = MagicMock()
    correct_agent.execute = AsyncMock(return_value=AgentExecutionResult(success=True, agent_name="test"))
    
    # This should work
    try:
        result = await correct_agent.execute("user_context", "run_id", True)
        print(f"✅ PASS: AsyncMock execute works: {result.success}")
        return True
    except Exception as e:
        print(f"❌ FAIL: AsyncMock execute failed: {e}")
        return False


async def test_mock_agent_run_method_compatibility():
    """Test that mock agents also need async run method for compatibility."""
    print("Testing mock agent run method compatibility...")
    
    # Some agent implementations might use run() instead of execute()
    agent = MagicMock()
    agent.run = AsyncMock(return_value={"success": True, "message": "Agent ran successfully"})
    
    try:
        result = await agent.run("user_context", "run_id", True)
        print(f"✅ PASS: AsyncMock run works: {result}")
        return True
    except Exception as e:
        print(f"❌ FAIL: AsyncMock run failed: {e}")
        return False


async def test_mock_registry_configuration():
    """Test mock registry configuration for proper agent retrieval."""
    print("Testing mock registry configuration...")
    
    # Mock agent with proper async methods
    mock_agent = MagicMock()
    mock_agent.execute = AsyncMock(return_value=AgentExecutionResult(success=True, agent_name="test"))
    mock_agent.set_trace_context = MagicMock()
    mock_agent.set_websocket_bridge = MagicMock()
    mock_agent.execution_engine = MagicMock()
    mock_agent.execution_engine.set_websocket_bridge = MagicMock()
    
    # Mock registry
    mock_registry = MagicMock()
    mock_registry.get_agent.return_value = mock_agent
    mock_registry.get_async = AsyncMock(return_value=mock_agent)
    
    # Test sync get_agent
    agent = mock_registry.get_agent("test-agent")
    assert agent == mock_agent
    print("✅ PASS: Registry get_agent works")
    
    # Test async get_async  
    agent_async = await mock_registry.get_async("test-agent")
    assert agent_async == mock_agent
    print("✅ PASS: Registry get_async works")
    
    # Test agent execute
    result = await agent.execute("user_context", "run_id", True)
    assert result.success
    print("✅ PASS: Agent execute from registry works")
    
    return True


async def test_websocket_bridge_configuration():
    """Test WebSocket bridge mock configuration."""
    print("Testing WebSocket bridge configuration...")
    
    # Mock WebSocket bridge with all required async methods
    mock_websocket_bridge = AsyncMock()
    mock_websocket_bridge.notify_agent_started = AsyncMock()
    mock_websocket_bridge.notify_agent_thinking = AsyncMock()
    mock_websocket_bridge.notify_agent_completed = AsyncMock()
    mock_websocket_bridge.notify_agent_error = AsyncMock()
    
    # Test each method
    await mock_websocket_bridge.notify_agent_started(
        run_id="test-run", 
        agent_name="test-agent", 
        context={"status": "starting"}
    )
    mock_websocket_bridge.notify_agent_started.assert_called_once()
    print("✅ PASS: WebSocket notify_agent_started works")
    
    await mock_websocket_bridge.notify_agent_thinking(
        run_id="test-run",
        agent_name="test-agent", 
        reasoning="Testing...",
        step_number=1
    )
    mock_websocket_bridge.notify_agent_thinking.assert_called_once()
    print("✅ PASS: WebSocket notify_agent_thinking works")
    
    return True


async def test_proper_agent_execution_core_mock_setup():
    """Test complete proper mock setup for AgentExecutionCore testing."""
    print("Testing complete proper mock setup...")
    
    from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
    
    # Create properly configured mocks
    mock_registry = MagicMock()
    mock_websocket_bridge = AsyncMock()
    mock_agent = MagicMock()
    
    # CRITICAL: Agent must have AsyncMock execute method
    expected_result = AgentExecutionResult(
        success=True,
        agent_name="test-agent",
        duration=2.5,
        data={"message": "Agent provided valuable insights"}
    )
    mock_agent.execute = AsyncMock(return_value=expected_result)
    mock_agent.set_trace_context = MagicMock()
    mock_agent.set_websocket_bridge = MagicMock()
    mock_agent.execution_engine = MagicMock()
    mock_agent.execution_engine.set_websocket_bridge = MagicMock()
    
    # Mock registry methods
    mock_registry.get_agent.return_value = mock_agent
    mock_registry.get_async = AsyncMock(return_value=mock_agent)
    
    # Mock WebSocket bridge methods
    mock_websocket_bridge.notify_agent_started = AsyncMock()
    mock_websocket_bridge.notify_agent_thinking = AsyncMock()
    mock_websocket_bridge.notify_agent_completed = AsyncMock()
    
    # Create execution core with proper mocks
    execution_core = AgentExecutionCore(
        registry=mock_registry, 
        websocket_bridge=mock_websocket_bridge
    )
    
    # Test execution context and user context
    execution_context = AgentExecutionContext(
        agent_name="test-agent",
        run_id=str(uuid4()),
        thread_id="test-thread", 
        user_id="test-user",
        correlation_id="test-correlation"
    )
    
    user_context = UserExecutionContext.from_request(
        user_id="test-user",
        thread_id="test-thread",
        run_id=str(uuid4())
    )
    
    # Execute agent - this should now work with proper mocks
    try:
        with_patches = [
            ('execution_core.execution_tracker.create_execution', lambda *a, **k: 'exec-123'),
            ('execution_core.execution_tracker.start_execution', lambda *a, **k: True), 
            ('execution_core.agent_tracker.create_execution', lambda *a, **k: 'state-exec-123'),
            ('execution_core.agent_tracker.start_execution', lambda *a, **k: True),
            ('execution_core.agent_tracker.transition_state', AsyncMock()),
            ('execution_core.agent_tracker.update_execution_state', lambda *a, **k: True),
            ('execution_core.execution_tracker.update_execution_state', lambda *a, **k: True),
        ]
        
        # Apply patches
        import unittest.mock
        patches = []
        for attr_path, mock_value in with_patches:
            parts = attr_path.split('.')
            obj = execution_core
            for part in parts[:-1]:
                obj = getattr(obj, part)
            patches.append(unittest.mock.patch.object(obj, parts[-1], mock_value))
        
        # Start all patches
        for patch in patches:
            patch.start()
            
        try:
            result = await execution_core.execute_agent(
                context=execution_context,
                user_context=user_context,
                timeout=30.0
            )
            
            print(f"✅ PASS: Agent execution succeeded: {result.success}")
            print(f"     Agent: {result.agent_name}")
            print(f"     Duration: {result.duration}")
            
            # Verify WebSocket calls were made
            mock_websocket_bridge.notify_agent_started.assert_called()
            print("✅ PASS: WebSocket started notification called")
            
            return True
            
        finally:
            # Stop all patches
            for patch in patches:
                patch.stop()
                
    except Exception as e:
        print(f"❌ FAIL: Agent execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all mock configuration validation tests."""
    print("🧪 Starting Mock Configuration Validation Tests (Issue #1131)")
    print("=" * 60)
    
    tests = [
        test_mock_agent_execute_method_configuration,
        test_mock_agent_run_method_compatibility,
        test_mock_registry_configuration,
        test_websocket_bridge_configuration,
        test_proper_agent_execution_core_mock_setup,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ FAIL: {test.__name__}: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"🎯 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ ALL TESTS PASSED - Mock configurations are working!")
        return True
    else:
        print("❌ SOME TESTS FAILED - Mock configurations need fixes")
        return False


if __name__ == '__main__':
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)