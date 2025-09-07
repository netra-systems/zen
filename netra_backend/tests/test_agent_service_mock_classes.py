"""Mock classes for agent service testing.

This module provides mock classes and enums for testing agent services.

DEPRECATED: Mock classes in this module are deprecated. 
Use test_framework.ssot.mocks.get_mock_factory() instead.
"""

import asyncio
import warnings
from enum import Enum
from typing import Dict, Any, Optional
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Import SSOT MockFactory
from test_framework.ssot.mocks import get_mock_factory


class AgentState(Enum):
    """Mock agent state enum."""
    IDLE = "idle"
    ACTIVE = "active"
    RUNNING = "running"
    ERROR = "error"
    RECOVERING = "recovering"


class MockAgent:
    """DEPRECATED: Use get_mock_factory().create_agent_mock() instead."""
    
    def __init__(self, agent_id: str = "test_agent", user_id: str = None):
        warnings.warn(
            "MockAgent is deprecated. Use get_mock_factory().create_agent_mock() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Delegate to SSOT MockFactory
        factory = get_mock_factory()
        factory_mock = factory.create_agent_mock(agent_id=agent_id, user_id=user_id)
        
        # Copy factory mock attributes for backward compatibility
        self.agent_id = agent_id
        self.user_id = user_id
        self.state = AgentState.IDLE
        self.error_count = 0
        self.last_error = None
        self.should_fail = False
        self.failure_message = "Test failure"
        self.execution_time = 0.1
        self.thread_id = None
        self.db_session = None
        
        # Copy all factory mock methods
        self.initialize = factory_mock.initialize
        self.process_request = factory_mock.process_request
        self.cleanup = factory_mock.cleanup
        self.run = factory_mock.run
        self.recover = factory_mock.recover
        self.get_state = factory_mock.get_state
        self.set_state = factory_mock.set_state
        self.execute_tool = factory_mock.execute_tool


class MockOrchestrator:
    """DEPRECATED: Use get_mock_factory().create_orchestrator_mock() instead."""
    
    def __init__(self):
        warnings.warn(
            "MockOrchestrator is deprecated. Use get_mock_factory().create_orchestrator_mock() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Delegate to SSOT MockFactory
        factory = get_mock_factory()
        factory_mock = factory.create_orchestrator_mock()
        
        # Copy factory mock attributes for backward compatibility
        self.agents = factory_mock.agents
        self.agent_pool = factory_mock.agent_pool
        self.error_threshold = factory_mock.error_threshold
        self.recovery_timeout = factory_mock.recovery_timeout
        self.retry_delay = factory_mock.retry_delay
        self.execution_timeout = factory_mock.execution_timeout
        self.max_concurrent_agents = factory_mock.max_concurrent_agents
        self.max_pool_size = factory_mock.max_pool_size
        self.metrics = factory_mock.metrics
        self._active_agents_override = factory_mock._active_agents_override
        
        # Copy all factory mock methods
        self.get_or_create_agent = factory_mock.get_or_create_agent
        self.execute_agent_task = factory_mock.execute_agent_task
        self.handle_agent_error = factory_mock.handle_agent_error
        self.release_agent = factory_mock.release_agent
        self.get_orchestration_metrics = factory_mock.get_orchestration_metrics
    # NOTE: All methods now delegated to SSOT MockFactory - old implementations removed