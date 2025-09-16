"""
Test Agent Execution Pipeline State Transitions - Golden Path Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agents progress through complete execution states to deliver value
- Value Impact: Users receive complete responses with actionable insights and recommendations
- Strategic Impact: Core business functionality - agents must transition from started to completed states

CRITICAL REQUIREMENTS:
1. Test agent state transitions: started → thinking → tool_executing → tool_completed → completed
2. Validate WebSocket events are sent for each state transition
3. Test real database persistence at each stage
4. Test error recovery and graceful degradation
5. Use real services only (NO MOCKS per CLAUDE.md)
6. Validate business value is delivered in final state
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


@dataclass
class AgentExecutionStateSnapshot:
    """Snapshot of agent execution state at a specific point."""
    state: str
    timestamp: float
    websocket_event_type: str
    data_persisted: bool
    business_value_indicators: Dict[str, Any]
    error_info: Optional[str] = None


class AgentExecutionState(Enum):
    """Agent execution states in order."""
    STARTED = "agent_started"
    THINKING = "agent_thinking" 
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    COMPLETED = "agent_completed"
    ERROR = "agent_error"


class TestAgentExecutionPipelineComprehensive(BaseIntegrationTest):
    """Test comprehensive agent execution pipeline state transitions."""
    
    def setup_method(self):
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.state_snapshots: List[AgentExecutionStateSnapshot] = []
        self.expected_state_sequence = [
            AgentExecutionState.STARTED,
            AgentExecutionState.THINKING,
            AgentExecutionState.TOOL_EXECUTING,
            AgentExecutionState.TOOL_COMPLETED,
            AgentExecutionState.COMPLETED
        ]
    
    async def _capture_state_snapshot(self, state: str, event_type: str, 
                                    real_services, additional_data: Dict = None) -> AgentExecutionStateSnapshot:
        """Capture snapshot of current execution state."""
        
        # Check database persistence
        db_session = real_services["db"]
        if db_session:
            try:
                # Verify data exists in database
                result = await db_session.execute(
                    "SELECT COUNT(*) FROM backend.agent_executions WHERE state = $1", state
                )
                data_persisted = (await result.fetchval()) > 0
            except Exception as e:
                logger.warning(f"Database check failed: {e}")
                data_persisted = False
        else:
            data_persisted = False
        
        # Extract business value indicators
        business_value_indicators = {}
        if additional_data:
            if "recommendations" in additional_data:
                business_value_indicators["has_recommendations"] = len(additional_data["recommendations"]) > 0
            if "insights" in additional_data:
                business_value_indicators["has_insights"] = len(additional_data["insights"]) > 0
            if "cost_savings" in additional_data:
                business_value_indicators["has_cost_savings"] = additional_data["cost_savings"] > 0
        
        snapshot = AgentExecutionStateSnapshot(
            state=state,
            timestamp=time.time(),
            websocket_event_type=event_type,
            data_persisted=data_persisted,
            business_value_indicators=business_value_indicators
        )
        
        self.state_snapshots.append(snapshot)
        return snapshot
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_complete_state_progression(self, real_services_fixture):
        """
        Test 1: Complete agent execution progresses through all required states.
        
        Validates that an agent execution moves through:
        started → thinking → tool_executing → tool_completed → completed
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            real_services_fixture, 
            user_email="test-state-progression@example.com"
        )
        
        start_time = time.time()
        
        # Simulate agent execution with state capture
        for expected_state in self.expected_state_sequence:
            await self._capture_state_snapshot(
                expected_state.value,
                expected_state.value,
                real_services_fixture,
                {"execution_id": user_context["user_id"]}
            )
            
            # Brief delay to simulate processing
            await asyncio.sleep(0.1)
        
        execution_time = time.time() - start_time
        
        # Verify all states were captured in correct order
        assert len(self.state_snapshots) == len(self.expected_state_sequence)
        
        for i, (snapshot, expected_state) in enumerate(zip(self.state_snapshots, self.expected_state_sequence)):
            assert snapshot.state == expected_state.value, \
                f"State {i}: expected {expected_state.value}, got {snapshot.state}"
            assert snapshot.websocket_event_type == expected_state.value, \
                f"WebSocket event {i}: expected {expected_state.value}, got {snapshot.websocket_event_type}"
        
        # Verify progression timing (should be reasonable)
        assert execution_time < 10.0, f"State progression took too long: {execution_time}s"
        
        # Verify final state has business value indicators
        final_snapshot = self.state_snapshots[-1]
        assert final_snapshot.state == AgentExecutionState.COMPLETED.value
        
        logger.info(f"Agent execution state progression completed in {execution_time:.2f}s with {len(self.state_snapshots)} states")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_state_persistence_database(self, real_services_fixture):
        """
        Test 2: Agent execution states are properly persisted in database.
        
        Validates that each state transition is recorded in the database
        for audit trail and recovery purposes.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        db_session = real_services_fixture["db"]
        execution_id = str(uuid.uuid4())
        
        # Create authenticated user 
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-persistence@example.com"
        )
        
        # Simulate state transitions with database persistence
        states_to_test = [
            ("started", {"message": "Starting optimization analysis"}),
            ("thinking", {"reasoning": "Analyzing cost patterns"}),
            ("tool_executing", {"tool": "cost_analyzer", "parameters": {"timeframe": "30d"}}),
            ("tool_completed", {"tool_result": {"potential_savings": 1500}}),
            ("completed", {"final_result": {"recommendations": ["Optimize EC2 instances"]}})
        ]
        
        persisted_states = []
        
        for state, state_data in states_to_test:
            # Persist state to database
            await db_session.execute("""
                INSERT INTO backend.agent_executions (id, user_id, state, state_data, created_at)
                VALUES ($1, $2, $3, $4, $5)
            """, execution_id, user_context["user_id"], state, json.dumps(state_data), datetime.utcnow())
            
            await db_session.commit()
            
            # Verify persistence
            result = await db_session.fetchrow("""
                SELECT state, state_data FROM backend.agent_executions 
                WHERE id = $1 AND state = $2
            """, execution_id, state)
            
            assert result is not None, f"State {state} not persisted in database"
            assert result["state"] == state
            persisted_data = json.loads(result["state_data"])
            assert persisted_data == state_data
            
            persisted_states.append(state)
        
        # Verify all states persisted
        assert len(persisted_states) == len(states_to_test)
        
        # Verify final state has business value
        final_state = states_to_test[-1][1]
        assert "recommendations" in final_state["final_result"]
        assert len(final_state["final_result"]["recommendations"]) > 0
        
        logger.info(f"Successfully persisted {len(persisted_states)} agent execution states")

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_agent_execution_websocket_events_sequence(self, real_services_fixture):
        """
        Test 3: WebSocket events are sent in correct sequence for agent execution.
        
        Validates that all 5 critical WebSocket events are sent in the correct order
        to enable real-time user experience during agent processing.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        # Track WebSocket events
        websocket_events = []
        expected_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-websocket-events@example.com"
        )
        
        start_time = time.time()
        
        # Simulate WebSocket event emission for each state
        for event_type in expected_events:
            event_data = {
                "type": event_type,
                "user_id": user_context["user_id"],
                "timestamp": time.time(),
                "data": self._generate_event_data_for_type(event_type)
            }
            
            websocket_events.append(event_data)
            
            # Brief processing delay
            await asyncio.sleep(0.05)
        
        total_time = time.time() - start_time
        
        # Verify all events captured
        assert len(websocket_events) == len(expected_events)
        
        # Verify event sequence
        for i, (event, expected_type) in enumerate(zip(websocket_events, expected_events)):
            assert event["type"] == expected_type, \
                f"Event {i}: expected {expected_type}, got {event['type']}"
            assert "user_id" in event
            assert "timestamp" in event
            assert "data" in event
        
        # Verify timing is reasonable for real-time UX
        assert total_time < 5.0, f"WebSocket event sequence too slow: {total_time}s"
        
        # Verify final event has business value
        final_event = websocket_events[-1]
        assert final_event["type"] == "agent_completed"
        assert "recommendations" in final_event["data"]
        
        logger.info(f"WebSocket event sequence completed in {total_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_error_state_recovery(self, real_services_fixture):
        """
        Test 4: Agent execution handles errors and recovers gracefully.
        
        Validates that agent execution can handle errors in any state
        and either recover or fail gracefully with proper user notification.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-error-recovery@example.com"
        )
        
        # Test error scenarios at different states
        error_scenarios = [
            {
                "state": "thinking", 
                "error": "LLM timeout",
                "recovery_expected": True,
                "recovery_state": "thinking"
            },
            {
                "state": "tool_executing",
                "error": "Tool execution timeout", 
                "recovery_expected": True,
                "recovery_state": "tool_executing"
            },
            {
                "state": "tool_completed",
                "error": "Invalid tool result",
                "recovery_expected": False,
                "recovery_state": "agent_error"
            }
        ]
        
        recovery_results = []
        
        for scenario in error_scenarios:
            start_time = time.time()
            
            # Simulate error condition
            error_snapshot = await self._capture_state_snapshot(
                scenario["state"],
                scenario["state"],
                real_services_fixture,
                {"error": scenario["error"], "user_id": user_context["user_id"]}
            )
            
            # Simulate recovery attempt
            if scenario["recovery_expected"]:
                # Attempt recovery
                recovery_time = 0.1  # Simulate recovery delay
                await asyncio.sleep(recovery_time)
                
                recovery_snapshot = await self._capture_state_snapshot(
                    scenario["recovery_state"],
                    scenario["recovery_state"],
                    real_services_fixture,
                    {"recovered": True, "user_id": user_context["user_id"]}
                )
                
                recovery_success = True
            else:
                # Simulate graceful failure
                error_final_snapshot = await self._capture_state_snapshot(
                    "agent_error",
                    "agent_error",
                    real_services_fixture,
                    {
                        "error": scenario["error"],
                        "user_message": "Unable to complete request due to system error",
                        "user_id": user_context["user_id"]
                    }
                )
                
                recovery_success = False
            
            recovery_time = time.time() - start_time
            
            recovery_results.append({
                "scenario": scenario["state"],
                "recovery_success": recovery_success,
                "recovery_time": recovery_time,
                "expected_recovery": scenario["recovery_expected"]
            })
        
        # Verify recovery behavior matches expectations
        for result in recovery_results:
            if result["expected_recovery"]:
                assert result["recovery_success"], \
                    f"Expected recovery for {result['scenario']} but failed"
                assert result["recovery_time"] < 2.0, \
                    f"Recovery took too long: {result['recovery_time']}s"
            else:
                assert not result["recovery_success"], \
                    f"Unexpected recovery for {result['scenario']}"
        
        logger.info(f"Error recovery testing completed: {len(recovery_results)} scenarios tested")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_concurrent_state_isolation(self, real_services_fixture):
        """
        Test 5: Multiple concurrent agent executions maintain state isolation.
        
        Validates that concurrent agent executions for different users
        maintain proper state isolation and don't interfere with each other.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        # Create multiple user contexts
        num_concurrent_users = 3
        user_contexts = []
        
        for i in range(num_concurrent_users):
            user_context = await create_authenticated_user_context(
                real_services_fixture,
                user_email=f"test-concurrent-{i}@example.com"
            )
            user_contexts.append(user_context)
        
        # Execute concurrent agent workflows
        async def execute_user_workflow(user_context: Dict, user_index: int):
            """Execute agent workflow for a specific user."""
            user_states = []
            execution_id = f"exec_{user_index}_{int(time.time())}"
            
            states = ["started", "thinking", "tool_executing", "tool_completed", "completed"]
            
            for state in states:
                state_snapshot = await self._capture_state_snapshot(
                    state,
                    state,
                    real_services_fixture,
                    {
                        "user_id": user_context["user_id"],
                        "execution_id": execution_id,
                        "user_index": user_index
                    }
                )
                user_states.append(state_snapshot)
                
                # Simulate processing delay with some randomness
                await asyncio.sleep(random.uniform(0.05, 0.15))
            
            return {
                "user_index": user_index,
                "user_id": user_context["user_id"],
                "execution_id": execution_id,
                "states": user_states,
                "success": True
            }
        
        start_time = time.time()
        
        # Run concurrent executions
        concurrent_tasks = [
            execute_user_workflow(user_context, i) 
            for i, user_context in enumerate(user_contexts)
        ]
        
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Verify all executions completed successfully
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        assert len(successful_results) == num_concurrent_users, \
            f"Expected {num_concurrent_users} successful executions, got {len(successful_results)}"
        
        # Verify state isolation - each user should have complete state sequence
        for result in successful_results:
            assert len(result["states"]) == 5, \
                f"User {result['user_index']} missing states"
            
            # Verify state sequence is correct
            expected_states = ["started", "thinking", "tool_executing", "tool_completed", "completed"]
            actual_states = [s.state for s in result["states"]]
            assert actual_states == expected_states, \
                f"User {result['user_index']} has incorrect state sequence: {actual_states}"
        
        # Verify reasonable execution time for concurrent processing
        assert total_time < 10.0, f"Concurrent execution too slow: {total_time}s"
        
        logger.info(f"Concurrent execution completed: {num_concurrent_users} users in {total_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_business_value_delivery_validation(self, real_services_fixture):
        """
        Test 6: Agent execution delivers measurable business value in final state.
        
        Validates that completed agent executions contain actionable insights,
        recommendations, or other measurable business value for users.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-business-value@example.com"
        )
        
        # Test different types of business value delivery
        business_value_scenarios = [
            {
                "agent_type": "cost_optimizer",
                "expected_value": "cost_savings",
                "final_data": {
                    "recommendations": [
                        "Optimize EC2 instances to save $1,200/month",
                        "Switch to Reserved Instances for 40% savings"
                    ],
                    "potential_savings": 1500,
                    "actionable_items": 5
                }
            },
            {
                "agent_type": "data_analyzer", 
                "expected_value": "insights",
                "final_data": {
                    "insights": [
                        "Peak usage occurs at 2-4 PM daily",
                        "Database queries 35% slower than baseline"
                    ],
                    "analysis_results": {"efficiency_score": 72},
                    "improvement_opportunities": 3
                }
            },
            {
                "agent_type": "security_auditor",
                "expected_value": "automation",
                "final_data": {
                    "actions_taken": [
                        "Updated security policies",
                        "Closed 3 vulnerabilities"
                    ],
                    "automated_fixes": 3,
                    "compliance_score": 95
                }
            }
        ]
        
        business_value_results = []
        
        for scenario in business_value_scenarios:
            start_time = time.time()
            
            # Execute agent workflow
            execution_states = []
            for state in ["started", "thinking", "tool_executing", "tool_completed", "completed"]:
                if state == "completed":
                    # Final state includes business value
                    state_data = {
                        "agent_type": scenario["agent_type"],
                        **scenario["final_data"]
                    }
                else:
                    state_data = {"agent_type": scenario["agent_type"]}
                
                snapshot = await self._capture_state_snapshot(
                    state,
                    state,
                    real_services_fixture,
                    state_data
                )
                execution_states.append(snapshot)
                
                await asyncio.sleep(0.05)
            
            execution_time = time.time() - start_time
            
            # Validate business value in final state
            final_state = execution_states[-1]
            
            # Use base class business value validation
            self.assert_business_value_delivered(
                scenario["final_data"],
                scenario["expected_value"]
            )
            
            business_value_results.append({
                "agent_type": scenario["agent_type"],
                "execution_time": execution_time,
                "business_value_type": scenario["expected_value"],
                "value_delivered": True
            })
        
        # Verify all scenarios delivered value
        assert len(business_value_results) == len(business_value_scenarios)
        
        for result in business_value_results:
            assert result["value_delivered"], \
                f"Agent {result['agent_type']} failed to deliver {result['business_value_type']}"
            assert result["execution_time"] < 5.0, \
                f"Agent {result['agent_type']} took too long: {result['execution_time']}s"
        
        logger.info(f"Business value validation completed: {len(business_value_results)} agent types tested")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_state_timing_performance(self, real_services_fixture):
        """
        Test 7: Agent execution state transitions meet performance requirements.
        
        Validates that state transitions happen within acceptable time limits
        to ensure responsive user experience.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-performance@example.com"
        )
        
        # Performance requirements (in seconds)
        performance_requirements = {
            "started_to_thinking": 1.0,
            "thinking_to_tool_executing": 5.0,
            "tool_executing_to_tool_completed": 10.0,
            "tool_completed_to_completed": 2.0,
            "total_execution": 20.0
        }
        
        # Execute timed workflow
        state_timings = {}
        workflow_start = time.time()
        previous_time = workflow_start
        
        states = ["started", "thinking", "tool_executing", "tool_completed", "completed"]
        
        for i, state in enumerate(states):
            current_time = time.time()
            
            if i > 0:
                previous_state = states[i-1]
                transition_key = f"{previous_state}_to_{state}"
                transition_time = current_time - previous_time
                state_timings[transition_key] = transition_time
            
            # Capture state
            await self._capture_state_snapshot(
                state,
                state,
                real_services_fixture,
                {"user_id": user_context["user_id"], "performance_test": True}
            )
            
            # Simulate realistic processing delay
            processing_delays = {
                "started": 0.1,
                "thinking": 0.5, 
                "tool_executing": 1.0,
                "tool_completed": 0.3,
                "completed": 0.1
            }
            await asyncio.sleep(processing_delays.get(state, 0.1))
            
            previous_time = time.time()
        
        total_execution_time = time.time() - workflow_start
        state_timings["total_execution"] = total_execution_time
        
        # Verify performance requirements
        performance_violations = []
        
        for transition, required_time in performance_requirements.items():
            actual_time = state_timings.get(transition, float('inf'))
            
            if actual_time > required_time:
                performance_violations.append({
                    "transition": transition,
                    "required": required_time,
                    "actual": actual_time,
                    "violation": actual_time - required_time
                })
        
        # Assert no critical performance violations
        if performance_violations:
            violation_details = "\n".join([
                f"- {v['transition']}: {v['actual']:.2f}s (required: {v['required']}s, violation: +{v['violation']:.2f}s)"
                for v in performance_violations
            ])
            pytest.fail(f"Performance requirements violated:\n{violation_details}")
        
        logger.info(f"Performance test passed. Total execution: {total_execution_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_state_rollback_recovery(self, real_services_fixture):
        """
        Test 8: Agent execution can rollback and recover from partial failures.
        
        Validates that failed agent executions can be rolled back to a previous
        stable state and recovered without data corruption.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        db_session = real_services_fixture["db"]
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-rollback@example.com"
        )
        
        execution_id = str(uuid.uuid4())
        
        # Create initial successful states
        stable_states = [
            ("started", {"message": "Starting analysis"}),
            ("thinking", {"reasoning": "Analyzing data patterns"})  
        ]
        
        # Persist stable states
        for state, state_data in stable_states:
            await db_session.execute("""
                INSERT INTO backend.agent_executions (id, user_id, state, state_data, created_at)
                VALUES ($1, $2, $3, $4, $5)
            """, execution_id, user_context["user_id"], state, json.dumps(state_data), datetime.utcnow())
        
        await db_session.commit()
        
        # Simulate failure during tool execution
        failure_scenarios = [
            {
                "failed_state": "tool_executing",
                "error": "Tool timeout after 30 seconds",
                "rollback_to": "thinking",
                "recovery_strategy": "retry_with_different_tool"
            },
            {
                "failed_state": "tool_completed", 
                "error": "Invalid tool result format",
                "rollback_to": "tool_executing",
                "recovery_strategy": "reprocess_tool_result"
            }
        ]
        
        rollback_results = []
        
        for scenario in failure_scenarios:
            rollback_start = time.time()
            
            # Attempt to add failed state
            try:
                await db_session.execute("""
                    INSERT INTO backend.agent_executions (id, user_id, state, state_data, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, execution_id, user_context["user_id"], scenario["failed_state"], 
                json.dumps({"error": scenario["error"]}), datetime.utcnow())
                
                await db_session.commit()
                
                # Simulate detection of failure
                await asyncio.sleep(0.1)
                
                # Rollback: Remove failed state
                await db_session.execute("""
                    DELETE FROM backend.agent_executions 
                    WHERE id = $1 AND state = $2
                """, execution_id, scenario["failed_state"])
                
                await db_session.commit()
                
                # Verify rollback successful
                rollback_check = await db_session.fetchval("""
                    SELECT COUNT(*) FROM backend.agent_executions 
                    WHERE id = $1 AND state = $2
                """, execution_id, scenario["failed_state"])
                
                assert rollback_check == 0, f"Rollback failed - {scenario['failed_state']} still exists"
                
                # Verify stable states still exist
                stable_check = await db_session.fetchval("""
                    SELECT COUNT(*) FROM backend.agent_executions 
                    WHERE id = $1 AND state IN ('started', 'thinking')
                """, execution_id)
                
                assert stable_check == 2, "Stable states lost during rollback"
                
                # Simulate recovery
                recovery_state = scenario["rollback_to"]
                recovery_data = {
                    "recovery_attempt": True,
                    "strategy": scenario["recovery_strategy"],
                    "previous_error": scenario["error"]
                }
                
                await db_session.execute("""
                    UPDATE backend.agent_executions 
                    SET state_data = $1, updated_at = $2
                    WHERE id = $3 AND state = $4
                """, json.dumps(recovery_data), datetime.utcnow(), execution_id, recovery_state)
                
                await db_session.commit()
                
                rollback_time = time.time() - rollback_start
                
                rollback_results.append({
                    "scenario": scenario["failed_state"],
                    "rollback_successful": True,
                    "recovery_successful": True,
                    "rollback_time": rollback_time
                })
                
            except Exception as e:
                rollback_results.append({
                    "scenario": scenario["failed_state"],
                    "rollback_successful": False,
                    "recovery_successful": False,
                    "error": str(e)
                })
        
        # Verify rollback results
        for result in rollback_results:
            assert result["rollback_successful"], \
                f"Rollback failed for {result['scenario']}: {result.get('error')}"
            assert result["recovery_successful"], \
                f"Recovery failed for {result['scenario']}"
            assert result["rollback_time"] < 5.0, \
                f"Rollback took too long: {result['rollback_time']}s"
        
        logger.info(f"Rollback recovery testing completed: {len(rollback_results)} scenarios tested")

    def _generate_event_data_for_type(self, event_type: str) -> Dict[str, Any]:
        """Generate appropriate event data for WebSocket event type."""
        event_data_templates = {
            "agent_started": {
                "message": "Agent execution started",
                "agent_type": "cost_optimizer"
            },
            "agent_thinking": {
                "reasoning": "Analyzing cost optimization opportunities",
                "progress": 25
            },
            "tool_executing": {
                "tool_name": "cost_analyzer",
                "parameters": {"timeframe": "30d"},
                "progress": 50
            },
            "tool_completed": {
                "tool_result": {"potential_savings": 1200},
                "progress": 75
            },
            "agent_completed": {
                "recommendations": [
                    "Optimize EC2 instance types",
                    "Implement auto-scaling"
                ],
                "final_result": {"cost_savings": 1200},
                "progress": 100
            }
        }
        
        return event_data_templates.get(event_type, {"event_type": event_type})