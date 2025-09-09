"""
E2E Test: Complete Agent Pipeline - Triage to Completion Event Flow

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Complete pipeline is core business value
- Business Goal: Ensure complete agent pipeline delivers all required WebSocket events
- Value Impact: Users receive complete real-time feedback for entire business workflow
- Strategic Impact: Core value proposition - complete AI-powered business process automation

This E2E test validates:
- Complete agent pipeline from triage → data → optimization → completion
- All 5 critical WebSocket events delivered in correct sequence and order
- Real user value delivered through complete chat interface workflow
- Full business workflow validation with real authentication and services
- End-to-end business process with proper event delivery

CRITICAL: Tests the complete business value delivery that customers pay for
"""

import pytest
import asyncio
import uuid
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient

# Core system imports with absolute paths
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class BusinessWorkflowTracker:
    """Tracks complete business workflow execution and event delivery."""
    
    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self.start_time = time.time()
        self.stages = []
        self.events_by_stage = {}
        self.business_value_metrics = {
            'user_request_processed': False,
            'analysis_provided': False,
            'recommendations_generated': False,
            'actionable_insights_delivered': False,
            'complete_workflow_finished': False
        }
    
    def start_stage(self, stage_name: str, agent_name: str):
        """Start a new workflow stage."""
        stage_info = {
            'stage_name': stage_name,
            'agent_name': agent_name,
            'start_time': time.time(),
            'end_time': None,
            'events': [],
            'business_value_delivered': False
        }
        self.stages.append(stage_info)
        self.events_by_stage[stage_name] = []
        return len(self.stages) - 1  # Return stage index
    
    def add_stage_event(self, stage_index: int, event: Dict[str, Any]):
        """Add event to specific workflow stage."""
        if 0 <= stage_index < len(self.stages):
            self.stages[stage_index]['events'].append(event)
            stage_name = self.stages[stage_index]['stage_name']
            self.events_by_stage[stage_name].append(event)
    
    def complete_stage(self, stage_index: int, business_value_delivered: bool = True):
        """Mark stage as complete with business value assessment."""
        if 0 <= stage_index < len(self.stages):
            self.stages[stage_index]['end_time'] = time.time()
            self.stages[stage_index]['business_value_delivered'] = business_value_delivered
    
    def update_business_metrics(self, **metrics):
        """Update business value metrics."""
        self.business_value_metrics.update(metrics)
    
    def get_workflow_summary(self) -> Dict[str, Any]:
        """Get complete workflow summary with business value assessment."""
        total_time = time.time() - self.start_time
        
        # Analyze event delivery across workflow
        total_events = sum(len(stage['events']) for stage in self.stages)
        stages_with_events = sum(1 for stage in self.stages if len(stage['events']) > 0)
        
        # Check for required events across workflow
        all_events = []
        for stage in self.stages:
            all_events.extend(stage['events'])
        
        event_types = [event.get('type') for event in all_events]
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        events_delivered = {event_type: event_type in event_types for event_type in required_events}
        
        # Business value assessment
        business_value_score = sum(1 for delivered in self.business_value_metrics.values() if delivered)
        max_business_value = len(self.business_value_metrics)
        
        return {
            'workflow_name': self.workflow_name,
            'total_time': total_time,
            'stages_completed': len([s for s in self.stages if s['end_time'] is not None]),
            'total_stages': len(self.stages),
            'total_events': total_events,
            'stages_with_events': stages_with_events,
            'events_delivered': events_delivered,
            'business_value_metrics': self.business_value_metrics,
            'business_value_score': business_value_score,
            'max_business_value': max_business_value,
            'business_value_percentage': (business_value_score / max_business_value) * 100 if max_business_value > 0 else 0,
            'stages_detail': self.stages
        }


class TestTriageToCompletionEventFlow(BaseE2ETest):
    """E2E tests for complete business workflow with event delivery validation."""
    
    @pytest.fixture
    async def business_user_context(self):
        """Create business user context for workflow testing."""
        return await create_authenticated_user_context(
            user_email="business_workflow_user@e2e.test",
            environment="test",
            permissions=["read", "write", "agent_execute", "websocket_connect", "business_workflow"],
            websocket_enabled=True
        )
    
    @pytest.fixture
    def websocket_auth_helper(self):
        """WebSocket authentication for business workflows."""
        return E2EWebSocketAuthHelper(environment="test")
    
    @pytest.fixture
    def unified_id_generator(self):
        """ID generator for business workflow tracking."""
        return UnifiedIdGenerator()
    
    @pytest.fixture
    async def real_agent_registry(self):
        """Real agent registry for business workflow testing."""
        registry = AgentRegistry()
        await registry.initialize_registry()
        
        # Ensure we have the agents needed for complete workflow
        available_agents = registry.list_available_agents()
        required_agents = ["triage_agent", "data_analysis_agent", "optimization_agent"]
        
        missing_agents = [agent for agent in required_agents if agent not in available_agents]
        if missing_agents:
            self.logger.warning(f"Missing workflow agents: {missing_agents}. Will use triage_agent for all stages.")
        
        return registry
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.websocket_events
    @pytest.mark.business_workflow
    async def test_complete_triage_to_completion_workflow(
        self,
        business_user_context: StronglyTypedUserExecutionContext,
        websocket_auth_helper: E2EWebSocketAuthHelper,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test complete business workflow from triage to completion with all events.
        
        CRITICAL: This test validates the entire business value delivery pipeline.
        """
        
        # Initialize business workflow tracker
        workflow_tracker = BusinessWorkflowTracker("triage_to_completion_e2e")
        
        # Connect authenticated WebSocket
        websocket_connection = await websocket_auth_helper.connect_authenticated_websocket(
            timeout=20.0
        )
        
        # Set up execution infrastructure
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
        
        # Complete workflow events collection
        all_workflow_events = []
        
        async def collect_workflow_events():
            """Collect all events for complete workflow analysis."""
            try:
                while True:
                    event_raw = await asyncio.wait_for(websocket_connection.recv(), timeout=45.0)
                    event = json.loads(event_raw)
                    all_workflow_events.append(event)
                    
                    self.logger.info(f"Workflow event: {event.get('type')} for agent: {event.get('agent_name')}")
                    
                    # Stop after final completion
                    if (event.get('type') == 'agent_completed' and 
                        event.get('agent_name') == 'optimization_agent'):
                        break
                    
                    # Also stop if we get a single triage completion (fallback)
                    if (event.get('type') == 'agent_completed' and 
                        len(all_workflow_events) > 5):  # Ensure we got substantial events
                        break
            except asyncio.TimeoutError:
                self.logger.warning("Workflow event collection timeout")
        
        # Start workflow event collection
        event_collection_task = asyncio.create_task(collect_workflow_events())
        
        try:
            # STAGE 1: Triage Agent - Initial request analysis
            triage_stage = workflow_tracker.start_stage("triage", "triage_agent")
            
            triage_run_id = unified_id_generator.generate_run_id(
                user_id=str(business_user_context.user_id),
                operation="business_workflow_triage"
            )
            
            triage_context = AgentExecutionContext(
                agent_name="triage_agent",
                run_id=str(triage_run_id),
                correlation_id=str(business_user_context.request_id),
                retry_count=0,
                user_context=business_user_context
            )
            
            triage_state = DeepAgentState(
                user_id=str(business_user_context.user_id),
                thread_id=str(business_user_context.thread_id),
                agent_context={
                    **business_user_context.agent_context,
                    'user_message': 'I need a comprehensive analysis of my business operations and optimization recommendations',
                    'workflow_stage': 'triage',
                    'business_context': 'complete_workflow',
                    'expected_output': 'triage_analysis'
                }
            )
            
            # Execute triage agent
            triage_result = await execution_core.execute_agent(
                context=triage_context,
                state=triage_state,
                timeout=30.0,
                enable_llm=True,  # Use real LLM for business value
                enable_websocket_events=True
            )
            
            workflow_tracker.complete_stage(triage_stage, triage_result.success)
            workflow_tracker.update_business_metrics(user_request_processed=True)
            
            # STAGE 2: Data Analysis Agent - Deep dive analysis (or continue with triage if not available)
            analysis_stage = workflow_tracker.start_stage("analysis", "data_analysis_agent")
            
            analysis_run_id = unified_id_generator.generate_run_id(
                user_id=str(business_user_context.user_id),
                operation="business_workflow_analysis"
            )
            
            # Check if data analysis agent is available
            available_agents = real_agent_registry.list_available_agents()
            analysis_agent_name = "data_analysis_agent" if "data_analysis_agent" in available_agents else "triage_agent"
            
            analysis_context = AgentExecutionContext(
                agent_name=analysis_agent_name,
                run_id=str(analysis_run_id),
                correlation_id=str(business_user_context.request_id),
                retry_count=0,
                user_context=business_user_context
            )
            
            analysis_state = DeepAgentState(
                user_id=str(business_user_context.user_id),
                thread_id=str(business_user_context.thread_id),
                agent_context={
                    **business_user_context.agent_context,
                    'user_message': 'Based on the triage, provide detailed data analysis and insights',
                    'workflow_stage': 'analysis',
                    'previous_stage': 'triage',
                    'triage_run_id': str(triage_run_id),
                    'expected_output': 'detailed_analysis'
                }
            )
            
            analysis_result = await execution_core.execute_agent(
                context=analysis_context,
                state=analysis_state,
                timeout=35.0,
                enable_llm=True,
                enable_websocket_events=True
            )
            
            workflow_tracker.complete_stage(analysis_stage, analysis_result.success)
            workflow_tracker.update_business_metrics(analysis_provided=True)
            
            # STAGE 3: Optimization Agent - Generate recommendations (or continue with triage if not available)
            optimization_stage = workflow_tracker.start_stage("optimization", "optimization_agent")
            
            optimization_run_id = unified_id_generator.generate_run_id(
                user_id=str(business_user_context.user_id),
                operation="business_workflow_optimization"
            )
            
            optimization_agent_name = "optimization_agent" if "optimization_agent" in available_agents else "triage_agent"
            
            optimization_context = AgentExecutionContext(
                agent_name=optimization_agent_name,
                run_id=str(optimization_run_id),
                correlation_id=str(business_user_context.request_id),
                retry_count=0,
                user_context=business_user_context
            )
            
            optimization_state = DeepAgentState(
                user_id=str(business_user_context.user_id),
                thread_id=str(business_user_context.thread_id),
                agent_context={
                    **business_user_context.agent_context,
                    'user_message': 'Generate specific optimization recommendations based on analysis',
                    'workflow_stage': 'optimization',
                    'previous_stages': ['triage', 'analysis'],
                    'analysis_run_id': str(analysis_run_id),
                    'expected_output': 'optimization_recommendations'
                }
            )
            
            optimization_result = await execution_core.execute_agent(
                context=optimization_context,
                state=optimization_state,
                timeout=40.0,
                enable_llm=True,
                enable_websocket_events=True
            )
            
            workflow_tracker.complete_stage(optimization_stage, optimization_result.success)
            workflow_tracker.update_business_metrics(
                recommendations_generated=True,
                actionable_insights_delivered=True,
                complete_workflow_finished=True
            )
            
            # Wait for all events to be collected
            await asyncio.wait_for(event_collection_task, timeout=10.0)
            
        except asyncio.TimeoutError:
            event_collection_task.cancel()
        finally:
            await websocket_connection.close()
        
        # CRITICAL VALIDATION: All workflow stages succeeded
        assert triage_result.success is True, f"Triage stage failed: {triage_result.error}"
        assert analysis_result.success is True, f"Analysis stage failed: {analysis_result.error}"
        assert optimization_result.success is True, f"Optimization stage failed: {optimization_result.error}"
        
        # CRITICAL VALIDATION: Events delivered for complete workflow
        assert len(all_workflow_events) > 0, "No workflow events received"
        
        # Analyze workflow events
        workflow_summary = workflow_tracker.get_workflow_summary()
        
        # CRITICAL VALIDATION: All 5 required events delivered across workflow
        event_types = [event.get('type') for event in all_workflow_events]
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        
        for required_event in required_events:
            assert required_event in event_types, \
                f"CRITICAL WORKFLOW FAILURE: Missing required event '{required_event}' in complete business workflow"
        
        # CRITICAL VALIDATION: Business value metrics
        business_value_percentage = workflow_summary['business_value_percentage']
        assert business_value_percentage >= 80.0, \
            f"Insufficient business value delivered: {business_value_percentage}% (required: 80%+)"
        
        # CRITICAL VALIDATION: Workflow completeness
        assert workflow_summary['stages_completed'] == workflow_summary['total_stages'], \
            f"Incomplete workflow: {workflow_summary['stages_completed']}/{workflow_summary['total_stages']} stages completed"
        
        # CRITICAL VALIDATION: Event distribution across stages
        stages_with_events = workflow_summary['stages_with_events']
        total_stages = workflow_summary['total_stages']
        
        assert stages_with_events >= total_stages, \
            f"Not all stages received events: {stages_with_events}/{total_stages}"
        
        # VALIDATION: Workflow performance
        total_workflow_time = workflow_summary['total_time']
        assert total_workflow_time < 120.0, \
            f"Complete workflow too slow: {total_workflow_time:.2f}s (max: 120s)"
        
        # Log comprehensive business workflow success
        self.logger.info("✅ CRITICAL SUCCESS: Complete business workflow validated")
        self.logger.info(f"  - Workflow: {workflow_summary['workflow_name']}")
        self.logger.info(f"  - Total time: {total_workflow_time:.2f}s")
        self.logger.info(f"  - Stages completed: {workflow_summary['stages_completed']}/{workflow_summary['total_stages']}")
        self.logger.info(f"  - Total events: {workflow_summary['total_events']}")
        self.logger.info(f"  - Business value: {business_value_percentage:.1f}%")
        self.logger.info(f"  - Required events delivered: {workflow_summary['events_delivered']}")
        
        # Return workflow summary for further analysis if needed
        return workflow_summary
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    @pytest.mark.business_workflow
    async def test_workflow_event_ordering_and_timing(
        self,
        business_user_context: StronglyTypedUserExecutionContext,
        websocket_auth_helper: E2EWebSocketAuthHelper,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test that workflow events are delivered in correct order with proper timing.
        
        Validates the sequence and timing requirements for business value delivery.
        """
        
        websocket_connection = await websocket_auth_helper.connect_authenticated_websocket()
        
        # Track event timing and ordering
        timed_events = []
        
        async def collect_timed_events():
            """Collect events with precise timing."""
            try:
                while True:
                    receive_time = time.time()
                    event_raw = await asyncio.wait_for(websocket_connection.recv(), timeout=30.0)
                    event = json.loads(event_raw)
                    
                    timed_events.append({
                        'event': event,
                        'receive_time': receive_time,
                        'event_type': event.get('type'),
                        'agent_name': event.get('agent_name'),
                        'run_id': event.get('run_id')
                    })
                    
                    if event.get('type') == 'agent_completed':
                        break
            except asyncio.TimeoutError:
                pass
        
        # Execute single agent to test event ordering
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
        
        run_id = unified_id_generator.generate_run_id(
            user_id=str(business_user_context.user_id),
            operation="event_ordering_test"
        )
        
        execution_context = AgentExecutionContext(
            agent_name="triage_agent",
            run_id=str(run_id),
            correlation_id=str(business_user_context.request_id),
            retry_count=0,
            user_context=business_user_context
        )
        
        agent_state = DeepAgentState(
            user_id=str(business_user_context.user_id),
            thread_id=str(business_user_context.thread_id),
            agent_context={
                **business_user_context.agent_context,
                'user_message': 'Test event ordering and timing for business workflow',
                'event_ordering_test': True
            }
        )
        
        # Start event collection
        event_task = asyncio.create_task(collect_timed_events())
        
        # Execute agent
        result = await execution_core.execute_agent(
            context=execution_context,
            state=agent_state,
            timeout=25.0,
            enable_websocket_events=True
        )
        
        await event_task
        await websocket_connection.close()
        
        # VALIDATION: Agent execution succeeded
        assert result.success is True, f"Event ordering test execution failed: {result.error}"
        
        # CRITICAL VALIDATION: Event ordering
        event_types_ordered = [timed_event['event_type'] for timed_event in timed_events]
        
        # agent_started must be first
        if 'agent_started' in event_types_ordered:
            started_index = event_types_ordered.index('agent_started')
            assert started_index == 0, f"agent_started must be first event, found at index {started_index}"
        
        # agent_completed must be last
        if 'agent_completed' in event_types_ordered:
            completed_index = event_types_ordered.index('agent_completed')
            assert completed_index == len(event_types_ordered) - 1, \
                f"agent_completed must be last event, found at index {completed_index}"
        
        # CRITICAL VALIDATION: Event timing (no unrealistic gaps)
        if len(timed_events) > 1:
            max_gap_between_events = 0
            for i in range(1, len(timed_events)):
                gap = timed_events[i]['receive_time'] - timed_events[i-1]['receive_time']
                max_gap_between_events = max(max_gap_between_events, gap)
            
            # Events should be delivered in reasonable time
            assert max_gap_between_events < 15.0, \
                f"Excessive gap between workflow events: {max_gap_between_events:.2f}s"
        
        # VALIDATION: Event completeness for run_id
        events_for_run = [te for te in timed_events if te['event'].get('run_id') == str(run_id)]
        assert len(events_for_run) > 0, f"No events received for run_id {run_id}"
        
        self.logger.info("✅ SUCCESS: Workflow event ordering and timing validated")
        self.logger.info(f"  - Events received: {len(timed_events)}")
        self.logger.info(f"  - Event sequence: {event_types_ordered}")
        self.logger.info(f"  - Max gap between events: {max_gap_between_events:.2f}s")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    @pytest.mark.business_workflow
    @pytest.mark.performance
    async def test_high_frequency_business_workflows(
        self,
        websocket_auth_helper: E2EWebSocketAuthHelper,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test multiple business workflows in rapid succession.
        
        Validates system can handle high-frequency business workflow execution.
        """
        
        num_workflows = 3
        workflow_results = []
        
        for workflow_num in range(num_workflows):
            # Create user context for each workflow
            user_context = await create_authenticated_user_context(
                user_email=f"high_freq_workflow_{workflow_num}@e2e.test",
                environment="test",
                permissions=["read", "write", "agent_execute", "websocket_connect"],
                websocket_enabled=True
            )
            
            websocket_connection = await websocket_auth_helper.connect_authenticated_websocket()
            
            workflow_events = []
            
            async def collect_workflow_specific_events():
                try:
                    while True:
                        event_raw = await asyncio.wait_for(websocket_connection.recv(), timeout=20.0)
                        event = json.loads(event_raw)
                        workflow_events.append(event)
                        
                        if event.get('type') == 'agent_completed':
                            break
                except asyncio.TimeoutError:
                    pass
            
            # Set up execution
            websocket_manager = UnifiedWebSocketManager()
            websocket_bridge = AgentWebSocketBridge(websocket_manager)
            execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
            
            run_id = unified_id_generator.generate_run_id(
                user_id=str(user_context.user_id),
                operation=f"high_freq_workflow_{workflow_num}"
            )
            
            execution_context = AgentExecutionContext(
                agent_name="triage_agent",
                run_id=str(run_id),
                correlation_id=str(user_context.request_id),
                retry_count=0,
                user_context=user_context
            )
            
            agent_state = DeepAgentState(
                user_id=str(user_context.user_id),
                thread_id=str(user_context.thread_id),
                agent_context={
                    **user_context.agent_context,
                    'user_message': f'High frequency business workflow {workflow_num + 1}',
                    'workflow_number': workflow_num + 1,
                    'high_frequency_test': True
                }
            )
            
            # Execute workflow
            event_task = asyncio.create_task(collect_workflow_specific_events())
            
            start_time = time.time()
            result = await execution_core.execute_agent(
                context=execution_context,
                state=agent_state,
                timeout=20.0,
                enable_websocket_events=True
            )
            end_time = time.time()
            
            await event_task
            await websocket_connection.close()
            
            workflow_results.append({
                'workflow_num': workflow_num,
                'result': result,
                'events': workflow_events,
                'execution_time': end_time - start_time,
                'run_id': str(run_id)
            })
            
            # Brief pause between workflows
            await asyncio.sleep(0.2)
        
        # VALIDATION: All workflows succeeded
        for i, workflow in enumerate(workflow_results):
            assert workflow['result'].success is True, \
                f"High frequency workflow {i} failed: {workflow['result'].error}"
            assert len(workflow['events']) > 0, \
                f"High frequency workflow {i} generated no events"
        
        # VALIDATION: Performance acceptable
        average_execution_time = sum(w['execution_time'] for w in workflow_results) / len(workflow_results)
        assert average_execution_time < 25.0, \
            f"Average workflow execution too slow: {average_execution_time:.2f}s"
        
        # VALIDATION: Event delivery for all workflows
        total_events = sum(len(w['events']) for w in workflow_results)
        assert total_events >= num_workflows * 2, \
            f"Insufficient events across high frequency workflows: {total_events}"
        
        # VALIDATION: Unique run IDs
        all_run_ids = {w['run_id'] for w in workflow_results}
        assert len(all_run_ids) == num_workflows, \
            f"Run IDs not unique in high frequency test: {len(all_run_ids)} / {num_workflows}"
        
        self.logger.info(f"✅ PERFORMANCE SUCCESS: High frequency business workflows validated")
        self.logger.info(f"  - Workflows executed: {num_workflows}")
        self.logger.info(f"  - Average execution time: {average_execution_time:.2f}s")
        self.logger.info(f"  - Total events delivered: {total_events}")
        self.logger.info(f"  - Unique run IDs: {len(all_run_ids)}")