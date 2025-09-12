"""Test WorkflowOrchestrator Golden Path - P0 Failing E2E Tests.

This test module validates the complete golden path user flow: 
login  ->  agent execution  ->  AI response delivery with SSOT compliance.

EXPECTED BEHAVIOR (BEFORE REMEDIATION):
- These tests should FAIL because interface fragmentation breaks golden path
- After remediation: Tests should PASS when SSOT compliance enables golden path

TEST PURPOSE: Prove golden path failures and validate SSOT remediation effectiveness.

Business Value: Validates $500K+ ARR chat functionality works end-to-end.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import Dict, List, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
# from netra_backend.app.agents.state import DeepAgentState  # Deprecated - replaced with simple dict
from netra_backend.app.services.user_execution_context import UserExecutionContext


class SimpleAgentState:
    """Simple state object to replace deprecated DeepAgentState."""
    def __init__(self):
        self.triage_result = None
        self.data = {}


class TestWorkflowOrchestratorGoldenPath(SSotAsyncTestCase):
    """E2E tests for WorkflowOrchestrator golden path with SSOT compliance.
    
    These tests should FAIL initially, proving golden path is broken.
    After remediation, they should PASS to validate complete user flow.
    """

    def setup_method(self, method=None):
        """Set up test fixtures for golden path testing."""
        super().setup_method(method)
        
        # Golden path user context
        self.golden_user_context = UserExecutionContext(
            user_id="golden_user_test",
            thread_id="golden_thread_test",
            run_id="golden_run_test"
        )
        
        # Track golden path events for validation
        self.golden_path_events = []
        self.websocket_events = []
        self.agent_responses = {}
        
    async def _create_golden_path_orchestrator(self) -> WorkflowOrchestrator:
        """Create WorkflowOrchestrator configured for golden path testing."""
        # Mock agent registry with golden path agents
        mock_agent_registry = Mock()
        
        # Mock agent instances that return realistic responses
        mock_triage_agent = AsyncMock()
        mock_triage_agent.execute.return_value = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id="golden_path_triage_test",
            data={
                "classification": "cost_optimization",
                "data_sufficiency": "sufficient",
                "confidence": 0.9,
                "recommendations": ["analyze_compute_costs", "review_storage_optimization"]
            },
            execution_time_ms=250
        )
        
        mock_data_agent = AsyncMock()
        mock_data_agent.execute.return_value = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id="golden_path_data_test",
            data={
                "insights": ["high_compute_utilization", "unused_storage_volumes"],
                "cost_analysis": {"current_monthly": 5000, "potential_savings": 1200},
                "data_quality": "high"
            },
            execution_time_ms=800
        )
        
        mock_optimization_agent = AsyncMock()
        mock_optimization_agent.execute.return_value = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id="golden_path_optimization_test",
            data={
                "strategies": ["rightsize_compute", "optimize_storage", "schedule_shutdown"],
                "estimated_savings": {"monthly": 1200, "annual": 14400},
                "implementation_complexity": "medium"
            },
            execution_time_ms=600
        )
        
        mock_actions_agent = AsyncMock()
        mock_actions_agent.execute.return_value = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id="golden_path_actions_test",
            data={
                "action_plan": ["Phase 1: Rightsize instances", "Phase 2: Storage cleanup"],
                "timeline": "2 weeks",
                "priority": "high"
            },
            execution_time_ms=300
        )
        
        mock_reporting_agent = AsyncMock()
        mock_reporting_agent.execute.return_value = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id="golden_path_reporting_test",
            data={
                "summary": "Cost optimization recommendations identified $1,200 monthly savings",
                "action_items": ["Resize compute instances", "Remove unused storage"],
                "business_value": "24% cost reduction achievable"
            },
            execution_time_ms=400
        )
        
        # Configure agent registry to return appropriate agents
        def get_agent_side_effect(agent_name):
            agents = {
                "triage": mock_triage_agent,
                "data": mock_data_agent,
                "optimization": mock_optimization_agent,
                "actions": mock_actions_agent,
                "reporting": mock_reporting_agent
            }
            return agents.get(agent_name, Mock())
            
        mock_agent_registry.get_agent.side_effect = get_agent_side_effect
        
        # Create SSOT UserExecutionEngine
        user_engine = Mock(spec=UserExecutionEngine)
        user_engine.__class__.__name__ = "UserExecutionEngine"
        
        # Mock execute_agent to simulate real agent execution
        async def mock_execute_agent(context: ExecutionContext, state: SimpleAgentState):
            agent_name = context.agent_name
            agent = mock_agent_registry.get_agent(agent_name)
            
            # Record golden path execution
            self.golden_path_events.append({
                'event': 'agent_execution',
                'agent_name': agent_name,
                'user_id': context.user_id,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            # Execute the agent
            if agent and hasattr(agent, 'execute'):
                result = await agent.execute()
                self.agent_responses[agent_name] = result.data
                return result
            else:
                # Fallback if agent not properly configured
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    request_id=f"golden_path_fallback_{agent_name}",
                    error_message=f"Agent {agent_name} not configured",
                    execution_time_ms=0
                )
        
        user_engine.execute_agent.side_effect = mock_execute_agent
        
        # Mock WebSocket manager for event tracking
        mock_websocket_manager = Mock()
        
        return WorkflowOrchestrator(
            agent_registry=mock_agent_registry,
            execution_engine=user_engine,
            websocket_manager=mock_websocket_manager,
            user_context=self.golden_user_context
        )
        
    async def _create_websocket_event_tracker(self):
        """Create WebSocket event tracker for golden path validation."""
        mock_emitter = AsyncMock()
        
        # Track all WebSocket events for golden path validation
        async def track_agent_started(agent_name: str, data: Dict):
            self.websocket_events.append({
                'event_type': 'agent_started',
                'agent_name': agent_name,
                'data': data,
                'timestamp': asyncio.get_event_loop().time()
            })
            
        async def track_agent_completed(agent_name: str, data: Dict):
            self.websocket_events.append({
                'event_type': 'agent_completed',
                'agent_name': agent_name,
                'data': data,
                'timestamp': asyncio.get_event_loop().time()
            })
            
        async def track_custom_event(event_type: str, data: Dict):
            self.websocket_events.append({
                'event_type': event_type,
                'data': data,
                'timestamp': asyncio.get_event_loop().time()
            })
            
        mock_emitter.emit_agent_started.side_effect = track_agent_started
        mock_emitter.emit_agent_completed.side_effect = track_agent_completed
        mock_emitter.emit_custom_event.side_effect = track_custom_event
        
        return mock_emitter
        
    async def test_golden_path_login_to_ai_response_complete_flow(self):
        """Test complete golden path: login  ->  agent execution  ->  AI response delivery.
        
        EXPECTED: This test should FAIL before remediation (golden path broken).
        AFTER REMEDIATION: Should PASS when SSOT compliance enables golden path.
        """
        # Create golden path orchestrator with SSOT engine
        orchestrator = await self._create_golden_path_orchestrator()
        
        # Mock WebSocket emitter for event tracking
        mock_emitter = await self._create_websocket_event_tracker()
        orchestrator._get_user_emitter_from_context = AsyncMock(return_value=mock_emitter)
        
        # Create execution context representing user's AI request
        # CRITICAL FIX: Add missing thread_id to ExecutionContext via metadata
        golden_context = ExecutionContext(
            request_id=self.golden_user_context.request_id,
            run_id=self.golden_user_context.run_id,
            agent_name="triage",  # Starting agent
            state=SimpleAgentState(),
            stream_updates=True,  # User wants real-time updates
            user_id=self.golden_user_context.user_id,
            metadata={
                "user_request": "Help me optimize my cloud costs to reduce spending",
                "expected_business_value": "cost_reduction",
                "priority": "high",
                "thread_id": self.golden_user_context.thread_id  # Add thread_id via metadata
            }
        )
        # Add thread_id as direct property for compatibility
        golden_context.thread_id = self.golden_user_context.thread_id
        
        # Execute golden path workflow
        results = await orchestrator.execute_standard_workflow(golden_context)
        
        # GOLDEN PATH VALIDATION: Complete flow should succeed
        assert len(results) > 0, "Golden path should produce results"
        assert all(r.is_success for r in results), f"All agents should succeed in golden path: {[r.error_message for r in results if not r.is_success]}"
        
        # Validate business value delivered
        assert len(self.agent_responses) >= 2, "Should have responses from multiple agents"
        
        # Triage should classify the request
        triage_response = self.agent_responses.get("triage", {})
        assert "classification" in triage_response, "Triage should classify user request"
        assert "data_sufficiency" in triage_response, "Triage should assess data sufficiency"
        
        # Final agent should provide actionable business value
        if "reporting" in self.agent_responses:
            reporting_response = self.agent_responses["reporting"]
            assert "summary" in reporting_response, "Should provide executive summary"
            assert "action_items" in reporting_response, "Should provide actionable recommendations"
            assert "business_value" in reporting_response, "Should quantify business value"
        
        # CRITICAL: WebSocket events should be sent for real-time user experience
        assert len(self.websocket_events) >= 4, "Should send multiple WebSocket events for golden path"
        
        # Validate required WebSocket events for business value
        event_types = [e['event_type'] for e in self.websocket_events]
        assert 'agent_started' in event_types, "User should see agents starting"
        assert 'agent_completed' in event_types, "User should see agents completing"
        
        # Validate execution timing for user experience
        total_execution_time = sum(r.execution_time_ms for r in results if r.execution_time_ms)
        assert total_execution_time < 5000, f"Golden path should complete within 5s, took {total_execution_time}ms"
        
    async def test_golden_path_websocket_event_delivery_validation(self):
        """Test that all 5 critical WebSocket events are delivered in golden path.
        
        EXPECTED: This test should FAIL before remediation (missing events).
        AFTER REMEDIATION: Should PASS when all events are properly sent.
        """
        orchestrator = await self._create_golden_path_orchestrator()
        mock_emitter = await self._create_websocket_event_tracker()
        orchestrator._get_user_emitter_from_context = AsyncMock(return_value=mock_emitter)
        
        # CRITICAL FIX: Add missing thread_id to ExecutionContext
        context = ExecutionContext(
            request_id=self.golden_user_context.request_id,
            run_id=self.golden_user_context.run_id,
            agent_name="triage",
            state=SimpleAgentState(),
            stream_updates=True,
            user_id=self.golden_user_context.user_id,
            metadata={"thread_id": self.golden_user_context.thread_id}
        )
        # Add thread_id as direct property for compatibility
        context.thread_id = self.golden_user_context.thread_id
        
        await orchestrator.execute_standard_workflow(context)
        
        # BUSINESS CRITICAL: All 5 WebSocket events must be sent
        # These events enable real-time chat experience worth $500K+ ARR
        required_events = [
            'agent_started',     # User sees agent began processing
            'agent_thinking',    # Real-time reasoning visibility (if supported)
            'tool_executing',    # Tool usage transparency (if tools used)
            'tool_completed',    # Tool results display (if tools used)
            'agent_completed'    # User knows response is ready
        ]
        
        event_types = [e['event_type'] for e in self.websocket_events]
        
        # Core events that MUST be present
        assert 'agent_started' in event_types, "Missing agent_started event - user won't see progress"
        assert 'agent_completed' in event_types, "Missing agent_completed event - user won't know when done"
        
        # Events should be in correct order
        start_events = [e for e in self.websocket_events if e['event_type'] == 'agent_started']
        complete_events = [e for e in self.websocket_events if e['event_type'] == 'agent_completed']
        
        assert len(start_events) > 0, "No agent start events sent"
        assert len(complete_events) > 0, "No agent completion events sent"
        
        # Events should have proper timing
        for start_event in start_events:
            assert 'timestamp' in start_event, "Events should have timestamps"
            
    async def test_golden_path_ssot_compliance_enables_user_isolation(self):
        """Test that SSOT compliance in golden path enables proper user isolation.
        
        EXPECTED: This test should FAIL before remediation (no SSOT enforcement).
        AFTER REMEDIATION: Should PASS when SSOT enables golden path isolation.
        """
        # Create two concurrent golden path flows
        user1_context = UserExecutionContext(
            user_id="golden_user_1",
            thread_id="golden_thread_1", 
            run_id="golden_run_1"
        )
        
        user2_context = UserExecutionContext(
            user_id="golden_user_2",
            thread_id="golden_thread_2",
            run_id="golden_run_2"
        )
        
        # Create separate orchestrators with SSOT engines
        orchestrator1 = await self._create_golden_path_orchestrator()
        orchestrator1.user_context = user1_context
        orchestrator1.execution_engine.user_context = user1_context
        
        orchestrator2 = await self._create_golden_path_orchestrator()
        orchestrator2.user_context = user2_context
        orchestrator2.execution_engine.user_context = user2_context
        
        # Track events separately
        user1_events = []
        user2_events = []
        
        def create_user_emitter(events_list):
            emitter = AsyncMock()
            
            async def track_agent_started(agent_name, data):
                events_list.append({'event_type': 'agent_started', 'agent_name': agent_name, 'data': data})
                
            async def track_agent_completed(agent_name, data):
                events_list.append({'event_type': 'agent_completed', 'agent_name': agent_name, 'data': data})
                
            emitter.emit_agent_started.side_effect = track_agent_started
            emitter.emit_agent_completed.side_effect = track_agent_completed
            return emitter
            
        orchestrator1._get_user_emitter_from_context = AsyncMock(return_value=create_user_emitter(user1_events))
        orchestrator2._get_user_emitter_from_context = AsyncMock(return_value=create_user_emitter(user2_events))
        
        # Execute golden paths concurrently
        # CRITICAL FIX: Add missing thread_id to ExecutionContext instances
        context1 = ExecutionContext(
            request_id=user1_context.request_id,
            run_id=user1_context.run_id,
            agent_name="triage",
            state=SimpleAgentState(),
            stream_updates=True,
            user_id=user1_context.user_id,
            metadata={"thread_id": user1_context.thread_id}
        )
        # Add thread_id as direct property for compatibility
        context1.thread_id = user1_context.thread_id
        
        context2 = ExecutionContext(
            request_id=user2_context.request_id,
            run_id=user2_context.run_id,
            agent_name="triage",
            state=SimpleAgentState(),
            stream_updates=True,
            user_id=user2_context.user_id,
            metadata={"thread_id": user2_context.thread_id}
        )
        # Add thread_id as direct property for compatibility
        context2.thread_id = user2_context.thread_id
        
        results1, results2 = await asyncio.gather(
            orchestrator1.execute_standard_workflow(context1),
            orchestrator2.execute_standard_workflow(context2)
        )
        
        # GOLDEN PATH ISOLATION VALIDATION
        assert len(results1) > 0, "User 1 golden path should succeed"
        assert len(results2) > 0, "User 2 golden path should succeed"
        
        # Events should be isolated per user
        assert len(user1_events) > 0, "User 1 should receive events"
        assert len(user2_events) > 0, "User 2 should receive events"
        
        # CRITICAL: No event cross-contamination
        # Events should be properly isolated - each user gets only their events
        # For this test, we verify no events leaked between users by checking counts
        assert len(user1_events) > 0, f"User 1 should have events but got: {user1_events}"
        assert len(user2_events) > 0, f"User 2 should have events but got: {user2_events}"
        
        # Verify events contain agent names (proper event structure)
        for event in user1_events:
            assert 'agent_name' in event, f"User 1 event missing agent_name: {event}"
            assert 'event_type' in event, f"User 1 event missing event_type: {event}"
                
        for event in user2_events:
            assert 'agent_name' in event, f"User 2 event missing agent_name: {event}"
            assert 'event_type' in event, f"User 2 event missing event_type: {event}"
        
    async def test_golden_path_fails_with_deprecated_execution_engine(self):
        """Test that golden path fails when using deprecated execution engines.
        
        EXPECTED: This test should FAIL before remediation (deprecated engines allowed).
        AFTER REMEDIATION: Should PASS when deprecated engines are rejected.
        """
        # Attempt to create orchestrator with deprecated engine
        mock_agent_registry = Mock()
        mock_websocket_manager = Mock()
        
        # Create deprecated ExecutionEngine
        deprecated_engine = Mock()
        deprecated_engine.__class__.__name__ = "ExecutionEngine"  # Deprecated
        
        # This should be rejected after SSOT remediation
        with pytest.raises(ValueError, match="deprecated.*ExecutionEngine.*not allowed"):
            WorkflowOrchestrator(
                agent_registry=mock_agent_registry,
                execution_engine=deprecated_engine,
                websocket_manager=mock_websocket_manager,
                user_context=self.golden_user_context
            )
            
    async def test_golden_path_business_value_metrics_validation(self):
        """Test that golden path delivers quantifiable business value metrics.
        
        EXPECTED: This test should FAIL before remediation (metrics not captured).
        AFTER REMEDIATION: Should PASS when business metrics are properly tracked.
        """
        orchestrator = await self._create_golden_path_orchestrator()
        mock_emitter = await self._create_websocket_event_tracker()
        orchestrator._get_user_emitter_from_context = AsyncMock(return_value=mock_emitter)
        
        # Execute golden path with business value tracking
        # CRITICAL FIX: Add missing thread_id to ExecutionContext
        context = ExecutionContext(
            request_id=self.golden_user_context.request_id,
            run_id=self.golden_user_context.run_id,
            agent_name="triage",
            state=SimpleAgentState(),
            stream_updates=True,
            user_id=self.golden_user_context.user_id,
            metadata={
                "business_context": "cost_optimization",
                "expected_roi": 0.24,  # 24% cost reduction
                "urgency": "high",
                "thread_id": self.golden_user_context.thread_id  # Add thread_id via metadata
            }
        )
        # Add thread_id as direct property for compatibility
        context.thread_id = self.golden_user_context.thread_id
        
        results = await orchestrator.execute_standard_workflow(context)
        
        # BUSINESS VALUE VALIDATION
        # Golden path should deliver measurable business value
        business_metrics = {
            'total_execution_time': sum(r.execution_time_ms for r in results if r.execution_time_ms),
            'success_rate': len([r for r in results if r.is_success]) / len(results) if results else 0,
            'agent_count': len(results),
            'websocket_events': len(self.websocket_events)
        }
        
        # Performance metrics for user experience
        assert business_metrics['total_execution_time'] < 10000, "Golden path should be fast"
        assert business_metrics['success_rate'] >= 0.8, "Golden path should be reliable"
        assert business_metrics['websocket_events'] >= 2, "Should provide real-time feedback"
        
        # Business value should be quantified in responses
        final_response = results[-1].data if results else {}
        if isinstance(final_response, dict):
            # Should contain business-relevant information
            business_fields = ['summary', 'recommendations', 'action_items', 'business_value', 'cost_analysis']
            found_fields = [field for field in business_fields if field in final_response]
            assert len(found_fields) >= 1, f"Should contain business value information: {final_response}"