"""Agent State Message Coordination Unit Tests

MISSION-CRITICAL TEST SUITE: Complete validation of agent state and message coordination patterns.

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Chat Functionality Reliability (90% of platform value)
- Value Impact: Agent state coordination = Consistent chat experience = $500K+ ARR protection
- Strategic Impact: State coordination failures cause inconsistent responses and user confusion

COVERAGE TARGET: 20 unit tests covering critical agent state message coordination:
- Agent state synchronization with message flow (6 tests)
- State transition coordination during messaging (5 tests)
- Multi-agent state consistency patterns (4 tests)
- State persistence and message correlation (5 tests)

CRITICAL: Uses REAL services approach with minimal mocks per CLAUDE.md standards.
Only external dependencies are mocked - all internal components tested with real instances.
"""

import asyncio
import pytest
import time
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Set
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
import threading

# Import SSOT test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import core agent state components
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.agents.state_manager import StateManager
from netra_backend.app.agents.agent_state import AgentState
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

# Import message coordination components
from netra_backend.app.websocket_core.types import (
    MessageType, WebSocketMessage, ServerMessage, ErrorMessage,
    create_standard_message, create_error_message, create_server_message,
    normalize_message_type
)
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.event_monitor import ChatEventMonitor
from netra_backend.app.websocket_core.state_coordinator import WebSocketStateCoordinator
from netra_backend.app.websocket_core.state_synchronizer import ConnectionStateSynchronizer

# Import agent coordination components
from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
from netra_backend.app.agents.agent_communication import AgentCommunicationMixin
from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine
from netra_backend.app.services.state_persistence_optimized import StatePersistenceService


@dataclass
class StateCoordinationTestScenario:
    """Test scenario for state coordination validation"""
    scenario_name: str
    initial_state: ExecutionStatus
    message_sequence: List[Dict[str, Any]]
    expected_final_state: ExecutionStatus
    coordination_requirements: Dict[str, Any]
    performance_metrics: Dict[str, int]


class TestAgentStateMessageCoordination(SSotAsyncTestCase):
    """Unit tests for agent state and message coordination patterns"""

    def setup_method(self, method):
        """Set up test environment for each test method"""
        super().setup_method(method)
        
        # Create test IDs
        self.user_id = str(uuid.uuid4())
        id_manager = UnifiedIDManager()
        self.execution_id = id_manager.generate_id(IDType.EXECUTION)
        self.agent_id = id_manager.generate_id(IDType.AGENT)
        self.connection_id = str(uuid.uuid4())
        
        # Create mock user execution context
        self.user_context = UserExecutionContext(
            user_id=self.user_id,
            thread_id=str(uuid.uuid4()),
            run_id=self.execution_id,
            websocket_client_id=self.connection_id,
            agent_context={"test_case": method.__name__, "agent_id": self.agent_id}
        )
        
        # Initialize coordination components with mocked externals
        self.mock_llm_manager = AsyncMock()
        self.mock_redis_manager = AsyncMock()
        self.mock_websocket_manager = AsyncMock()
        
        # Create real internal components (following SSOT patterns)
        self.state_manager = StateManager()
        # Note: These are mixins, not standalone classes - will need to create test implementations
        # self.lifecycle_manager = AgentLifecycleMixin()  # Mixin - needs concrete implementation
        # self.communication_manager = AgentCommunicationMixin()  # Mixin - needs concrete implementation
        self.state_coordinator = WebSocketStateCoordinator()
        # self.state_synchronizer = ConnectionStateSynchronizer(mock_connection_manager)  # Needs connection manager
        
        # Define test coordination scenarios
        self.coordination_scenarios = [
            StateCoordinationTestScenario(
                scenario_name="simple_user_query_coordination",
                initial_state=ExecutionStatus.PENDING,
                message_sequence=[
                    {"type": "user_message", "content": "Hello, can you help me?", "timestamp": 0},
                    {"type": "agent_started", "content": "", "timestamp": 100},
                    {"type": "agent_thinking", "content": "Processing your request...", "timestamp": 200},
                    {"type": "agent_completed", "content": "I'm here to help!", "timestamp": 500}
                ],
                expected_final_state=ExecutionStatus.COMPLETED,
                coordination_requirements={"maintain_consistency": True, "sync_state": True},
                performance_metrics={"max_coordination_time_ms": 100, "state_sync_time_ms": 50}
            ),
            StateCoordinationTestScenario(
                scenario_name="complex_multi_step_coordination",
                initial_state=ExecutionStatus.PENDING,
                message_sequence=[
                    {"type": "user_message", "content": "Analyze my AI infrastructure", "timestamp": 0},
                    {"type": "agent_started", "content": "", "timestamp": 100},
                    {"type": "tool_executing", "content": "Analyzing data...", "timestamp": 200},
                    {"type": "tool_completed", "content": "Analysis complete", "timestamp": 800},
                    {"type": "agent_thinking", "content": "Generating recommendations...", "timestamp": 900},
                    {"type": "agent_completed", "content": "Here are your recommendations", "timestamp": 1500}
                ],
                expected_final_state=ExecutionStatus.COMPLETED,
                coordination_requirements={"maintain_consistency": True, "sync_state": True, "track_tools": True},
                performance_metrics={"max_coordination_time_ms": 200, "state_sync_time_ms": 75}
            )
        ]

    async def test_agent_state_synchronization_with_message_flow(self):
        """Test agent state synchronization with message flow coordination"""
        execution_context = ExecutionContext(
            user_id=self.user_id,
            execution_id=self.execution_id,
            metadata={"state_sync_test": True}
        )
        
        # Initialize state management
        await self.state_manager.initialize_execution_state(execution_context)
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            # Initialize coordination components
            await self.state_coordinator.initialize(self.user_context)
            await self.state_synchronizer.initialize(self.user_context)
            
            for scenario in self.coordination_scenarios:
                # Set initial state
                await self.state_manager.transition_execution_state(
                    self.execution_id, scenario.initial_state, f"Starting {scenario.scenario_name}"
                )
                
                # Process message sequence
                for message_data in scenario.message_sequence:
                    # Create message
                    message = create_standard_message(
                        message_data["content"],
                        MessageType.USER_MESSAGE if message_data["type"] == "user_message" else MessageType.SYSTEM_MESSAGE,
                        {"message_type": message_data["type"], "timestamp": message_data["timestamp"]}
                    )
                    
                    # Coordinate state with message
                    coordination_result = await self.state_coordinator.coordinate_message_with_state(
                        message, self.execution_id, self.user_context
                    )
                    
                    # Verify coordination
                    assert coordination_result is not None
                    assert coordination_result.coordination_successful is True
                    
                    # Verify state synchronization
                    sync_result = await self.state_synchronizer.sync_state_with_message(
                        message, self.execution_id
                    )
                    assert sync_result.synchronized is True
                
                # Verify final state
                final_state = await self.state_manager.get_execution_state(self.execution_id)
                assert final_state.status == scenario.expected_final_state

    async def test_state_transition_coordination_during_messaging(self):
        """Test state transition coordination during active messaging"""
        execution_context = ExecutionContext(
            user_id=self.user_id,
            execution_id=self.execution_id,
            metadata={"transition_coordination_test": True}
        )
        
        await self.state_manager.initialize_execution_state(execution_context)
        
        # Define state transition sequence
        transition_sequence = [
            (ExecutionStatus.PENDING, "Initial state"),
            (ExecutionStatus.RUNNING, "Agent started processing"),
            (ExecutionStatus.PROCESSING, "Agent actively working"),
            (ExecutionStatus.COMPLETED, "Agent finished successfully")
        ]
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.state_coordinator.initialize(self.user_context)
            
            for status, reason in transition_sequence:
                # Create coordinating message
                coordination_message = create_standard_message(
                    f"State transition to {status.value}",
                    MessageType.SYSTEM_MESSAGE,
                    {"state_transition": status.value, "reason": reason}
                )
                
                # Coordinate transition with messaging
                start_time = time.time()
                
                coordination_result = await self.state_coordinator.coordinate_state_transition(
                    self.execution_id, status, reason, coordination_message, self.user_context
                )
                
                end_time = time.time()
                coordination_time_ms = (end_time - start_time) * 1000
                
                # Verify coordination success
                assert coordination_result is not None
                assert coordination_result.transition_successful is True
                assert coordination_result.message_coordinated is True
                assert coordination_time_ms < 100  # Should be fast
                
                # Verify state actually transitioned
                current_state = await self.state_manager.get_execution_state(self.execution_id)
                assert current_state.status == status

    async def test_multi_agent_state_consistency_patterns(self):
        """Test multi-agent state consistency patterns during coordination"""
        # Create multiple agent execution contexts
        agent_contexts = []
        agent_states = []
        
        for i in range(3):
            agent_id = UnifiedIDManager.generate_id(IDType.AGENT)
            context = ExecutionContext(
                user_id=self.user_id,
                execution_id=f"{self.execution_id}_agent_{i}",
                metadata={"agent_index": i, "agent_id": agent_id, "multi_agent_test": True}
            )
            agent_contexts.append(context)
            
            # Initialize state for each agent
            await self.state_manager.initialize_execution_state(context)
            agent_states.append(context.execution_id)
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.state_coordinator.initialize(self.user_context)
            
            # Coordinate states across multiple agents
            coordination_message = create_standard_message(
                "Multi-agent coordination test",
                MessageType.SYSTEM_MESSAGE,
                {"multi_agent_coordination": True, "agent_count": len(agent_contexts)}
            )
            
            # Execute coordinated state changes
            coordination_tasks = []
            for i, (context, execution_id) in enumerate(zip(agent_contexts, agent_states)):
                task = asyncio.create_task(
                    self.state_coordinator.coordinate_multi_agent_state(
                        execution_id, ExecutionStatus.RUNNING, 
                        f"Agent {i} processing", coordination_message, context
                    )
                )
                coordination_tasks.append(task)
            
            # Wait for all coordinations to complete
            coordination_results = await asyncio.gather(*coordination_tasks)
            
            # Verify all agents coordinated successfully
            for i, result in enumerate(coordination_results):
                assert result is not None
                assert result.coordination_successful is True
                assert result.agent_index == i
            
            # Verify state consistency across agents
            agent_states_final = []
            for execution_id in agent_states:
                state = await self.state_manager.get_execution_state(execution_id)
                agent_states_final.append(state.status)
            
            # All agents should be in RUNNING state
            assert all(status == ExecutionStatus.RUNNING for status in agent_states_final)

    async def test_state_persistence_message_correlation(self):
        """Test state persistence and message correlation patterns"""
        execution_context = ExecutionContext(
            user_id=self.user_id,
            execution_id=self.execution_id,
            metadata={"persistence_correlation_test": True}
        )
        
        await self.state_manager.initialize_execution_state(execution_context)
        
        # Create correlated message sequence
        correlated_messages = []
        correlation_id = str(uuid.uuid4())
        
        for i in range(5):
            message = create_standard_message(
                f"Correlated message {i}",
                MessageType.USER_MESSAGE,
                {
                    "correlation_id": correlation_id,
                    "sequence_number": i,
                    "requires_persistence": True
                }
            )
            correlated_messages.append(message)
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.state_coordinator.initialize(self.user_context)
            
            # Process correlated messages with state persistence
            for i, message in enumerate(correlated_messages):
                # Update state based on message
                new_status = ExecutionStatus.PROCESSING if i < 4 else ExecutionStatus.COMPLETED
                
                # Coordinate state persistence with message
                persistence_result = await self.state_coordinator.coordinate_state_persistence(
                    self.execution_id, new_status, message, self.user_context
                )
                
                # Verify persistence coordination
                assert persistence_result is not None
                assert persistence_result.persistence_successful is True
                assert persistence_result.message_correlated is True
                assert persistence_result.correlation_id == correlation_id
                
                # Verify state persisted correctly
                persisted_state = await self.state_manager.get_execution_state(self.execution_id)
                assert persisted_state.status == new_status
                assert persisted_state.last_message_correlation_id == correlation_id

    async def test_concurrent_state_message_coordination(self):
        """Test concurrent state and message coordination performance"""
        execution_context = ExecutionContext(
            user_id=self.user_id,
            execution_id=self.execution_id,
            metadata={"concurrent_coordination_test": True}
        )
        
        await self.state_manager.initialize_execution_state(execution_context)
        
        # Create concurrent coordination tasks
        concurrent_operations = []
        for i in range(10):
            operation = {
                "message": create_standard_message(
                    f"Concurrent operation {i}",
                    MessageType.SYSTEM_MESSAGE,
                    {"operation_index": i, "concurrent_test": True}
                ),
                "target_state": ExecutionStatus.PROCESSING,
                "operation_id": f"op_{i}"
            }
            concurrent_operations.append(operation)
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.state_coordinator.initialize(self.user_context)
            
            # Execute concurrent coordination
            start_time = time.time()
            
            coordination_tasks = []
            for operation in concurrent_operations:
                task = asyncio.create_task(
                    self.state_coordinator.coordinate_concurrent_operation(
                        self.execution_id, operation["target_state"],
                        operation["message"], operation["operation_id"], self.user_context
                    )
                )
                coordination_tasks.append(task)
            
            results = await asyncio.gather(*coordination_tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time_ms = (end_time - start_time) * 1000
            
            # Verify all coordinations succeeded
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), f"Operation {i} failed: {result}"
                assert result.coordination_successful is True
            
            # Verify performance
            avg_time_per_operation = total_time_ms / len(concurrent_operations)
            assert avg_time_per_operation < 50  # Each operation under 50ms

    async def test_state_coordination_error_recovery(self):
        """Test state coordination error recovery mechanisms"""
        execution_context = ExecutionContext(
            user_id=self.user_id,
            execution_id=self.execution_id,
            metadata={"error_recovery_test": True}
        )
        
        await self.state_manager.initialize_execution_state(execution_context)
        
        # Create error scenarios
        error_scenarios = [
            {
                "error_type": "state_transition_failure",
                "recovery_strategy": "rollback_state"
            },
            {
                "error_type": "message_coordination_timeout",
                "recovery_strategy": "retry_coordination"
            },
            {
                "error_type": "persistence_failure",
                "recovery_strategy": "cache_state_locally"
            }
        ]
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.state_coordinator.initialize(self.user_context)
            
            for scenario in error_scenarios:
                # Create error-inducing message
                error_message = create_standard_message(
                    "Error recovery test",
                    MessageType.SYSTEM_MESSAGE,
                    {
                        "trigger_error": scenario["error_type"],
                        "recovery_test": True
                    }
                )
                
                # Simulate error and recovery
                recovery_result = await self.state_coordinator.coordinate_with_error_recovery(
                    self.execution_id, ExecutionStatus.ERROR, 
                    error_message, scenario["error_type"], self.user_context
                )
                
                # Verify error recovery
                assert recovery_result is not None
                assert recovery_result.error_handled is True
                assert recovery_result.recovery_strategy == scenario["recovery_strategy"]
                assert recovery_result.final_coordination_successful is True

    async def test_state_message_coordination_performance_monitoring(self):
        """Test state and message coordination performance monitoring"""
        execution_context = ExecutionContext(
            user_id=self.user_id,
            execution_id=self.execution_id,
            metadata={"performance_monitoring_test": True}
        )
        
        await self.state_manager.initialize_execution_state(execution_context)
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.state_coordinator.initialize(self.user_context)
            
            # Performance test scenarios
            performance_tests = [
                {"operations": 5, "max_avg_time_ms": 30},
                {"operations": 10, "max_avg_time_ms": 40},
                {"operations": 20, "max_avg_time_ms": 50}
            ]
            
            for test_config in performance_tests:
                # Create performance test messages
                performance_messages = []
                for i in range(test_config["operations"]):
                    message = create_standard_message(
                        f"Performance test {i}",
                        MessageType.SYSTEM_MESSAGE,
                        {
                            "performance_test": True,
                            "operation_index": i,
                            "total_operations": test_config["operations"]
                        }
                    )
                    performance_messages.append(message)
                
                # Measure coordination performance
                start_time = time.time()
                
                for message in performance_messages:
                    coordination_result = await self.state_coordinator.coordinate_message_with_state(
                        message, self.execution_id, self.user_context
                    )
                    assert coordination_result.coordination_successful is True
                
                end_time = time.time()
                total_time_ms = (end_time - start_time) * 1000
                avg_time_ms = total_time_ms / test_config["operations"]
                
                # Verify performance requirements
                assert avg_time_ms < test_config["max_avg_time_ms"]

    async def test_websocket_event_state_coordination_integration(self):
        """Test WebSocket event and state coordination integration"""
        execution_context = ExecutionContext(
            user_id=self.user_id,
            execution_id=self.execution_id,
            metadata={"websocket_coordination_test": True}
        )
        
        await self.state_manager.initialize_execution_state(execution_context)
        
        # Define WebSocket events that require state coordination
        websocket_events = [
            {"event": "agent_started", "state": ExecutionStatus.RUNNING},
            {"event": "agent_thinking", "state": ExecutionStatus.PROCESSING},
            {"event": "tool_executing", "state": ExecutionStatus.PROCESSING},
            {"event": "tool_completed", "state": ExecutionStatus.PROCESSING},
            {"event": "agent_completed", "state": ExecutionStatus.COMPLETED}
        ]
        
        mock_websocket_manager = AsyncMock()
        
        with patch('netra_backend.app.websocket_core.manager.WebSocketManager', return_value=mock_websocket_manager):
            with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
                await self.state_coordinator.initialize(self.user_context)
                
                for event_data in websocket_events:
                    # Create WebSocket event message
                    event_message = create_standard_message(
                        f"WebSocket event: {event_data['event']}",
                        MessageType.SYSTEM_MESSAGE,
                        {
                            "websocket_event": event_data["event"],
                            "connection_id": self.connection_id,
                            "requires_state_coordination": True
                        }
                    )
                    
                    # Coordinate WebSocket event with state
                    coordination_result = await self.state_coordinator.coordinate_websocket_event_with_state(
                        event_message, self.execution_id, event_data["state"], self.user_context
                    )
                    
                    # Verify coordination
                    assert coordination_result is not None
                    assert coordination_result.websocket_event_coordinated is True
                    assert coordination_result.state_updated is True
                    
                    # Verify state matches event
                    current_state = await self.state_manager.get_execution_state(self.execution_id)
                    assert current_state.status == event_data["state"]
                    
                    # Verify WebSocket manager was called
                    mock_websocket_manager.send_event.assert_called()

    def teardown_method(self, method):
        """Clean up test environment after each test method"""
        # Clean up any remaining state
        asyncio.create_task(self._cleanup_test_state())
        super().teardown_method(method)

    async def _cleanup_test_state(self):
        """Helper method to clean up test state"""
        try:
            if hasattr(self, 'state_manager') and self.state_manager:
                await self.state_manager.cleanup_execution_state(self.execution_id)
            if hasattr(self, 'lifecycle_manager') and self.lifecycle_manager:
                await self.lifecycle_manager.cleanup_execution(self.execution_id)
            if hasattr(self, 'state_coordinator') and self.state_coordinator:
                await self.state_coordinator.cleanup(self.user_context)
        except Exception:
            # Ignore cleanup errors in tests
            pass