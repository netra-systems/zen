"""
Setup fixtures and mock classes for Agent Service orchestration tests.
Provides shared infrastructure for testing agent lifecycle, orchestration, and error handling.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from netra_backend.app import schemas
from netra_backend.app.agents.supervisor_consolidated import (
    SupervisorAgent as Supervisor,
)
from netra_backend.app.core.exceptions_base import NetraException

# Add project root to path
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.thread_service import ThreadService

# Add project root to path


class AgentState(Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    TERMINATED = "terminated"


class MockSupervisorAgent:
    """Mock supervisor agent for testing.
    
    This is a TEST DOUBLE that simulates the SupervisorAgent behavior
    without making actual LLM calls or complex orchestration.
    
    MOCK CAPABILITIES:
    - Simulates agent state transitions
    - Records execution history for verification
    - Configurable execution time and failure modes
    - Thread-safe for concurrent testing
    """
    
    def __init__(self):
        self.state = AgentState.IDLE
        self.user_id = None
        self.thread_id = None
        self.db_session = None
        self.run_history = []
        self.execution_time = 0.1  # Default execution time
        self.should_fail = False
        self.failure_message = "Mock agent failure"
        
    async def run(self, user_request: str, run_id: str, stream_updates: bool = False):
        """Mock agent run method.
        
        SIMULATES: The actual agent.run() without LLM calls
        EXECUTION TIME: Configurable via self.execution_time (default 0.1s)
        FAILURE MODE: Set self.should_fail=True to simulate errors
        
        Returns:
            dict: Simulated agent response with status and metadata
        """
        self.state = AgentState.STARTING
        
        # Simulate startup time
        await asyncio.sleep(0.01)
        self.state = AgentState.RUNNING
        
        try:
            if self.should_fail:
                self.state = AgentState.ERROR
                raise NetraException(self.failure_message)
            
            # Simulate processing time
            await asyncio.sleep(self.execution_time)
            
            # Record run
            run_record = {
                'user_request': user_request,
                'run_id': run_id,
                'stream_updates': stream_updates,
                'timestamp': datetime.now(UTC),
                'user_id': self.user_id,
                'thread_id': self.thread_id
            }
            self.run_history.append(run_record)
            
            self.state = AgentState.IDLE
            return {
                'status': 'completed',
                'response': f'Processed: {user_request}',
                'run_id': run_id,
                'execution_time': self.execution_time
            }
            
        except Exception as e:
            self.state = AgentState.ERROR
            raise
    
    def stop(self):
        """Stop the agent"""
        if self.state == AgentState.RUNNING:
            self.state = AgentState.STOPPING
            # Simulate stop time
            asyncio.create_task(self._complete_stop())
    
    async def _complete_stop(self):
        await asyncio.sleep(0.01)
        self.state = AgentState.TERMINATED


class AgentOrchestrator:
    """Orchestrates multiple agents and their lifecycle.
    
    TEST HELPER CLASS: Manages multiple mock agents for testing
    concurrent scenarios and agent coordination patterns.
    
    This is NOT production code - it's a test utility to verify
    that the real AgentService handles multiple agents correctly.
    """
    
    def __init__(self):
        self.agents = {}  # user_id -> agent_instance
        self.agent_pool = []  # Pool of available agents
        self.max_concurrent_agents = 10
        self.active_agents = 0
        self.orchestration_metrics = {
            'agents_created': 0,
            'agents_destroyed': 0,
            'total_executions': 0,
            'failed_executions': 0,
            'average_execution_time': 0,
            'concurrent_peak': 0
        }
        
    async def get_or_create_agent(self, user_id: str) -> MockSupervisorAgent:
        """Get existing agent or create new one for user"""
        if user_id in self.agents:
            return self.agents[user_id]
        
        if self.active_agents >= self.max_concurrent_agents:
            raise NetraException("Maximum concurrent agents reached")
        
        # Try to get agent from pool
        if self.agent_pool:
            agent = self.agent_pool.pop()
        else:
            agent = MockSupervisorAgent()
            self.orchestration_metrics['agents_created'] += 1
        
        agent.user_id = user_id
        self.agents[user_id] = agent
        self.active_agents += 1
        
        # Update peak concurrent agents
        if self.active_agents > self.orchestration_metrics['concurrent_peak']:
            self.orchestration_metrics['concurrent_peak'] = self.active_agents
        
        return agent
    
    async def release_agent(self, user_id: str):
        """Release agent back to pool"""
        if user_id in self.agents:
            agent = self.agents[user_id]
            
            # Reset agent state
            agent.user_id = None
            agent.thread_id = None
            agent.db_session = None
            agent.state = AgentState.IDLE
            
            # Return to pool if not at capacity
            if len(self.agent_pool) < 5:  # Max pool size
                self.agent_pool.append(agent)
            else:
                self.orchestration_metrics['agents_destroyed'] += 1
            
            del self.agents[user_id]
            self.active_agents -= 1
    
    async def execute_agent_task(self, user_id: str, user_request: str, run_id: str, stream_updates: bool = False):
        """Execute task using orchestrated agent"""
        agent = await self.get_or_create_agent(user_id)
        
        # Increment total executions at the start
        self.orchestration_metrics['total_executions'] += 1
        
        try:
            start_time = datetime.now(UTC)
            result = await agent.run(user_request, run_id, stream_updates)
            execution_time = (datetime.now(UTC) - start_time).total_seconds()
            
            # Update average execution time
            total_execs = self.orchestration_metrics['total_executions']
            current_avg = self.orchestration_metrics['average_execution_time']
            new_avg = ((current_avg * (total_execs - 1)) + execution_time) / total_execs
            self.orchestration_metrics['average_execution_time'] = new_avg
            
            return result
            
        except Exception as e:
            self.orchestration_metrics['failed_executions'] += 1
            raise
    
    def get_orchestration_metrics(self) -> Dict[str, Any]:
        """Get orchestration metrics"""
        return {
            **self.orchestration_metrics,
            'active_agents': self.active_agents,
            'pooled_agents': len(self.agent_pool),
            'success_rate': (
                (self.orchestration_metrics['total_executions'] - 
                 self.orchestration_metrics['failed_executions']) / 
                max(self.orchestration_metrics['total_executions'], 1)
            ) * 100
        }


class AgentServiceTestBase:
    """Base class for agent service tests with common fixtures"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager"""
        manager = MagicMock()
        manager.send_to_thread = AsyncMock()
        manager.broadcast = AsyncMock()
        return manager

    @pytest.fixture
    def mock_supervisor_agent(self):
        """Create mock supervisor agent"""
        return MockSupervisorAgent()

    @pytest.fixture  
    def agent_service(self, mock_supervisor_agent, mock_db_session, mock_websocket_manager):
        """Create AgentService with mocked dependencies"""
        service = AgentService(mock_supervisor_agent)
        service.websocket_manager = mock_websocket_manager
        service.db_session = mock_db_session
        return service

    @pytest.fixture
    def orchestrator(self):
        """Create agent orchestrator for multi-agent tests"""
        return AgentOrchestrator()

    def create_test_request(self, user_id="test_user", query="test query"):
        """Create a test request object"""
        return {
            "user_id": user_id,
            "query": query,
            "workloads": [],
            "constraints": {}
        }

    def assert_agent_execution_completed(self, agent: MockSupervisorAgent, expected_runs=1):
        """Assert that agent execution completed successfully"""
        assert len(agent.run_history) == expected_runs
        assert agent.state == AgentState.IDLE
        for run in agent.run_history:
            assert run['timestamp'] is not None
            assert run['user_request'] is not None

    def assert_orchestration_metrics_valid(self, metrics: Dict[str, Any]):
        """Assert that orchestration metrics are valid"""
        assert metrics['agents_created'] >= 0
        assert metrics['total_executions'] >= 0
        assert metrics['success_rate'] >= 0
        assert metrics['success_rate'] <= 100
        assert metrics['active_agents'] >= 0