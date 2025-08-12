"""
Comprehensive tests for Agent Service orchestration, lifecycle management, and concurrent handling
Tests agent lifecycle, orchestration, concurrent execution, and error recovery
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
from enum import Enum

from app.services.agent_service import AgentService
from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.services.thread_service import ThreadService
from app.services.message_handlers import MessageHandlerService
from app.core.exceptions import NetraException
from app import schemas
from starlette.websockets import WebSocketDisconnect


class AgentState(Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    TERMINATED = "terminated"


class MockSupervisorAgent:
    """Mock supervisor agent for testing"""
    
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
        """Mock agent run method"""
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
                'timestamp': datetime.utcnow(),
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
    """Orchestrates multiple agents and their lifecycle"""
    
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
        
        try:
            start_time = datetime.utcnow()
            result = await agent.run(user_request, run_id, stream_updates)
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Update metrics
            self.orchestration_metrics['total_executions'] += 1
            
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


class TestAgentServiceOrchestration:
    """Test agent service orchestration functionality"""
    
    @pytest.fixture
    def mock_supervisor(self):
        """Create mock supervisor agent"""
        return MockSupervisorAgent()
    
    @pytest.fixture
    def mock_thread_service(self):
        """Create mock thread service"""
        service = MagicMock(spec=ThreadService)
        service.get_or_create_thread = AsyncMock()
        service.get_thread_history = AsyncMock()
        service.create_thread = AsyncMock()
        service.delete_thread = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_message_handler(self):
        """Create mock message handler service"""
        handler = MagicMock(spec=MessageHandlerService)
        handler.handle_start_agent = AsyncMock()
        handler.handle_user_message = AsyncMock()
        handler.handle_thread_history = AsyncMock()
        handler.handle_stop_agent = AsyncMock()
        handler.handle_create_thread = AsyncMock()
        handler.handle_switch_thread = AsyncMock()
        handler.handle_delete_thread = AsyncMock()
        handler.handle_list_threads = AsyncMock()
        return handler
    
    @pytest.fixture
    def agent_service(self, mock_supervisor):
        """Create agent service with mocked dependencies"""
        service = AgentService(mock_supervisor)
        service.message_handler = MagicMock(spec=MessageHandlerService)
        return service
    
    @pytest.mark.asyncio
    async def test_agent_service_initialization(self, mock_supervisor):
        """Test agent service initialization"""
        service = AgentService(mock_supervisor)
        
        assert service.supervisor is mock_supervisor
        assert service.thread_service != None
        assert service.message_handler != None
    
    @pytest.mark.asyncio
    async def test_agent_run_execution(self, agent_service, mock_supervisor):
        """Test agent run execution"""
        # Setup
        request_model = MagicMock()
        request_model.user_request = "Test user request"
        run_id = "test_run_123"
        
        mock_supervisor.run = AsyncMock(return_value={'status': 'completed'})
        
        # Execute
        result = await agent_service.run(request_model, run_id, stream_updates=True)
        
        # Assert
        assert result == {'status': 'completed'}
        mock_supervisor.run.assert_called_once_with("Test user request", run_id, True)
    
    @pytest.mark.asyncio
    async def test_agent_run_with_model_dump_fallback(self, agent_service, mock_supervisor):
        """Test agent run with model dump fallback when user_request not available"""
        # Setup
        request_model = MagicMock()
        del request_model.user_request  # Remove user_request attribute
        request_model.model_dump.return_value = {'query': 'test query'}
        run_id = "test_run_456"
        
        mock_supervisor.run = AsyncMock(return_value={'status': 'completed'})
        
        # Execute
        result = await agent_service.run(request_model, run_id)
        
        # Assert
        mock_supervisor.run.assert_called_once_with("{'query': 'test query'}", run_id, False)
    
    @pytest.mark.asyncio
    async def test_websocket_message_handling_start_agent(self, agent_service):
        """Test WebSocket message handling for start_agent"""
        # Setup
        user_id = "user123"
        message = {
            "type": "start_agent",
            "payload": {"query": "start analysis"}
        }
        
        agent_service.message_handler.handle_start_agent = AsyncMock()
        
        # Execute
        await agent_service.handle_websocket_message(user_id, message)
        
        # Assert
        agent_service.message_handler.handle_start_agent.assert_called_once_with(
            user_id, {"query": "start analysis"}, None
        )
    
    @pytest.mark.asyncio
    async def test_websocket_message_handling_user_message(self, agent_service):
        """Test WebSocket message handling for user_message"""
        # Setup
        user_id = "user456"
        message = {
            "type": "user_message",
            "payload": {"content": "Hello agent"}
        }
        
        agent_service.message_handler.handle_user_message = AsyncMock()
        
        # Execute
        await agent_service.handle_websocket_message(user_id, message)
        
        # Assert
        agent_service.message_handler.handle_user_message.assert_called_once_with(
            user_id, {"content": "Hello agent"}, None
        )
    
    @pytest.mark.asyncio
    async def test_websocket_message_handling_thread_operations(self, agent_service):
        """Test WebSocket message handling for thread operations"""
        user_id = "user789"
        
        # Test different thread operations
        operations = [
            ("thread_history", {}),
            ("create_thread", {"name": "New Thread"}),
            ("switch_thread", {"thread_id": "thread_123"}),
            ("delete_thread", {"thread_id": "thread_456"}),
            ("list_threads", {})
        ]
        
        for message_type, payload in operations:
            message = {"type": message_type, "payload": payload}
            
            # Execute
            await agent_service.handle_websocket_message(user_id, message)
            
            # Assert corresponding handler was called
            handler_method = getattr(agent_service.message_handler, f"handle_{message_type}")
            if payload:
                handler_method.assert_called_with(user_id, payload, None)
            else:
                handler_method.assert_called_with(user_id, None)
    
    @pytest.mark.asyncio
    async def test_websocket_message_handling_stop_agent(self, agent_service):
        """Test WebSocket message handling for stop_agent"""
        user_id = "user999"
        message = {"type": "stop_agent", "payload": {}}
        
        agent_service.message_handler.handle_stop_agent = AsyncMock()
        
        # Execute
        await agent_service.handle_websocket_message(user_id, message)
        
        # Assert
        agent_service.message_handler.handle_stop_agent.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_websocket_message_handling_unknown_type(self, agent_service):
        """Test WebSocket message handling for unknown message type"""
        user_id = "user_unknown"
        message = {"type": "unknown_message_type", "payload": {}}
        
        # Execute (should not raise exception)
        await agent_service.handle_websocket_message(user_id, message)
        
        # Should handle gracefully without calling any specific handler
    
    @pytest.mark.asyncio
    async def test_websocket_message_handling_json_error(self, agent_service):
        """Test WebSocket message handling with JSON decode error"""
        user_id = "user_json_error"
        invalid_message = "invalid json {broken"
        
        with patch('app.ws_manager.manager.send_error') as mock_send_error:
            mock_send_error = AsyncMock()
            
            # Execute
            await agent_service.handle_websocket_message(user_id, invalid_message)
            
            # Should handle JSON error gracefully
    
    @pytest.mark.asyncio
    async def test_websocket_disconnect_handling(self, agent_service):
        """Test handling of WebSocket disconnect during message processing"""
        user_id = "user_disconnect"
        message = {"type": "start_agent", "payload": {}}
        
        # Mock handler to raise WebSocketDisconnect
        agent_service.message_handler.handle_start_agent = AsyncMock(
            side_effect=WebSocketDisconnect()
        )
        
        # Execute (should not raise exception)
        await agent_service.handle_websocket_message(user_id, message)
        
        # Should handle disconnect gracefully
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(self, agent_service, mock_supervisor):
        """Test concurrent agent execution"""
        # Setup multiple concurrent requests
        num_concurrent = 5
        mock_supervisor.run = AsyncMock(return_value={'status': 'completed'})
        
        # Create concurrent tasks
        tasks = []
        for i in range(num_concurrent):
            request_model = MagicMock()
            request_model.user_request = f"Concurrent request {i}"
            task = agent_service.run(request_model, f"run_{i}")
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Assert all completed successfully
        assert len(results) == num_concurrent
        assert all(result['status'] == 'completed' for result in results)
        assert mock_supervisor.run.call_count == num_concurrent
    
    @pytest.mark.asyncio
    async def test_message_parsing_string_input(self, agent_service):
        """Test message parsing with string input"""
        # Test valid JSON string
        json_string = '{"type": "start_agent", "payload": {"query": "test"}}'
        parsed = agent_service._parse_message(json_string)
        
        assert parsed["type"] == "start_agent"
        assert parsed["payload"]["query"] == "test"
    
    @pytest.mark.asyncio
    async def test_message_parsing_dict_input(self, agent_service):
        """Test message parsing with dict input"""
        # Test dict input
        dict_message = {"type": "user_message", "payload": {"content": "hello"}}
        parsed = agent_service._parse_message(dict_message)
        
        assert parsed["type"] == "user_message"
        assert parsed["payload"]["content"] == "hello"


class TestAgentLifecycleManagement:
    """Test agent lifecycle management"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create agent orchestrator"""
        return AgentOrchestrator()
    
    @pytest.mark.asyncio
    async def test_agent_creation_and_assignment(self, orchestrator):
        """Test agent creation and user assignment"""
        # Get agent for user
        agent = await orchestrator.get_or_create_agent("user1")
        
        assert agent != None
        assert agent.user_id == "user1"
        assert orchestrator.active_agents == 1
        assert orchestrator.orchestration_metrics['agents_created'] == 1
    
    @pytest.mark.asyncio
    async def test_agent_reuse_for_same_user(self, orchestrator):
        """Test agent reuse for same user"""
        # Get agent twice for same user
        agent1 = await orchestrator.get_or_create_agent("user1")
        agent2 = await orchestrator.get_or_create_agent("user1")
        
        assert agent1 is agent2
        assert orchestrator.active_agents == 1  # Still only one active
    
    @pytest.mark.asyncio
    async def test_agent_pool_management(self, orchestrator):
        """Test agent pool management"""
        # Create and release agent
        agent = await orchestrator.get_or_create_agent("user1")
        await orchestrator.release_agent("user1")
        
        # Agent should be in pool
        assert len(orchestrator.agent_pool) == 1
        assert orchestrator.active_agents == 0
        
        # Get agent for new user should reuse from pool
        agent2 = await orchestrator.get_or_create_agent("user2")
        assert agent2 is agent
        assert agent2.user_id == "user2"
        assert len(orchestrator.agent_pool) == 0
        assert orchestrator.active_agents == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_limit_enforcement(self, orchestrator):
        """Test enforcement of concurrent agent limits"""
        # Set low limit for testing
        orchestrator.max_concurrent_agents = 3
        
        # Create agents up to limit
        agents = []
        for i in range(3):
            agent = await orchestrator.get_or_create_agent(f"user_{i}")
            agents.append(agent)
        
        assert orchestrator.active_agents == 3
        
        # Try to create one more (should fail)
        with pytest.raises(NetraException) as exc_info:
            await orchestrator.get_or_create_agent("user_overflow")
        
        assert "Maximum concurrent agents reached" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_agent_task_execution_tracking(self, orchestrator):
        """Test agent task execution tracking"""
        # Execute task
        result = await orchestrator.execute_agent_task(
            "user1", "test request", "run_123", True
        )
        
        # Verify result
        assert result['status'] == 'completed'
        assert result['run_id'] == "run_123"
        
        # Verify metrics
        metrics = orchestrator.get_orchestration_metrics()
        assert metrics['total_executions'] == 1
        assert metrics['failed_executions'] == 0
        assert metrics['success_rate'] == 100.0
        assert metrics['average_execution_time'] > 0
    
    @pytest.mark.asyncio
    async def test_agent_task_failure_handling(self, orchestrator):
        """Test agent task failure handling"""
        # Force agent failure
        agent = await orchestrator.get_or_create_agent("user1")
        agent.should_fail = True
        
        # Execute task (should fail)
        with pytest.raises(NetraException):
            await orchestrator.execute_agent_task("user1", "failing request", "run_fail")
        
        # Verify failure metrics
        metrics = orchestrator.get_orchestration_metrics()
        assert metrics['failed_executions'] == 1
        assert metrics['success_rate'] == 0.0
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_orchestration(self, orchestrator):
        """Test concurrent agent orchestration"""
        # Execute multiple tasks concurrently
        num_tasks = 5
        tasks = []
        
        for i in range(num_tasks):
            task = orchestrator.execute_agent_task(
                f"user_{i}", f"concurrent request {i}", f"run_{i}"
            )
            tasks.append(task)
        
        # Execute all concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert len(results) == num_tasks
        assert all(result['status'] == 'completed' for result in results)
        
        # Verify metrics
        metrics = orchestrator.get_orchestration_metrics()
        assert metrics['total_executions'] == num_tasks
        assert metrics['failed_executions'] == 0
        assert metrics['concurrent_peak'] == num_tasks
    
    @pytest.mark.asyncio
    async def test_agent_state_transitions(self, orchestrator):
        """Test agent state transitions during lifecycle"""
        agent = await orchestrator.get_or_create_agent("user1")
        
        # Initial state
        assert agent.state == AgentState.IDLE
        
        # Start execution
        task = asyncio.create_task(
            agent.run("test request", "run_state", False)
        )
        
        # Wait briefly for state change
        await asyncio.sleep(0.02)
        
        # Should be running
        assert agent.state == AgentState.RUNNING
        
        # Wait for completion
        await task
        
        # Should return to idle
        assert agent.state == AgentState.IDLE
    
    def test_orchestration_metrics_calculation(self, orchestrator):
        """Test orchestration metrics calculation"""
        # Simulate some activity
        orchestrator.orchestration_metrics.update({
            'total_executions': 10,
            'failed_executions': 2,
            'agents_created': 5,
            'agents_destroyed': 2,
            'average_execution_time': 0.25,
            'concurrent_peak': 3
        })
        orchestrator.active_agents = 2
        orchestrator.agent_pool = [MagicMock(), MagicMock()]  # 2 in pool
        
        metrics = orchestrator.get_orchestration_metrics()
        
        assert metrics['total_executions'] == 10
        assert metrics['failed_executions'] == 2
        assert metrics['success_rate'] == 80.0  # (10-2)/10 * 100
        assert metrics['active_agents'] == 2
        assert metrics['pooled_agents'] == 2
        assert metrics['concurrent_peak'] == 3


class TestAgentErrorRecovery:
    """Test agent error recovery and resilience"""
    
    @pytest.fixture
    def resilient_orchestrator(self):
        """Create orchestrator with error recovery features"""
        orchestrator = AgentOrchestrator()
        orchestrator.error_recovery_enabled = True
        orchestrator.max_retries = 3
        orchestrator.retry_delay = 0.01  # Fast retry for testing
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_agent_failure_recovery(self, resilient_orchestrator):
        """Test recovery from agent failures"""
        # Get agent and make it fail initially
        agent = await resilient_orchestrator.get_or_create_agent("user1")
        agent.should_fail = True
        agent.failure_message = "Temporary failure"
        
        # Create a recovery mechanism (simplified)
        async def execute_with_retry(user_id, request, run_id):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    return await resilient_orchestrator.execute_agent_task(
                        user_id, request, run_id
                    )
                except NetraException:
                    if attempt == max_retries - 1:
                        raise
                    
                    # Reset agent for retry
                    agent = resilient_orchestrator.agents[user_id]
                    if attempt == 1:  # Second attempt succeeds
                        agent.should_fail = False
                    
                    await asyncio.sleep(resilient_orchestrator.retry_delay)
        
        # Execute with retry
        result = await execute_with_retry("user1", "retry request", "run_retry")
        
        # Should succeed on retry
        assert result['status'] == 'completed'
    
    @pytest.mark.asyncio
    async def test_agent_timeout_handling(self, resilient_orchestrator):
        """Test handling of agent timeouts"""
        # Get agent and make it slow
        agent = await resilient_orchestrator.get_or_create_agent("user1")
        agent.execution_time = 1.0  # 1 second execution
        
        # Execute with timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                resilient_orchestrator.execute_agent_task("user1", "slow request", "run_slow"),
                timeout=0.1  # 100ms timeout
            )
    
    @pytest.mark.asyncio
    async def test_agent_resource_cleanup_on_error(self, resilient_orchestrator):
        """Test resource cleanup when agent encounters errors"""
        # Create agent and set up failure
        agent = await resilient_orchestrator.get_or_create_agent("user1")
        agent.should_fail = True
        
        initial_active = resilient_orchestrator.active_agents
        
        # Execute task that will fail
        with pytest.raises(NetraException):
            await resilient_orchestrator.execute_agent_task("user1", "failing request", "run_cleanup")
        
        # Release agent to trigger cleanup
        await resilient_orchestrator.release_agent("user1")
        
        # Verify cleanup
        assert resilient_orchestrator.active_agents == initial_active - 1
        assert "user1" not in resilient_orchestrator.agents
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, resilient_orchestrator):
        """Test circuit breaker pattern for failing agents"""
        # Simulate circuit breaker
        failure_threshold = 3
        failure_count = 0
        circuit_open = False
        
        async def circuit_breaker_execute(user_id, request, run_id):
            nonlocal failure_count, circuit_open
            
            if circuit_open:
                raise NetraException("Circuit breaker open")
            
            try:
                return await resilient_orchestrator.execute_agent_task(
                    user_id, request, run_id
                )
            except NetraException:
                failure_count += 1
                if failure_count >= failure_threshold:
                    circuit_open = True
                raise
        
        # Make agent fail
        agent = await resilient_orchestrator.get_or_create_agent("user1")
        agent.should_fail = True
        
        # Execute until circuit breaker opens
        for i in range(failure_threshold):
            with pytest.raises(NetraException):
                await circuit_breaker_execute("user1", f"request_{i}", f"run_{i}")
        
        # Circuit should now be open
        assert circuit_open == True
        assert failure_count == failure_threshold
        
        # Next call should fail immediately due to circuit breaker
        with pytest.raises(NetraException) as exc_info:
            await circuit_breaker_execute("user1", "circuit_test", "run_circuit")
        
        assert "Circuit breaker open" in str(exc_info.value)