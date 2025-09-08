#!/usr/bin/env python3
"""
Debug script to investigate the AgentInstanceFactory configuration issue.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "netra_backend"))

from unittest.mock import Mock, AsyncMock
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry


def debug_factory_configuration():
    """Debug the factory configuration process."""
    print("=== Debugging AgentInstanceFactory Configuration ===")
    
    # Create mock components
    mock_agent_class_registry = Mock(spec=AgentClassRegistry)
    mock_agent_class_registry.__len__ = Mock(return_value=5)
    mock_agent_class_registry.get_agent_class = Mock(return_value=Mock)  # Mock agent class
    
    mock_websocket_bridge = Mock()
    mock_llm_manager = Mock()
    mock_tool_dispatcher = Mock()
    
    print(f"Mock registry created: {mock_agent_class_registry}")
    print(f"Mock registry __len__: {mock_agent_class_registry.__len__()}")
    
    # Create factory and configure
    factory = AgentInstanceFactory()
    print(f"Factory created: {factory}")
    print(f"Initial _agent_class_registry: {getattr(factory, '_agent_class_registry', 'NOT_SET')}")
    
    # Configure factory
    factory.configure(
        agent_class_registry=mock_agent_class_registry,
        websocket_bridge=mock_websocket_bridge,
        llm_manager=mock_llm_manager,
        tool_dispatcher=mock_tool_dispatcher
    )
    
    print(f"After configure _agent_class_registry: {getattr(factory, '_agent_class_registry', 'NOT_SET')}")
    print(f"_agent_class_registry is mock_agent_class_registry: {factory._agent_class_registry is mock_agent_class_registry}")
    print(f"_agent_class_registry type: {type(factory._agent_class_registry)}")
    
    # Test the condition that is failing
    print(f"\nTesting conditions:")
    print(f"  self._agent_class_registry: {factory._agent_class_registry}")
    print(f"  bool(self._agent_class_registry): {bool(factory._agent_class_registry)}")
    
    # Test the condition from line 690
    AgentClass = None
    condition_result = not AgentClass and factory._agent_class_registry
    print(f"  (not AgentClass and self._agent_class_registry): {condition_result}")
    
    if factory._agent_class_registry:
        print(f"  Registry get_agent_class result: {factory._agent_class_registry.get_agent_class('test_agent')}")
    
    print("\n=== Factory Configuration Debug Complete ===")


if __name__ == "__main__":
    debug_factory_configuration()
