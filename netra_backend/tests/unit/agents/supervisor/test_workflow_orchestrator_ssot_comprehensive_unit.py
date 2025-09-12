"""
Comprehensive Unit Test Suite for WorkflowOrchestrator SSOT

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Core platform functionality
- Business Goal: Ensure reliable adaptive workflow orchestration for AI optimization value delivery
- Value Impact: Validates that adaptive workflow orchestration provides proper triage-based workflow definition,
  UserExecutionEngine integration, WebSocket event routing with user isolation, and agent coordination
- Revenue Impact: Protects $500K+ ARR by ensuring chat functionality delivers substantive AI value through
  reliable workflow execution, proper error handling, and consistent user experience

SSOT Testing Focus:
This test suite validates the WorkflowOrchestrator SSOT implementation following all TEST_CREATION_GUIDE.md
standards, ensuring:
1. Adaptive workflow orchestration (triage-based workflow definition)  
2. UserExecutionEngine integration validation (no deprecated ExecutionEngine usage)
3. WebSocket event routing with proper user isolation using factory patterns
4. Pipeline step execution coordination with proper dependencies
5. Agent coordination validation for Enterprise data integrity
6. Error handling and recovery scenarios
7. SSOT compliance (no duplicate orchestration implementations)

Critical Requirements Tested:
- Factory pattern for user isolation in WebSocket events
- UserExecutionEngine validation (SSOT compliance)
- AgentCoordinationValidator integration for Enterprise workflows
- Adaptive workflow definition based on triage results
- Proper ExecutionContext handling and step context creation
- WebSocket emitter user isolation and factory pattern usage
- Pipeline step configuration and dependency management
- Error handling and graceful degradation patterns

Test Categories: Unit Tests (no external dependencies, focused on business logic)
Infrastructure: None required (pure unit tests with mocks for external dependencies)
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, MagicMock, patch, call
from typing import Any, Dict, List, Optional, Union
import time
from dataclasses import dataclass

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import system under test
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator

# Import dependencies for testing
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.supervisor.execution_context import (
    PipelineStepConfig, PipelineStep, AgentExecutionStrategy
)
from netra_backend.app.agents.supervisor.agent_coordination_validator import (
    AgentCoordinationValidator, CoordinationValidationResult
)
from netra_backend.app.schemas.core_enums import ExecutionStatus


class TestWorkflowOrchestratorSSOTComprehensiveUnit(SSotAsyncTestCase):
    """
    Comprehensive unit test suite for WorkflowOrchestrator SSOT.
    
    This test class validates the complete WorkflowOrchestrator functionality including:
    - Adaptive workflow orchestration based on triage results
    - UserExecutionEngine integration validation
    - WebSocket event routing with user isolation
    - Pipeline step execution coordination
    - Agent coordination validation
    - Error handling and recovery scenarios
    - SSOT compliance verification
    """
    
    def setup_method(self, method):
        """Setup test fixtures for each test method."""
        super().setup_method(method)
        
        # Create mock dependencies
        self.mock_agent_registry = Mock()
        self.mock_execution_engine = Mock()
        self.mock_websocket_manager = Mock()
        self.mock_user_context = Mock()
        
        # Configure mock user context
        self.mock_user_context.user_id = "test_user_123"
        self.mock_user_context.thread_id = "test_thread_456" 
        self.mock_user_context.run_id = "test_run_789"
        
        # Create WorkflowOrchestrator instance
        self.orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.mock_user_context
        )
        
        # Track test metrics
        self.record_metric("test_setup_completed", True)
    
    async def test_init_validates_execution_engine_ssot_compliance(self):
        """
        Test that WorkflowOrchestrator __init__ validates SSOT compliance by rejecting deprecated ExecutionEngine.
        
        BVJ: Ensures SSOT compliance by preventing usage of deprecated ExecutionEngine,
        maintaining system consistency and preventing architectural violations.
        """
        # Test deprecated ExecutionEngine rejection
        deprecated_engine = Mock()
        deprecated_engine.__class__.__name__ = "ExecutionEngine"
        
        with self.expect_exception(ValueError, "deprecated ExecutionEngine not allowed"):
            WorkflowOrchestrator(
                agent_registry=self.mock_agent_registry,
                execution_engine=deprecated_engine,
                websocket_manager=self.mock_websocket_manager
            )
        
        # Test valid UserExecutionEngine acceptance
        valid_engine = Mock()
        valid_engine.__class__.__name__ = "UserExecutionEngine"
        
        orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=valid_engine,
            websocket_manager=self.mock_websocket_manager
        )
        
        self.assertIsNotNone(orchestrator)
        self.assertEqual(orchestrator.execution_engine, valid_engine)
        self.assertIsInstance(orchestrator.coordination_validator, AgentCoordinationValidator)
        self.record_metric("ssot_validation_tests", 1)
    
    async def test_set_user_context_enables_factory_pattern(self):
        """
        Test that set_user_context properly configures user isolation using factory pattern.
        
        BVJ: Validates factory pattern implementation for user isolation, ensuring
        WebSocket events are delivered to correct users without data leakage.
        """
        new_user_context = Mock()
        new_user_context.user_id = "new_user_456"
        new_user_context.thread_id = "new_thread_789"
        new_user_context.run_id = "new_run_123"
        
        # Set new user context
        self.orchestrator.set_user_context(new_user_context)
        
        # Verify context is set
        self.assertEqual(self.orchestrator.user_context, new_user_context)
        
        # Verify emitter is reset for recreation with new context
        self.assertIsNone(self.orchestrator._websocket_emitter)
        
        self.record_metric("factory_pattern_tests", 1)
    
    async def test_define_workflow_based_on_triage_sufficient_data(self):
        """
        Test adaptive workflow definition for sufficient data scenario.
        
        BVJ: Validates that triage-based workflow orchestration properly defines
        full optimization workflow when sufficient data is available.
        """
        triage_result = {
            "data_sufficiency": "sufficient",
            "confidence": 0.9,
            "classification": "optimization_ready"
        }
        
        workflow_steps = self.orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Verify full workflow for sufficient data
        self.assertEqual(len(workflow_steps), 5)
        
        expected_agents = ["triage", "data", "optimization", "actions", "reporting"]
        actual_agents = [step.agent_name for step in workflow_steps]
        self.assertEqual(actual_agents, expected_agents)
        
        # Verify step configuration
        for i, step in enumerate(workflow_steps):
            self.assertIsInstance(step, PipelineStepConfig)
            self.assertEqual(step.strategy, AgentExecutionStrategy.SEQUENTIAL)
            self.assertEqual(step.metadata["order"], i + 1)
            self.assertFalse(step.metadata["continue_on_error"])
            self.assertTrue(step.metadata["requires_sequential"])
        
        # Verify reporting step has no hard dependencies (UVS pattern)
        reporting_step = workflow_steps[-1]
        self.assertEqual(reporting_step.dependencies, [])
        
        self.record_metric("adaptive_workflow_sufficient_tests", 1)
    
    async def test_define_workflow_based_on_triage_partial_data(self):
        """
        Test adaptive workflow definition for partial data scenario.
        
        BVJ: Validates that adaptive workflow handles partial data scenarios
        by including data helper for guidance while maintaining value delivery.
        """
        triage_result = {
            "data_sufficiency": "partial",
            "confidence": 0.6,
            "classification": "needs_data_helper"
        }
        
        workflow_steps = self.orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Verify partial data workflow
        self.assertEqual(len(workflow_steps), 4)
        
        expected_agents = ["triage", "data_helper", "data", "reporting"]
        actual_agents = [step.agent_name for step in workflow_steps]
        self.assertEqual(actual_agents, expected_agents)
        
        # Verify data helper is included
        data_helper_step = workflow_steps[1]
        self.assertEqual(data_helper_step.agent_name, "data_helper")
        self.assertEqual(data_helper_step.metadata["step_type"], "data_guidance")
        
        self.record_metric("adaptive_workflow_partial_tests", 1)
    
    async def test_define_workflow_based_on_triage_insufficient_data(self):
        """
        Test adaptive workflow definition for insufficient data scenario (DEFAULT UVS FLOW).
        
        BVJ: Validates default UVS (Universal Value System) flow for insufficient data,
        ensuring value delivery even with minimal data through guidance-focused workflow.
        """
        triage_result = {
            "data_sufficiency": "insufficient",
            "confidence": 0.3,
            "classification": "data_collection_needed"
        }
        
        workflow_steps = self.orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Verify DEFAULT UVS FLOW: Triage -> Data Helper -> Reporting
        self.assertEqual(len(workflow_steps), 3)
        
        expected_agents = ["triage", "data_helper", "reporting"]
        actual_agents = [step.agent_name for step in workflow_steps]
        self.assertEqual(actual_agents, expected_agents)
        
        # Verify UVS pattern - reporting handles guidance scenario
        reporting_step = workflow_steps[-1]
        self.assertEqual(reporting_step.metadata["step_type"], "guidance_report")
        self.assertEqual(reporting_step.dependencies, [])  # UVS provides guidance
        
        self.record_metric("adaptive_workflow_insufficient_tests", 1)
    
    async def test_define_workflow_based_on_triage_unknown_fallback(self):
        """
        Test adaptive workflow definition for unknown data sufficiency (MINIMAL UVS FLOW).
        
        BVJ: Validates minimal UVS fallback workflow for unknown or failed triage,
        ensuring system resilience and continued value delivery.
        """
        triage_result = {
            "data_sufficiency": "unknown",
            "classification": "triage_failed"
        }
        
        workflow_steps = self.orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Verify MINIMAL UVS FLOW: Data Helper -> Reporting
        self.assertEqual(len(workflow_steps), 2)
        
        expected_agents = ["data_helper", "reporting"]
        actual_agents = [step.agent_name for step in workflow_steps]
        self.assertEqual(actual_agents, expected_agents)
        
        # Verify fallback configuration
        data_helper_step = workflow_steps[0]
        self.assertEqual(data_helper_step.metadata["step_type"], "initial_guidance")
        
        reporting_step = workflow_steps[1]
        self.assertEqual(reporting_step.metadata["step_type"], "fallback_report")
        self.assertEqual(reporting_step.dependencies, [])  # UVS fallback
        
        self.record_metric("adaptive_workflow_fallback_tests", 1)
    
    @patch('netra_backend.app.agents.supervisor.workflow_orchestrator.create_agent_websocket_bridge')
    async def test_get_user_emitter_factory_pattern(self, mock_create_bridge):
        """
        Test user emitter creation using factory pattern for isolation.
        
        BVJ: Validates factory pattern implementation for WebSocket emitter creation,
        ensuring proper user isolation and preventing event delivery mix-ups.
        """
        # Setup mock bridge and emitter
        mock_bridge = Mock()
        mock_emitter = AsyncMock()
        mock_bridge.create_user_emitter = AsyncMock(return_value=mock_emitter)
        mock_create_bridge.return_value = mock_bridge
        
        # Test emitter creation
        emitter = await self.orchestrator._get_user_emitter()
        
        # Verify factory pattern usage
        mock_create_bridge.assert_called_once_with(self.mock_user_context)
        mock_bridge.create_user_emitter.assert_called_once_with(self.mock_user_context)
        self.assertEqual(emitter, mock_emitter)
        
        # Verify lazy initialization (cached for subsequent calls)
        emitter2 = await self.orchestrator._get_user_emitter()
        self.assertEqual(emitter2, mock_emitter)
        
        # Should not create bridge again (cached)
        self.assertEqual(mock_create_bridge.call_count, 1)
        
        self.record_metric("factory_pattern_emitter_tests", 1)
    
    @patch('netra_backend.app.agents.supervisor.workflow_orchestrator.create_agent_websocket_bridge')
    async def test_get_user_emitter_from_context_creation(self, mock_create_bridge):
        """
        Test user emitter creation from ExecutionContext using factory pattern.
        
        BVJ: Validates dynamic user context creation from ExecutionContext,
        enabling WebSocket event delivery even when user_context is not pre-configured.
        """
        # Setup mock context
        mock_context = Mock()
        mock_context.user_id = "context_user_123"
        mock_context.thread_id = "context_thread_456"
        mock_context.run_id = "context_run_789"
        
        # Setup mock bridge and emitter
        mock_bridge = Mock()
        mock_emitter = AsyncMock()
        mock_bridge.create_user_emitter = AsyncMock(return_value=mock_emitter)
        mock_create_bridge.return_value = mock_bridge
        
        # Create orchestrator without user_context
        orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=None
        )
        
        # Test emitter creation from context
        with patch('netra_backend.app.agents.supervisor.workflow_orchestrator.UserExecutionContext') as mock_user_context_class:
            emitter = await orchestrator._get_user_emitter_from_context(mock_context)
            
            # Verify UserExecutionContext creation
            mock_user_context_class.assert_called_once_with(
                user_id="context_user_123",
                thread_id="context_thread_456",
                run_id="context_run_789"
            )
            
            # Verify bridge creation and emitter
            self.assertIsNotNone(emitter)
        
        self.record_metric("context_emitter_creation_tests", 1)
    
    async def test_get_user_emitter_from_context_missing_fields(self):
        """
        Test user emitter creation with missing ExecutionContext fields.
        
        BVJ: Validates graceful handling of incomplete ExecutionContext,
        ensuring system resilience when context information is missing.
        """
        # Test with missing fields
        mock_context = Mock()
        del mock_context.user_id  # Missing user_id
        mock_context.thread_id = "thread_456"
        mock_context.run_id = "run_789"
        
        orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=None
        )
        
        # Should return None gracefully
        emitter = await orchestrator._get_user_emitter_from_context(mock_context)
        self.assertIsNone(emitter)
        
        self.record_metric("context_missing_fields_tests", 1)
    
    async def test_create_step_context_preserves_execution_context(self):
        """
        Test step context creation preserves ExecutionContext data properly.
        
        BVJ: Validates that step context creation maintains all required ExecutionContext
        attributes while configuring step-specific parameters for agent execution.
        """
        # Create base context
        base_context = ExecutionContext(
            request_id="req_123",
            run_id="run_456",
            agent_name="base_agent",
            state=Mock(),
            stream_updates=True,
            user_id="user_789"
        )
        base_context.thread_id = "thread_123"  # Dynamically added
        
        # Create pipeline step
        step = PipelineStepConfig(
            agent_name="test_agent",
            strategy=AgentExecutionStrategy.SEQUENTIAL,
            dependencies=["dep1"],
            metadata={
                "step_type": "test_step",
                "order": 1,
                "custom_param": "test_value"
            }
        )
        
        # Create step context
        step_context = self.orchestrator._create_step_context(base_context, step)
        
        # Verify preserved attributes
        self.assertEqual(step_context.request_id, "req_123")
        self.assertEqual(step_context.run_id, "run_456")
        self.assertEqual(step_context.agent_name, "test_agent")  # Updated for step
        self.assertEqual(step_context.state, base_context.state)
        self.assertEqual(step_context.stream_updates, True)
        self.assertEqual(step_context.user_id, "user_789")
        self.assertEqual(step_context.metadata, step.metadata)
        
        # Verify thread_id is preserved if available
        self.assertEqual(step_context.thread_id, "thread_123")
        
        self.record_metric("step_context_creation_tests", 1)
    
    @patch('netra_backend.app.agents.supervisor.workflow_orchestrator.create_agent_websocket_bridge')
    async def test_send_workflow_started_user_isolation(self, mock_create_bridge):
        """
        Test workflow started notification with proper user isolation.
        
        BVJ: Validates that workflow started events are sent with proper user isolation,
        ensuring users receive notifications only for their own workflow executions.
        """
        # Setup mock bridge and emitter
        mock_bridge = Mock()
        mock_emitter = AsyncMock()
        mock_bridge.create_user_emitter = AsyncMock(return_value=mock_emitter)
        mock_create_bridge.return_value = mock_bridge
        
        # Create execution context
        context = ExecutionContext(
            request_id="req_123",
            run_id="run_456",
            agent_name="test_agent",
            state=Mock(),
            stream_updates=True,
            user_id="user_789"
        )
        context.user_id = "user_789"
        context.thread_id = "thread_123"
        context.run_id = "run_456"
        
        # Set workflow steps
        self.orchestrator._workflow_steps = [
            PipelineStepConfig("agent1", metadata={"order": 1}),
            PipelineStepConfig("agent2", metadata={"order": 2})
        ]
        
        # Send workflow started notification
        await self.orchestrator._send_workflow_started(context)
        
        # Verify user-isolated emitter was called
        mock_emitter.emit_agent_started.assert_called_once_with(
            "WorkflowOrchestrator",
            {
                "workflow_started": True,
                "total_steps": 2
            }
        )
        
        self.record_metric("workflow_started_isolation_tests", 1)
    
    @patch('netra_backend.app.agents.supervisor.workflow_orchestrator.create_agent_websocket_bridge')
    async def test_send_step_started_notification(self, mock_create_bridge):
        """
        Test step started notification with proper event data.
        
        BVJ: Validates that step started events contain proper metadata
        for user visibility into workflow execution progress.
        """
        # Setup mock bridge and emitter
        mock_bridge = Mock()
        mock_emitter = AsyncMock()
        mock_bridge.create_user_emitter = AsyncMock(return_value=mock_emitter)
        mock_create_bridge.return_value = mock_bridge
        
        # Create execution context
        context = ExecutionContext(
            request_id="req_123",
            run_id="run_456",
            agent_name="test_agent",
            state=Mock(),
            stream_updates=True,
            user_id="user_789"
        )
        context.user_id = "user_789"
        context.thread_id = "thread_123"
        context.run_id = "run_456"
        
        # Create pipeline step
        step = PipelineStepConfig(
            agent_name="data_agent",
            metadata={
                "step_type": "data_analysis",
                "order": 2
            }
        )
        
        # Send step started notification
        await self.orchestrator._send_step_started(context, step)
        
        # Verify step started event
        mock_emitter.emit_agent_started.assert_called_once_with(
            "data_agent",
            {
                "step_type": "data_analysis",
                "order": 2
            }
        )
        
        self.record_metric("step_started_notification_tests", 1)
    
    @patch('netra_backend.app.agents.supervisor.workflow_orchestrator.create_agent_websocket_bridge')
    async def test_send_step_completed_success(self, mock_create_bridge):
        """
        Test step completed notification for successful execution.
        
        BVJ: Validates that successful step completion events provide
        proper execution metrics and completion status to users.
        """
        # Setup mock bridge and emitter
        mock_bridge = Mock()
        mock_emitter = AsyncMock()
        mock_bridge.create_user_emitter = AsyncMock(return_value=mock_emitter)
        mock_create_bridge.return_value = mock_bridge
        
        # Create execution context
        context = ExecutionContext(
            request_id="req_123",
            run_id="run_456",
            agent_name="test_agent",
            state=Mock(),
            stream_updates=True,
            user_id="user_789"
        )
        context.user_id = "user_789"
        context.thread_id = "thread_123"
        context.run_id = "run_456"
        
        # Create pipeline step
        step = PipelineStepConfig(
            agent_name="optimization_agent",
            metadata={
                "step_type": "strategy_generation",
                "order": 3
            }
        )
        
        # Create successful execution result
        result = Mock()
        result.is_success = True
        result.execution_time_ms = 2500.0
        
        # Send step completed notification
        await self.orchestrator._send_step_completed(context, step, result)
        
        # Verify successful completion event
        mock_emitter.emit_agent_completed.assert_called_once_with(
            "optimization_agent",
            {
                "step_type": "strategy_generation",
                "execution_time_ms": 2500.0,
                "agent_name": "optimization_agent"
            }
        )
        
        self.record_metric("step_completed_success_tests", 1)
    
    @patch('netra_backend.app.agents.supervisor.workflow_orchestrator.create_agent_websocket_bridge')
    async def test_send_step_completed_failure(self, mock_create_bridge):
        """
        Test step completed notification for failed execution.
        
        BVJ: Validates that failed step execution events provide
        proper error information and failure context to users.
        """
        # Setup mock bridge and emitter
        mock_bridge = Mock()
        mock_emitter = AsyncMock()
        mock_bridge.create_user_emitter = AsyncMock(return_value=mock_emitter)
        mock_create_bridge.return_value = mock_bridge
        
        # Create execution context
        context = ExecutionContext(
            request_id="req_123",
            run_id="run_456",
            agent_name="test_agent",
            state=Mock(),
            stream_updates=True,
            user_id="user_789"
        )
        context.user_id = "user_789"
        context.thread_id = "thread_123"
        context.run_id = "run_456"
        
        # Create pipeline step
        step = PipelineStepConfig(
            agent_name="failed_agent",
            metadata={
                "step_type": "data_processing",
                "order": 2
            }
        )
        
        # Create failed execution result
        result = Mock()
        result.is_success = False
        result.error_message = "Data processing failed due to invalid format"
        
        # Send step completed notification
        await self.orchestrator._send_step_completed(context, step, result)
        
        # Verify error event
        mock_emitter.emit_custom_event.assert_called_once_with(
            "agent_error",
            {
                "agent_name": "failed_agent",
                "error_message": "Data processing failed due to invalid format",
                "step_type": "data_processing"
            }
        )
        
        self.record_metric("step_completed_failure_tests", 1)
    
    @patch('netra_backend.app.agents.supervisor.workflow_orchestrator.create_agent_websocket_bridge')
    async def test_send_workflow_completed_metrics(self, mock_create_bridge):
        """
        Test workflow completed notification with execution metrics.
        
        BVJ: Validates that workflow completion events provide comprehensive
        execution metrics for user visibility into overall workflow performance.
        """
        # Setup mock bridge and emitter
        mock_bridge = Mock()
        mock_emitter = AsyncMock()
        mock_bridge.create_user_emitter = AsyncMock(return_value=mock_emitter)
        mock_create_bridge.return_value = mock_bridge
        
        # Create execution context
        context = ExecutionContext(
            request_id="req_123",
            run_id="run_456",
            agent_name="test_agent",
            state=Mock(),
            stream_updates=True,
            user_id="user_789"
        )
        context.user_id = "user_789"
        context.thread_id = "thread_123"
        context.run_id = "run_456"
        
        # Create execution results with metrics
        results = [
            Mock(is_success=True, execution_time_ms=1000.0),
            Mock(is_success=True, execution_time_ms=1500.0),
            Mock(is_success=False, execution_time_ms=800.0)
        ]
        
        # Send workflow completed notification
        await self.orchestrator._send_workflow_completed(context, results)
        
        # Verify workflow completion event with metrics
        mock_emitter.emit_agent_completed.assert_called_once_with(
            "WorkflowOrchestrator",
            {
                "workflow_completed": True,
                "successful_steps": 2,
                "total_steps": 3,
                "total_execution_time_ms": 3300.0,
                "agent_name": "WorkflowOrchestrator"
            }
        )
        
        self.record_metric("workflow_completed_metrics_tests", 1)
    
    async def test_execute_workflow_step_integration(self):
        """
        Test workflow step execution with proper timing and context.
        
        BVJ: Validates that individual workflow steps execute properly
        with timing metrics and proper context propagation to execution engine.
        """
        # Create execution context
        context = ExecutionContext(
            request_id="req_123",
            run_id="run_456",
            agent_name="test_agent",
            state=Mock(),
            stream_updates=False,  # Disable WebSocket to focus on execution
            user_id="user_789"
        )
        
        # Create pipeline step
        step = PipelineStepConfig(
            agent_name="data_agent",
            metadata={
                "step_type": "data_analysis",
                "order": 1
            }
        )
        
        # Setup mock execution result
        mock_result = Mock()
        mock_result.execution_time_ms = None  # Will be set by orchestrator
        self.mock_execution_engine.execute_agent = AsyncMock(return_value=mock_result)
        
        # Execute workflow step
        with patch('time.time', side_effect=[100.0, 102.5]):  # 2.5 second execution
            result = await self.orchestrator._execute_workflow_step(context, step)
        
        # Verify execution engine called with proper context
        self.mock_execution_engine.execute_agent.assert_called_once()
        call_args = self.mock_execution_engine.execute_agent.call_args
        step_context, state = call_args[0]
        
        # Verify step context properties
        self.assertEqual(step_context.agent_name, "data_agent")
        self.assertEqual(step_context.request_id, "req_123")
        self.assertEqual(step_context.metadata, step.metadata)
        
        # Verify timing was added
        self.assertEqual(result.execution_time_ms, 2500.0)  # 2.5 seconds * 1000
        
        self.record_metric("workflow_step_execution_tests", 1)
    
    async def test_coordination_validator_integration(self):
        """
        Test agent coordination validation for Enterprise data integrity.
        
        BVJ: Validates that WorkflowOrchestrator integrates with AgentCoordinationValidator
        to ensure Enterprise-grade data integrity across multi-agent workflows.
        """
        # Create execution context
        context = ExecutionContext(
            request_id="req_123",
            run_id="enterprise_run_456",
            agent_name="test_agent",
            state=Mock(),
            stream_updates=False,
            user_id="enterprise_user_789"
        )
        context.state.triage_result = {"data_sufficiency": "sufficient"}
        
        # Setup mock execution results with data
        mock_results = [
            Mock(
                is_success=True,
                data={"agent": "triage", "result": "classification_complete"},
                metadata={"agent_name": "triage"}
            ),
            Mock(
                is_success=True,
                data={"agent": "data", "result": "analysis_complete"},
                metadata={"agent_name": "data"}
            )
        ]
        
        # Setup mock coordination validator
        mock_validation_result = CoordinationValidationResult(
            coordination_valid=True,
            execution_order_correct=True,
            data_handoffs_valid=True,
            tool_results_propagated=True,
            isolation_maintained=True,
            validation_details={"validation_passed": True}
        )
        
        self.orchestrator.coordination_validator.validate_complete_coordination = Mock(
            return_value=mock_validation_result
        )
        
        # Mock execution engine to return results
        async def mock_execute_agent(context, state):
            if "triage" in context.agent_name:
                return mock_results[0]
            elif "data" in context.agent_name:
                return mock_results[1]
            else:
                return Mock(is_success=True, data={}, metadata={})
        
        self.mock_execution_engine.execute_agent = AsyncMock(side_effect=mock_execute_agent)
        
        # Execute standard workflow
        with patch.object(self.orchestrator, '_send_workflow_started', new_callable=AsyncMock), \
             patch.object(self.orchestrator, '_send_workflow_completed', new_callable=AsyncMock):
            
            results = await self.orchestrator.execute_standard_workflow(context)
        
        # Verify coordination validation was called
        validation_call = self.orchestrator.coordination_validator.validate_complete_coordination
        validation_call.assert_called_once()
        
        # Verify validation parameters
        call_kwargs = validation_call.call_args[1]
        self.assertIn("workflow_id", call_kwargs)
        self.assertIn("executed_agents", call_kwargs)
        self.assertIn("agent_results", call_kwargs)
        self.assertIn("dependency_rules", call_kwargs)
        
        self.record_metric("coordination_validation_integration_tests", 1)
    
    async def test_coordination_validation_failure_handling(self):
        """
        Test handling of coordination validation failures.
        
        BVJ: Validates that WorkflowOrchestrator properly handles coordination validation
        failures by logging errors and adding validation metadata to results.
        """
        # Create execution context
        context = ExecutionContext(
            request_id="req_123",
            run_id="validation_fail_run",
            agent_name="test_agent",
            state=Mock(),
            stream_updates=False,
            user_id="user_789"
        )
        context.state.triage_result = {"data_sufficiency": "sufficient"}
        
        # Setup mock execution results
        mock_results = [
            Mock(
                is_success=True,
                data={"agent": "triage"},
                metadata={},
                success=None  # Test different result API patterns
            )
        ]
        
        # Setup failed coordination validation
        mock_validation_result = CoordinationValidationResult(
            coordination_valid=False,
            execution_order_correct=False,
            data_handoffs_valid=True,
            tool_results_propagated=False,
            isolation_maintained=True,
            validation_details={"errors": ["execution_order_violation", "missing_tool_results"]}
        )
        
        self.orchestrator.coordination_validator.validate_complete_coordination = Mock(
            return_value=mock_validation_result
        )
        
        # Mock execution engine
        self.mock_execution_engine.execute_agent = AsyncMock(return_value=mock_results[0])
        
        # Execute workflow with validation failure
        with patch.object(self.orchestrator, '_send_workflow_started', new_callable=AsyncMock), \
             patch.object(self.orchestrator, '_send_workflow_completed', new_callable=AsyncMock), \
             patch('netra_backend.app.agents.supervisor.workflow_orchestrator.logger') as mock_logger:
            
            results = await self.orchestrator.execute_standard_workflow(context)
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        self.assertIn("COORDINATION VALIDATION FAILED", error_call)
        
        # Verify validation failure metadata added to results
        result = results[0]
        self.assertIn('coordination_validation', result.metadata)
        validation_meta = result.metadata['coordination_validation']
        self.assertEqual(validation_meta['status'], 'FAILED')
        self.assertIn('details', validation_meta)
        
        self.record_metric("coordination_validation_failure_tests", 1)
    
    async def test_error_handling_continue_on_error(self):
        """
        Test error handling with continue_on_error configuration.
        
        BVJ: Validates that workflow orchestration handles step failures gracefully
        based on continue_on_error configuration, ensuring system resilience.
        """
        # Create execution context
        context = ExecutionContext(
            request_id="req_123",
            run_id="error_handling_run",
            agent_name="test_agent",
            state=Mock(),
            stream_updates=False,
            user_id="user_789"
        )
        context.state.triage_result = {"data_sufficiency": "partial"}
        
        # Setup execution results - second step fails
        mock_results = [
            Mock(is_success=True, data={"triage": "success"}),
            Mock(is_success=False, data={"error": "data_helper_failed"}, success=False),  # Failed step
            Mock(is_success=True, data={"reporting": "success"})  # Should not execute
        ]
        
        result_index = 0
        async def mock_execute_agent(context, state):
            nonlocal result_index
            result = mock_results[result_index]
            result_index += 1
            return result
        
        self.mock_execution_engine.execute_agent = AsyncMock(side_effect=mock_execute_agent)
        
        # Mock coordination validator
        self.orchestrator.coordination_validator.validate_complete_coordination = Mock(
            return_value=CoordinationValidationResult(
                coordination_valid=True,
                execution_order_correct=True,
                data_handoffs_valid=True,
                tool_results_propagated=True,
                isolation_maintained=True,
                validation_details={}
            )
        )
        
        # Execute workflow - should stop at failed step
        with patch.object(self.orchestrator, '_send_workflow_started', new_callable=AsyncMock), \
             patch.object(self.orchestrator, '_send_workflow_completed', new_callable=AsyncMock):
            
            results = await self.orchestrator.execute_standard_workflow(context)
        
        # Verify execution stopped at failed step (2 results: triage + failed data_helper)
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].is_success)  # triage succeeded
        self.assertFalse(results[1].is_success)  # data_helper failed
        
        self.record_metric("error_handling_tests", 1)
    
    def test_assess_data_completeness_high_completeness(self):
        """
        Test data completeness assessment for high completeness scenarios.
        
        BVJ: Validates that data completeness assessment correctly identifies
        high-quality data scenarios for full optimization workflows.
        """
        request_data = {
            "completeness": 0.9,
            "available_data": {
                "monthly_cost": 5000,
                "usage_patterns": "analysis_complete",
                "optimization_goals": "cost_reduction"
            }
        }
        
        assessment = self.orchestrator.assess_data_completeness(request_data)
        
        # Verify high completeness assessment
        self.assertEqual(assessment["completeness"], 0.9)
        self.assertEqual(assessment["workflow"], "full_optimization")
        self.assertEqual(assessment["confidence"], 0.90)
        self.assertEqual(assessment["data_sufficiency"], "sufficient")
        
        self.record_metric("data_completeness_high_tests", 1)
    
    def test_assess_data_completeness_calculated_from_fields(self):
        """
        Test data completeness calculation from available/missing data fields.
        
        BVJ: Validates that data completeness assessment can calculate completeness
        from field analysis when explicit completeness score is not provided.
        """
        request_data = {
            "available_data": {
                "field1": "value1",
                "field2": "value2",
                "field3": "value3"
            },
            "missing_data": ["field4", "field5"]  # 3 available, 2 missing = 60% complete
        }
        
        assessment = self.orchestrator.assess_data_completeness(request_data)
        
        # Verify calculated completeness (3/5 = 0.6)
        self.assertEqual(assessment["completeness"], 0.6)
        self.assertEqual(assessment["workflow"], "modified_optimization")
        self.assertEqual(assessment["confidence"], 0.65)
        self.assertEqual(assessment["data_sufficiency"], "partial")
        
        self.record_metric("data_completeness_calculated_tests", 1)
    
    def test_assess_data_completeness_low_completeness(self):
        """
        Test data completeness assessment for low completeness scenarios.
        
        BVJ: Validates that data completeness assessment correctly identifies
        low-quality data scenarios requiring data collection focus workflows.
        """
        request_data = {
            "completeness": 0.2,
            "available_data": {
                "basic_info": "minimal"
            }
        }
        
        assessment = self.orchestrator.assess_data_completeness(request_data)
        
        # Verify low completeness assessment
        self.assertEqual(assessment["completeness"], 0.2)
        self.assertEqual(assessment["workflow"], "data_collection_focus")
        self.assertEqual(assessment["confidence"], 0.10)
        self.assertEqual(assessment["data_sufficiency"], "insufficient")
        
        self.record_metric("data_completeness_low_tests", 1)
    
    async def test_select_workflow_full_optimization(self):
        """
        Test workflow selection for full optimization scenarios.
        
        BVJ: Validates that workflow selection provides comprehensive
        phase configuration for full optimization workflows.
        """
        request_data = {"completeness": 0.85}
        
        workflow_config = await self.orchestrator.select_workflow(request_data)
        
        # Verify full optimization workflow
        self.assertEqual(workflow_config["type"], "full_optimization")
        self.assertEqual(workflow_config["confidence"], 0.90)
        self.assertEqual(workflow_config["completeness"], 0.85)
        
        expected_phases = [
            "triage",
            "data_analysis", 
            "optimization",
            "actions",
            "reporting"
        ]
        self.assertEqual(workflow_config["phases"], expected_phases)
        
        self.record_metric("workflow_selection_full_tests", 1)
    
    async def test_select_workflow_modified_optimization(self):
        """
        Test workflow selection for modified optimization scenarios.
        
        BVJ: Validates that workflow selection provides appropriate
        phase configuration for partial data optimization workflows.
        """
        request_data = {"completeness": 0.6}
        
        workflow_config = await self.orchestrator.select_workflow(request_data)
        
        # Verify modified optimization workflow
        self.assertEqual(workflow_config["type"], "modified_optimization")
        self.assertEqual(workflow_config["confidence"], 0.65)
        self.assertEqual(workflow_config["completeness"], 0.6)
        
        expected_phases = [
            "triage",
            "quick_wins",
            "data_request",
            "partial_optimization",
            "phased_actions",
            "reporting_with_caveats"
        ]
        self.assertEqual(workflow_config["phases"], expected_phases)
        
        self.record_metric("workflow_selection_modified_tests", 1)
    
    async def test_select_workflow_data_collection_focus(self):
        """
        Test workflow selection for data collection focus scenarios.
        
        BVJ: Validates that workflow selection provides appropriate
        phase configuration for data collection and education workflows.
        """
        request_data = {"completeness": 0.1}
        
        workflow_config = await self.orchestrator.select_workflow(request_data)
        
        # Verify data collection focus workflow
        self.assertEqual(workflow_config["type"], "data_collection_focus")
        self.assertEqual(workflow_config["confidence"], 0.10)
        self.assertEqual(workflow_config["completeness"], 0.1)
        
        expected_phases = [
            "triage",
            "educate",
            "collect",
            "demonstrate_value"
        ]
        self.assertEqual(workflow_config["phases"], expected_phases)
        
        self.record_metric("workflow_selection_data_collection_tests", 1)
    
    def test_get_workflow_definition_compatibility(self):
        """
        Test workflow definition getter for test compatibility.
        
        BVJ: Validates that workflow definition getter provides
        consistent default workflow structure for monitoring and testing.
        """
        workflow_definition = self.orchestrator.get_workflow_definition()
        
        # Verify default workflow structure
        self.assertIsInstance(workflow_definition, list)
        self.assertEqual(len(workflow_definition), 5)
        
        # Verify expected agents
        expected_agents = ["triage", "data", "optimization", "actions", "reporting"]
        actual_agents = [step["agent_name"] for step in workflow_definition]
        self.assertEqual(actual_agents, expected_agents)
        
        # Verify step structure
        for i, step in enumerate(workflow_definition):
            self.assertIn("agent_name", step)
            self.assertIn("step_type", step)
            self.assertIn("order", step)
            self.assertIn("metadata", step)
            self.assertEqual(step["order"], i + 1)
        
        self.record_metric("workflow_definition_compatibility_tests", 1)
    
    def test_classify_data_sufficiency_boundaries(self):
        """
        Test data sufficiency classification boundary conditions.
        
        BVJ: Validates that data sufficiency classification provides
        consistent boundary handling for workflow decision making.
        """
        # Test sufficient boundary (>= 0.8)
        self.assertEqual(
            self.orchestrator._classify_data_sufficiency(0.8),
            "sufficient"
        )
        self.assertEqual(
            self.orchestrator._classify_data_sufficiency(0.9),
            "sufficient"
        )
        
        # Test partial boundary (>= 0.4 and < 0.8)
        self.assertEqual(
            self.orchestrator._classify_data_sufficiency(0.4),
            "partial"
        )
        self.assertEqual(
            self.orchestrator._classify_data_sufficiency(0.7),
            "partial"
        )
        
        # Test insufficient boundary (< 0.4)
        self.assertEqual(
            self.orchestrator._classify_data_sufficiency(0.3),
            "insufficient"
        )
        self.assertEqual(
            self.orchestrator._classify_data_sufficiency(0.0),
            "insufficient"
        )
        
        self.record_metric("data_sufficiency_boundary_tests", 1)
    
    def teardown_method(self, method):
        """Cleanup test fixtures after each test method."""
        # Record final test metrics
        total_metrics = len([k for k in self.get_all_metrics().keys() if k.endswith('_tests')])
        self.record_metric("total_test_categories", total_metrics)
        
        # Log test completion
        if self.get_test_context():
            test_time = self.get_metrics().execution_time
            logger = self.get_env().get("TEST_LOGGER", "test")
            print(f"Completed {self.get_test_context().test_name} in {test_time:.3f}s")
        
        super().teardown_method(method)


# Test execution markers for pytest integration
pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
    pytest.mark.ssot_compliance
]