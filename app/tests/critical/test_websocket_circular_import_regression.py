"""Critical test for WebSocket circular import regression.

This test specifically prevents the regression where WebSocket modules
importing BaseExecutionEngine caused circular dependencies that prevented
agent registration and message processing.

REGRESSION HISTORY:
- Date: 2025-01-19
- Issue: Circular import between app.websocket.connection_executor and app.agents.base.executor
- Impact: Agents couldn't be imported, WebSocket messages sent but no responses
- Fix: Removed BaseExecutionEngine imports from WebSocket modules
"""

import pytest
import importlib
import sys
from typing import List, Set
import ast
import os


class TestCircularImportRegression:
    """Prevent the specific circular import regression."""
    
    def test_no_baseexecutionengine_import_in_websocket(self):
        """WebSocket modules MUST NOT import BaseExecutionEngine."""
        websocket_modules = [
            'app.websocket.connection_executor',
            'app.websocket.message_handler_core',
            'app.websocket.websocket_broadcast_executor',
            'app.websocket.error_handler',
            'app.websocket.message_router'
        ]
        
        for module_name in websocket_modules:
            # Get the file path
            module_path = module_name.replace('.', os.sep) + '.py'
            
            # Read the file content
            with open(module_path, 'r') as f:
                content = f.read()
            
            # Check for BaseExecutionEngine import
            assert 'from app.agents.base.executor import BaseExecutionEngine' not in content, \
                f"{module_name} imports BaseExecutionEngine - CIRCULAR DEPENDENCY!"
            
            # Also check for any reference to BaseExecutionEngine
            if 'BaseExecutionEngine' in content and 'Removed BaseExecutionEngine' not in content:
                pytest.fail(f"{module_name} references BaseExecutionEngine - potential circular dependency!")
    
    def test_websocket_modules_use_local_execution(self):
        """Verify WebSocket modules use local execution patterns."""
        from app.websocket.connection_executor import ConnectionExecutor
        
        # Verify execution_engine is None or local implementation
        executor = ConnectionExecutor()
        assert executor.execution_engine is None, \
            "ConnectionExecutor should not use BaseExecutionEngine"
    
    def test_import_order_independence(self):
        """Test that modules can be imported in any order."""
        # Clear any cached imports
        modules_to_test = [
            'app.websocket.connection_executor',
            'app.agents.base.executor',
            'app.agents.supervisor_consolidated',
            'app.services.agent_service_core'
        ]
        
        # Test forward order
        for module in modules_to_test:
            if module in sys.modules:
                del sys.modules[module]
        
        try:
            for module in modules_to_test:
                importlib.import_module(module)
        except ImportError as e:
            pytest.fail(f"Forward import failed: {e}")
        
        # Clear and test reverse order
        for module in modules_to_test:
            if module in sys.modules:
                del sys.modules[module]
        
        try:
            for module in reversed(modules_to_test):
                importlib.import_module(module)
        except ImportError as e:
            pytest.fail(f"Reverse import failed: {e}")
    
    def test_agent_registry_accessible_after_imports(self):
        """Verify agent registry is accessible after all imports."""
        # Import in problematic order
        from app.websocket.connection_executor import ConnectionExecutor
        from app.agents.supervisor_consolidated import SupervisorAgent
        from app.agents.supervisor.agent_registry import AgentRegistry
        
        # Verify classes are accessible
        assert ConnectionExecutor is not None
        assert SupervisorAgent is not None  
        assert AgentRegistry is not None
        
        # Verify registry can be instantiated
        mock_llm = type('MockLLM', (), {})()
        mock_dispatcher = type('MockDispatcher', (), {})()
        
        registry = AgentRegistry(mock_llm, mock_dispatcher)
        registry.register_default_agents()
        
        # Verify agents are registered
        assert len(registry.list_agents()) >= 5, \
            "Agent registry should have at least 5 default agents"
    
    def test_websocket_handler_without_execution_engine(self):
        """Test WebSocket handlers work without BaseExecutionEngine."""
        from app.websocket.message_handler_core import ReliableMessageHandler
        
        # Create handler
        handler = ReliableMessageHandler()
        
        # Verify it doesn't have execution_engine or it's None
        if hasattr(handler, 'execution_engine'):
            assert handler.execution_engine is None, \
                "Message handler should not use BaseExecutionEngine"
    
    def test_broadcast_executor_without_execution_engine(self):
        """Test broadcast executor works without BaseExecutionEngine."""
        from app.websocket.websocket_broadcast_executor import BroadcastExecutor
        
        # Mock dependencies
        mock_conn_manager = type('MockConnManager', (), {})()
        mock_room_manager = type('MockRoomManager', (), {})()
        mock_executor = type('MockExecutor', (), {})()
        
        # Create broadcast executor
        broadcast = BroadcastExecutor(
            mock_conn_manager,
            mock_room_manager,
            mock_executor
        )
        
        # Verify execution_engine is None
        if hasattr(broadcast, 'execution_engine'):
            assert broadcast.execution_engine is None, \
                "Broadcast executor should not use BaseExecutionEngine"
    
    @pytest.mark.asyncio
    async def test_message_flow_without_circular_dependency(self):
        """Test message flow works after circular dependency fix."""
        from app.services.agent_service_core import AgentService
        from unittest.mock import AsyncMock, Mock, patch
        
        # Create mock supervisor
        mock_supervisor = AsyncMock()
        mock_supervisor.run = AsyncMock(return_value="Test response")
        
        # Create agent service
        service = AgentService(mock_supervisor)
        
        # Test message
        message = {
            "type": "user_message",
            "payload": {"content": "Test after circular fix"}
        }
        
        # Process message
        with patch('app.ws_manager.manager'):
            await service.handle_websocket_message(
                user_id="test_user",
                message=message,
                db_session=None
            )
        
        # Verify supervisor was called
        assert mock_supervisor.run.called, \
            "Message should trigger supervisor execution after circular fix"