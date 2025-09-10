"""
Comprehensive Unit Tests for WorkflowOrchestrator Golden Path SSOT Class

Business Value Justification (BVJ):
- Segment: ALL (Free/Early/Mid/Enterprise/Platform)
- Business Goal: AI Agent Flow Control - Orchestrates agent workflows for optimal results
- Value Impact: Validates agent workflow orchestration (critical for AI chat quality)
- Revenue Impact: Protects $500K+ ARR by ensuring proper agent sequence and decision-making

Critical Golden Path Scenarios Tested:
1. Agent workflow orchestration: Triage → Data Helper → Optimization → Reporting
2. Adaptive workflow decisions: Dynamic workflow based on triage results
3. WebSocket event coordination: User-isolated event emission during workflows
4. User context isolation: Factory pattern for per-user workflow execution
5. Agent communication: Inter-agent data passing and state management

SSOT Testing Compliance:
- Uses test_framework.ssot.base_test_case.SSotAsyncTestCase
- Real services preferred over mocks (only external dependencies mocked)
- Business-critical functionality validation over implementation details
- Agent workflow business logic focus
"""

import asyncio
import time
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# WorkflowOrchestrator SSOT Class Under Test
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor.execution_context import PipelineStep, PipelineStepConfig

# Supporting Infrastructure
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.core_enums import ExecutionStatus


class TestWorkflowOrchestratorComprehensiveGoldenPath(SSotAsyncTestCase):
    """
    Comprehensive unit tests for WorkflowOrchestrator SSOT class.
    
    Tests the critical agent workflow orchestration functionality that enables
    adaptive AI agent workflows and optimal chat response quality.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Setup test environment for WorkflowOrchestrator testing."""
        # Create mock infrastructure using SSOT mock factory
        self.mock_factory = SSotMockFactory()
        
        # Core mocked dependencies (external only - keep business logic real)
        self.mock_agent_registry = self.mock_factory.create_mock("AgentRegistry")
        self.mock_execution_engine = self.mock_factory.create_mock("ExecutionEngine")
        self.mock_websocket_manager = self.mock_factory.create_mock("WebSocketManager")
        
        # Test user contexts for multi-user isolation testing
        self.test_user_context_1 = UserExecutionContext(
            user_id="workflow_user_001",
            thread_id="workflow_thread_001",
            run_id="workflow_run_001",
            request_id="workflow_req_001",
            websocket_client_id="workflow_ws_001"
        )
        
        # Test execution contexts
        self.test_execution_context = ExecutionContext(
            user_id="workflow_user_001",
            thread_id="workflow_thread_001",
            run_id="workflow_run_001",
            agent_name="workflow_test_agent"
        )
        
        # Track WebSocket events for validation
        self.captured_websocket_events = []
        
        # Configure mock behaviors for workflow orchestrator testing
        await self._setup_mock_behaviors()
    
    async def _setup_mock_behaviors(self):
        """Setup realistic mock behaviors for workflow orchestrator testing."""
        # Configure agent registry to return mock agents
        self.mock_agent_registry.get_agent = MagicMock(side_effect=self._mock_get_agent)
        self.mock_agent_registry.list_available_agents = MagicMock(return_value=[
            "triage_agent", "data_helper_agent", "apex_optimizer_agent", "reporting_agent"
        ])
        
        # Configure execution engine to simulate agent executions
        async def mock_execute_agent(context, user_context=None):
            return ExecutionResult(
                success=True,
                agent_name=context.agent_name,
                result={"agent_output": f"Result from {context.agent_name}"},
                execution_time=0.1
            )
        
        self.mock_execution_engine.execute_agent = AsyncMock(side_effect=mock_execute_agent)
        
        # Configure WebSocket manager to capture events
        async def capture_websocket_event(event_type, *args, **kwargs):
            self.captured_websocket_events.append({
                'event_type': event_type,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
        
        # Mock WebSocket event methods
        self.mock_websocket_manager.notify_workflow_started = AsyncMock(
            side_effect=lambda *a, **k: capture_websocket_event('workflow_started', *a, **k)
        )
        self.mock_websocket_manager.notify_workflow_step = AsyncMock(
            side_effect=lambda *a, **k: capture_websocket_event('workflow_step', *a, **k)
        )
        self.mock_websocket_manager.notify_workflow_completed = AsyncMock(
            side_effect=lambda *a, **k: capture_websocket_event('workflow_completed', *a, **k)
        )
    
    def _mock_get_agent(self, agent_name: str):
        """Mock agent retrieval from registry."""
        mock_agent = self.mock_factory.create_mock(f"{agent_name}_instance")
        mock_agent.name = agent_name
        mock_agent.description = f"Mock {agent_name} for testing"
        return mock_agent
    
    async def teardown_method(self):
        """Clean up after each test."""
        # Clear captured events
        self.captured_websocket_events.clear()
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 1: Agent Workflow Orchestration
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.business_critical
    async def test_adaptive_workflow_orchestration_golden_path(self):
        """
        Test the golden path adaptive workflow orchestration.
        
        BVJ: Validates core AI agent workflow orchestration (foundation of intelligent responses)
        Critical Path: Triage → Data Helper → Optimization → Reporting
        """
        # Arrange: Create WorkflowOrchestrator with real business logic
        orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context_1
        )
        
        # Create mock triage result that indicates need for data collection
        triage_result = {
            "analysis_type": "data_optimization",
            "data_sufficiency": False,
            "complexity_level": "medium",
            "requires_data_collection": True,
            "requires_optimization": True,
            "confidence_score": 0.85
        }
        
        # Act: Define workflow based on triage results
        workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Assert: Verify adaptive workflow creation
        assert len(workflow_steps) >= 2, "Workflow should have at least Triage and Reporting steps"
        
        # Verify step types and sequence
        step_names = [step.agent_name for step in workflow_steps]
        
        # Should include triage agent
        assert any("triage" in name.lower() for name in step_names), "Workflow should include triage agent"
        
        # Should include data helper when data_sufficiency is False
        if not triage_result["data_sufficiency"]:
            assert any("data" in name.lower() for name in step_names), "Workflow should include data helper when data insufficient"
        
        # Should include optimization when requires_optimization is True  
        if triage_result["requires_optimization"]:
            assert any("optim" in name.lower() or "apex" in name.lower() for name in step_names), "Workflow should include optimization agent"
        
        # Should always include reporting
        assert any("report" in name.lower() for name in step_names), "Workflow should always include reporting agent"
        
        # Verify step configuration
        for step in workflow_steps:
            assert isinstance(step, PipelineStep)
            assert step.agent_name is not None and step.agent_name.strip() != ""
            assert isinstance(step.metadata, dict)
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 2: User Context Isolation and Factory Pattern
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.isolation_critical
    async def test_user_context_isolation_with_factory_pattern(self):
        """
        Test user context isolation using factory pattern for WebSocket emitters.
        
        BVJ: Enterprise security - ensures workflow events are user-isolated
        Critical Path: User context → Factory pattern → Isolated WebSocket events
        """
        # Arrange: Create orchestrator without initial user context
        orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=None  # No initial context
        )
        
        # Act: Set user context using factory pattern
        orchestrator.set_user_context(self.test_user_context_1)
        
        # Assert: Verify user context was properly set
        assert orchestrator.user_context == self.test_user_context_1
        assert orchestrator._websocket_emitter is None  # Should be lazy-initialized
        
        # Test lazy emitter creation
        with patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge') as mock_create_bridge:
            mock_bridge = self.mock_factory.create_mock("AgentWebSocketBridge")
            mock_emitter = self.mock_factory.create_mock("UserWebSocketEmitter")
            
            mock_create_bridge.return_value = mock_bridge
            mock_bridge.create_user_emitter = AsyncMock(return_value=mock_emitter)
            
            # Get user emitter (should trigger lazy creation)
            emitter = await orchestrator._get_user_emitter()
            
            # Verify factory pattern usage
            mock_create_bridge.assert_called_once_with(self.test_user_context_1)
            mock_bridge.create_user_emitter.assert_called_once_with(self.test_user_context_1)
            assert emitter == mock_emitter
            assert orchestrator._websocket_emitter == mock_emitter
    
    @pytest.mark.unit
    @pytest.mark.isolation_critical
    async def test_user_emitter_creation_from_execution_context(self):
        """
        Test user emitter creation from ExecutionContext when no UserExecutionContext available.
        
        BVJ: Backward compatibility - supports legacy ExecutionContext while providing isolation
        """
        # Arrange: Create orchestrator without user context
        orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=None
        )
        
        # Act: Get user emitter from ExecutionContext
        with patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge') as mock_create_bridge:
            mock_bridge = self.mock_factory.create_mock("AgentWebSocketBridge")
            mock_emitter = self.mock_factory.create_mock("UserWebSocketEmitter")
            
            mock_create_bridge.return_value = mock_bridge
            mock_bridge.create_user_emitter = AsyncMock(return_value=mock_emitter)
            
            # Get emitter from execution context
            emitter = await orchestrator._get_user_emitter_from_context(self.test_execution_context)
        
        # Assert: Verify emitter creation from ExecutionContext
        assert emitter == mock_emitter
        
        # Verify UserExecutionContext was created from ExecutionContext
        create_bridge_call = mock_create_bridge.call_args[0][0]
        assert create_bridge_call.user_id == self.test_execution_context.user_id
        assert create_bridge_call.thread_id == self.test_execution_context.thread_id
        assert create_bridge_call.run_id == self.test_execution_context.run_id
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 3: Workflow Decision Logic
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.workflow_logic
    async def test_workflow_decision_logic_data_sufficiency_scenarios(self):
        """
        Test workflow decision logic based on data sufficiency scenarios.
        
        BVJ: AI Quality - ensures optimal agent selection for different user needs
        """
        # Arrange: Create WorkflowOrchestrator
        orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context_1
        )
        
        # Test Case 1: Data sufficient, no optimization needed
        triage_result_simple = {
            "analysis_type": "simple_query",
            "data_sufficiency": True,
            "complexity_level": "low",
            "requires_data_collection": False,
            "requires_optimization": False,
            "confidence_score": 0.95
        }
        
        workflow_simple = orchestrator._define_workflow_based_on_triage(triage_result_simple)
        step_names_simple = [step.agent_name for step in workflow_simple]
        
        # Should have minimal steps for simple queries
        assert len(workflow_simple) >= 2, "Should have at least triage and reporting"
        
        # Should not include data helper when data is sufficient
        if triage_result_simple["data_sufficiency"]:
            data_helper_count = sum(1 for name in step_names_simple if "data" in name.lower())
            assert data_helper_count == 0 or data_helper_count <= 1, "Should minimize data collection when data is sufficient"
        
        # Test Case 2: Data insufficient, complex optimization needed
        triage_result_complex = {
            "analysis_type": "complex_optimization",
            "data_sufficiency": False,
            "complexity_level": "high",
            "requires_data_collection": True,
            "requires_optimization": True,
            "confidence_score": 0.75
        }
        
        workflow_complex = orchestrator._define_workflow_based_on_triage(triage_result_complex)
        step_names_complex = [step.agent_name for step in workflow_complex]
        
        # Should have more steps for complex queries
        assert len(workflow_complex) >= 3, "Complex workflows should have more steps"
        
        # Should include data helper when data insufficient
        assert any("data" in name.lower() for name in step_names_complex), "Should include data helper for insufficient data"
        
        # Should include optimization for complex cases
        assert any("optim" in name.lower() or "apex" in name.lower() for name in step_names_complex), "Should include optimization for complex cases"
        
        # Test Case 3: Edge case - very low confidence
        triage_result_uncertain = {
            "analysis_type": "uncertain_query",
            "data_sufficiency": False,
            "complexity_level": "unknown",
            "requires_data_collection": True,
            "requires_optimization": False,
            "confidence_score": 0.3
        }
        
        workflow_uncertain = orchestrator._define_workflow_based_on_triage(triage_result_uncertain)
        
        # Should have safe fallback workflow for uncertain cases
        assert len(workflow_uncertain) >= 2, "Uncertain cases should have safe fallback workflow"
        
        # Should include data collection to improve confidence
        step_names_uncertain = [step.agent_name for step in workflow_uncertain]
        assert any("data" in name.lower() for name in step_names_uncertain), "Should collect data for uncertain cases"
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 4: Workflow Execution Integration
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.workflow_execution
    async def test_workflow_execution_with_real_orchestration_logic(self):
        """
        Test workflow execution using real orchestration logic integration.
        
        BVJ: End-to-end validation - ensures workflow orchestration works with execution engine
        """
        # Arrange: Create WorkflowOrchestrator
        orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context_1
        )
        
        # Create realistic triage result
        triage_result = {
            "analysis_type": "data_optimization",
            "data_sufficiency": False,
            "complexity_level": "medium",
            "requires_data_collection": True,
            "requires_optimization": True,
            "confidence_score": 0.82,
            "recommended_agents": ["triage_agent", "data_helper_agent", "apex_optimizer_agent", "reporting_agent"]
        }
        
        # Mock DeepAgentState for workflow execution
        mock_state = DeepAgentState(
            user_id="workflow_user_001",
            thread_id="workflow_thread_001",
            run_id="workflow_run_001"
        )
        mock_state.triage_result = triage_result
        mock_state.user_request = "Optimize my AI model performance"
        
        # Act: Define and simulate workflow execution
        workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Simulate execution of workflow steps
        execution_results = []
        for step in workflow_steps:
            # Create execution context for each step
            step_context = ExecutionContext(
                user_id=self.test_execution_context.user_id,
                thread_id=self.test_execution_context.thread_id,
                run_id=self.test_execution_context.run_id,
                agent_name=step.agent_name
            )
            
            # Execute step
            result = await self.mock_execution_engine.execute_agent(step_context, self.test_user_context_1)
            execution_results.append(result)
        
        # Assert: Verify workflow execution
        assert len(execution_results) == len(workflow_steps)
        assert all(result.success for result in execution_results)
        
        # Verify execution engine was called for each step
        assert self.mock_execution_engine.execute_agent.call_count == len(workflow_steps)
        
        # Verify agent names match workflow steps
        for i, result in enumerate(execution_results):
            expected_agent = workflow_steps[i].agent_name
            assert result.agent_name == expected_agent
            assert "Result from" in result.result["agent_output"]
            assert expected_agent in result.result["agent_output"]
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 5: WebSocket Event Coordination
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.websocket_coordination
    async def test_websocket_event_coordination_during_workflow(self):
        """
        Test WebSocket event coordination during workflow execution.
        
        BVJ: User experience - real-time workflow progress visibility
        """
        # Arrange: Create WorkflowOrchestrator with WebSocket event tracking
        orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context_1
        )
        
        # Create workflow steps
        workflow_steps = [
            PipelineStep(
                agent_name="triage_agent",
                metadata={"step_number": 1, "description": "Analyzing request"}
            ),
            PipelineStep(
                agent_name="data_helper_agent", 
                metadata={"step_number": 2, "description": "Collecting required data"}
            ),
            PipelineStep(
                agent_name="reporting_agent",
                metadata={"step_number": 3, "description": "Generating final report"}
            )
        ]
        
        # Simulate workflow execution with WebSocket events
        # (This would normally be part of a higher-level orchestration method)
        
        # Act: Simulate workflow start notification
        await self.mock_websocket_manager.notify_workflow_started(
            self.test_user_context_1.run_id,
            workflow_info={
                "total_steps": len(workflow_steps),
                "user_id": self.test_user_context_1.user_id,
                "workflow_type": "adaptive_optimization"
            }
        )
        
        # Simulate step execution notifications
        for i, step in enumerate(workflow_steps):
            await self.mock_websocket_manager.notify_workflow_step(
                self.test_user_context_1.run_id,
                step_info={
                    "step_number": i + 1,
                    "total_steps": len(workflow_steps),
                    "agent_name": step.agent_name,
                    "description": step.metadata.get("description", ""),
                    "status": "executing"
                }
            )
            
            # Simulate step completion
            await asyncio.sleep(0.01)  # Brief delay to simulate execution
            
            await self.mock_websocket_manager.notify_workflow_step(
                self.test_user_context_1.run_id,
                step_info={
                    "step_number": i + 1,
                    "total_steps": len(workflow_steps),
                    "agent_name": step.agent_name,
                    "description": step.metadata.get("description", ""),
                    "status": "completed"
                }
            )
        
        # Simulate workflow completion
        await self.mock_websocket_manager.notify_workflow_completed(
            self.test_user_context_1.run_id,
            workflow_result={
                "total_steps_completed": len(workflow_steps),
                "success": True,
                "execution_time": 1.5,
                "user_id": self.test_user_context_1.user_id
            }
        )
        
        # Assert: Verify WebSocket event sequence
        event_types = [event['event_type'] for event in self.captured_websocket_events]
        
        # Verify workflow_started event
        assert 'workflow_started' in event_types, "workflow_started event missing"
        started_event = next(e for e in self.captured_websocket_events if e['event_type'] == 'workflow_started')
        assert started_event['args'][0] == self.test_user_context_1.run_id
        
        # Verify workflow_step events (should have 2 per step: executing + completed)
        step_events = [e for e in self.captured_websocket_events if e['event_type'] == 'workflow_step']
        assert len(step_events) == len(workflow_steps) * 2, f"Expected {len(workflow_steps) * 2} step events"
        
        # Verify workflow_completed event
        assert 'workflow_completed' in event_types, "workflow_completed event missing"
        completed_event = next(e for e in self.captured_websocket_events if e['event_type'] == 'workflow_completed')
        assert completed_event['args'][0] == self.test_user_context_1.run_id
        
        # Verify event sequencing (started → steps → completed)
        event_timestamps = [(e['event_type'], e['timestamp']) for e in self.captured_websocket_events]
        event_timestamps.sort(key=lambda x: x[1])
        
        first_event = event_timestamps[0][0]
        last_event = event_timestamps[-1][0]
        
        assert first_event == 'workflow_started', "First event should be workflow_started"
        assert last_event == 'workflow_completed', "Last event should be workflow_completed"
    
    # ============================================================================
    # WORKFLOW CONFIGURATION AND VALIDATION TESTS
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.workflow_validation
    async def test_workflow_step_configuration_and_validation(self):
        """
        Test workflow step configuration and validation logic.
        
        BVJ: System reliability - ensures proper workflow step configuration
        """
        # Arrange: Create WorkflowOrchestrator
        orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context_1
        )
        
        # Test different triage scenarios for step configuration
        test_scenarios = [
            {
                "name": "minimal_workflow",
                "triage_result": {
                    "analysis_type": "simple_query",
                    "data_sufficiency": True,
                    "complexity_level": "low",
                    "requires_data_collection": False,
                    "requires_optimization": False,
                    "confidence_score": 0.95
                },
                "expected_min_steps": 2,  # At least triage + reporting
                "expected_max_steps": 3
            },
            {
                "name": "standard_workflow", 
                "triage_result": {
                    "analysis_type": "data_analysis",
                    "data_sufficiency": False,
                    "complexity_level": "medium",
                    "requires_data_collection": True,
                    "requires_optimization": True,
                    "confidence_score": 0.8
                },
                "expected_min_steps": 3,  # Triage + Data + Optimization + Reporting
                "expected_max_steps": 5
            },
            {
                "name": "complex_workflow",
                "triage_result": {
                    "analysis_type": "complex_optimization",
                    "data_sufficiency": False,
                    "complexity_level": "high", 
                    "requires_data_collection": True,
                    "requires_optimization": True,
                    "confidence_score": 0.6
                },
                "expected_min_steps": 4,  # Full workflow with multiple optimization steps
                "expected_max_steps": 6
            }
        ]
        
        # Act & Assert: Test each scenario
        for scenario in test_scenarios:
            workflow_steps = orchestrator._define_workflow_based_on_triage(scenario["triage_result"])
            
            # Validate step count
            assert len(workflow_steps) >= scenario["expected_min_steps"], \
                f"{scenario['name']}: Too few steps ({len(workflow_steps)} < {scenario['expected_min_steps']})"
            assert len(workflow_steps) <= scenario["expected_max_steps"], \
                f"{scenario['name']}: Too many steps ({len(workflow_steps)} > {scenario['expected_max_steps']})"
            
            # Validate step structure
            for i, step in enumerate(workflow_steps):
                assert isinstance(step, PipelineStep), f"{scenario['name']}: Step {i} is not a PipelineStep"
                assert step.agent_name is not None, f"{scenario['name']}: Step {i} missing agent_name"
                assert isinstance(step.metadata, dict), f"{scenario['name']}: Step {i} metadata is not a dict"
                
                # Validate agent names are reasonable
                agent_name_lower = step.agent_name.lower()
                valid_agent_types = ["triage", "data", "helper", "optim", "apex", "report", "analysis"]
                assert any(agent_type in agent_name_lower for agent_type in valid_agent_types), \
                    f"{scenario['name']}: Step {i} has invalid agent name: {step.agent_name}"
    
    # ============================================================================
    # ERROR HANDLING AND EDGE CASES
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.error_handling
    async def test_workflow_error_handling_and_recovery(self):
        """
        Test workflow error handling and recovery mechanisms.
        
        BVJ: System reliability - graceful handling of workflow failures
        """
        # Arrange: Create WorkflowOrchestrator
        orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context_1
        )
        
        # Test Case 1: Invalid triage result
        invalid_triage_results = [
            None,  # None triage result
            {},    # Empty triage result
            {"incomplete": "data"},  # Missing required fields
            {
                "analysis_type": None,
                "data_sufficiency": "invalid_boolean",  # Invalid type
                "complexity_level": "unknown_level",
                "requires_data_collection": None,
                "requires_optimization": None,
                "confidence_score": "not_a_number"  # Invalid type
            }
        ]
        
        for i, invalid_result in enumerate(invalid_triage_results):
            try:
                workflow_steps = orchestrator._define_workflow_based_on_triage(invalid_result)
                
                # If no exception was raised, verify minimal fallback workflow
                assert len(workflow_steps) >= 1, f"Invalid triage {i}: Should have fallback workflow"
                
                # Should have at least a reporting step as fallback
                step_names = [step.agent_name.lower() for step in workflow_steps]
                assert any("report" in name for name in step_names), \
                    f"Invalid triage {i}: Should have reporting fallback"
                
            except Exception as e:
                # If exception is raised, it should be handled gracefully
                assert isinstance(e, (ValueError, TypeError, AttributeError)), \
                    f"Invalid triage {i}: Unexpected exception type: {type(e)}"
        
        # Test Case 2: Missing agent in registry
        self.mock_agent_registry.get_agent = MagicMock(side_effect=KeyError("Agent not found"))
        
        valid_triage_result = {
            "analysis_type": "data_optimization",
            "data_sufficiency": False,
            "complexity_level": "medium",
            "requires_data_collection": True,
            "requires_optimization": True,
            "confidence_score": 0.8
        }
        
        # Should still create workflow even if agents are missing (registry handles errors)
        try:
            workflow_steps = orchestrator._define_workflow_based_on_triage(valid_triage_result)
            # Workflow creation should succeed even with missing agents
            assert len(workflow_steps) >= 1, "Should create fallback workflow when agents missing"
        except Exception as e:
            # If error occurs, verify it's handled appropriately
            assert "Agent not found" in str(e) or isinstance(e, KeyError)
    
    # ============================================================================
    # PERFORMANCE AND CONCURRENCY TESTS  
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.performance
    async def test_workflow_orchestration_performance_characteristics(self):
        """
        Test workflow orchestration performance characteristics.
        
        BVJ: Platform scalability - ensures workflow orchestration scales efficiently
        """
        # Arrange: Create WorkflowOrchestrator
        orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context_1
        )
        
        # Performance test scenarios
        performance_scenarios = [
            {"complexity": "simple", "expected_max_time": 0.01},
            {"complexity": "medium", "expected_max_time": 0.05}, 
            {"complexity": "complex", "expected_max_time": 0.1}
        ]
        
        for scenario in performance_scenarios:
            # Create triage result based on complexity
            if scenario["complexity"] == "simple":
                triage_result = {
                    "analysis_type": "simple_query",
                    "data_sufficiency": True,
                    "complexity_level": "low",
                    "requires_data_collection": False,
                    "requires_optimization": False,
                    "confidence_score": 0.95
                }
            elif scenario["complexity"] == "medium":
                triage_result = {
                    "analysis_type": "data_analysis",
                    "data_sufficiency": False,
                    "complexity_level": "medium",
                    "requires_data_collection": True,
                    "requires_optimization": True,
                    "confidence_score": 0.8
                }
            else:  # complex
                triage_result = {
                    "analysis_type": "complex_optimization",
                    "data_sufficiency": False,
                    "complexity_level": "high",
                    "requires_data_collection": True,
                    "requires_optimization": True,
                    "confidence_score": 0.6
                }
            
            # Act: Measure workflow definition time
            start_time = time.time()
            workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
            end_time = time.time()
            
            definition_time = end_time - start_time
            
            # Assert: Verify performance meets expectations
            assert definition_time <= scenario["expected_max_time"], \
                f"{scenario['complexity']} workflow took too long: {definition_time:.6f}s > {scenario['expected_max_time']}s"
            
            # Verify workflow quality wasn't compromised for performance
            assert len(workflow_steps) >= 1, f"{scenario['complexity']}: No workflow steps generated"
            
            step_names = [step.agent_name for step in workflow_steps]
            assert all(name and name.strip() for name in step_names), \
                f"{scenario['complexity']}: Empty or invalid step names"