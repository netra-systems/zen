"""Test WebSocket factory import-time compliance.

Validates that the WebSocket factory bug fix prevents import-time initialization
and enforces proper User Context Architecture patterns.
"""
import pytest
import sys
from unittest.mock import patch
from netra_backend.app.services.user_execution_context import UserExecutionContext

class ImportTimeFactoryComplianceTests:
    """Test suite for WebSocket factory import-time compliance."""

    def test_agent_service_factory_imports_without_error(self):
        """Test that agent_service_factory.py can be imported without WebSocket creation."""
        from netra_backend.app.services.agent_service_factory import get_agent_service
        assert callable(get_agent_service)

    def test_supervisor_agent_imports_without_websocket_bridge(self):
        """Test that SupervisorAgent can be imported and initialized without WebSocket bridge."""
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.llm.llm_manager import LLMManager
        llm_manager = LLMManager()
        supervisor = SupervisorAgent(llm_manager=llm_manager, websocket_bridge=None)
        assert supervisor is not None
        assert supervisor.websocket_bridge is None
        assert supervisor.llm_manager is llm_manager

    def test_websocket_manager_creation_requires_user_context(self):
        """Test that get_websocket_manager enforces user context requirement."""
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
        with pytest.raises(ValueError, match='WebSocket manager creation requires valid UserExecutionContext'):
            get_websocket_manager()
        with pytest.raises(ValueError, match='WebSocket manager creation requires valid UserExecutionContext'):
            get_websocket_manager(user_context=None)

    def test_websocket_manager_creation_with_valid_context(self):
        """Test that get_websocket_manager works with valid UserExecutionContext."""
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
        user_context = UserExecutionContext.from_request(user_id='test-user-123', thread_id='test-thread-456', run_id='test-run-789')
        manager = get_websocket_manager(user_context)
        assert manager is not None
        assert hasattr(manager, 'user_context')
        assert manager.user_context.user_id == 'test-user-123'

    def test_no_import_time_websocket_creation(self):
        """Test that importing modules doesn't trigger WebSocket manager creation."""
        factory_called = []

        def mock_create_websocket_manager(user_context):
            factory_called.append(user_context)
            from unittest.mock import Mock
            return Mock()
        with patch('netra_backend.app.websocket_core.create_websocket_manager', side_effect=mock_create_websocket_manager):
            from netra_backend.app.services.agent_service_factory import get_agent_service
            from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
            assert len(factory_called) == 0, 'WebSocket factory was called during import - this violates architecture'

    def test_agent_service_factory_creates_supervisor_without_websocket(self):
        """Test that agent service factory can create supervisor without WebSocket manager."""
        from netra_backend.app.services.agent_service_factory import _create_supervisor_agent
        from netra_backend.app.llm.llm_manager import LLMManager
        from unittest.mock import Mock
        llm_manager = LLMManager()
        db_session = Mock()
        supervisor = _create_supervisor_agent(db_session, llm_manager)
        assert supervisor is not None
        assert supervisor.websocket_bridge is None
        assert supervisor.llm_manager is llm_manager

    def test_factory_pattern_compliance_validation(self):
        """Test comprehensive factory pattern compliance."""
        from netra_backend.app.services import agent_service_factory
        from netra_backend.app.agents import supervisor_consolidated
        from netra_backend.app.websocket_core import websocket_manager_factory
        assert True
        assert not hasattr(agent_service_factory, 'manager'), 'Global manager found in agent_service_factory'

    def test_lazy_initialization_pattern(self):
        """Test that lazy initialization works correctly."""
        from netra_backend.app.services.agent_service_core import AgentService
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.llm.llm_manager import LLMManager
        llm_manager = LLMManager()
        supervisor = SupervisorAgent(llm_manager=llm_manager)
        agent_service = AgentService(supervisor)
        assert agent_service is not None
        assert agent_service.supervisor is supervisor
        assert supervisor.websocket_bridge is None

    @pytest.mark.asyncio
    async def test_websocket_bridge_initialization_during_execution(self):
        """Test that WebSocket bridge is properly initialized when needed."""
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.websocket_core import create_websocket_manager
        llm_manager = LLMManager()
        supervisor = SupervisorAgent(llm_manager=llm_manager)
        user_context = UserExecutionContext.from_request(user_id='test-user-123', thread_id='test-thread-456', run_id='test-run-789')
        websocket_manager = create_websocket_manager(user_context)
        supervisor.websocket_bridge = AgentWebSocketBridge()
        supervisor.websocket_bridge.websocket_manager = websocket_manager
        assert supervisor.websocket_bridge is not None
        assert supervisor.websocket_bridge.websocket_manager is not None
        assert supervisor.websocket_bridge.websocket_manager.user_context.user_id == 'test-user-123'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')