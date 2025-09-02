"""
SSOT Mock Compatibility Bridge

This module provides backward compatibility for existing mock usage patterns
while encouraging migration to the SSOT MockFactory.

Business Value: Platform/Internal - Test Infrastructure Stability
Ensures no test breakage during consolidation while enabling gradual migration.
"""

import warnings
from typing import Any
from unittest.mock import AsyncMock, Mock

from test_framework.ssot.mocks import get_mock_factory

def deprecated_mock_warning(old_class: str, new_method: str):
    """Issue deprecation warning for mock usage."""
    warnings.warn(
        f"{old_class} is deprecated. Use get_mock_factory().{new_method}() instead.",
        DeprecationWarning,
        stacklevel=3
    )

# ========== Deprecated Mock Classes with Compatibility ==========

class MockAgent(AsyncMock):
    """DEPRECATED: Use MockFactory.create_agent_mock() instead."""
    
    def __init__(self, agent_id: str = "test_agent", user_id: str = None, *args, **kwargs):
        deprecated_mock_warning("MockAgent", "create_agent_mock")
        
        # Get factory mock and copy its behavior
        factory = get_mock_factory()
        factory_mock = factory.create_agent_mock(agent_id=agent_id, user_id=user_id)
        
        # Initialize with factory mock's configuration
        super().__init__(*args, **kwargs)
        
        # Copy all attributes and methods from factory mock
        for attr_name in dir(factory_mock):
            if not attr_name.startswith('_'):
                setattr(self, attr_name, getattr(factory_mock, attr_name))


class MockOrchestrator(AsyncMock):
    """DEPRECATED: Use MockFactory.create_orchestrator_mock() instead."""
    
    def __init__(self, *args, **kwargs):
        deprecated_mock_warning("MockOrchestrator", "create_orchestrator_mock")
        
        factory = get_mock_factory()
        factory_mock = factory.create_orchestrator_mock()
        
        super().__init__(*args, **kwargs)
        
        for attr_name in dir(factory_mock):
            if not attr_name.startswith('_'):
                setattr(self, attr_name, getattr(factory_mock, attr_name))


class MockWebSocketManager(AsyncMock):
    """DEPRECATED: Use MockFactory.create_websocket_manager_mock() instead."""
    
    def __init__(self, *args, **kwargs):
        deprecated_mock_warning("MockWebSocketManager", "create_websocket_manager_mock")
        
        factory = get_mock_factory()
        factory_mock = factory.create_websocket_manager_mock()
        
        super().__init__(*args, **kwargs)
        
        for attr_name in dir(factory_mock):
            if not attr_name.startswith('_'):
                setattr(self, attr_name, getattr(factory_mock, attr_name))


class MockWebSocket(AsyncMock):
    """DEPRECATED: Use MockFactory.create_websocket_connection_mock() instead."""
    
    def __init__(self, *args, **kwargs):
        deprecated_mock_warning("MockWebSocket", "create_websocket_connection_mock")
        
        factory = get_mock_factory()
        factory_mock = factory.create_websocket_connection_mock()
        
        super().__init__(*args, **kwargs)
        
        for attr_name in dir(factory_mock):
            if not attr_name.startswith('_'):
                setattr(self, attr_name, getattr(factory_mock, attr_name))


class MockWebSocketConnection(AsyncMock):
    """DEPRECATED: Use MockFactory.create_websocket_connection_mock() instead."""
    
    def __init__(self, *args, **kwargs):
        deprecated_mock_warning("MockWebSocketConnection", "create_websocket_connection_mock")
        
        factory = get_mock_factory()
        factory_mock = factory.create_websocket_connection_mock()
        
        super().__init__(*args, **kwargs)
        
        for attr_name in dir(factory_mock):
            if not attr_name.startswith('_'):
                setattr(self, attr_name, getattr(factory_mock, attr_name))


class MockAuthService(AsyncMock):
    """DEPRECATED: Use MockFactory.create_auth_service_mock() instead."""
    
    def __init__(self, *args, **kwargs):
        deprecated_mock_warning("MockAuthService", "create_auth_service_mock")
        
        factory = get_mock_factory()
        factory_mock = factory.create_auth_service_mock()
        
        super().__init__(*args, **kwargs)
        
        for attr_name in dir(factory_mock):
            if not attr_name.startswith('_'):
                setattr(self, attr_name, getattr(factory_mock, attr_name))


class MockLLMService(AsyncMock):
    """DEPRECATED: Use MockFactory.create_llm_client_mock() instead."""
    
    def __init__(self, *args, **kwargs):
        deprecated_mock_warning("MockLLMService", "create_llm_client_mock")
        
        factory = get_mock_factory()
        factory_mock = factory.create_llm_client_mock()
        
        super().__init__(*args, **kwargs)
        
        for attr_name in dir(factory_mock):
            if not attr_name.startswith('_'):
                setattr(self, attr_name, getattr(factory_mock, attr_name))


class MockServiceManager(AsyncMock):
    """DEPRECATED: Use MockFactory.create_service_manager_mock() instead."""
    
    def __init__(self, *args, **kwargs):
        deprecated_mock_warning("MockServiceManager", "create_service_manager_mock")
        
        factory = get_mock_factory()
        factory_mock = factory.create_service_manager_mock()
        
        super().__init__(*args, **kwargs)
        
        for attr_name in dir(factory_mock):
            if not attr_name.startswith('_'):
                setattr(self, attr_name, getattr(factory_mock, attr_name))


class MockAgentService(AsyncMock):
    """DEPRECATED: Use MockFactory.create_agent_mock() instead."""
    
    def __init__(self, *args, **kwargs):
        deprecated_mock_warning("MockAgentService", "create_agent_mock")
        
        factory = get_mock_factory()
        factory_mock = factory.create_agent_mock()
        
        super().__init__(*args, **kwargs)
        
        for attr_name in dir(factory_mock):
            if not attr_name.startswith('_'):
                setattr(self, attr_name, getattr(factory_mock, attr_name))


# Export compatibility classes
__all__ = [
    'MockAgent',
    'MockOrchestrator', 
    'MockWebSocketManager',
    'MockWebSocket',
    'MockWebSocketConnection',
    'MockAuthService',
    'MockLLMService',
    'MockServiceManager',
    'MockAgentService',
    'deprecated_mock_warning'
]