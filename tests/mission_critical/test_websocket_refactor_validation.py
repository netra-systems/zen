"""
Simple validation test for WebSocket refactoring.
Verifies dead code removal and fixes are working correctly.
"""

import asyncio
from unittest.mock import Mock
from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
# Note: triage_sub_agent is a file, not a module directory
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from netra_backend.app.agents.triage.unified_triage_agent import TriageSubAgent
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


def test_dead_methods_removed():
    """Verify dead methods have been removed from all agents."""
    # Create mocks for required parameters
    llm_manager = Mock()
    tool_dispatcher = Mock()
    
    # Test ValidationSubAgent
    val_agent = ValidationSubAgent(llm_manager, tool_dispatcher)
    assert not hasattr(val_agent, '_setup_websocket_context_if_available'), \
        "ValidationSubAgent still has dead method _setup_websocket_context_if_available"
    assert not hasattr(val_agent, '_setup_websocket_context_for_legacy'), \
        "ValidationSubAgent still has dead method _setup_websocket_context_for_legacy"
    
    # Test DataSubAgent  
    data_agent = DataSubAgent(llm_manager, tool_dispatcher)
    assert not hasattr(data_agent, '_setup_websocket_context_if_available'), \
        "DataSubAgent still has dead method _setup_websocket_context_if_available"
    assert not hasattr(data_agent, '_setup_websocket_context_for_legacy'), \
        "DataSubAgent still has dead method _setup_websocket_context_for_legacy"
    
    # Test TriageSubAgent
    triage_agent = TriageSubAgent(llm_manager, tool_dispatcher)
    assert not hasattr(triage_agent, '_setup_websocket_context_if_available'), \
        "TriageSubAgent still has dead method _setup_websocket_context_if_available"
    assert not hasattr(triage_agent, '_setup_websocket_context_for_legacy'), \
        "TriageSubAgent still has dead method _setup_websocket_context_for_legacy"
    
    print("✅ All dead methods successfully removed")


def test_websocket_enabled_bug_fixed():
    """Verify the websocket_enabled bug in ValidationSubAgent is fixed."""
    llm_manager = Mock()
    tool_dispatcher = Mock()
    
    agent = ValidationSubAgent(llm_manager, tool_dispatcher)
    
    # This should not raise AttributeError anymore
    try:
        health_status = agent.get_health_status()
        assert 'websocket_enabled' in health_status, \
            "Health status missing websocket_enabled field"
        assert isinstance(health_status['websocket_enabled'], bool), \
            "websocket_enabled should be a boolean"
        print(f"✅ Health status websocket_enabled works: {health_status['websocket_enabled']}")
    except AttributeError as e:
        assert False, f"websocket_enabled bug not fixed: {e}"


def test_websocket_bridge_integration():
    """Test that WebSocket bridge integration still works."""
    llm_manager = Mock()
    tool_dispatcher = Mock()
    
    # Create agent and bridge
    agent = DataSubAgent(llm_manager, tool_dispatcher)
    bridge = AgentWebSocketBridge()
    
    # Set bridge on agent
    agent.set_websocket_bridge(bridge, "test_run_123")
    
    # Verify bridge is set correctly
    assert hasattr(agent, '_websocket_adapter'), \
        "Agent missing _websocket_adapter"
    assert agent.has_websocket_context(), \
        "has_websocket_context() should return True when bridge is set"
    
    print("✅ WebSocket bridge integration working correctly")


async def test_websocket_event_emission():
    """Test that agents can still emit WebSocket events."""
    llm_manager = Mock()
    tool_dispatcher = Mock()
    
    # Create agent with mock bridge
    agent = ValidationSubAgent(llm_manager, tool_dispatcher)
    mock_bridge = Mock(spec=AgentWebSocketBridge)
    mock_bridge.notify_agent_thinking = Mock(return_value=asyncio.coroutine(lambda: None)())
    mock_bridge.notify_tool_executing = Mock(return_value=asyncio.coroutine(lambda: None)())
    
    agent.set_websocket_bridge(mock_bridge, "test_run")
    
    # Test event emission methods exist and work
    await agent.emit_thinking("Test thinking")
    await agent.emit_tool_executing("test_tool", {})
    await agent.emit_progress("Test progress", is_complete=False)
    
    print("✅ WebSocket event emission methods working")


def main():
    """Run all validation tests."""
    print("\n" + "="*60)
    print("WebSocket Refactoring Validation Tests")
    print("="*60 + "\n")
    
    # Run synchronous tests
    test_dead_methods_removed()
    test_websocket_enabled_bug_fixed()
    test_websocket_bridge_integration()
    
    # Run async test
    asyncio.run(test_websocket_event_emission())
    
    print("\n" + "="*60)
    print("✅ ALL VALIDATION TESTS PASSED!")
    print("="*60)


if __name__ == "__main__":
    main()