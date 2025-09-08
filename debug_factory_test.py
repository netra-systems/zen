#!/usr/bin/env python3
"""
Debug script to understand why the AgentInstanceFactory test is failing.
"""
import asyncio
from unittest.mock import Mock, AsyncMock
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.base_agent import BaseAgent

# Mock agent exactly like the test
class MockAgent(BaseAgent):
    """Mock agent implementation for testing."""
    
    def __init__(self, llm_manager=None, tool_dispatcher=None):
        super().__init__()
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.websocket_bridge = None
        self.run_id = None
        self._websocket_adapter = Mock()
        self._websocket_adapter.set_websocket_bridge = Mock()
        
    def set_websocket_bridge(self, bridge, run_id):
        self.websocket_bridge = bridge
        self.run_id = run_id
        
    async def execute(self, state, run_id):
        return {"status": "success", "result": "mock_result"}

# Create mocks exactly like the test
mock_agent_class_registry = Mock(spec=AgentClassRegistry)
mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)

# Configure mock registry like the test - CRITICAL FIX
mock_agent_class_registry.__len__ = Mock(return_value=5)
mock_agent_class_registry.get_agent_class.return_value = MockAgent  # Should return MockAgent, not None
mock_agent_class_registry.list_agent_names.return_value = ["test_agent", "other_agent"]

# Configure WebSocket bridge
mock_websocket_bridge.notify_agent_started = AsyncMock(return_value=True)
mock_websocket_bridge.notify_agent_thinking = AsyncMock(return_value=True)
mock_websocket_bridge.notify_tool_executing = AsyncMock(return_value=True)
mock_websocket_bridge.notify_tool_completed = AsyncMock(return_value=True)
mock_websocket_bridge.notify_agent_completed = AsyncMock(return_value=True)
mock_websocket_bridge.notify_agent_error = AsyncMock(return_value=True)
mock_websocket_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
mock_websocket_bridge.unregister_run_mapping = AsyncMock(return_value=True)

async def main():
    print(f"Mock agent class registry: {mock_agent_class_registry}")
    print(f"Mock registry truthiness: {bool(mock_agent_class_registry)}")
    print(f"Mock registry __len__: {mock_agent_class_registry.__len__()}")
    print(f"Mock registry len(): {len(mock_agent_class_registry)}")

    # Create factory and configure
    factory = AgentInstanceFactory()

    print(f"\nBefore configure:")
    print(f"factory._agent_class_registry: {factory._agent_class_registry}")
    print(f"factory._agent_registry: {factory._agent_registry}")

    try:
        factory.configure(
            agent_class_registry=mock_agent_class_registry,
            websocket_bridge=mock_websocket_bridge
        )
        
        print(f"\nAfter configure:")
        print(f"factory._agent_class_registry: {factory._agent_class_registry}")
        print(f"factory._agent_registry: {factory._agent_registry}")
        
        # Test the specific condition that should be True
        print(f"\nCondition tests:")
        print(f"agent_class_registry is not None: {mock_agent_class_registry is not None}")
        print(f"bool(agent_class_registry): {bool(mock_agent_class_registry)}")
        print(f"if agent_class_registry: {bool(mock_agent_class_registry)}")
        
        print(f"\nFactory state after configure:")
        print(f"self._agent_class_registry is not None: {factory._agent_class_registry is not None}")
        print(f"bool(self._agent_class_registry): {bool(factory._agent_class_registry)}")
        print(f"if self._agent_class_registry: {bool(factory._agent_class_registry)}")
        
        # Now test the full flow - create context and agent
        print(f"\nTesting full flow:")
        
        # Create user execution context
        context = await factory.create_user_execution_context(
            user_id="test_user_12345",
            thread_id="test_thread_67890",
            run_id="test_run_abcdef"
        )
        print(f"Created context: {context}")
        
        # Test create_agent_instance - this is where the error occurs
        print(f"Testing create_agent_instance...")
        print(f"Mock get_agent_class will return: {mock_agent_class_registry.get_agent_class.return_value}")
        
        # Check factory state right before create_agent_instance call
        print(f"\nFactory state immediately before create_agent_instance:")
        print(f"factory._agent_class_registry: {factory._agent_class_registry}")
        print(f"factory._agent_registry: {factory._agent_registry}")
        print(f"factory._agent_class_registry is not None: {factory._agent_class_registry is not None}")
        print(f"bool(factory._agent_class_registry): {bool(factory._agent_class_registry)}")
        
        # Check what will happen in the condition chain
        print(f"\nLogical flow check:")
        print(f"Line 683: agent_class = None (starting value)")
        print(f"Line 686: enable_class_caching = {factory._performance_config.enable_class_caching}")
        
        # Simulate the caching logic
        AgentClass = None
        if factory._performance_config.enable_class_caching:
            print(f"Line 687: Calling _get_cached_agent_class('test_agent')")
            cached_result = factory._get_cached_agent_class('test_agent')  
            print(f"Cached result: {cached_result}")
            AgentClass = cached_result
        
        print(f"After caching, AgentClass = {AgentClass}")
        print(f"Line 690: not AgentClass and self._agent_class_registry = {not AgentClass and factory._agent_class_registry}")
        if not AgentClass and factory._agent_class_registry:
            print(f"Line 691: Would call get_agent_class('test_agent')")
            mock_result = mock_agent_class_registry.get_agent_class('test_agent')
            print(f"Mock would return: {mock_result}")
            if mock_result:
                print(f"AgentClass would be set to: {mock_result}")
            else:
                print(f"AgentClass would remain None, error at line 709")
        else:
            print(f"Skipping line 690-724 because condition is False")
        
        print(f"Line 726: self._agent_registry = {factory._agent_registry}")
        if factory._agent_registry:
            print(f"Would enter elif block at line 726")
        else:
            print(f"Line 735: Would enter else block - ERROR!")
        
        agent = await factory.create_agent_instance("test_agent", context)
        print(f"SUCCESS: Created agent: {agent}")
        print(f"Agent type: {type(agent)}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
