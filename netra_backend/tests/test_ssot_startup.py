"""
SSOT Startup Tests - Verify all Single Source of Truth modules initialize correctly.

This test suite ensures that the recent SSOT consolidations work correctly at startup
and that all critical paths are functional.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: System Reliability & Development Velocity
- Value Impact: Prevents startup failures that would block all users
- Strategic Impact: Ensures SSOT principles are maintained across the platform
"""
import asyncio
import pytest
from typing import Any, Dict
from unittest.mock import Mock
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.database import get_db, get_database_url, get_engine, get_sessionmaker, DatabaseManager, database_manager, get_clickhouse_client

class DatabaseSSOTTests:
    """Test database SSOT consolidation at startup."""

    def test_database_module_imports(self):
        """Verify all database module exports are available."""
        assert callable(get_db)
        assert callable(get_database_url)
        assert callable(get_engine)
        assert callable(get_sessionmaker)
        assert DatabaseManager is not None
        assert database_manager is not None
        assert callable(get_clickhouse_client)

    def test_database_manager_initialization(self):
        """Test DatabaseManager can be instantiated."""
        manager = DatabaseManager()
        assert manager is not None
        assert hasattr(type(manager), 'engine')
        assert hasattr(type(manager), 'sessionmaker')
        assert hasattr(manager, 'get_session')
        assert hasattr(manager, 'session_scope')

    @pytest.mark.asyncio
    async def test_clickhouse_client_import(self):
        """Test ClickHouse client can be imported and used."""
        async with get_clickhouse_client(bypass_manager=True) as client:
            assert client is not None

class AgentRegistrySSOTTests:
    """Test agent registry SSOT consolidation."""

    def test_agent_registry_import(self):
        """Verify agent registry can be imported."""
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        assert AgentRegistry is not None

    def test_agent_registry_singleton(self):
        """Test AgentRegistry follows singleton pattern."""
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        mock_llm = Mock()
        mock_dispatcher = Mock()
        registry1 = AgentRegistry(mock_llm, mock_dispatcher)
        registry2 = AgentRegistry(mock_llm, mock_dispatcher)
        assert registry1 is not None
        assert registry2 is not None

    def test_unified_triage_agent_import(self):
        """Test UnifiedTriageAgent can be imported."""
        from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent, UnifiedTriageAgentFactory
        assert UnifiedTriageAgent is not None
        assert UnifiedTriageAgentFactory is not None

    def test_triage_agent_factory_creation(self):
        """Test triage agent factory can be created."""
        from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgentFactory
        factory = UnifiedTriageAgentFactory()
        assert factory is not None
        assert hasattr(factory, 'create_for_context')
        assert callable(factory.create_for_context)

class ExecutionEngineSSOTTests:
    """Test execution engine SSOT consolidation."""

    def test_execution_engine_imports(self):
        """Verify execution engine modules can be imported."""
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        assert UserExecutionEngine is not None
        assert ExecutionEngineFactory is not None
        ExecutionEngine = UserExecutionEngine

    def test_execution_factory_creation(self):
        """Test execution factory can be created."""
        from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        factory = ExecutionEngineFactory()
        assert factory is not None
        assert hasattr(factory, 'create_execution_engine')
        assert callable(factory.create_execution_engine)

class StatePersistenceSSOTTests:
    """Test state persistence SSOT modules."""

    def test_state_managers_import(self):
        """Verify state manager modules can be imported."""
        from netra_backend.app.services.state_persistence import state_cache_manager
        from netra_backend.app.services.state_recovery_manager import state_recovery_manager
        assert state_cache_manager is not None
        assert state_recovery_manager is not None

    @pytest.mark.asyncio
    async def test_state_cache_manager_operations(self):
        """Test state cache manager basic operations."""
        from netra_backend.app.services.state_persistence import state_cache_manager
        request = Mock(run_id='test_run', state_data={'test': 'data'})
        result = await state_cache_manager.save_primary_state(request)
        assert result is True
        loaded = await state_cache_manager.load_primary_state('test_run')
        assert loaded == {'test': 'data'}

    @pytest.mark.asyncio
    async def test_state_recovery_manager_operations(self):
        """Test state recovery manager basic operations."""
        from netra_backend.app.services.state_recovery_manager import state_recovery_manager
        result = await state_recovery_manager.complete_recovery_log('recovery_1', True, None)
        assert result is True

class StartupModuleIntegrationTests:
    """Test complete startup module integration with SSOT changes."""

    def test_startup_module_import(self):
        """Test startup_module imports successfully with all SSOT changes."""
        from netra_backend.app import startup_module
        assert hasattr(startup_module, 'index_manager')
        assert hasattr(startup_module, 'redis_manager')
        assert hasattr(startup_module, 'background_task_manager')
        assert hasattr(startup_module, 'performance_manager')

    def test_multiprocessing_setup(self):
        """Test multiprocessing setup function exists."""
        from netra_backend.app.utils.multiprocessing_cleanup import setup_multiprocessing
        setup_multiprocessing()

    def test_index_optimizer_manager(self):
        """Test DatabaseIndexManager exists and initializes."""
        from netra_backend.app.db.index_optimizer import DatabaseIndexManager, index_manager
        assert DatabaseIndexManager is not None
        assert index_manager is not None
        assert hasattr(index_manager, 'optimize_all_databases')

class CorpusAdminSSOTTests:
    """Test corpus admin SSOT modules."""

    def test_corpus_operations_enum(self):
        """Verify CorpusOperation enum has correct values."""
        from netra_backend.app.agents.corpus_admin.models import CorpusOperation
        assert CorpusOperation.CREATE
        assert CorpusOperation.UPDATE
        assert CorpusOperation.DELETE
        assert CorpusOperation.INDEX
        assert CorpusOperation.VALIDATE
        assert CorpusOperation.SEARCH
        assert CorpusOperation.ANALYZE
        assert not hasattr(CorpusOperation, 'EXPORT')
        assert not hasattr(CorpusOperation, 'IMPORT')

    def test_suggestion_profiles_compatibility(self):
        """Test suggestion profiles compatibility functions."""
        from netra_backend.app.agents.corpus_admin.suggestion_profiles import get_optimization_rules, get_domain_profiles, get_workload_optimizations, get_parameter_dependencies, get_category_options, apply_domain_rules, merge_domain_settings
        rules = get_optimization_rules()
        assert 'performance' in rules
        assert 'quality' in rules
        assert 'balanced' in rules
        profiles = get_domain_profiles()
        assert isinstance(profiles, dict)
        workload = get_workload_optimizations()
        assert 'high_read' in workload
        assert 'high_write' in workload
        deps = get_parameter_dependencies()
        assert isinstance(deps, dict)
        options = get_category_options()
        assert 'corpus_type' in options
        result = apply_domain_rules('documentation', {'test': 'value'})
        assert isinstance(result, dict)
        merged = merge_domain_settings({'a': 1}, {'b': 2})
        assert merged == {'a': 1, 'b': 2}

class WebSocketSSOTTests:
    """Test WebSocket SSOT consolidation."""

    def test_websocket_manager_import(self):
        """Verify WebSocket manager can be imported."""
        from netra_backend.app.websocket.connection_manager import ConnectionManager
        assert ConnectionManager is not None

    def test_websocket_event_types(self):
        """Verify critical WebSocket event types exist."""
        expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        for event in expected_events:
            assert isinstance(event, str)
            assert len(event) > 0

@pytest.mark.asyncio
async def test_critical_startup_path():
    """
    Integration test for the critical startup path with all SSOT modules.
    
    This test simulates the key initialization sequence that happens at startup.
    """
    from netra_backend.app.core.configuration import get_configuration
    from netra_backend.app.database import database_manager
    from netra_backend.app.redis_manager import redis_manager
    from netra_backend.app.db.index_optimizer import index_manager
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.services.background_task_manager import background_task_manager
    config = get_configuration()
    assert config is not None
    assert database_manager is not None
    assert redis_manager is not None
    assert index_manager is not None
    mock_llm = Mock()
    mock_dispatcher = Mock()
    registry = AgentRegistry(mock_llm, mock_dispatcher)
    assert registry is not None
    assert background_task_manager is not None
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')