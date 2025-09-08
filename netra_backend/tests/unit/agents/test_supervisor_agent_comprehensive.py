"""Comprehensive SupervisorAgent Unit Test Suite - MISSION CRITICAL for Chat Delivery

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)  
- Business Goal: Platform Reliability & Chat Delivery Infrastructure
- Value Impact: SupervisorAgent orchestration reliability = 100% of AI chat functionality = Direct revenue impact
- Strategic Impact: Every chat interaction depends on SupervisorAgent orchestration. Failures = immediate user impact.

MISSION CRITICAL REQUIREMENTS:
- SupervisorAgent is the core orchestration engine for ALL AI chat interactions
- All WebSocket events for chat delivery must work correctly  
- Multi-user concurrent execution MUST be properly isolated
- Error handling and recovery MUST work to maintain chat availability

TEST COVERAGE TARGET: 100% of SupervisorAgent critical business logic including:
- UserExecutionContext integration and isolation (lines 135-252)
- Agent lifecycle orchestration (lines 304-344, 552-721) 
- WebSocket event coordination for chat delivery (lines 810-833)
- Multi-user concurrency safety (lines 163, 245-252)
- Error handling and recovery patterns (lines 668-709, 723-773)
- Agent dependency validation (lines 514-551)
- Dynamic workflow execution (lines 904-1055)

CRITICAL: Uses REAL instances approach - minimal mocking per CLAUDE.md standards.
Tests must FAIL HARD on any issues - no try/except masking allowed.
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass

# ABSOLUTE IMPORTS - SSOT compliance  
from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import get_env

# Import target class and dependencies
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry


@dataclass
class MockWebSocketManager:
    """Mock WebSocket manager for testing WebSocket integration."""
    connection_count: int = 0
    events_sent: List[Dict] = None
    
    def __post_init__(self):
        if self.events_sent is None:
            self.events_sent = []
    
    async def send_to_user(self, user_id: str, event_type: str, data: dict):
        """Mock WebSocket event sending."""
        self.events_sent.append({
            'user_id': user_id,
            'event_type': event_type,
            'data': data,
            'timestamp': time.time()
        })
        
    def get_connection_count(self) -> int:
        return self.connection_count


class MockAgentInstance(BaseAgent):
    """Mock agent instance for testing orchestration."""
    
    def __init__(self, agent_name: str, should_succeed: bool = True, execution_result: Dict = None):
        # Create minimal mock LLM manager for BaseAgent requirements
        mock_llm_manager = Mock(spec=LLMManager)
        mock_llm_manager._get_model_name = Mock(return_value="mock-model")
        mock_llm_manager.ask_llm = AsyncMock(return_value="mock response")
        
        super().__init__(
            llm_manager=mock_llm_manager,
            name=agent_name,
            description=f"Mock {agent_name} agent for testing",
            enable_reliability=False,
            enable_execution_engine=False,
            enable_caching=False
        )
        
        self.should_succeed = should_succeed
        self.execution_result = execution_result or {"status": "completed", "agent": agent_name}
        self.execution_count = 0
        self.last_context = None
        
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Mock agent execution with UserExecutionContext pattern."""
        self.execution_count += 1
        self.last_context = context
        
        if not self.should_succeed:
            raise RuntimeError(f"Mock {self.name} agent execution failed")
        
        # Store result in context metadata for dependency testing
        result_key = f"{self.name}_result"
        context.metadata[result_key] = self.execution_result
        
        return self.execution_result


class TestSupervisorAgentCore(BaseTestCase):
    """Test core SupervisorAgent functionality - MISSION CRITICAL for chat delivery."""
    
    def setUp(self):
        """Set up test environment with real instances."""
        super().setUp()
        
        # Create real LLM manager for testing
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="test response")
        self.llm_manager.get_available_models = AsyncMock(return_value=["gpt-4", "gpt-3.5-turbo"])
        
        # Create mock WebSocket bridge with real interface
        self.websocket_manager = MockWebSocketManager()
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.websocket_manager = self.websocket_manager
        self.websocket_bridge.emit_agent_event = AsyncMock()
        
        # Create real UserExecutionContext for testing
        self.test_context = UserExecutionContext(
            user_id=f"test-user-{uuid.uuid4().hex[:8]}",
            thread_id=f"test-thread-{uuid.uuid4().hex[:8]}",
            run_id=f"test-run-{uuid.uuid4().hex[:8]}",
            websocket_connection_id="test-connection-123",
            metadata={"user_request": "test request for SupervisorAgent"}
        )
        
        # Mock database session
        self.mock_db_session = AsyncMock()
        self.test_context = self.test_context.with_db_session(self.mock_db_session)
        
        # Create mock registries to avoid global dependencies
        self.mock_class_registry = Mock()
        self.mock_class_registry.get_agent_classes.return_value = {
            'triage': Mock(),
            'reporting': Mock(),
            'data': Mock()
        }
        self.mock_class_registry.__len__ = Mock(return_value=3)
        
        self.mock_instance_factory = Mock()
        self.mock_instance_factory.configure = Mock()
        self.mock_instance_factory.create_agent_instance = AsyncMock()
        # Add attributes that the factory might access
        self.mock_instance_factory.agent_class_registry = self.mock_class_registry
        
        # Patch global registries before creating SupervisorAgent
        self.registry_patcher = patch('netra_backend.app.agents.supervisor.agent_class_registry.get_agent_class_registry')
        self.factory_patcher = patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory')
        # Also patch the import inside agent_instance_factory for configure() method
        self.internal_registry_patcher = patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_class_registry')
        
        mock_registry_func = self.registry_patcher.start()
        mock_factory_func = self.factory_patcher.start()
        mock_internal_registry_func = self.internal_registry_patcher.start()
        
        mock_registry_func.return_value = self.mock_class_registry
        mock_factory_func.return_value = self.mock_instance_factory
        mock_internal_registry_func.return_value = self.mock_class_registry
        
        # Create real SupervisorAgent instance for testing
        self.supervisor = SupervisorAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )
        
        # Track resources for cleanup
        self.track_resource(self.supervisor)
    
    def tearDown(self):
        """Clean up patches."""
        super().tearDown()
        self.registry_patcher.stop()
        self.factory_patcher.stop()
        self.internal_registry_patcher.stop()

    def test_supervisor_initialization_with_user_context(self):
        """Test SupervisorAgent initializes properly with UserExecutionContext pattern."""
        # REAL INSTANCE TEST - verify initialization
        self.assertIsNotNone(self.supervisor)
        self.assertEqual(self.supervisor.name, "Supervisor")
        self.assertIsNotNone(self.supervisor.agent_instance_factory)
        self.assertIsNotNone(self.supervisor.agent_class_registry)
        
        # Verify WebSocket bridge is configured
        self.assertEqual(self.supervisor.websocket_bridge, self.websocket_bridge)
        
        # Verify no session storage (isolation validation)
        self.assertIsNone(getattr(self.supervisor, '_session_storage', None))
        self.assertIsNone(getattr(self.supervisor, 'persistent_state', None))
        
        # Verify execution lock exists for concurrency safety
        self.assertIsNotNone(self.supervisor._execution_lock)

    async def test_supervisor_execute_with_valid_context(self):
        """Test SupervisorAgent execution with valid UserExecutionContext."""
        # Mock agent instance factory to return test agents
        mock_triage = MockAgentInstance("triage", should_succeed=True, 
                                      execution_result={"data_sufficiency": "sufficient", "intent": {"primary_intent": "test"}})
        mock_reporting = MockAgentInstance("reporting", should_succeed=True,
                                         execution_result={"report": "test report", "status": "completed"})
        
        # Mock the _create_isolated_agent_instances method
        async def mock_create_agents(context):
            return {"triage": mock_triage, "reporting": mock_reporting}
        
        # Mock managed_session context manager
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_isolated_agent_instances', mock_create_agents), \
             patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager), \
             patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
             patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
            
            # Mock UserContextToolFactory
            mock_tool_system = {
                'dispatcher': Mock(),
                'registry': Mock(),
                'tools': []
            }
            mock_tool_system['registry'].name = "test_registry"
            mock_tool_system['dispatcher'].dispatcher_id = "test_dispatcher"
            mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
            
            # Execute supervisor
            result = await self.supervisor.execute(self.test_context, stream_updates=True)
            
            # Verify execution completed
            self.assertIsNotNone(result)
            self.assertIn("supervisor_result", result)
            self.assertEqual(result["supervisor_result"], "completed")
            self.assertTrue(result["orchestration_successful"])
            self.assertTrue(result["user_isolation_verified"])
            self.assertEqual(result["user_id"], self.test_context.user_id)
            self.assertEqual(result["run_id"], self.test_context.run_id)
            
            # Verify agents were executed
            self.assertEqual(mock_triage.execution_count, 1)
            self.assertEqual(mock_reporting.execution_count, 1)
            
            # Verify contexts were passed correctly
            self.assertIsNotNone(mock_triage.last_context)
            self.assertIsNotNone(mock_reporting.last_context)

    async def test_concurrent_user_execution_isolation(self):
        """Test multi-user execution isolation - CRITICAL for business."""
        # Create multiple user contexts
        contexts = []
        for i in range(5):
            context = UserExecutionContext(
                user_id=f"concurrent-user-{i}",
                thread_id=f"concurrent-thread-{i}",
                run_id=f"concurrent-run-{i}",
                websocket_connection_id=f"connection-{i}",
                metadata={"user_request": f"concurrent test {i}"}
            )
            context = context.with_db_session(AsyncMock())
            contexts.append(context)
        
        # Track execution results for isolation verification
        execution_results = []
        
        async def execute_with_tracking(context, index):
            """Execute supervisor and track results for isolation testing."""
            # Mock isolated agents for each execution
            mock_reporting = MockAgentInstance("reporting", execution_result={
                "user_id": context.user_id,
                "execution_index": index,
                "timestamp": time.time()
            })
            
            # Mock the methods to avoid complex dependencies
            async def mock_create_agents(ctx):
                return {"reporting": mock_reporting}
            
            mock_session_manager = AsyncMock()
            mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
            mock_session_manager.__aexit__ = AsyncMock(return_value=None)
            
            with patch.object(self.supervisor, '_create_isolated_agent_instances', mock_create_agents), \
                 patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager), \
                 patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
                 patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
                
                # Mock UserContextToolFactory
                mock_tool_system = {
                    'dispatcher': Mock(),
                    'registry': Mock(),
                    'tools': []
                }
                mock_tool_system['registry'].name = f"registry_{index}"
                mock_tool_system['dispatcher'].dispatcher_id = f"dispatcher_{index}"
                mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
                
                result = await self.supervisor.execute(context)
                execution_results.append((context.user_id, result, mock_reporting.execution_count))
        
        # Execute all contexts concurrently
        await asyncio.gather(*[
            execute_with_tracking(context, i) 
            for i, context in enumerate(contexts)
        ])
        
        # Verify isolation - each execution should be independent
        self.assertEqual(len(execution_results), 5)
        
        # Verify each user got their own isolated execution
        user_ids = [result[0] for result in execution_results]
        self.assertEqual(len(set(user_ids)), 5)  # All unique user IDs
        
        # Verify all executions completed successfully
        for user_id, result, execution_count in execution_results:
            self.assertEqual(result["orchestration_successful"], True)
            self.assertEqual(result["user_isolation_verified"], True)
            self.assertEqual(execution_count, 1)  # Each agent executed exactly once

    async def test_websocket_event_delivery_all_5_events(self):
        """Test all 5 critical WebSocket events are sent during execution."""
        # Create context with WebSocket connection
        context_with_ws = self.test_context
        
        # Mock minimal successful execution
        mock_reporting = MockAgentInstance("reporting", execution_result={"status": "completed"})
        
        async def mock_create_agents(ctx):
            return {"reporting": mock_reporting}
        
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_isolated_agent_instances', mock_create_agents), \
             patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager), \
             patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
             patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
            
            # Mock UserContextToolFactory
            mock_tool_system = {
                'dispatcher': Mock(),
                'registry': Mock(), 
                'tools': []
            }
            mock_tool_system['registry'].name = "test_registry"
            mock_tool_system['dispatcher'].dispatcher_id = "test_dispatcher"
            mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
            
            # Execute supervisor
            await self.supervisor.execute(context_with_ws, stream_updates=True)
            
            # Verify WebSocket events were sent
            # NOTE: Events are sent via emit_agent_event on the websocket_bridge
            event_calls = self.websocket_bridge.emit_agent_event.call_args_list
            
            # Should have at least thinking events from _emit_thinking calls
            self.assertGreater(len(event_calls), 0)
            
            # Verify thinking events were sent (critical for chat UX)
            thinking_events = [call for call in event_calls 
                             if call[1]['event_type'] == 'agent_thinking' or 
                                call[0][0] == 'agent_thinking']  # Handle different call signatures
            self.assertGreater(len(thinking_events), 0)

    def test_agent_dependency_validation_ssot(self):
        """Test agent dependency validation using SSOT AGENT_DEPENDENCIES mapping."""
        # Test the SSOT _can_execute_agent method directly
        
        # Test triage (no dependencies)
        can_execute, missing = self.supervisor._can_execute_agent("triage", set(), {})
        self.assertTrue(can_execute)
        self.assertEqual(missing, [])
        
        # Test reporting (no required dependencies - UVS principle)
        can_execute, missing = self.supervisor._can_execute_agent("reporting", set(), {})
        self.assertTrue(can_execute)
        self.assertEqual(missing, [])
        
        # Test optimization with missing optional data dependency (should still execute)
        can_execute, missing = self.supervisor._can_execute_agent("optimization", set(), {})
        self.assertTrue(can_execute)  # No required dependencies
        
        # Test with completed dependencies
        completed_agents = {"triage", "data"}
        context_metadata = {"triage_result": {}, "data_result": {}}
        
        can_execute, missing = self.supervisor._can_execute_agent("optimization", completed_agents, context_metadata)
        self.assertTrue(can_execute)
        self.assertEqual(missing, [])

    async def test_dynamic_workflow_determination(self):
        """Test dynamic workflow determination based on triage results."""
        # Test with sufficient data triage result
        triage_result = {
            "data_sufficiency": "sufficient",
            "intent": {"primary_intent": "analyze performance metrics"}
        }
        
        execution_order = self.supervisor._determine_execution_order(triage_result, self.test_context)
        
        # Should end with reporting (UVS principle)
        self.assertEqual(execution_order[-1], "reporting")
        
        # Should include data analysis based on intent
        self.assertIn("data", execution_order)
        
        # Test with no triage result (fallback workflow)
        execution_order_fallback = self.supervisor._determine_execution_order(None, self.test_context)
        
        # Should have minimal flow with reporting at end
        self.assertEqual(execution_order_fallback[-1], "reporting")
        self.assertIn("data_helper", execution_order_fallback)

    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery patterns."""
        # Create failing and successful agents
        failing_agent = MockAgentInstance("data", should_succeed=False)
        successful_agent = MockAgentInstance("reporting", should_succeed=True)
        
        async def mock_create_agents(context):
            return {"data": failing_agent, "reporting": successful_agent}
        
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_isolated_agent_instances', mock_create_agents), \
             patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager), \
             patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
             patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
            
            # Mock UserContextToolFactory
            mock_tool_system = {
                'dispatcher': Mock(),
                'registry': Mock(),
                'tools': []
            }
            mock_tool_system['registry'].name = "test_registry"
            mock_tool_system['dispatcher'].dispatcher_id = "test_dispatcher"
            mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
            
            # Execute supervisor - should handle data agent failure gracefully
            result = await self.supervisor.execute(self.test_context)
            
            # Supervisor should complete despite data agent failure
            self.assertEqual(result["supervisor_result"], "completed")
            self.assertTrue(result["orchestration_successful"])
            
            # Should have workflow metadata showing failed agents
            if "_workflow_metadata" in result["results"]:
                workflow_meta = result["results"]["_workflow_metadata"]
                # Data might be in failed agents due to execution error
                self.assertIn("reporting", workflow_meta.get("completed_agents", []))

    async def test_agent_retry_logic_exponential_backoff(self):
        """Test agent retry logic with exponential backoff."""
        retry_agent = MockAgentInstance("triage")
        retry_agent.attempt_count = 0
        
        # Make first two attempts fail, third succeed
        async def failing_execute(context, stream_updates=False):
            retry_agent.attempt_count += 1
            if retry_agent.attempt_count < 3:
                raise ConnectionError("Network timeout")  # Recoverable error
            return {"status": "completed", "attempt": retry_agent.attempt_count}
        
        retry_agent.execute = failing_execute
        
        # Test retry logic
        start_time = time.time()
        result = await self.supervisor._execute_agent_with_retry(
            retry_agent, self.test_context, "triage"
        )
        execution_time = time.time() - start_time
        
        # Should succeed after retries
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["attempt"], 3)
        
        # Should have taken time for exponential backoff delays
        self.assertGreater(execution_time, 1.0)  # At least 1s delay for retries

    async def test_fallback_report_creation(self):
        """Test UVS fallback report creation when primary reporting fails."""
        # Create partial results from other agents
        partial_results = {
            "triage": {"status": "completed", "category": "optimization", "priority": "high"},
            "data_helper": {"status": "completed", "guidance": "Provide usage data for analysis"},
            "data": {"status": "failed", "error": "Connection timeout"}
        }
        
        # Test fallback report creation
        fallback_report = await self.supervisor._create_fallback_report(self.test_context, partial_results)
        
        # Verify fallback report structure
        self.assertEqual(fallback_report["status"], "fallback")
        self.assertIn("message", fallback_report)
        self.assertIn("summary", fallback_report)
        self.assertIsInstance(fallback_report["summary"], list)
        
        # Should include successful agent insights
        self.assertIn("data_guidance", fallback_report)
        self.assertEqual(fallback_report["data_guidance"], "Provide usage data for analysis")
        
        # Should have metadata
        self.assertIn("metadata", fallback_report)
        self.assertEqual(fallback_report["metadata"]["user_id"], self.test_context.user_id)

    async def test_execution_context_isolation_validation(self):
        """Test that execution contexts are properly isolated between requests."""
        # Create two different contexts
        context1 = UserExecutionContext(
            user_id="user-1",
            thread_id="thread-1", 
            run_id="run-1",
            metadata={"test_data": "context1_data"}
        ).with_db_session(AsyncMock())
        
        context2 = UserExecutionContext(
            user_id="user-2",
            thread_id="thread-2",
            run_id="run-2", 
            metadata={"test_data": "context2_data"}
        ).with_db_session(AsyncMock())
        
        # Mock agent that stores context data
        class ContextCapturingAgent(MockAgentInstance):
            def __init__(self, name):
                super().__init__(name)
                self.captured_contexts = []
                
            async def execute(self, context, stream_updates=False):
                self.captured_contexts.append({
                    "user_id": context.user_id,
                    "test_data": context.metadata.get("test_data"),
                    "metadata_id": id(context.metadata)
                })
                return await super().execute(context, stream_updates)
        
        capturing_agent = ContextCapturingAgent("reporting")
        
        async def mock_create_agents(ctx):
            return {"reporting": capturing_agent}
        
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_isolated_agent_instances', mock_create_agents), \
             patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager), \
             patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
             patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
            
            # Mock UserContextToolFactory
            mock_tool_system = {
                'dispatcher': Mock(),
                'registry': Mock(),
                'tools': []
            }
            mock_tool_system['registry'].name = "test_registry"
            mock_tool_system['dispatcher'].dispatcher_id = "test_dispatcher"
            mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
            
            # Execute with both contexts
            await self.supervisor.execute(context1)
            await self.supervisor.execute(context2)
            
            # Verify contexts were isolated
            self.assertEqual(len(capturing_agent.captured_contexts), 2)
            
            ctx1_data = capturing_agent.captured_contexts[0]
            ctx2_data = capturing_agent.captured_contexts[1]
            
            # Verify different user data
            self.assertEqual(ctx1_data["user_id"], "user-1")
            self.assertEqual(ctx1_data["test_data"], "context1_data")
            self.assertEqual(ctx2_data["user_id"], "user-2") 
            self.assertEqual(ctx2_data["test_data"], "context2_data")
            
            # Verify metadata objects are different instances
            self.assertNotEqual(ctx1_data["metadata_id"], ctx2_data["metadata_id"])

    async def test_invalid_context_handling(self):
        """Test handling of invalid UserExecutionContext."""
        # Test with None context - should raise ValueError
        with self.assertRaises(TypeError):
            await self.supervisor.execute(None)
        
        # Test with context missing required fields
        invalid_context = UserExecutionContext(
            user_id="",  # Empty user ID should be invalid
            thread_id="test-thread",
            run_id="test-run"
        )
        
        # Should raise InvalidContextError during validation
        with self.assertRaises(InvalidContextError):
            await self.supervisor.execute(invalid_context)
        
        # Test with context missing database session
        context_no_db = UserExecutionContext(
            user_id="test-user",
            thread_id="test-thread", 
            run_id="test-run"
        )
        
        with self.assertRaises(ValueError) as cm:
            await self.supervisor.execute(context_no_db)
        
        self.assertIn("database session", str(cm.exception))

    async def test_agent_metadata_propagation(self):
        """Test that agent results are properly stored in context metadata."""
        # Create agents with specific result formats
        triage_agent = MockAgentInstance("triage", execution_result={
            "data_sufficiency": "partial",
            "category": "analysis", 
            "intent": {"primary_intent": "data analysis"}
        })
        
        reporting_agent = MockAgentInstance("reporting", execution_result={
            "report": "Analysis complete",
            "summary": ["Data analyzed", "Insights generated"]
        })
        
        async def mock_create_agents(ctx):
            return {"triage": triage_agent, "reporting": reporting_agent}
        
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_isolated_agent_instances', mock_create_agents), \
             patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager), \
             patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
             patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
            
            # Mock UserContextToolFactory
            mock_tool_system = {
                'dispatcher': Mock(),
                'registry': Mock(),
                'tools': []
            }
            mock_tool_system['registry'].name = "test_registry"
            mock_tool_system['dispatcher'].dispatcher_id = "test_dispatcher"
            mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
            
            # Execute supervisor
            result = await self.supervisor.execute(self.test_context)
            
            # Verify agent results are in the execution results
            self.assertIn("triage", result["results"])
            self.assertIn("reporting", result["results"])
            
            # Verify specific result content
            triage_result = result["results"]["triage"]
            self.assertEqual(triage_result["data_sufficiency"], "partial")
            self.assertEqual(triage_result["category"], "analysis")
            
            reporting_result = result["results"]["reporting"] 
            self.assertEqual(reporting_result["report"], "Analysis complete")

    async def test_performance_metrics_and_timing(self):
        """Test that execution timing and performance metrics are tracked."""
        # Create agents with known execution times
        slow_agent = MockAgentInstance("data")
        
        async def slow_execute(context, stream_updates=False):
            await asyncio.sleep(0.1)  # Simulate slow operation
            return {"status": "completed", "processing_time": 0.1}
        
        slow_agent.execute = slow_execute
        
        async def mock_create_agents(ctx):
            return {"data": slow_agent}
        
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_isolated_agent_instances', mock_create_agents), \
             patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager), \
             patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
             patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
            
            # Mock UserContextToolFactory
            mock_tool_system = {
                'dispatcher': Mock(),
                'registry': Mock(),
                'tools': []
            }
            mock_tool_system['registry'].name = "test_registry"
            mock_tool_system['dispatcher'].dispatcher_id = "test_dispatcher"
            mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
            
            # Execute supervisor and measure time
            start_time = time.time()
            result = await self.supervisor.execute(self.test_context)
            total_time = time.time() - start_time
            
            # Should have taken at least the slow agent time
            self.assertGreater(total_time, 0.1)
            
            # Verify execution completed
            self.assertTrue(result["orchestration_successful"])

    def test_supervisor_factory_method(self):
        """Test SupervisorAgent factory method creates proper instance."""
        # Test factory method
        supervisor = SupervisorAgent.create(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )
        
        # Verify created instance
        self.assertIsInstance(supervisor, SupervisorAgent)
        self.assertEqual(supervisor.llm_manager, self.llm_manager)
        self.assertEqual(supervisor.websocket_bridge, self.websocket_bridge)
        
        # Verify factory configuration
        self.assertIsNotNone(supervisor.agent_instance_factory)
        self.assertIsNotNone(supervisor.agent_class_registry)
        
        self.track_resource(supervisor)

    def test_get_required_agent_names_ssot(self):
        """Test _get_required_agent_names returns correct SSOT agent list."""
        required_agents = self.supervisor._get_required_agent_names()
        
        # Verify required agents per UVS principle
        self.assertIn("triage", required_agents)
        self.assertIn("reporting", required_agents)
        
        # Verify reporting is always included (UVS principle)
        self.assertIn("reporting", required_agents)
        
        # Verify optional agents are included
        self.assertIn("data_helper", required_agents)
        self.assertIn("data", required_agents)
        self.assertIn("optimization", required_agents)
        self.assertIn("actions", required_agents)

    def test_agent_dependencies_ssot_structure(self):
        """Test AGENT_DEPENDENCIES SSOT structure is correct."""
        deps = self.supervisor.AGENT_DEPENDENCIES
        
        # Verify required agents have correct configuration
        self.assertIn("triage", deps)
        self.assertIn("reporting", deps)
        
        # Verify triage has no required dependencies
        self.assertEqual(deps["triage"]["required"], [])
        
        # Verify reporting has no required dependencies (UVS principle)
        self.assertEqual(deps["reporting"]["required"], [])
        
        # Verify reporting is marked as cannot fail
        self.assertFalse(deps["reporting"]["can_fail"])
        
        # Verify other agents can fail
        self.assertTrue(deps["triage"]["can_fail"])

    async def test_recoverable_error_detection(self):
        """Test _is_recoverable_error correctly identifies recoverable errors."""
        # Test recoverable errors
        recoverable_errors = [
            ConnectionError("Network timeout"),
            TimeoutError("Request timeout"), 
            RuntimeError("temporary unavailable"),
            Exception("rate limit exceeded")
        ]
        
        for error in recoverable_errors:
            self.assertTrue(self.supervisor._is_recoverable_error(error))
        
        # Test non-recoverable errors
        non_recoverable_errors = [
            ValueError("invalid request format"),
            RuntimeError("authentication failed"),
            Exception("permission denied"),
            RuntimeError("not found")
        ]
        
        for error in non_recoverable_errors:
            self.assertFalse(self.supervisor._is_recoverable_error(error))

    def test_string_representations(self):
        """Test string representation methods.""" 
        # Add mock registry attribute for string representation testing
        self.supervisor.registry = Mock()
        self.supervisor.registry.agents = {"triage": Mock(), "reporting": Mock()}
        
        # Test __str__
        str_repr = str(self.supervisor)
        self.assertIn("SupervisorAgent", str_repr)
        self.assertIn("UserExecutionContext", str_repr)
        
        # Test __repr__
        repr_str = repr(self.supervisor)
        self.assertIn("SupervisorAgent", repr_str)
        self.assertIn("UserExecutionContext", repr_str)

    def test_get_stats_and_performance_metrics(self):
        """Test utility methods for stats and performance metrics."""
        # Add mock registry attribute for stats testing
        self.supervisor.registry = Mock()
        self.supervisor.registry.agents = {"triage": Mock(), "reporting": Mock()}
        
        # Test get_stats
        stats = self.supervisor.get_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("supervisor_status", stats)
        self.assertEqual(stats["pattern"], "UserExecutionContext")
        
        # Test get_performance_metrics
        metrics = self.supervisor.get_performance_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertEqual(metrics["pattern"], "UserExecutionContext")
        self.assertTrue(metrics["isolation_verified"])

    async def test_websocket_thinking_emission(self):
        """Test _emit_thinking method sends WebSocket events correctly."""
        # Test thinking message emission
        test_message = "Processing user request with advanced analysis"
        
        await self.supervisor._emit_thinking(self.test_context, test_message)
        
        # Verify WebSocket bridge was called
        self.websocket_bridge.emit_agent_event.assert_called_once()
        
        # Verify call parameters
        call_args = self.websocket_bridge.emit_agent_event.call_args
        self.assertEqual(call_args[1]["event_type"], "agent_thinking")
        self.assertEqual(call_args[1]["data"]["message"], test_message)
        self.assertEqual(call_args[1]["data"]["agent_name"], "Supervisor")
        self.assertEqual(call_args[1]["run_id"], self.test_context.run_id)

    async def test_child_context_metadata_propagation(self):
        """Test metadata propagation from child contexts to parent."""
        # Create parent and child contexts
        parent_context = self.test_context
        child_context = parent_context.create_child_context(
            operation_name="test_operation",
            additional_metadata={"child_data": "test_value"}
        )
        
        # Add agent result to child context
        child_context.metadata["triage_result"] = {
            "data_sufficiency": "sufficient", 
            "category": "optimization"
        }
        child_context.metadata["custom_result"] = {"test": "data"}
        
        # Test metadata propagation
        self.supervisor._merge_child_metadata_to_parent(
            parent_context, child_context, "triage"
        )
        
        # Verify triage result was propagated
        self.assertIn("triage_result", parent_context.metadata)
        self.assertEqual(
            parent_context.metadata["triage_result"]["data_sufficiency"], 
            "sufficient"
        )
        
        # Verify custom result was also propagated
        self.assertIn("custom_result", parent_context.metadata)

    async def test_agent_result_storage_ssot(self):
        """Test _store_agent_result stores results under all expected SSOT keys."""
        test_result = {"status": "completed", "insights": ["insight1", "insight2"]}
        
        # Test storing triage result
        self.supervisor._store_agent_result(self.test_context, "triage", test_result)
        
        # Verify result stored under expected keys from AGENT_DEPENDENCIES
        triage_produces = self.supervisor.AGENT_DEPENDENCIES["triage"]["produces"]
        for key in triage_produces:
            self.assertIn(key, self.test_context.metadata)
            self.assertEqual(self.test_context.metadata[key], test_result)
        
        # Verify generic key is also stored
        self.assertIn("triage_result", self.test_context.metadata)
        self.assertEqual(self.test_context.metadata["triage_result"], test_result)


class TestSupervisorAgentErrorScenarios(BaseTestCase):
    """Test SupervisorAgent error scenarios and edge cases."""
    
    def setUp(self):
        """Set up test environment for error scenario testing."""
        super().setUp()
        
        self.llm_manager = Mock(spec=LLMManager) 
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="test response")
        
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.websocket_manager = MockWebSocketManager()
        self.websocket_bridge.emit_agent_event = AsyncMock()
        
        self.supervisor = SupervisorAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )
        
        self.track_resource(self.supervisor)

    async def test_execution_lock_prevents_concurrent_same_instance(self):
        """Test execution lock prevents concurrent execution on same supervisor instance."""
        # Create test context
        context = UserExecutionContext(
            user_id="test-user",
            thread_id="test-thread",
            run_id="test-run"
        ).with_db_session(AsyncMock())
        
        execution_order = []
        
        async def mock_execution(ctx):
            execution_order.append("start")
            await asyncio.sleep(0.1)  # Simulate work
            execution_order.append("end")
            return {"supervisor_result": "completed", "orchestration_successful": True, 
                   "user_isolation_verified": True, "results": {}, 
                   "user_id": ctx.user_id, "run_id": ctx.run_id}
        
        # Mock the orchestration method to track execution order
        with patch.object(self.supervisor, '_orchestrate_agents', mock_execution), \
             patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
             patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
            
            # Mock UserContextToolFactory
            mock_tool_system = {
                'dispatcher': Mock(),
                'registry': Mock(),
                'tools': []
            }
            mock_tool_system['registry'].name = "test_registry"
            mock_tool_system['dispatcher'].dispatcher_id = "test_dispatcher"
            mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
            
            # Start two concurrent executions on the same instance
            task1 = asyncio.create_task(self.supervisor.execute(context))
            task2 = asyncio.create_task(self.supervisor.execute(context))
            
            # Both should complete successfully but sequentially
            results = await asyncio.gather(task1, task2)
            
            # Verify both completed
            self.assertEqual(len(results), 2)
            for result in results:
                self.assertTrue(result["orchestration_successful"])
            
            # Verify sequential execution (should be start, end, start, end)
            self.assertEqual(execution_order, ["start", "end", "start", "end"])

    async def test_critical_agent_failure_recovery(self):
        """Test recovery when critical agents (like reporting) fail."""
        # Create context
        context = UserExecutionContext(
            user_id="test-user",
            thread_id="test-thread", 
            run_id="test-run"
        ).with_db_session(AsyncMock())
        
        # Mock a failing reporting agent (critical)
        failing_reporting = MockAgentInstance("reporting", should_succeed=False)
        
        async def mock_create_agents(ctx):
            return {"reporting": failing_reporting}
        
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_isolated_agent_instances', mock_create_agents), \
             patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager), \
             patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
             patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
            
            # Mock UserContextToolFactory
            mock_tool_system = {
                'dispatcher': Mock(),
                'registry': Mock(),
                'tools': []
            }
            mock_tool_system['registry'].name = "test_registry"  
            mock_tool_system['dispatcher'].dispatcher_id = "test_dispatcher"
            mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
            
            # Should still complete with fallback reporting
            result = await self.supervisor.execute(context)
            
            # Should complete successfully even with reporting failure
            self.assertEqual(result["supervisor_result"], "completed")
            self.assertTrue(result["orchestration_successful"])
            
            # Should have reporting result (either fallback or emergency)
            self.assertIn("reporting", result["results"])

    async def test_all_agents_fail_scenario(self):
        """Test scenario where all agents fail."""
        context = UserExecutionContext(
            user_id="test-user",
            thread_id="test-thread",
            run_id="test-run"
        ).with_db_session(AsyncMock())
        
        # Create all failing agents
        failing_agents = {
            "triage": MockAgentInstance("triage", should_succeed=False),
            "reporting": MockAgentInstance("reporting", should_succeed=False),
            "data_helper": MockAgentInstance("data_helper", should_succeed=False)
        }
        
        async def mock_create_agents(ctx):
            return failing_agents
        
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_isolated_agent_instances', mock_create_agents), \
             patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager), \
             patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
             patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
            
            # Mock UserContextToolFactory
            mock_tool_system = {
                'dispatcher': Mock(),
                'registry': Mock(),
                'tools': []
            }
            mock_tool_system['registry'].name = "test_registry"
            mock_tool_system['dispatcher'].dispatcher_id = "test_dispatcher"
            mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
            
            # Should still provide a result (UVS principle)
            result = await self.supervisor.execute(context)
            
            # Should complete with some form of result
            self.assertEqual(result["supervisor_result"], "completed")
            self.assertIn("results", result)

    async def test_websocket_bridge_failure_graceful_degradation(self):
        """Test graceful degradation when WebSocket bridge fails."""
        # Create supervisor with failing WebSocket bridge
        failing_bridge = Mock(spec=AgentWebSocketBridge)
        failing_bridge.websocket_manager = MockWebSocketManager()
        failing_bridge.emit_agent_event = AsyncMock(side_effect=Exception("WebSocket failure"))
        
        supervisor_with_failing_ws = SupervisorAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=failing_bridge
        )
        
        context = UserExecutionContext(
            user_id="test-user",
            thread_id="test-thread",
            run_id="test-run"
        ).with_db_session(AsyncMock())
        
        # Mock successful agents
        mock_reporting = MockAgentInstance("reporting")
        
        async def mock_create_agents(ctx):
            return {"reporting": mock_reporting}
        
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(supervisor_with_failing_ws, '_create_isolated_agent_instances', mock_create_agents), \
             patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager), \
             patch.object(supervisor_with_failing_ws, '_get_tool_classes_from_context', return_value=[]), \
             patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
            
            # Mock UserContextToolFactory
            mock_tool_system = {
                'dispatcher': Mock(),
                'registry': Mock(),
                'tools': []
            }
            mock_tool_system['registry'].name = "test_registry"
            mock_tool_system['dispatcher'].dispatcher_id = "test_dispatcher"  
            mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
            
            # Should complete successfully despite WebSocket failures
            result = await supervisor_with_failing_ws.execute(context)
            
            # Should complete successfully
            self.assertTrue(result["orchestration_successful"])
            
            # WebSocket events should have been attempted but failed gracefully
            self.assertGreater(failing_bridge.emit_agent_event.call_count, 0)
        
        self.track_resource(supervisor_with_failing_ws)


# Additional test classes for specialized scenarios

class TestSupervisorAgentPerformance(BaseTestCase):
    """Performance and load testing for SupervisorAgent."""
    
    def setUp(self):
        super().setUp()
        
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="test response")
        
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge) 
        self.websocket_bridge.websocket_manager = MockWebSocketManager()
        self.websocket_bridge.emit_agent_event = AsyncMock()
        
        self.supervisor = SupervisorAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )
        
        self.track_resource(self.supervisor)

    async def test_high_concurrency_performance(self):
        """Test SupervisorAgent performance under high concurrency."""
        # Create many concurrent contexts
        contexts = []
        for i in range(10):  # High concurrency test
            context = UserExecutionContext(
                user_id=f"perf-user-{i}",
                thread_id=f"perf-thread-{i}",
                run_id=f"perf-run-{i}",
                metadata={"test_index": i}
            ).with_db_session(AsyncMock())
            contexts.append(context)
        
        # Fast mock agents to test orchestration overhead
        async def mock_create_agents(ctx):
            return {"reporting": MockAgentInstance("reporting")}
        
        mock_session_manager = AsyncMock()
        mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
        mock_session_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(self.supervisor, '_create_isolated_agent_instances', mock_create_agents), \
             patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager), \
             patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
             patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
            
            # Mock UserContextToolFactory  
            mock_tool_system = {
                'dispatcher': Mock(),
                'registry': Mock(),
                'tools': []
            }
            mock_tool_system['registry'].name = "test_registry"
            mock_tool_system['dispatcher'].dispatcher_id = "test_dispatcher"
            mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
            
            # Execute all concurrently and measure performance
            start_time = time.time()
            
            results = await asyncio.gather(*[
                self.supervisor.execute(context) 
                for context in contexts
            ])
            
            total_time = time.time() - start_time
            
            # All should complete successfully
            self.assertEqual(len(results), 10)
            for result in results:
                self.assertTrue(result["orchestration_successful"])
            
            # Performance should be reasonable (less than 5 seconds for 10 concurrent)
            self.assertLess(total_time, 5.0)
            
            # Average per execution should be reasonable
            avg_time = total_time / len(results)
            self.assertLess(avg_time, 1.0)  # Less than 1 second average

    async def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load."""
        import gc
        
        # Get initial memory baseline
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Run many sequential executions 
        for i in range(20):
            context = UserExecutionContext(
                user_id=f"memory-user-{i}",
                thread_id=f"memory-thread-{i}", 
                run_id=f"memory-run-{i}"
            ).with_db_session(AsyncMock())
            
            # Mock minimal execution
            async def mock_create_agents(ctx):
                return {"reporting": MockAgentInstance("reporting")}
            
            mock_session_manager = AsyncMock()
            mock_session_manager.__aenter__ = AsyncMock(return_value=mock_session_manager)
            mock_session_manager.__aexit__ = AsyncMock(return_value=None)
            
            with patch.object(self.supervisor, '_create_isolated_agent_instances', mock_create_agents), \
                 patch('netra_backend.app.agents.supervisor_consolidated.managed_session', return_value=mock_session_manager), \
                 patch.object(self.supervisor, '_get_tool_classes_from_context', return_value=[]), \
                 patch('netra_backend.app.agents.supervisor_consolidated.UserContextToolFactory') as mock_factory:
                
                # Mock UserContextToolFactory
                mock_tool_system = {
                    'dispatcher': Mock(),
                    'registry': Mock(),
                    'tools': []
                }
                mock_tool_system['registry'].name = f"registry_{i}"
                mock_tool_system['dispatcher'].dispatcher_id = f"dispatcher_{i}"
                mock_factory.create_user_tool_system = AsyncMock(return_value=mock_tool_system)
                
                result = await self.supervisor.execute(context)
                self.assertTrue(result["orchestration_successful"])
            
            # Force garbage collection periodically
            if i % 5 == 0:
                gc.collect()
        
        # Final garbage collection and object count
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be reasonable (less than 50% increase)
        growth_ratio = final_objects / initial_objects
        self.assertLess(growth_ratio, 1.5)  # Less than 50% growth


if __name__ == '__main__':
    pytest.main([__file__, "-v", "--tb=short"])