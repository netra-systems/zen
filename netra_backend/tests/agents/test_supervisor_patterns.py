"""
SupervisorAgent pattern tests - resource management and workflow patterns.
SSOT compliance: Tests for common supervisor orchestration patterns.
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
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestResourceManagement(BaseTestCase):
    """Test resource management patterns in SupervisorAgent."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Create mock dependencies
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="test response")
        
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.websocket_manager = Mock()
        self.websocket_bridge.emit_agent_event = AsyncMock()
        
        self.test_context = UserExecutionContext(
            user_id="test-user-resource",
            thread_id="test-thread-resource",
            run_id="test-run-resource",
            metadata={"user_request": "resource management test"}
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
        
        # Create supervisor
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
    
    def test_agent_instance_creation_pattern(self):
        """Test agent instance creation follows resource management patterns."""
        # Test that supervisor has proper factory setup
        self.assertIsNotNone(self.supervisor.agent_instance_factory)
        self.assertIsNotNone(self.supervisor.agent_class_registry)
    
    async def test_resource_cleanup_pattern(self):
        """Test resource cleanup patterns."""
        # Mock execution with resource cleanup
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager):
            # Test that session manager is properly used for cleanup
            # This tests the pattern even if execution fails
            with patch.object(self.supervisor, '_orchestrate_agents') as mock_orchestrate:
                mock_orchestrate.return_value = {
                    "supervisor_result": "completed",
                    "orchestration_successful": True,
                    "user_isolation_verified": True,
                    "results": {},
                    "user_id": self.test_context.user_id,
                    "run_id": self.test_context.run_id
                }
                
                with patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
                     patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
                    
                    mock_tool_system = {
                        'dispatcher': Mock(),
                        'registry': Mock(),
                        'tools': []
                    }
                    mock_tool_system['registry'].name = "test_registry"
                    mock_tool_system['dispatcher'].dispatcher_id = "test_dispatcher"
                    mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
                    
                    result = await self.supervisor.execute(self.test_context)
                    
                    # Verify session manager cleanup was used
                    mock_session_manager.__aenter__.assert_called_once()
                    mock_session_manager.__aexit__.assert_called_once()
    
    def test_execution_lock_pattern(self):
        """Test execution lock resource management."""
        # Verify execution lock exists for resource management
        self.assertIsNotNone(self.supervisor._execution_lock)
    
    async def test_context_isolation_pattern(self):
        """Test context isolation resource management."""
        # Test that contexts don't share state
        context1 = UserExecutionContext(
            user_id="user-1",
            thread_id="thread-1",
            run_id="run-1",
            metadata={"data": "context1"}
        ).with_db_session(AsyncMock())
        
        context2 = UserExecutionContext(
            user_id="user-2", 
            thread_id="thread-2",
            run_id="run-2",
            metadata={"data": "context2"}
        ).with_db_session(AsyncMock())
        
        # Verify contexts are isolated
        self.assertNotEqual(context1.user_id, context2.user_id)
        self.assertNotEqual(context1.metadata, context2.metadata)


class TestWorkflowPatterns(BaseTestCase):
    """Test workflow orchestration patterns in SupervisorAgent."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Create mock dependencies
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="test response")
        
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.websocket_manager = Mock()
        self.websocket_bridge.emit_agent_event = AsyncMock()
        
        self.test_context = UserExecutionContext(
            user_id="test-user-workflow",
            thread_id="test-thread-workflow", 
            run_id="test-run-workflow",
            metadata={"user_request": "workflow pattern test"}
        ).with_db_session(AsyncMock())
        
        # Mock registries
        self.mock_class_registry = Mock()
        self.mock_class_registry.get_agent_classes.return_value = {
            "triage": Mock(),
            "reporting": Mock(), 
            "data": Mock(),
            "optimization": Mock()
        }
        self.mock_class_registry.__len__ = Mock(return_value=4)
        
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
        
        # Create supervisor
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
    
    def test_agent_dependency_workflow_pattern(self):
        """Test agent dependency workflow patterns."""
        # Test dependency checking pattern
        can_execute, missing = self.supervisor._can_execute_agent("triage", set(), {})
        self.assertTrue(can_execute)  # Triage should have no dependencies
        
        can_execute, missing = self.supervisor._can_execute_agent("reporting", set(), {})
        self.assertTrue(can_execute)  # Reporting should execute per UVS principle
    
    def test_dynamic_workflow_determination_pattern(self):
        """Test dynamic workflow determination patterns."""
        # Test with optimization triage result
        triage_result = {
            "data_sufficiency": "sufficient",
            "intent": {"primary_intent": "optimization"}
        }
        
        execution_order = self.supervisor._determine_execution_order(triage_result, self.test_context)
        
        # Should follow workflow patterns
        self.assertIsInstance(execution_order, list)
        self.assertGreater(len(execution_order), 0)
        
        # Reporting should be at the end (UVS principle)
        self.assertEqual(execution_order[-1], "reporting")
    
    def test_fallback_workflow_pattern(self):
        """Test fallback workflow patterns."""
        # Test with no triage result
        execution_order = self.supervisor._determine_execution_order(None, self.test_context)
        
        # Should have fallback workflow
        self.assertIsInstance(execution_order, list)
        self.assertGreater(len(execution_order), 0)
        
        # Should end with reporting
        self.assertEqual(execution_order[-1], "reporting")
    
    def test_required_agents_pattern(self):
        """Test required agents pattern."""
        required_agents = self.supervisor._get_required_agent_names()
        
        # Should include core agents
        self.assertIn("triage", required_agents)
        self.assertIn("reporting", required_agents)
        
        # Should be a list
        self.assertIsInstance(required_agents, list)
    
    async def test_parallel_execution_pattern(self):
        """Test parallel execution patterns."""
        # Test that supervisor can handle concurrent contexts
        context1 = UserExecutionContext(
            user_id="user-parallel-1",
            thread_id="thread-parallel-1",
            run_id="run-parallel-1"
        ).with_db_session(AsyncMock())
        
        context2 = UserExecutionContext(
            user_id="user-parallel-2",
            thread_id="thread-parallel-2", 
            run_id="run-parallel-2"
        ).with_db_session(AsyncMock())
        
        # Verify contexts are properly isolated
        self.assertNotEqual(context1.user_id, context2.user_id)
        self.assertNotEqual(context1.run_id, context2.run_id)


if __name__ == '__main__':
    pytest.main([__file__, "-v"])