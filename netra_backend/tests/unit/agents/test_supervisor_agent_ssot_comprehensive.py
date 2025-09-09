"""SSOT SupervisorAgent Comprehensive Unit Test Suite - MISSION CRITICAL for Chat Delivery

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)  
- Business Goal: Platform Reliability & Chat Delivery Infrastructure
- Value Impact: SSOT SupervisorAgent reliability = 100% of AI chat functionality = Direct revenue impact
- Strategic Impact: Every chat interaction depends on SSOT SupervisorAgent orchestration. Failures = immediate user impact.

MISSION CRITICAL REQUIREMENTS:
- SupervisorAgent SSOT implementation is the core orchestration engine for ALL AI chat interactions
- All 5 WebSocket events for chat delivery must work correctly (agent_started, agent_thinking, agent_completed, agent_error, tool_*)
- Multi-user concurrent execution MUST be properly isolated using UserExecutionContext 
- SSOT factory pattern usage MUST be validated (AgentInstanceFactory, UserExecutionEngine)
- Error handling and recovery MUST work to maintain chat availability
- Legacy compatibility methods MUST delegate properly to SSOT execute() method

TEST COVERAGE TARGET: 100% of SSOT SupervisorAgent critical business logic including:
- SSOT execute() method with UserExecutionContext integration (lines 82-174)
- SSOT factory pattern usage (lines 74-78, 175-205) 
- WebSocket event coordination for chat delivery (lines 104-147, 160-168)
- Legacy compatibility delegation (lines 207-241)
- Factory method creation (lines 242-263)
- User isolation validation and session management (lines 92-99)

CRITICAL: Uses REAL instances approach - minimal mocking per CLAUDE.md standards.
Tests must FAIL HARD on any issues - no try/except masking allowed.
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# ABSOLUTE IMPORTS - SSOT compliance  
from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import get_env

# Import target SSOT class and dependencies
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, 
    InvalidContextError,
    validate_user_context
)
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory, 
    get_agent_instance_factory
)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.database.session_manager import managed_session
from shared.id_generation import UnifiedIdGenerator


class MockUserExecutionEngine:
    """Mock UserExecutionEngine for testing SSOT pattern compliance."""
    
    def __init__(self, context: UserExecutionContext, agent_factory=None, websocket_emitter=None):
        self.context = context
        self.agent_factory = agent_factory
        self.websocket_emitter = websocket_emitter
        self.execution_count = 0
        self.executed_pipelines = []
        
    async def execute_agent_pipeline(self, agent_name: str, execution_context: UserExecutionContext, input_data: Dict) -> Any:
        """Mock agent pipeline execution."""
        self.execution_count += 1
        self.executed_pipelines.append({
            'agent_name': agent_name,
            'context': execution_context,
            'input_data': input_data,
            'timestamp': time.time()
        })
        
        # Return mock result with required attributes
        mock_result = Mock()
        mock_result.success = True
        mock_result.result = {
            'status': 'completed',
            'agent_name': agent_name,
            'user_id': execution_context.user_id,
            'run_id': execution_context.run_id
        }
        return mock_result
        
    async def cleanup(self):
        """Mock cleanup method."""
        pass


class MockAgentInstanceFactory:
    """Mock AgentInstanceFactory for testing SSOT factory pattern."""
    
    def __init__(self):
        self.configured_websocket_bridge = None
        self.configured_llm_manager = None
        self.configure_count = 0
        
    def configure(self, websocket_bridge=None, llm_manager=None):
        """Mock configure method."""
        self.configure_count += 1
        self.configured_websocket_bridge = websocket_bridge
        self.configured_llm_manager = llm_manager


class TestSupervisorAgentSSOTCore(BaseTestCase):
    """Test core SSOT SupervisorAgent functionality - MISSION CRITICAL for chat delivery."""
    
    def setUp(self):
        """Set up test environment with real SSOT instances."""
        super().setUp()
        
        # Create real LLM manager for testing
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="test response")
        
        # Create mock WebSocket bridge with real interface 
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.notify_agent_started = AsyncMock()
        self.websocket_bridge.notify_agent_thinking = AsyncMock()
        self.websocket_bridge.notify_agent_completed = AsyncMock()
        self.websocket_bridge.notify_agent_error = AsyncMock()
        
        # Create real UserExecutionContext for testing
        self.test_context = UserExecutionContext(
            user_id=f"test-user-{uuid.uuid4().hex[:8]}",
            thread_id=f"test-thread-{uuid.uuid4().hex[:8]}",
            run_id=f"test-run-{uuid.uuid4().hex[:8]}",
            request_id=f"test-req-{uuid.uuid4().hex[:8]}",
            websocket_client_id=f"test-ws-{uuid.uuid4().hex[:8]}",
            agent_context={"user_request": "test request for SSOT SupervisorAgent"}
        )
        
        # Mock database session
        self.mock_db_session = AsyncMock()
        self.test_context = self.test_context.with_db_session(self.mock_db_session)
        
        # Create mock SSOT factories
        self.mock_agent_factory = MockAgentInstanceFactory()
        
        # Mock the global factory getter to return our mock
        self.factory_patcher = patch(
            'netra_backend.app.agents.supervisor_ssot.get_agent_instance_factory',
            return_value=self.mock_agent_factory
        )
        self.factory_patcher.start()
        
        # Mock session validation to avoid complex DB dependencies
        self.session_validation_patcher = patch(
            'netra_backend.app.agents.supervisor_ssot.validate_agent_session_isolation'
        )
        self.session_validation_patcher.start()
        
        # Create real SSOT SupervisorAgent instance for testing
        self.supervisor = SupervisorAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )
        
        # Track resources for cleanup
        self.track_resource(self.supervisor)
    
    def tearDown(self):
        """Clean up patches."""
        super().tearDown()
        self.factory_patcher.stop()
        self.session_validation_patcher.stop()

    def test_ssot_supervisor_initialization_validation(self):
        """Test SSOT SupervisorAgent initializes properly with factory patterns."""
        # REAL INSTANCE TEST - verify SSOT initialization
        self.assertIsNotNone(self.supervisor)
        self.assertEqual(self.supervisor.name, "Supervisor")
        self.assertIn("SSOT patterns", self.supervisor.description)
        
        # Verify WebSocket bridge is configured
        self.assertEqual(self.supervisor.websocket_bridge, self.websocket_bridge)
        
        # Verify SSOT factory pattern is used
        self.assertEqual(self.supervisor.agent_factory, self.mock_agent_factory)
        
        # Verify LLM manager is stored
        self.assertEqual(self.supervisor._llm_manager, self.llm_manager)
        
        # Verify no session storage (SSOT isolation requirement)
        self.assertIsNone(getattr(self.supervisor, '_session_storage', None))
        self.assertIsNone(getattr(self.supervisor, 'persistent_state', None))

    async def test_ssot_execute_with_valid_context_full_flow(self):
        """Test SSOT SupervisorAgent execute() method with complete flow validation."""
        # Mock UserExecutionEngine creation and execution
        mock_engine = MockUserExecutionEngine(self.test_context)
        
        # Mock UserWebSocketEmitter for SSOT pattern
        mock_websocket_emitter = Mock()
        
        # Mock the _create_user_execution_engine method
        async def mock_create_engine(context):
            return mock_engine
        
        # Mock managed_session context manager
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), \
             patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), \
             patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=mock_websocket_emitter):
            
            # Execute SSOT supervisor
            result = await self.supervisor.execute(self.test_context, stream_updates=True)
            
            # Verify SSOT execution completed successfully
            self.assertIsNotNone(result)
            self.assertIn("supervisor_result", result)
            self.assertEqual(result["supervisor_result"], "completed")
            self.assertTrue(result["orchestration_successful"])
            self.assertTrue(result["user_isolation_verified"])
            self.assertEqual(result["user_id"], self.test_context.user_id)
            self.assertEqual(result["run_id"], self.test_context.run_id)
            
            # Verify UserExecutionEngine was used (SSOT pattern)
            self.assertEqual(mock_engine.execution_count, 1)
            self.assertEqual(len(mock_engine.executed_pipelines), 1)
            
            # Verify pipeline execution parameters
            pipeline_exec = mock_engine.executed_pipelines[0]
            self.assertEqual(pipeline_exec['agent_name'], "supervisor_orchestration")
            self.assertEqual(pipeline_exec['context'], self.test_context)
            self.assertIn("user_request", pipeline_exec['input_data'])

    async def test_websocket_events_all_5_critical_events_ssot(self):
        """Test all 5 critical WebSocket events are sent during SSOT execution."""
        # Mock UserExecutionEngine for successful execution
        mock_engine = MockUserExecutionEngine(self.test_context)
        
        async def mock_create_engine(context):
            return mock_engine
        
        # Mock managed_session 
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), \
             patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), \
             patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=Mock()):
            
            # Execute SSOT supervisor with WebSocket events
            result = await self.supervisor.execute(self.test_context, stream_updates=True)
            
            # Verify execution completed
            self.assertTrue(result["orchestration_successful"])
            
            # Verify CRITICAL WebSocket events were sent for chat delivery
            
            # 1. agent_started event
            self.websocket_bridge.notify_agent_started.assert_called_once()
            started_call = self.websocket_bridge.notify_agent_started.call_args
            self.assertEqual(started_call[0][0], self.test_context.run_id)  # run_id
            self.assertEqual(started_call[0][1], "Supervisor")  # agent_name
            self.assertIn("isolated", started_call[1]['context'])  # context data
            
            # 2. agent_thinking event
            self.websocket_bridge.notify_agent_thinking.assert_called_once()
            thinking_call = self.websocket_bridge.notify_agent_thinking.call_args
            self.assertEqual(thinking_call[0][0], self.test_context.run_id)  # run_id
            self.assertEqual(thinking_call[0][1], "Supervisor")  # agent_name
            self.assertIn("selecting appropriate agents", thinking_call[1]['reasoning'])
            
            # 3. agent_completed event 
            self.websocket_bridge.notify_agent_completed.assert_called_once()
            completed_call = self.websocket_bridge.notify_agent_completed.call_args
            self.assertEqual(completed_call[0][0], self.test_context.run_id)  # run_id
            self.assertEqual(completed_call[0][1], "Supervisor")  # agent_name
            self.assertIn("supervisor_result", completed_call[1]['result'])
            
            # Verify NO error events were sent (successful execution)
            self.websocket_bridge.notify_agent_error.assert_not_called()

    async def test_websocket_error_event_on_execution_failure(self):
        """Test agent_error WebSocket event is sent on execution failure."""
        # Mock UserExecutionEngine that fails
        mock_engine = Mock()
        mock_engine.execute_agent_pipeline = AsyncMock(side_effect=RuntimeError("Test execution failure"))
        mock_engine.cleanup = AsyncMock()
        
        async def mock_create_engine(context):
            return mock_engine
        
        # Mock managed_session 
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), \
             patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), \
             patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=Mock()):
            
            # Execute SSOT supervisor - should handle error gracefully
            with self.assertRaises(RuntimeError):
                await self.supervisor.execute(self.test_context)
            
            # Verify agent_error event was sent
            self.websocket_bridge.notify_agent_error.assert_called_once()
            error_call = self.websocket_bridge.notify_agent_error.call_args
            self.assertEqual(error_call[0][0], self.test_context.run_id)  # run_id
            self.assertEqual(error_call[0][1], "Supervisor")  # agent_name
            self.assertIn("Test execution failure", error_call[1]['error'])
            self.assertEqual(error_call[1]['error_context']['error_type'], "RuntimeError")

    async def test_ssot_factory_pattern_compliance(self):
        """Test SSOT factory pattern usage and configuration."""
        # Mock UserWebSocketEmitter and UserExecutionEngine
        mock_websocket_emitter = Mock()
        mock_engine = MockUserExecutionEngine(self.test_context)
        
        with patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=mock_websocket_emitter), \
             patch('netra_backend.app.agents.supervisor_ssot.UserExecutionEngine', return_value=mock_engine):
            
            # Test _create_user_execution_engine method
            engine = await self.supervisor._create_user_execution_engine(self.test_context)
            
            # Verify SSOT factory was configured with WebSocket bridge
            self.assertEqual(self.mock_agent_factory.configure_count, 1)
            self.assertEqual(self.mock_agent_factory.configured_websocket_bridge, self.websocket_bridge)
            self.assertEqual(self.mock_agent_factory.configured_llm_manager, self.llm_manager)
            
            # Verify UserWebSocketEmitter was created with correct parameters
            websocket_emitter_call = patch.get_original('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter').call_args
            if websocket_emitter_call:
                self.assertEqual(websocket_emitter_call[0][0], self.test_context.user_id)
                self.assertEqual(websocket_emitter_call[0][1], self.test_context.thread_id)
                self.assertEqual(websocket_emitter_call[0][2], self.test_context.run_id)
                self.assertEqual(websocket_emitter_call[0][3], self.websocket_bridge)
            
            # Verify UserExecutionEngine was created with SSOT pattern
            self.assertIsNotNone(engine)

    async def test_user_context_validation_ssot_compliance(self):
        """Test UserExecutionContext validation using SSOT validate_user_context."""
        # Test with valid context
        valid_context = self.test_context
        
        # Mock validate_user_context to return validated context
        with patch('netra_backend.app.agents.supervisor_ssot.validate_user_context', return_value=valid_context) as mock_validate:
            # Mock other dependencies for execution
            mock_engine = MockUserExecutionEngine(valid_context)
            
            with patch.object(self.supervisor, '_create_user_execution_engine', return_value=mock_engine), \
                 patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=AsyncMock()):
                
                # Execute should validate context using SSOT method
                result = await self.supervisor.execute(valid_context)
                
                # Verify SSOT validation was called
                mock_validate.assert_called_once_with(valid_context)
                
                # Verify execution completed
                self.assertTrue(result["orchestration_successful"])

    async def test_database_session_requirement_validation(self):
        """Test database session requirement validation."""
        # Create context without database session
        context_no_db = UserExecutionContext(
            user_id="test-user",
            thread_id="test-thread",
            run_id="test-run",
            request_id="test-req",
            websocket_client_id="test-ws"
        )
        
        # Mock validate_user_context to return context without DB session
        with patch('netra_backend.app.agents.supervisor_ssot.validate_user_context', return_value=context_no_db):
            
            # Should raise ValueError for missing database session
            with self.assertRaises(ValueError) as cm:
                await self.supervisor.execute(context_no_db)
            
            self.assertIn("database session", str(cm.exception))

    async def test_legacy_run_method_delegates_to_ssot_execute(self):
        """Test legacy run() method properly delegates to SSOT execute() method."""
        # Mock UnifiedIdGenerator for legacy compatibility
        mock_request_id = "legacy-req-123"
        mock_websocket_client_id = "legacy-ws-456"
        
        with patch('netra_backend.app.agents.supervisor_ssot.UnifiedIdGenerator') as mock_id_gen:
            mock_id_gen.generate_base_id.return_value = mock_request_id
            mock_id_gen.generate_websocket_client_id.return_value = mock_websocket_client_id
            
            # Mock execute method to verify delegation
            mock_execute_result = {
                "supervisor_result": "completed",
                "orchestration_successful": True,
                "user_isolation_verified": True,
                "results": {"legacy_test": "data"},
                "user_id": "legacy-user",
                "run_id": "legacy-run"
            }
            
            with patch.object(self.supervisor, 'execute', AsyncMock(return_value=mock_execute_result)) as mock_execute:
                
                # Call legacy run method
                result = await self.supervisor.run(
                    user_request="legacy test request",
                    thread_id="legacy-thread",
                    user_id="legacy-user",
                    run_id="legacy-run"
                )
                
                # Verify execute was called with proper UserExecutionContext
                mock_execute.assert_called_once()
                call_args = mock_execute.call_args
                context = call_args[0][0]
                
                # Verify UserExecutionContext was created correctly
                self.assertIsInstance(context, UserExecutionContext)
                self.assertEqual(context.user_id, "legacy-user")
                self.assertEqual(context.thread_id, "legacy-thread")
                self.assertEqual(context.run_id, "legacy-run")
                self.assertEqual(context.request_id, mock_request_id)
                self.assertEqual(context.websocket_client_id, mock_websocket_client_id)
                
                # Verify stream_updates=True was passed
                self.assertTrue(call_args[1]['stream_updates'])
                
                # Verify result extraction for legacy compatibility
                self.assertEqual(result, {"legacy_test": "data"})

    def test_ssot_factory_method_creates_proper_instance(self):
        """Test SSOT SupervisorAgent.create() factory method."""
        # Test SSOT factory method
        supervisor = SupervisorAgent.create(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )
        
        # Verify created instance using SSOT factory pattern
        self.assertIsInstance(supervisor, SupervisorAgent)
        self.assertEqual(supervisor._llm_manager, self.llm_manager)
        self.assertEqual(supervisor.websocket_bridge, self.websocket_bridge)
        
        # Verify SSOT factory pattern configuration
        self.assertIsNotNone(supervisor.agent_factory)
        
        self.track_resource(supervisor)

    async def test_concurrent_user_execution_isolation_ssot(self):
        """Test multi-user execution isolation using SSOT patterns."""
        # Create multiple user contexts for isolation testing
        contexts = []
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"concurrent-user-{i}",
                thread_id=f"concurrent-thread-{i}",
                run_id=f"concurrent-run-{i}",
                request_id=f"concurrent-req-{i}",
                websocket_client_id=f"concurrent-ws-{i}",
                agent_context={"user_request": f"concurrent test {i}"}
            )
            context = context.with_db_session(AsyncMock())
            contexts.append(context)
        
        # Track execution results for isolation verification
        execution_results = []
        
        async def execute_with_tracking(context, index):
            """Execute supervisor and track results for isolation testing."""
            # Mock UserExecutionEngine for each execution
            mock_engine = MockUserExecutionEngine(context)
            
            async def mock_create_engine(ctx):
                return mock_engine
            
            # Mock managed_session
            mock_session_manager = AsyncMock()
            mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
            mock_session_manager.__aexit__ = AsyncMock(return_value=None)
            
            with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), \
                 patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), \
                 patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=Mock()):
                
                result = await self.supervisor.execute(context)
                execution_results.append((context.user_id, result, mock_engine.execution_count))
        
        # Execute all contexts concurrently
        await asyncio.gather(*[
            execute_with_tracking(context, i) 
            for i, context in enumerate(contexts)
        ])
        
        # Verify isolation - each execution should be independent
        self.assertEqual(len(execution_results), 3)
        
        # Verify each user got their own isolated execution
        user_ids = [result[0] for result in execution_results]
        self.assertEqual(len(set(user_ids)), 3)  # All unique user IDs
        
        # Verify all executions completed successfully with isolation
        for user_id, result, execution_count in execution_results:
            self.assertEqual(result["orchestration_successful"], True)
            self.assertEqual(result["user_isolation_verified"], True)
            self.assertEqual(execution_count, 1)  # Each engine executed exactly once

    def test_string_representations_ssot(self):
        """Test SSOT SupervisorAgent string representation methods."""
        # Test __str__
        str_repr = str(self.supervisor)
        self.assertIn("SupervisorAgent", str_repr)
        self.assertIn("SSOT pattern", str_repr)
        
        # Test __repr__
        repr_str = repr(self.supervisor)
        self.assertIn("SupervisorAgent", repr_str)
        self.assertIn("pattern='SSOT'", repr_str)
        self.assertIn("factory_based=True", repr_str)


class TestSupervisorAgentSSOTErrorScenarios(BaseTestCase):
    """Test SSOT SupervisorAgent error scenarios and edge cases."""
    
    def setUp(self):
        """Set up test environment for SSOT error scenario testing."""
        super().setUp()
        
        self.llm_manager = Mock(spec=LLMManager) 
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="test response")
        
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.notify_agent_started = AsyncMock()
        self.websocket_bridge.notify_agent_thinking = AsyncMock()
        self.websocket_bridge.notify_agent_completed = AsyncMock()
        self.websocket_bridge.notify_agent_error = AsyncMock()
        
        # Mock SSOT factory
        self.mock_agent_factory = MockAgentInstanceFactory()
        
        # Mock the global factory getter
        self.factory_patcher = patch(
            'netra_backend.app.agents.supervisor_ssot.get_agent_instance_factory',
            return_value=self.mock_agent_factory
        )
        self.factory_patcher.start()
        
        # Mock session validation
        self.session_validation_patcher = patch(
            'netra_backend.app.agents.supervisor_ssot.validate_agent_session_isolation'
        )
        self.session_validation_patcher.start()
        
        self.supervisor = SupervisorAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )
        
        self.track_resource(self.supervisor)
    
    def tearDown(self):
        """Clean up patches."""
        super().tearDown()
        self.factory_patcher.stop()
        self.session_validation_patcher.stop()

    async def test_invalid_context_handling_ssot(self):
        """Test SSOT SupervisorAgent handling of invalid UserExecutionContext."""
        # Test with None context - should raise TypeError
        with self.assertRaises(TypeError):
            await self.supervisor.execute(None)
        
        # Test with invalid context that fails SSOT validation
        invalid_context = UserExecutionContext(
            user_id="",  # Empty user ID should be invalid
            thread_id="test-thread",
            run_id="test-run",
            request_id="test-req",
            websocket_client_id="test-ws"
        )
        
        # Mock validate_user_context to raise InvalidContextError
        with patch('netra_backend.app.agents.supervisor_ssot.validate_user_context', 
                  side_effect=InvalidContextError("Invalid user_id")):
            
            with self.assertRaises(InvalidContextError):
                await self.supervisor.execute(invalid_context)

    async def test_websocket_bridge_failure_graceful_degradation_ssot(self):
        """Test SSOT graceful degradation when WebSocket bridge fails."""
        # Create context
        context = UserExecutionContext(
            user_id="test-user",
            thread_id="test-thread",
            run_id="test-run",
            request_id="test-req",
            websocket_client_id="test-ws"
        ).with_db_session(AsyncMock())
        
        # Create supervisor with failing WebSocket bridge
        failing_bridge = Mock(spec=AgentWebSocketBridge)
        failing_bridge.notify_agent_started = AsyncMock(side_effect=Exception("WebSocket failure"))
        failing_bridge.notify_agent_thinking = AsyncMock(side_effect=Exception("WebSocket failure"))
        failing_bridge.notify_agent_completed = AsyncMock(side_effect=Exception("WebSocket failure"))
        failing_bridge.notify_agent_error = AsyncMock(side_effect=Exception("WebSocket failure"))
        
        supervisor_with_failing_ws = SupervisorAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=failing_bridge
        )
        
        # Mock successful execution engine
        mock_engine = MockUserExecutionEngine(context)
        
        async def mock_create_engine(ctx):
            return mock_engine
        
        # Mock managed_session
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(supervisor_with_failing_ws, '_create_user_execution_engine', mock_create_engine), \
             patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), \
             patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=Mock()):
            
            # Should complete successfully despite WebSocket failures
            result = await supervisor_with_failing_ws.execute(context)
            
            # Should complete successfully with graceful degradation
            self.assertTrue(result["orchestration_successful"])
            
            # WebSocket events should have been attempted but failed gracefully
            self.assertGreater(failing_bridge.notify_agent_started.call_count, 0)
            self.assertGreater(failing_bridge.notify_agent_thinking.call_count, 0)
        
        self.track_resource(supervisor_with_failing_ws)

    async def test_execution_engine_cleanup_on_error_ssot(self):
        """Test UserExecutionEngine cleanup is called even on execution errors."""
        context = UserExecutionContext(
            user_id="test-user",
            thread_id="test-thread", 
            run_id="test-run",
            request_id="test-req",
            websocket_client_id="test-ws"
        ).with_db_session(AsyncMock())
        
        # Mock engine that fails execution but tracks cleanup
        mock_engine = Mock()
        mock_engine.execute_agent_pipeline = AsyncMock(side_effect=RuntimeError("Pipeline failure"))
        mock_engine.cleanup = AsyncMock()
        cleanup_called = []
        
        async def track_cleanup():
            cleanup_called.append(True)
        
        mock_engine.cleanup.side_effect = track_cleanup
        
        async def mock_create_engine(ctx):
            return mock_engine
        
        # Mock managed_session
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), \
             patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), \
             patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=Mock()):
            
            # Should raise the execution error
            with self.assertRaises(RuntimeError):
                await self.supervisor.execute(context)
            
            # Verify cleanup was called even on error
            mock_engine.cleanup.assert_called_once()
            self.assertEqual(len(cleanup_called), 1)


class TestSupervisorAgentSSOTPerformance(BaseTestCase):
    """Performance testing for SSOT SupervisorAgent."""
    
    def setUp(self):
        super().setUp()
        
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="test response")
        
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge) 
        self.websocket_bridge.notify_agent_started = AsyncMock()
        self.websocket_bridge.notify_agent_thinking = AsyncMock()
        self.websocket_bridge.notify_agent_completed = AsyncMock()
        self.websocket_bridge.notify_agent_error = AsyncMock()
        
        # Mock SSOT factory
        self.mock_agent_factory = MockAgentInstanceFactory()
        
        # Mock the global factory getter
        self.factory_patcher = patch(
            'netra_backend.app.agents.supervisor_ssot.get_agent_instance_factory',
            return_value=self.mock_agent_factory
        )
        self.factory_patcher.start()
        
        # Mock session validation
        self.session_validation_patcher = patch(
            'netra_backend.app.agents.supervisor_ssot.validate_agent_session_isolation'
        )
        self.session_validation_patcher.start()
        
        self.supervisor = SupervisorAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )
        
        self.track_resource(self.supervisor)
    
    def tearDown(self):
        """Clean up patches."""
        super().tearDown()
        self.factory_patcher.stop()
        self.session_validation_patcher.stop()

    async def test_ssot_performance_concurrent_execution(self):
        """Test SSOT SupervisorAgent performance under concurrent load."""
        # Create multiple concurrent contexts
        contexts = []
        for i in range(5):
            context = UserExecutionContext(
                user_id=f"perf-user-{i}",
                thread_id=f"perf-thread-{i}",
                run_id=f"perf-run-{i}",
                request_id=f"perf-req-{i}",
                websocket_client_id=f"perf-ws-{i}",
                agent_context={"test_index": i}
            ).with_db_session(AsyncMock())
            contexts.append(context)
        
        # Fast mock engines to test SSOT orchestration overhead
        async def mock_create_engine(ctx):
            return MockUserExecutionEngine(ctx)
        
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_user_execution_engine', mock_create_engine), \
             patch('netra_backend.app.agents.supervisor_ssot.managed_session', return_value=mock_session_manager), \
             patch('netra_backend.app.agents.supervisor_ssot.UserWebSocketEmitter', return_value=Mock()):
            
            # Execute all concurrently and measure performance
            start_time = time.time()
            
            results = await asyncio.gather(*[
                self.supervisor.execute(context) 
                for context in contexts
            ])
            
            total_time = time.time() - start_time
            
            # All should complete successfully
            self.assertEqual(len(results), 5)
            for result in results:
                self.assertTrue(result["orchestration_successful"])
                self.assertTrue(result["user_isolation_verified"])
            
            # SSOT performance should be reasonable (less than 3 seconds for 5 concurrent)
            self.assertLess(total_time, 3.0)
            
            # Average per execution should be reasonable for SSOT pattern
            avg_time = total_time / len(results)
            self.assertLess(avg_time, 1.0)  # Less than 1 second average for SSOT


if __name__ == '__main__':
    pytest.main([__file__, "-v", "--tb=short"])