#!/usr/bin/env python3
"""
Debug script to trace the exact execution path in AgentInstanceFactory.create_agent_instance.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "netra_backend"))

from unittest.mock import Mock, AsyncMock, patch
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


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


async def debug_execution_path():
    """Debug the exact execution path that leads to the error."""
    print("=== Debugging AgentInstanceFactory Execution Path ===")
    
    # Create mocks exactly like in the test
    mock_agent_class_registry = Mock(spec=AgentClassRegistry)
    mock_agent_class_registry.__len__ = Mock(return_value=5)
    mock_agent_class_registry.get_agent_class = Mock(return_value=MockAgent)
    mock_agent_class_registry.list_agent_names = Mock(return_value=["test_agent", "other_agent"])
    
    mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
    mock_websocket_bridge.notify_agent_started = AsyncMock(return_value=True)
    mock_websocket_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
    
    mock_llm_manager = Mock()
    mock_tool_dispatcher = Mock()
    
    # Create and configure factory
    factory = AgentInstanceFactory()
    factory.configure(
        agent_class_registry=mock_agent_class_registry,
        websocket_bridge=mock_websocket_bridge,
        llm_manager=mock_llm_manager,
        tool_dispatcher=mock_tool_dispatcher
    )
    
    # Create user context
    context = await factory.create_user_execution_context(
        user_id="debug_user",
        thread_id="debug_thread", 
        run_id="debug_run"
    )
    
    print(f"Factory configured with registry: {factory._agent_class_registry}")
    print(f"Registry type: {type(factory._agent_class_registry)}")
    print(f"Registry mock configured: {mock_agent_class_registry.get_agent_class.return_value}")
    
    # Now trace the execution step by step
    print("\n=== Tracing create_agent_instance execution ===")
    
    # Manually check the conditions that are failing
    agent_name = "test_agent"
    agent_class = None  # This is what gets set initially
    
    print(f"Initial agent_class: {agent_class}")
    print(f"Performance config enable_class_caching: {factory._performance_config.enable_class_caching}")
    
    # Step 1: Check caching
    if factory._performance_config.enable_class_caching:
        cached_class = factory._get_cached_agent_class(agent_name)
        print(f"Cached class result: {cached_class}")
        agent_class = cached_class
    
    print(f"After caching check, agent_class: {agent_class}")
    
    # Step 2: Check main registry condition  
    condition_result = not agent_class and factory._agent_class_registry
    print(f"Condition 'not agent_class and factory._agent_class_registry': {condition_result}")
    print(f"  - not agent_class: {not agent_class}")
    print(f"  - factory._agent_class_registry: {factory._agent_class_registry}")
    print(f"  - bool(factory._agent_class_registry): {bool(factory._agent_class_registry)}")
    
    if condition_result:
        print("Condition is True, calling registry.get_agent_class...")
        registry_result = factory._agent_class_registry.get_agent_class(agent_name)
        print(f"Registry get_agent_class result: {registry_result}")
        agent_class = registry_result
        print(f"Updated agent_class: {agent_class}")
        
        if not agent_class:
            print("Registry returned None! This would trigger the error path.")
            available_agents = factory._agent_class_registry.list_agent_names()
            print(f"Available agents: {available_agents}")
        else:
            print("Registry returned a valid class!")
    else:
        print("Condition is False! This means:")
        if agent_class:
            print(f"  - agent_class is already set: {agent_class}")
        if not factory._agent_class_registry:
            print("  - factory._agent_class_registry is None/False")
    
    print(f"\nFinal agent_class before next conditions: {agent_class}")
    
    # Check what would happen next
    if not agent_class and not factory._agent_registry:
        print("ERROR PATH: Both agent_class is None and no legacy registry - this triggers line 739!")
    elif factory._agent_registry:
        print("LEGACY PATH: Would use legacy agent registry")
    else:
        print("SUCCESS PATH: Would proceed with agent creation")
    
    print("\n=== Execution Path Debug Complete ===")


if __name__ == "__main__":
    asyncio.run(debug_execution_path())