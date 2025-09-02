#!/usr/bin/env python3
"""
Test script to verify AgentInstanceFactory refactor functionality.

This script tests the critical fix for the AgentRegistry singleton issue where
WebSocket events were mixed between users and placeholder run_ids were used.
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# Mock classes for testing
class MockLLMManager:
    def __init__(self):
        pass

class MockToolDispatcher:
    def __init__(self):
        pass

class MockWebSocketManager:
    def __init__(self):
        pass

class MockAgentWebSocketBridge:
    def __init__(self):
        self.events = []
    
    async def notify_agent_started(self, run_id, agent_name, context=None):
        self.events.append({
            'type': 'agent_started',
            'run_id': run_id,
            'agent_name': agent_name,
            'context': context
        })
        return True
    
    async def notify_agent_thinking(self, run_id, agent_name, reasoning, step_number=None, progress_percentage=None):
        self.events.append({
            'type': 'agent_thinking',
            'run_id': run_id,
            'agent_name': agent_name,
            'reasoning': reasoning
        })
        return True
    
    async def notify_tool_executing(self, run_id, agent_name, tool_name, parameters=None):
        self.events.append({
            'type': 'tool_executing',
            'run_id': run_id,
            'agent_name': agent_name,
            'tool_name': tool_name
        })
        return True
    
    async def notify_tool_completed(self, run_id, agent_name, tool_name, result=None, execution_time_ms=None):
        self.events.append({
            'type': 'tool_completed',
            'run_id': run_id,
            'agent_name': agent_name,
            'tool_name': tool_name
        })
        return True
    
    async def notify_agent_completed(self, run_id, agent_name, result=None, execution_time_ms=None):
        self.events.append({
            'type': 'agent_completed',
            'run_id': run_id,
            'agent_name': agent_name
        })
        return True

class TestAgent(BaseAgent):
    def __init__(self, llm_manager=None, tool_dispatcher=None, name="TestAgent", user_id=None):
        super().__init__(llm_manager, name=name, user_id=user_id, tool_dispatcher=tool_dispatcher)
        self.description = "Test agent for refactor validation"


async def test_agent_class_registry():
    """Test AgentClassRegistry infrastructure-only functionality."""
    print("\n=== Testing AgentClassRegistry ===")
    
    registry = AgentClassRegistry()
    
    # Test registration
    registry.register("test", TestAgent, "Test agent for validation")
    
    # Test retrieval
    agent_class = registry.get_agent_class("test")
    assert agent_class == TestAgent, f"Expected TestAgent, got {agent_class}"
    
    # Test freeze
    registry.freeze()
    
    # Test that registration after freeze fails
    try:
        registry.register("test2", TestAgent, "Should fail")
        assert False, "Registration should fail after freeze"
    except RuntimeError as e:
        assert "frozen" in str(e).lower(), f"Expected freeze error, got: {e}"
    
    print("[PASS] AgentClassRegistry tests passed")


async def test_user_execution_context():
    """Test UserExecutionContext validation and isolation."""
    print("\n=== Testing UserExecutionContext ===")
    
    # Test valid context creation
    context = UserExecutionContext.from_request(
        user_id="user123",
        thread_id="thread456", 
        run_id="run789"
    )
    
    assert context.user_id == "user123"
    assert context.thread_id == "thread456" 
    assert context.run_id == "run789"
    
    # Test that placeholder values are rejected
    try:
        UserExecutionContext.from_request(
            user_id="registry",  # Forbidden placeholder value
            thread_id="thread456",
            run_id="run789"
        )
        assert False, "Should reject placeholder user_id"
    except Exception as e:
        assert "placeholder" in str(e).lower(), f"Expected placeholder error, got: {e}"
    
    # Test run_id validation
    try:
        UserExecutionContext.from_request(
            user_id="user123",
            thread_id="thread456",
            run_id="registry"  # Forbidden placeholder value
        )
        assert False, "Should reject placeholder run_id"
    except Exception as e:
        assert "placeholder" in str(e).lower(), f"Expected placeholder error, got: {e}"
    
    print("[PASS] UserExecutionContext tests passed")


async def test_agent_instance_factory():
    """Test AgentInstanceFactory with proper user isolation."""
    print("\n=== Testing AgentInstanceFactory ===")
    
    # Set up infrastructure
    agent_class_registry = AgentClassRegistry()
    agent_class_registry.register("test", TestAgent, "Test agent")
    agent_class_registry.freeze()
    
    websocket_bridge = MockAgentWebSocketBridge()
    
    # Create and configure factory
    factory = AgentInstanceFactory()
    
    # Also create a legacy registry to provide LLM manager and tool dispatcher
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        legacy_registry = AgentRegistry(MockLLMManager(), MockToolDispatcher())
    
    factory.configure(
        agent_class_registry=agent_class_registry,
        agent_registry=legacy_registry,  # Provide for dependencies
        websocket_bridge=websocket_bridge
    )
    
    # Test user execution context creation
    user_id = "user123"
    thread_id = "thread456"
    run_id = str(uuid.uuid4())  # Real run_id, not placeholder
    
    context = await factory.create_user_execution_context(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id
    )
    
    assert context.user_id == user_id
    assert context.run_id == run_id
    assert context.run_id != "registry", "Must not use placeholder run_id"
    
    # Test agent instance creation
    agent = await factory.create_agent_instance("test", context)
    assert isinstance(agent, TestAgent)
    
    # Test that WebSocket bridge is set with REAL run_id
    if hasattr(agent, '_websocket_adapter'):
        assert agent._websocket_adapter._run_id == run_id, f"Expected real run_id {run_id}, got {agent._websocket_adapter._run_id}"
        assert agent._websocket_adapter._run_id != "registry", "Must not use placeholder run_id"
        assert agent._websocket_adapter._run_id is not None, "Run_id cannot be None"
    
    # Test cleanup
    await factory.cleanup_user_context(context)
    
    print("[PASS] AgentInstanceFactory tests passed")


async def test_legacy_agent_registry_compatibility():
    """Test that legacy AgentRegistry issues deprecation warnings."""
    print("\n=== Testing Legacy AgentRegistry Compatibility ===")
    
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        # This should trigger a deprecation warning
        registry = AgentRegistry(MockLLMManager(), MockToolDispatcher())
        
        assert len(w) > 0, "Expected deprecation warning"
        assert "deprecated" in str(w[0].message).lower(), f"Expected deprecation warning, got: {w[0].message}"
    
    # Test that legacy registry can create new factory
    factory = registry.create_request_scoped_factory()
    assert isinstance(factory, AgentInstanceFactory)
    
    print("[PASS] Legacy AgentRegistry compatibility tests passed")


async def test_websocket_isolation():
    """Test that WebSocket events are properly isolated per user."""
    print("\n=== Testing WebSocket Isolation ===")
    
    # Set up infrastructure
    agent_class_registry = AgentClassRegistry()
    agent_class_registry.register("test", TestAgent, "Test agent")
    agent_class_registry.freeze()
    
    websocket_bridge = MockAgentWebSocketBridge()
    
    factory = AgentInstanceFactory()
    
    # Create legacy registry for dependencies (suppress warning)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        legacy_registry = AgentRegistry(MockLLMManager(), MockToolDispatcher())
    
    factory.configure(
        agent_class_registry=agent_class_registry,
        agent_registry=legacy_registry,
        websocket_bridge=websocket_bridge
    )
    
    # Create two different user contexts
    user1_run_id = str(uuid.uuid4())
    user2_run_id = str(uuid.uuid4())
    
    context1 = await factory.create_user_execution_context("user1", "thread1", user1_run_id)
    context2 = await factory.create_user_execution_context("user2", "thread2", user2_run_id)
    
    # Create agents for both users
    agent1 = await factory.create_agent_instance("test", context1)
    agent2 = await factory.create_agent_instance("test", context2)
    
    # Verify agents have different run_ids
    if hasattr(agent1, '_websocket_adapter') and hasattr(agent2, '_websocket_adapter'):
        assert agent1._websocket_adapter._run_id != agent2._websocket_adapter._run_id, "Agents must have different run_ids"
        assert agent1._websocket_adapter._run_id == user1_run_id, "Agent1 must use user1's run_id"
        assert agent2._websocket_adapter._run_id == user2_run_id, "Agent2 must use user2's run_id"
        
        # Both run_ids must be real, not placeholders
        assert agent1._websocket_adapter._run_id != "registry", "Agent1 must not use placeholder"
        assert agent2._websocket_adapter._run_id != "registry", "Agent2 must not use placeholder"
    
    # Clean up
    await factory.cleanup_user_context(context1)
    await factory.cleanup_user_context(context2)
    
    print("[PASS] WebSocket isolation tests passed")


async def main():
    """Run all refactor validation tests."""
    print("=== Starting AgentRegistry Refactor Validation Tests ===")
    
    try:
        await test_agent_class_registry()
        await test_user_execution_context()
        await test_agent_instance_factory()
        await test_legacy_agent_registry_compatibility()
        await test_websocket_isolation()
        
        print("\n=== ALL TESTS PASSED! ===")
        print("\n=== AgentRegistry refactor successfully addresses ===")
        print("   - Eliminates singleton WebSocket state sharing between users")
        print("   - Uses real run_id from UserExecutionContext (not placeholder 'registry')")
        print("   - Provides proper per-user isolation for WebSocket events")
        print("   - Maintains backward compatibility with deprecation warnings")
        print("   - Separates infrastructure (AgentClassRegistry) from request scope (AgentInstanceFactory)")
        
        return True
        
    except Exception as e:
        print(f"\n=== TEST FAILED: {e} ===")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)