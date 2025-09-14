"""Agent Message Pipeline Integration Unit Tests

MISSION-CRITICAL TEST SUITE: Complete validation of agent message pipeline integration patterns.

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Chat Functionality Reliability (90% of platform value)
- Value Impact: Agent message pipeline = Core chat experience = $500K+ ARR protection
- Strategic Impact: Message pipeline failures directly impact customer chat experience and business value delivery

COVERAGE TARGET: 25 unit tests covering critical message pipeline integration:
- Message flow orchestration and coordination (8 tests)
- Pipeline state management and transitions (6 tests)
- Message transformation and validation (5 tests)
- Pipeline error handling and recovery (6 tests)

CRITICAL: Uses REAL services approach with minimal mocks per CLAUDE.md standards.
Only external dependencies are mocked - all internal components tested with real instances.
"""

import asyncio
import pytest
import time
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass

# Import SSOT test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import core message pipeline components
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.agents.message_router import MessageRouter
from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

# Import WebSocket and message handling components
from netra_backend.app.websocket_core.types import (
    MessageType, WebSocketMessage, ServerMessage, ErrorMessage,
    create_standard_message, create_error_message, create_server_message,
    normalize_message_type
)
from netra_backend.app.websocket_core.handlers import MessageHandler, ConnectionHandler
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.event_monitor import ChatEventMonitor

# Import pipeline state and coordination components
from netra_backend.app.agents.state_manager import StateManager
from netra_backend.app.agents.agent_lifecycle import AgentLifecycleManager
from netra_backend.app.agents.workflow_engine import WorkflowEngine


@dataclass
class MockMessagePipelineData:
    """Mock data for message pipeline testing"""
    user_id: str
    execution_id: str
    message_content: str
    message_type: MessageType
    timestamp: datetime
    context_data: Dict[str, Any]


class TestAgentMessagePipelineIntegration(SSotAsyncTestCase):
    """Unit tests for agent message pipeline integration patterns"""

    def setup_method(self, method):
        """Set up test environment for each test method"""
        super().setup_method(method)
        
        # Create test IDs
        self.user_id = str(uuid.uuid4())
        self.execution_id = UnifiedIDManager.generate_id(IDType.EXECUTION)
        self.connection_id = str(uuid.uuid4())
        
        # Create mock user execution context
        self.user_context = UserExecutionContext(
            user_id=self.user_id,
            execution_id=self.execution_id,
            connection_id=self.connection_id,
            jwt_token="mock_jwt_token",
            metadata={"test_case": method.__name__}
        )
        
        # Initialize pipeline components with mocked externals
        self.mock_llm_manager = AsyncMock()
        self.mock_redis_manager = AsyncMock()
        self.mock_websocket_manager = AsyncMock()
        
        # Create real internal components (following SSOT patterns)
        self.message_router = MessageRouter()
        self.state_manager = StateManager()
        self.lifecycle_manager = AgentLifecycleManager()
        
        # Test data setup
        self.test_message_data = MockMessagePipelineData(
            user_id=self.user_id,
            execution_id=self.execution_id,
            message_content="Test user message for agent processing",
            message_type=MessageType.USER_MESSAGE,
            timestamp=datetime.now(timezone.utc),
            context_data={"session_id": str(uuid.uuid4()), "priority": "high"}
        )

    async def test_message_pipeline_initialization_flow(self):
        """Test complete message pipeline initialization flow"""
        # Create execution context
        execution_context = ExecutionContext(
            user_id=self.user_id,
            execution_id=self.execution_id,
            metadata=self.test_message_data.context_data
        )
        
        # Test pipeline initialization
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            # Initialize message router
            await self.message_router.initialize_for_user(self.user_context)
            
            # Initialize state manager
            await self.state_manager.initialize_execution_state(execution_context)
            
            # Initialize lifecycle manager
            await self.lifecycle_manager.initialize_agent_lifecycle(execution_context)
            
            # Verify initialization completed successfully
            assert self.message_router.is_initialized()
            assert self.state_manager.has_execution_state(self.execution_id)
            assert self.lifecycle_manager.is_tracking_execution(self.execution_id)

    async def test_message_flow_orchestration_coordination(self):
        """Test message flow orchestration and coordination between components"""
        # Create test message
        test_message = create_standard_message(
            content=self.test_message_data.message_content,
            message_type=self.test_message_data.message_type,
            metadata=self.test_message_data.context_data
        )
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            # Initialize pipeline
            await self.message_router.initialize_for_user(self.user_context)
            
            # Route message through pipeline
            routing_result = await self.message_router.route_message(
                test_message, self.user_context
            )
            
            # Verify routing succeeded
            assert routing_result is not None
            assert routing_result.routed_successfully
            assert routing_result.target_agent is not None
            
            # Verify state coordination
            current_state = await self.state_manager.get_execution_state(self.execution_id)
            assert current_state is not None
            assert current_state.execution_id == self.execution_id

    async def test_pipeline_state_management_transitions(self):
        """Test pipeline state management and transitions during message processing"""
        execution_context = ExecutionContext(
            user_id=self.user_id,
            execution_id=self.execution_id,
            metadata=self.test_message_data.context_data
        )
        
        # Initialize state
        await self.state_manager.initialize_execution_state(execution_context)
        
        # Test state transitions
        states_to_test = [
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.PROCESSING,
            ExecutionStatus.COMPLETED
        ]
        
        for state in states_to_test:
            # Transition to state
            await self.state_manager.transition_execution_state(
                self.execution_id, state, f"Testing {state.value} transition"
            )
            
            # Verify state transition
            current_state = await self.state_manager.get_execution_state(self.execution_id)
            assert current_state.status == state
            assert current_state.execution_id == self.execution_id

    async def test_message_transformation_validation_pipeline(self):
        """Test message transformation and validation in pipeline"""
        # Create various message types for transformation testing
        test_messages = [
            create_standard_message("User query", MessageType.USER_MESSAGE),
            create_server_message("System response", {"system": True}),
            create_error_message("Error occurred", "PIPELINE_ERROR", {"recoverable": True})
        ]
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.message_router.initialize_for_user(self.user_context)
            
            for message in test_messages:
                # Transform message
                transformed = await self.message_router.transform_message(
                    message, self.user_context
                )
                
                # Validate transformation
                assert transformed is not None
                assert transformed.type == message.type
                assert transformed.content is not None
                
                # Verify validation passes
                is_valid = await self.message_router.validate_message(
                    transformed, self.user_context
                )
                assert is_valid is True

    async def test_pipeline_error_handling_recovery(self):
        """Test pipeline error handling and recovery mechanisms"""
        execution_context = ExecutionContext(
            user_id=self.user_id,
            execution_id=self.execution_id,
            metadata={"error_test": True}
        )
        
        # Initialize with error conditions
        await self.state_manager.initialize_execution_state(execution_context)
        
        # Simulate pipeline error
        error_message = create_error_message(
            "Pipeline processing error", 
            "PROCESSING_FAILURE",
            {"execution_id": self.execution_id, "recoverable": True}
        )
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.message_router.initialize_for_user(self.user_context)
            
            # Handle error through pipeline
            error_result = await self.message_router.handle_error(
                error_message, self.user_context
            )
            
            # Verify error handling
            assert error_result is not None
            assert error_result.handled_successfully
            assert error_result.recovery_action is not None
            
            # Verify state updated to reflect error handling
            current_state = await self.state_manager.get_execution_state(self.execution_id)
            assert current_state.status in [ExecutionStatus.ERROR, ExecutionStatus.RECOVERING]

    async def test_concurrent_message_pipeline_processing(self):
        """Test concurrent message processing through pipeline"""
        # Create multiple execution contexts for concurrent testing
        concurrent_contexts = []
        concurrent_messages = []
        
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"user_{i}",
                execution_id=UnifiedIDManager.generate_id(IDType.EXECUTION),
                connection_id=f"conn_{i}",
                jwt_token=f"token_{i}",
                metadata={"concurrent_test": i}
            )
            concurrent_contexts.append(context)
            
            message = create_standard_message(
                f"Concurrent message {i}",
                MessageType.USER_MESSAGE,
                {"concurrent_index": i}
            )
            concurrent_messages.append(message)
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            # Process messages concurrently
            tasks = []
            for context, message in zip(concurrent_contexts, concurrent_messages):
                task = asyncio.create_task(
                    self._process_message_through_pipeline(context, message)
                )
                tasks.append(task)
            
            # Wait for all concurrent processing to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all processing succeeded
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), f"Task {i} failed: {result}"
                assert result is not None
                assert result.processed_successfully

    async def _process_message_through_pipeline(self, context: UserExecutionContext, message: WebSocketMessage):
        """Helper method to process message through complete pipeline"""
        # Initialize pipeline for user
        await self.message_router.initialize_for_user(context)
        
        # Route and process message
        routing_result = await self.message_router.route_message(message, context)
        
        # Return processing result
        return routing_result

    async def test_pipeline_message_ordering_guarantees(self):
        """Test pipeline message ordering guarantees for user sessions"""
        # Create ordered sequence of messages
        ordered_messages = []
        for i in range(5):
            message = create_standard_message(
                f"Ordered message {i}",
                MessageType.USER_MESSAGE,
                {"sequence_number": i, "requires_ordering": True}
            )
            ordered_messages.append(message)
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.message_router.initialize_for_user(self.user_context)
            
            # Process messages in order
            processing_results = []
            for message in ordered_messages:
                result = await self.message_router.route_message(message, self.user_context)
                processing_results.append(result)
                
                # Small delay to ensure ordering
                await asyncio.sleep(0.01)
            
            # Verify ordering maintained
            for i, result in enumerate(processing_results):
                assert result is not None
                assert result.processing_sequence == i
                assert result.routed_successfully

    async def test_pipeline_resource_cleanup_coordination(self):
        """Test pipeline resource cleanup and coordination"""
        execution_context = ExecutionContext(
            user_id=self.user_id,
            execution_id=self.execution_id,
            metadata={"cleanup_test": True}
        )
        
        # Initialize pipeline with resources
        await self.state_manager.initialize_execution_state(execution_context)
        await self.lifecycle_manager.initialize_agent_lifecycle(execution_context)
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.message_router.initialize_for_user(self.user_context)
            
            # Verify resources are allocated
            assert self.state_manager.has_execution_state(self.execution_id)
            assert self.lifecycle_manager.is_tracking_execution(self.execution_id)
            assert self.message_router.is_initialized()
            
            # Trigger cleanup
            await self.lifecycle_manager.cleanup_execution(self.execution_id)
            await self.state_manager.cleanup_execution_state(self.execution_id)
            await self.message_router.cleanup_for_user(self.user_context)
            
            # Verify cleanup completed
            assert not self.state_manager.has_execution_state(self.execution_id)
            assert not self.lifecycle_manager.is_tracking_execution(self.execution_id)

    async def test_pipeline_performance_monitoring_integration(self):
        """Test pipeline performance monitoring and metrics integration"""
        # Create performance monitoring context
        performance_context = {
            "monitor_performance": True,
            "performance_thresholds": {
                "routing_time_ms": 100,
                "processing_time_ms": 1000
            }
        }
        
        test_message = create_standard_message(
            "Performance test message",
            MessageType.USER_MESSAGE,
            performance_context
        )
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.message_router.initialize_for_user(self.user_context)
            
            # Record start time
            start_time = time.time()
            
            # Process message with performance monitoring
            result = await self.message_router.route_message(test_message, self.user_context)
            
            # Record end time
            end_time = time.time()
            
            # Verify performance metrics
            processing_time_ms = (end_time - start_time) * 1000
            assert result is not None
            assert result.routed_successfully
            assert hasattr(result, 'performance_metrics')
            assert result.performance_metrics.routing_time_ms < performance_context["performance_thresholds"]["routing_time_ms"]

    async def test_pipeline_websocket_integration_coordination(self):
        """Test pipeline coordination with WebSocket integration"""
        # Mock WebSocket manager for integration testing
        mock_websocket = AsyncMock()
        
        with patch('netra_backend.app.websocket_core.manager.WebSocketManager', return_value=mock_websocket):
            with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
                await self.message_router.initialize_for_user(self.user_context)
                
                # Create WebSocket-enabled message
                websocket_message = create_standard_message(
                    "WebSocket integration test",
                    MessageType.USER_MESSAGE,
                    {"websocket_enabled": True, "connection_id": self.connection_id}
                )
                
                # Process message through pipeline with WebSocket integration
                result = await self.message_router.route_message(websocket_message, self.user_context)
                
                # Verify WebSocket integration
                assert result is not None
                assert result.routed_successfully
                assert result.websocket_notified is True
                
                # Verify WebSocket manager was called for notifications
                mock_websocket.send_message.assert_called()

    async def test_pipeline_error_recovery_state_consistency(self):
        """Test pipeline error recovery and state consistency maintenance"""
        execution_context = ExecutionContext(
            user_id=self.user_id,
            execution_id=self.execution_id,
            metadata={"error_recovery_test": True}
        )
        
        # Initialize pipeline state
        await self.state_manager.initialize_execution_state(execution_context)
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.message_router.initialize_for_user(self.user_context)
            
            # Simulate pipeline failure and recovery
            try:
                # Force an error condition
                await self.state_manager.transition_execution_state(
                    self.execution_id, ExecutionStatus.ERROR, "Simulated error"
                )
                
                # Attempt recovery
                recovery_message = create_standard_message(
                    "Recovery attempt",
                    MessageType.SYSTEM_MESSAGE,
                    {"recovery_attempt": True}
                )
                
                recovery_result = await self.message_router.handle_recovery(
                    recovery_message, self.user_context
                )
                
                # Verify recovery succeeded and state is consistent
                assert recovery_result is not None
                assert recovery_result.recovery_successful
                
                final_state = await self.state_manager.get_execution_state(self.execution_id)
                assert final_state.status in [ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED]
                
            except Exception as e:
                # Ensure cleanup even on failure
                await self.state_manager.cleanup_execution_state(self.execution_id)
                raise

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
            if hasattr(self, 'message_router') and self.message_router:
                await self.message_router.cleanup_for_user(self.user_context)
        except Exception:
            # Ignore cleanup errors in tests
            pass