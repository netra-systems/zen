"""
Basic SupervisorAgent tests - basic functionality validation.
SSOT compliance: Uses real instances, minimal mocking per CLAUDE.md standards.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# ABSOLUTE IMPORTS - SSOT compliance
from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import get_env

# Import target class and dependencies
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestSupervisorOrchestration(BaseTestCase):
    """Basic SupervisorAgent orchestration tests."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Create mock LLM manager
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="test response")
        
        # Create mock WebSocket bridge
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.websocket_manager = Mock()
        self.websocket_bridge.emit_agent_event = AsyncMock()
        
        # Create real UserExecutionContext
        self.test_context = UserExecutionContext(
            user_id="test-user-basic",
            thread_id="test-thread-basic", 
            run_id="test-run-basic",
            metadata={"user_request": "basic test request"}
        ).with_db_session(AsyncMock())
        
        # Mock registries
        self.mock_class_registry = Mock()
        self.mock_class_registry.get_agent_classes.return_value = {"triage": Mock(), "reporting": Mock()}
        self.mock_class_registry.__len__ = Mock(return_value=2)
        
        self.mock_instance_factory = Mock()
        self.mock_instance_factory.configure = Mock()
        self.mock_instance_factory.create_agent_instance = AsyncMock()
        self.mock_instance_factory.agent_class_registry = self.mock_class_registry
        
        # Patch global registries
        self.registry_patcher = patch('netra_backend.app.agents.supervisor.agent_class_registry.get_agent_class_registry')
        self.factory_patcher = patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory')
        self.internal_registry_patcher = patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_class_registry')
        
        mock_registry_func = self.registry_patcher.start()
        mock_factory_func = self.factory_patcher.start() 
        mock_internal_registry_func = self.internal_registry_patcher.start()
        
        mock_registry_func.return_value = self.mock_class_registry
        mock_factory_func.return_value = self.mock_instance_factory
        mock_internal_registry_func.return_value = self.mock_class_registry
        
        # Create SupervisorAgent instance
        self.supervisor = SupervisorAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )
        
        self.track_resource(self.supervisor)
    
    def tearDown(self):
        """Clean up patches."""
        super().tearDown()
        self.registry_patcher.stop()
        self.factory_patcher.stop()
        self.internal_registry_patcher.stop()
    
    def test_supervisor_initialization(self):
        """Test SupervisorAgent initializes correctly."""
        self.assertIsNotNone(self.supervisor)
        self.assertEqual(self.supervisor.name, "Supervisor")
        self.assertIsNotNone(self.supervisor.agent_instance_factory)
        self.assertIsNotNone(self.supervisor.agent_class_registry)
    
    async def test_basic_execution_flow(self):
        """Test basic execution flow with minimal setup."""
        # Mock minimal successful execution
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager), \
             patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
             patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory, \
             patch.object(self.supervisor, '_orchestrate_agents') as mock_orchestrate:
            
            # Mock UserContextToolFactory
            mock_tool_system = {
                'dispatcher': Mock(),
                'registry': Mock(),
                'tools': []
            }
            mock_tool_system['registry'].name = "test_registry"
            mock_tool_system['dispatcher'].dispatcher_id = "test_dispatcher"
            mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
            
            # Mock orchestration result
            mock_orchestrate.return_value = {
                "supervisor_result": "completed",
                "orchestration_successful": True,
                "user_isolation_verified": True,
                "results": {"reporting": {"status": "completed"}},
                "user_id": self.test_context.user_id,
                "run_id": self.test_context.run_id
            }
            
            # Execute supervisor
            result = await self.supervisor.execute(self.test_context)
            
            # Verify basic execution completed
            self.assertIsNotNone(result)
            self.assertEqual(result["supervisor_result"], "completed")
            self.assertTrue(result["orchestration_successful"])
    
    def test_agent_dependencies_validation(self):
        """Test agent dependency validation."""
        # Test triage (no dependencies)
        can_execute, missing = self.supervisor._can_execute_agent("triage", set(), {})
        self.assertTrue(can_execute)
        self.assertEqual(missing, [])
        
        # Test reporting (no required dependencies)
        can_execute, missing = self.supervisor._can_execute_agent("reporting", set(), {})
        self.assertTrue(can_execute)
        self.assertEqual(missing, [])


if __name__ == '__main__':
    pytest.main([__file__, "-v"])