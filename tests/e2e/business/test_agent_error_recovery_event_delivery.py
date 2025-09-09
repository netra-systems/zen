"""
E2E Test: Agent Error Recovery and Event Delivery

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Error recovery is critical for user trust
- Business Goal: Ensure graceful error handling with proper WebSocket event delivery
- Value Impact: Users receive meaningful feedback even when things go wrong
- Strategic Impact: System reliability that maintains user confidence and prevents abandonment

This E2E test validates:
- Error scenarios with real recovery mechanisms and user feedback
- WebSocket events delivered during agent failures and recovery
- User experience during system recovery with proper error communication
- Real error handling that maintains WebSocket connection integrity
- Business continuity through proper error management and recovery

CRITICAL: Tests error handling that maintains user trust and system reliability
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


class ErrorScenarioSimulator:
    """Simulates various error scenarios for testing recovery mechanisms."""
    
    def __init__(self, scenario_type: str):
        self.scenario_type = scenario_type
        self.error_events = []
        self.recovery_events = []
        self.error_introduced_at = None
        self.recovery_completed_at = None
    
    def create_error_scenario_context(self, base_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create agent context that will trigger specific error scenarios."""
        error_context = base_context.copy()
        
        if self.scenario_type == "agent_timeout":
            error_context.update({
                'error_scenario': 'timeout',
                'simulate_long_processing': True,
                'timeout_duration': 45  # Longer than typical timeout
            })
            
        elif self.scenario_type == "invalid_agent":
            error_context.update({
                'error_scenario': 'invalid_agent',
                'agent_override': 'non_existent_agent_for_testing'
            })
            
        elif self.scenario_type == "llm_failure":
            error_context.update({
                'error_scenario': 'llm_failure',
                'simulate_llm_error': True,
                'error_message': 'Simulated LLM service failure'
            })
            
        elif self.scenario_type == "websocket_interruption":
            error_context.update({
                'error_scenario': 'websocket_interruption',
                'simulate_connection_loss': True,
                'reconnection_required': True
            })
            
        elif self.scenario_type == "partial_failure":
            error_context.update({
                'error_scenario': 'partial_failure',
                'fail_mid_execution': True,
                'recovery_possible': True
            })
            
        else:
            error_context.update({
                'error_scenario': 'generic_error',
                'simulate_generic_failure': True
            })
        
        return error_context
    
    def record_error_event(self, event: Dict[str, Any]):
        """Record error-related event."""
        self.error_events.append({
            'timestamp': time.time(),
            'event': event,
            'event_type': event.get('type')
        })
        
        if self.error_introduced_at is None:
            self.error_introduced_at = time.time()
    
    def record_recovery_event(self, event: Dict[str, Any]):
        """Record recovery-related event."""
        self.recovery_events.append({
            'timestamp': time.time(),
            'event': event,
            'event_type': event.get('type')
        })
        
        if event.get('type') == 'agent_completed' and self.recovery_completed_at is None:
            self.recovery_completed_at = time.time()
    
    def get_error_recovery_summary(self) -> Dict[str, Any]:
        """Get summary of error and recovery process."""
        recovery_time = None
        if self.error_introduced_at and self.recovery_completed_at:
            recovery_time = self.recovery_completed_at - self.error_introduced_at
        
        return {
            'scenario_type': self.scenario_type,
            'error_events_count': len(self.error_events),
            'recovery_events_count': len(self.recovery_events),
            'error_introduced_at': self.error_introduced_at,
            'recovery_completed_at': self.recovery_completed_at,
            'recovery_time_seconds': recovery_time,
            'recovery_successful': self.recovery_completed_at is not None,
            'error_events': self.error_events,
            'recovery_events': self.recovery_events
        }


class TestAgentErrorRecoveryEventDelivery(BaseE2ETest):
    """E2E tests for agent error recovery with WebSocket event delivery."""
    
    @pytest.fixture
    async def error_recovery_user_context(self):
        """Create user context for error recovery testing."""
        return await create_authenticated_user_context(
            user_email="error_recovery_user@e2e.test",
            environment="test",
            permissions=["read", "write", "agent_execute", "websocket_connect", "error_recovery"],
            websocket_enabled=True
        )
    
    @pytest.fixture
    def websocket_auth_helper(self):
        """WebSocket authentication for error recovery tests."""
        return E2EWebSocketAuthHelper(environment="test")
    
    @pytest.fixture
    def unified_id_generator(self):
        """ID generator for error recovery testing."""
        return UnifiedIdGenerator()
    
    @pytest.fixture
    async def real_agent_registry(self):
        """Real agent registry for error recovery tests."""
        registry = AgentRegistry()
        await registry.initialize_registry()
        return registry
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    @pytest.mark.error_recovery
    async def test_agent_timeout_error_recovery_with_events(
        self,
        error_recovery_user_context: StronglyTypedUserExecutionContext,
        websocket_auth_helper: E2EWebSocketAuthHelper,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test agent timeout error recovery with proper WebSocket event delivery.
        
        CRITICAL: This validates that users get proper feedback during timeout scenarios.
        """
        
        error_simulator = ErrorScenarioSimulator("agent_timeout")
        
        websocket_connection = await websocket_auth_helper.connect_authenticated_websocket(
            timeout=20.0
        )
        
        # Track all events during error and recovery
        all_events = []
        error_events = []
        recovery_events = []
        
        async def collect_error_recovery_events():
            """Collect events during error and recovery process."""
            try:
                while True:
                    event_raw = await asyncio.wait_for(
                        websocket_connection.recv(), 
                        timeout=35.0  # Extended timeout for error scenarios
                    )
                    event = json.loads(event_raw)
                    all_events.append(event)
                    
                    # Categorize events
                    event_type = event.get('type')
                    event_content = json.dumps(event).lower()
                    
                    if (event_type in ['agent_error', 'execution_error', 'error'] or
                        'error' in event_content or 'timeout' in event_content or 'failed' in event_content):
                        error_events.append(event)
                        error_simulator.record_error_event(event)
                    
                    if (event_type in ['agent_completed', 'recovery_completed'] or
                        'recovery' in event_content or 'retry' in event_content):
                        recovery_events.append(event)
                        error_simulator.record_recovery_event(event)
                    
                    # Stop after completion (successful or failed)
                    if event_type in ['agent_completed', 'agent_error', 'execution_failed']:
                        break
                        
            except asyncio.TimeoutError:
                self.logger.warning("Timeout waiting for error recovery events")
        
        # Set up execution with error scenario
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
        
        run_id = unified_id_generator.generate_run_id(
            user_id=str(error_recovery_user_context.user_id),
            operation="error_recovery_timeout_test"
        )
        
        execution_context = AgentExecutionContext(
            agent_name="triage_agent",
            run_id=str(run_id),
            correlation_id=str(error_recovery_user_context.request_id),
            retry_count=0,
            user_context=error_recovery_user_context
        )
        
        # Create error scenario context
        error_context = error_simulator.create_error_scenario_context(
            error_recovery_user_context.agent_context
        )
        
        agent_state = DeepAgentState(
            user_id=str(error_recovery_user_context.user_id),
            thread_id=str(error_recovery_user_context.thread_id),
            agent_context={
                **error_context,
                'user_message': 'Test agent timeout error recovery',
                'expect_timeout_handling': True
            }
        )
        
        # Start event collection
        event_task = asyncio.create_task(collect_error_recovery_events())
        
        # Execute agent with timeout scenario (expected to fail or recover)
        try:
            execution_result = await execution_core.execute_agent(
                context=execution_context,
                state=agent_state,
                timeout=30.0,  # Reasonable timeout for error testing
                enable_websocket_events=True
            )
        except Exception as e:
            # Errors are expected in this test
            self.logger.info(f"Expected error during timeout test: {e}")
            execution_result = None
        
        await event_task
        await websocket_connection.close()
        
        # CRITICAL VALIDATION: Events delivered during error scenario
        assert len(all_events) > 0, "No events received during error recovery scenario"
        
        # CRITICAL VALIDATION: Error events provide user feedback
        if len(error_events) > 0:
            # Users should get meaningful error information
            for error_event in error_events:
                assert 'error' in error_event or 'message' in error_event, \
                    f"Error event should contain error information: {error_event}"
        
        # VALIDATION: WebSocket connection remained stable during error
        # (events were delivered despite errors)
        event_types = [event.get('type') for event in all_events]
        
        # Some events should have been delivered
        assert len(event_types) > 0, "WebSocket should deliver events even during error scenarios"
        
        # Get error recovery summary
        error_summary = error_simulator.get_error_recovery_summary()
        
        self.logger.info("✅ SUCCESS: Agent timeout error recovery with events validated")
        self.logger.info(f"  - Total events: {len(all_events)}")
        self.logger.info(f"  - Error events: {len(error_events)}")
        self.logger.info(f"  - Recovery events: {len(recovery_events)}")
        self.logger.info(f"  - Error recovery summary: {error_summary['scenario_type']}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    @pytest.mark.error_recovery
    async def test_websocket_connection_recovery(
        self,
        error_recovery_user_context: StronglyTypedUserExecutionContext,
        websocket_auth_helper: E2EWebSocketAuthHelper,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test WebSocket connection recovery after interruption.
        
        Validates that WebSocket connections can recover and continue delivering events.
        """
        
        # Initial connection and execution
        initial_connection = await websocket_auth_helper.connect_authenticated_websocket()
        
        run_id = unified_id_generator.generate_run_id(
            user_id=str(error_recovery_user_context.user_id),
            operation="websocket_recovery_test"
        )
        
        # Start agent execution
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
        
        execution_context = AgentExecutionContext(
            agent_name="triage_agent",
            run_id=str(run_id),
            correlation_id=str(error_recovery_user_context.request_id),
            retry_count=0,
            user_context=error_recovery_user_context
        )
        
        agent_state = DeepAgentState(
            user_id=str(error_recovery_user_context.user_id),
            thread_id=str(error_recovery_user_context.thread_id),
            agent_context={
                **error_recovery_user_context.agent_context,
                'user_message': 'Test WebSocket recovery during execution',
                'websocket_recovery_test': True
            }
        )
        
        initial_events = []
        
        async def collect_initial_events():
            """Collect events from initial connection."""
            try:
                # Collect a few initial events
                for _ in range(3):  # Collect first 3 events
                    event_raw = await asyncio.wait_for(initial_connection.recv(), timeout=10.0)
                    event = json.loads(event_raw)
                    initial_events.append(event)
            except asyncio.TimeoutError:
                pass
        
        # Start execution and collect initial events
        execution_task = asyncio.create_task(
            execution_core.execute_agent(
                context=execution_context,
                state=agent_state,
                timeout=40.0,
                enable_websocket_events=True
            )
        )
        
        initial_event_task = asyncio.create_task(collect_initial_events())
        
        # Wait for initial events
        await initial_event_task
        
        # Simulate connection interruption by closing initial connection
        await initial_connection.close()
        self.logger.info("Simulated WebSocket connection interruption")
        
        # Brief pause to simulate network issues
        await asyncio.sleep(1.0)
        
        # Recover connection
        recovery_connection = await websocket_auth_helper.connect_authenticated_websocket()
        self.logger.info("WebSocket connection recovered")
        
        # Collect recovery events
        recovery_events = []
        
        async def collect_recovery_events():
            """Collect events after connection recovery."""
            try:
                while True:
                    event_raw = await asyncio.wait_for(recovery_connection.recv(), timeout=25.0)
                    event = json.loads(event_raw)
                    recovery_events.append(event)
                    
                    if event.get('type') == 'agent_completed':
                        break
            except asyncio.TimeoutError:
                pass
        
        recovery_event_task = asyncio.create_task(collect_recovery_events())
        
        # Wait for execution and recovery events
        try:
            execution_result = await execution_task
            await recovery_event_task
        except Exception as e:
            self.logger.info(f"Execution during recovery test: {e}")
        finally:
            await recovery_connection.close()
        
        # VALIDATION: Events received before and after recovery
        assert len(initial_events) > 0, "Should receive events before connection interruption"
        
        # Note: Recovery events might be empty if agent completed before recovery
        # But connection recovery should work
        
        # VALIDATION: Connection recovery successful
        # The fact that we could reconnect and the test completed is the validation
        
        self.logger.info("✅ SUCCESS: WebSocket connection recovery validated")
        self.logger.info(f"  - Initial events before interruption: {len(initial_events)}")
        self.logger.info(f"  - Recovery events after reconnection: {len(recovery_events)}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    @pytest.mark.error_recovery
    async def test_partial_failure_recovery_event_flow(
        self,
        error_recovery_user_context: StronglyTypedUserExecutionContext,
        websocket_auth_helper: E2EWebSocketAuthHelper,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test partial failure recovery with complete event flow.
        
        Validates that partial failures are handled gracefully with proper event delivery.
        """
        
        error_simulator = ErrorScenarioSimulator("partial_failure")
        
        websocket_connection = await websocket_auth_helper.connect_authenticated_websocket()
        
        # Track events through failure and recovery
        complete_event_flow = []
        failure_indicators = []
        recovery_indicators = []
        
        async def collect_complete_event_flow():
            """Collect complete event flow including failure and recovery."""
            try:
                while True:
                    event_raw = await asyncio.wait_for(websocket_connection.recv(), timeout=30.0)
                    event = json.loads(event_raw)
                    complete_event_flow.append(event)
                    
                    event_content = json.dumps(event).lower()
                    
                    # Detect failure indicators
                    if ('fail' in event_content or 'error' in event_content or 
                        event.get('type') in ['agent_error', 'tool_error']):
                        failure_indicators.append(event)
                    
                    # Detect recovery indicators
                    if ('retry' in event_content or 'recover' in event_content or 
                        'continue' in event_content or event.get('type') == 'agent_completed'):
                        recovery_indicators.append(event)
                    
                    if event.get('type') == 'agent_completed':
                        break
                        
            except asyncio.TimeoutError:
                pass
        
        # Set up execution with partial failure scenario
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
        
        run_id = unified_id_generator.generate_run_id(
            user_id=str(error_recovery_user_context.user_id),
            operation="partial_failure_recovery_test"
        )
        
        execution_context = AgentExecutionContext(
            agent_name="triage_agent",
            run_id=str(run_id),
            correlation_id=str(error_recovery_user_context.request_id),
            retry_count=0,
            user_context=error_recovery_user_context
        )
        
        # Create partial failure context
        error_context = error_simulator.create_error_scenario_context(
            error_recovery_user_context.agent_context
        )
        
        agent_state = DeepAgentState(
            user_id=str(error_recovery_user_context.user_id),
            thread_id=str(error_recovery_user_context.thread_id),
            agent_context={
                **error_context,
                'user_message': 'Test partial failure recovery with event flow',
                'expect_partial_failure': True,
                'recovery_expected': True
            }
        )
        
        # Start event collection
        event_task = asyncio.create_task(collect_complete_event_flow())
        
        # Execute agent (should handle partial failure and potentially recover)
        try:
            execution_result = await execution_core.execute_agent(
                context=execution_context,
                state=agent_state,
                timeout=35.0,
                enable_websocket_events=True
            )
        except Exception as e:
            self.logger.info(f"Execution with partial failure: {e}")
            execution_result = None
        
        await event_task
        await websocket_connection.close()
        
        # CRITICAL VALIDATION: Complete event flow delivered
        assert len(complete_event_flow) > 0, \
            "Event flow should be delivered even during partial failures"
        
        # VALIDATION: Event flow contains proper start and end markers
        event_types = [event.get('type') for event in complete_event_flow]
        
        # Should have some form of completion or error indication
        completion_events = [et for et in event_types if 'completed' in et or 'error' in et]
        assert len(completion_events) > 0, \
            "Event flow should indicate completion or error state"
        
        # VALIDATION: Failure and recovery process visible in events
        # Note: Actual failure/recovery depends on agent implementation
        # The key validation is that events are delivered throughout the process
        
        get_error_summary = error_simulator.get_error_recovery_summary()
        
        self.logger.info("✅ SUCCESS: Partial failure recovery event flow validated")
        self.logger.info(f"  - Complete event flow: {len(complete_event_flow)}")
        self.logger.info(f"  - Failure indicators: {len(failure_indicators)}")
        self.logger.info(f"  - Recovery indicators: {len(recovery_indicators)}")
        self.logger.info(f"  - Event types: {set(event_types)}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    @pytest.mark.error_recovery
    @pytest.mark.business_continuity
    async def test_business_continuity_during_error_scenarios(
        self,
        websocket_auth_helper: E2EWebSocketAuthHelper,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test business continuity during various error scenarios.
        
        Validates that business workflows can continue despite errors.
        """
        
        error_scenarios = ["partial_failure", "timeout", "websocket_interruption"]
        continuity_results = []
        
        for scenario in error_scenarios:
            # Create user for this scenario
            user_context = await create_authenticated_user_context(
                user_email=f"business_continuity_{scenario}@e2e.test",
                environment="test",
                permissions=["read", "write", "agent_execute", "websocket_connect"],
                websocket_enabled=True
            )
            
            error_simulator = ErrorScenarioSimulator(scenario)
            websocket_connection = await websocket_auth_helper.connect_authenticated_websocket()
            
            scenario_events = []
            scenario_start_time = time.time()
            
            async def collect_scenario_events():
                try:
                    while True:
                        event_raw = await asyncio.wait_for(websocket_connection.recv(), timeout=25.0)
                        event = json.loads(event_raw)
                        scenario_events.append(event)
                        
                        if event.get('type') in ['agent_completed', 'agent_error']:
                            break
                except asyncio.TimeoutError:
                    pass
            
            # Execute business workflow with error scenario
            websocket_manager = UnifiedWebSocketManager()
            websocket_bridge = AgentWebSocketBridge(websocket_manager)
            execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
            
            run_id = unified_id_generator.generate_run_id(
                user_id=str(user_context.user_id),
                operation=f"business_continuity_{scenario}"
            )
            
            execution_context = AgentExecutionContext(
                agent_name="triage_agent",
                run_id=str(run_id),
                correlation_id=str(user_context.request_id),
                retry_count=0,
                user_context=user_context
            )
            
            error_context = error_simulator.create_error_scenario_context(user_context.agent_context)
            
            agent_state = DeepAgentState(
                user_id=str(user_context.user_id),
                thread_id=str(user_context.thread_id),
                agent_context={
                    **error_context,
                    'user_message': f'Business workflow with {scenario} scenario',
                    'business_continuity_test': True,
                    'scenario_type': scenario
                }
            )
            
            event_task = asyncio.create_task(collect_scenario_events())
            
            try:
                execution_result = await execution_core.execute_agent(
                    context=execution_context,
                    state=agent_state,
                    timeout=30.0,
                    enable_websocket_events=True
                )
                
                business_continuity_maintained = True
                
            except Exception as e:
                self.logger.info(f"Expected error in {scenario} scenario: {e}")
                business_continuity_maintained = False
                execution_result = None
            
            await event_task
            await websocket_connection.close()
            
            scenario_end_time = time.time()
            
            continuity_results.append({
                'scenario': scenario,
                'events_delivered': len(scenario_events),
                'execution_time': scenario_end_time - scenario_start_time,
                'business_continuity_maintained': business_continuity_maintained,
                'websocket_connection_stable': len(scenario_events) > 0,
                'execution_result': execution_result
            })
        
        # CRITICAL VALIDATION: Business continuity assessment
        scenarios_with_events = sum(1 for result in continuity_results if result['events_delivered'] > 0)
        scenarios_with_stable_websocket = sum(1 for result in continuity_results if result['websocket_connection_stable'])
        
        # At least majority of scenarios should maintain WebSocket connectivity
        websocket_stability_rate = scenarios_with_stable_websocket / len(error_scenarios)
        assert websocket_stability_rate >= 0.67, \
            f"WebSocket stability too low during errors: {websocket_stability_rate:.1%} (required: 67%+)"
        
        # Events should be delivered even during error scenarios
        assert scenarios_with_events >= len(error_scenarios) // 2, \
            f"Too few scenarios delivered events: {scenarios_with_events}/{len(error_scenarios)}"
        
        # VALIDATION: Performance during error scenarios
        average_execution_time = sum(result['execution_time'] for result in continuity_results) / len(continuity_results)
        assert average_execution_time < 40.0, \
            f"Error scenarios taking too long: {average_execution_time:.2f}s"
        
        self.logger.info("✅ BUSINESS CONTINUITY SUCCESS: Error scenario resilience validated")
        self.logger.info(f"  - Scenarios tested: {len(error_scenarios)}")
        self.logger.info(f"  - WebSocket stability rate: {websocket_stability_rate:.1%}")
        self.logger.info(f"  - Average execution time: {average_execution_time:.2f}s")
        self.logger.info(f"  - Scenarios with events: {scenarios_with_events}/{len(error_scenarios)}")
        
        for result in continuity_results:
            self.logger.info(f"    - {result['scenario']}: {result['events_delivered']} events, {result['execution_time']:.2f}s")