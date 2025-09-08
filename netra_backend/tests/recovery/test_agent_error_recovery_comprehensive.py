"""
Agent Error Recovery Testing (Iterations 36-40 completion).

Tests comprehensive error recovery, resilience patterns,
and fault tolerance mechanisms for agent operations.
"""

import asyncio
import pytest
from typing import Dict, Any, List
import time
import random
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import RedisTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent


@pytest.mark.recovery
class TestAgentErrorRecovery:
    """Test comprehensive agent error recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_agent_automatic_error_recovery(self):
        """Test agent automatic recovery from various error scenarios."""
        # Mock recovery strategies
        recovery_attempts = []
        
        def mock_execute_recovery_strategy(strategy_name, error_context, attempt_number):
            recovery_attempt = {
                "strategy": strategy_name,
                "error_context": error_context,
                "attempt": attempt_number,
                "timestamp": time.time(),
                "success": attempt_number <= 2  # Succeed after 2 attempts
            }
            recovery_attempts.append(recovery_attempt)
            return recovery_attempt["success"]
        
        with patch('netra_backend.app.recovery.recovery_manager.execute_strategy', side_effect=mock_execute_recovery_strategy):
            
            agent_state = DeepAgentState(
                agent_id="recovery_agent",
                session_id="recovery_session",
                thread_id="recovery_thread",
                context={"automatic_recovery": True, "recovery_strategies": ["retry", "fallback", "circuit_breaker"]}
            )
            
            agent = SupervisorAgent(
                agent_id="error_recovery_test",
                initial_state=agent_state
            )
            
            # Test different error scenarios with recovery
            error_scenarios = [
                {
                    "error_type": "ConnectionError",
                    "error_message": "Database connection failed",
                    "recovery_strategy": "retry_with_backoff",
                    "expected_recovery": True
                },
                {
                    "error_type": "TimeoutError", 
                    "error_message": "Operation timeout",
                    "recovery_strategy": "timeout_adjustment",
                    "expected_recovery": True
                },
                {
                    "error_type": "ServiceUnavailableError",
                    "error_message": "External service down",
                    "recovery_strategy": "fallback_service",
                    "expected_recovery": True
                },
                {
                    "error_type": "ValidationError",
                    "error_message": "Invalid input data",
                    "recovery_strategy": "data_sanitization", 
                    "expected_recovery": False  # Some errors can't be auto-recovered
                }
            ]
            
            recovery_results = []
            
            for scenario in error_scenarios:
                result = await agent._execute_with_automatic_recovery({
                    "operation": "test_operation",
                    "simulate_error": scenario,
                    "max_recovery_attempts": 3
                })
                recovery_results.append(result)
            
            # Verify recovery attempts were made
            assert len(recovery_attempts) >= len([s for s in error_scenarios if s["expected_recovery"]])
            
            # Check recovery success rates
            successful_recoveries = [r for r in recovery_results if r.get("status") == "recovered"]
            expected_successes = [s for s in error_scenarios if s["expected_recovery"]]
            
            assert len(successful_recoveries) >= len(expected_successes) * 0.8  # 80% success rate
            
            # Verify recovery strategies were used appropriately
            connection_recoveries = [a for a in recovery_attempts if "connection" in a["error_context"].get("error_type", "").lower()]
            timeout_recoveries = [a for a in recovery_attempts if "timeout" in a["error_context"].get("error_type", "").lower()]
            
            assert len(connection_recoveries) >= 1
            assert len(timeout_recoveries) >= 1
            
            # Check recovery attempt progression
            for attempt in recovery_attempts:
                assert attempt["attempt"] >= 1
                assert attempt["strategy"] in ["retry_with_backoff", "timeout_adjustment", "fallback_service", "data_sanitization"]
    
    @pytest.mark.asyncio
    async def test_agent_cascading_failure_prevention(self):
        """Test agent prevents cascading failures through isolation."""
        # Mock failure propagation tracking
        failure_events = []
        isolation_actions = []
        
        def mock_detect_failure_cascade(failure_context):
            failure_event = {
                "failure_id": f"failure_{len(failure_events) + 1}",
                "failure_type": failure_context.get("type", "unknown"),
                "origin_agent": failure_context.get("agent_id"),
                "affected_components": failure_context.get("components", []),
                "cascade_risk": failure_context.get("cascade_risk", "medium"),
                "timestamp": time.time()
            }
            failure_events.append(failure_event)
            
            # Determine if isolation is needed
            return failure_event["cascade_risk"] in ["high", "critical"]
        
        def mock_isolate_component(component_id, isolation_type, duration):
            isolation_action = {
                "component_id": component_id,
                "isolation_type": isolation_type,  # "circuit_break", "throttle", "quarantine"
                "duration": duration,
                "timestamp": time.time(),
                "isolation_id": f"isolation_{len(isolation_actions) + 1}"
            }
            isolation_actions.append(isolation_action)
            return isolation_action
        
        with patch('netra_backend.app.recovery.cascade_detector.detect_cascade', side_effect=mock_detect_failure_cascade):
            with patch('netra_backend.app.recovery.isolation_manager.isolate', side_effect=mock_isolate_component):
                
                agent_state = DeepAgentState(
                    agent_id="cascade_prevention_agent",
                    session_id="cascade_session",
                    thread_id="cascade_thread",
                    context={
                        "cascade_prevention": True,
                        "isolation_enabled": True,
                        "failure_detection": True
                    }
                )
                
                agent = SupervisorAgent(
                    agent_id="cascade_prevention_test",
                    initial_state=agent_state
                )
                
                # Simulate cascading failure scenarios
                cascade_scenarios = [
                    {
                        "failure_sequence": [
                            {"component": "database", "type": "connection_pool_exhausted", "cascade_risk": "high"},
                            {"component": "cache", "type": "memory_overflow", "cascade_risk": "medium"},
                            {"component": "api_gateway", "type": "rate_limit_exceeded", "cascade_risk": "critical"}
                        ]
                    },
                    {
                        "failure_sequence": [
                            {"component": "llm_service", "type": "quota_exceeded", "cascade_risk": "high"},
                            {"component": "websocket_manager", "type": "connection_storm", "cascade_risk": "medium"}
                        ]
                    }
                ]
                
                for scenario_idx, scenario in enumerate(cascade_scenarios):
                    for step_idx, failure in enumerate(scenario["failure_sequence"]):
                        # Simulate failure propagation
                        await agent._handle_component_failure({
                            "component": failure["component"],
                            "failure_type": failure["type"],
                            "cascade_risk": failure["cascade_risk"],
                            "scenario_id": scenario_idx,
                            "step_id": step_idx
                        })
                        
                        # Small delay to simulate failure propagation
                        await asyncio.sleep(0.01)
                
                # Verify failure detection and isolation
                assert len(failure_events) >= 5  # Total failures across scenarios
                
                # Check that high-risk failures triggered isolation
                high_risk_failures = [f for f in failure_events if f["cascade_risk"] in ["high", "critical"]]
                assert len(isolation_actions) >= len(high_risk_failures)
                
                # Verify isolation types are appropriate
                isolation_types = [a["isolation_type"] for a in isolation_actions]
                assert "circuit_break" in isolation_types or "throttle" in isolation_types
                
                # Check component-specific isolations
                database_isolations = [a for a in isolation_actions if "database" in a["component_id"]]
                api_isolations = [a for a in isolation_actions if "api" in a["component_id"]]
                
                assert len(database_isolations) >= 1
                assert len(api_isolations) >= 1
    
    @pytest.mark.asyncio
    async def test_agent_state_recovery_and_rollback(self):
        """Test agent state recovery and transaction rollback mechanisms."""
        # Mock state management
        state_snapshots = []
        rollback_operations = []
        
        def mock_create_state_snapshot(agent_id, checkpoint_name):
            snapshot = {
                "snapshot_id": f"snapshot_{len(state_snapshots) + 1}",
                "agent_id": agent_id,
                "checkpoint_name": checkpoint_name,
                "state_data": {
                    "current_task": "data_processing",
                    "progress": 0.6,
                    "context_variables": {"processed_records": 1200, "batch_id": "batch_123"},
                    "resource_allocations": {"memory_mb": 256, "cpu_cores": 2}
                },
                "timestamp": time.time()
            }
            state_snapshots.append(snapshot)
            return snapshot
        
        def mock_rollback_to_snapshot(snapshot_id, rollback_reason):
            rollback_op = {
                "rollback_id": f"rollback_{len(rollback_operations) + 1}",
                "snapshot_id": snapshot_id,
                "rollback_reason": rollback_reason,
                "timestamp": time.time(),
                "success": True
            }
            rollback_operations.append(rollback_op)
            return rollback_op
        
        with patch('netra_backend.app.recovery.state_manager.create_snapshot', side_effect=mock_create_state_snapshot):
            with patch('netra_backend.app.recovery.state_manager.rollback_to_snapshot', side_effect=mock_rollback_to_snapshot):
                
                agent_state = DeepAgentState(
                    agent_id="state_recovery_agent",
                    session_id="state_session",
                    thread_id="state_thread",
                    context={
                        "state_recovery": True,
                        "checkpoint_frequency": "before_critical_operations",
                        "automatic_rollback": True
                    }
                )
                
                agent = SupervisorAgent(
                    agent_id="state_recovery_test", 
                    initial_state=agent_state
                )
                
                # Execute operations with state checkpointing
                operation_sequence = [
                    {"name": "initialize_processing", "checkpoint": True, "expect_success": True},
                    {"name": "load_data", "checkpoint": True, "expect_success": True},
                    {"name": "validate_data", "checkpoint": False, "expect_success": True},
                    {"name": "process_batch_1", "checkpoint": True, "expect_success": True},
                    {"name": "process_batch_2", "checkpoint": False, "expect_success": False},  # This will fail
                    {"name": "rollback_and_retry", "checkpoint": False, "expect_success": True}
                ]
                
                execution_results = []
                
                for operation in operation_sequence:
                    result = await agent._execute_stateful_operation(operation)
                    execution_results.append(result)
                
                # Verify state snapshots were created
                checkpoint_operations = [op for op in operation_sequence if op.get("checkpoint")]
                assert len(state_snapshots) >= len(checkpoint_operations)
                
                # Verify rollback occurred after failure
                failed_operations = [op for op in operation_sequence if not op.get("expect_success")]
                assert len(rollback_operations) >= len(failed_operations)
                
                # Check rollback details
                for rollback in rollback_operations:
                    assert rollback["success"] is True
                    assert "rollback_reason" in rollback
                    assert rollback["snapshot_id"] in [s["snapshot_id"] for s in state_snapshots]
                
                # Verify state consistency after recovery
                final_result = execution_results[-1]
                assert final_result["status"] == "completed"
                assert final_result["state_consistent"] is True
                
                # Check that rollback restored to valid checkpoint
                if rollback_operations:
                    last_rollback = rollback_operations[-1]
                    rollback_snapshot = next(s for s in state_snapshots if s["snapshot_id"] == last_rollback["snapshot_id"])
                    assert rollback_snapshot["checkpoint_name"] in ["initialize_processing", "load_data", "process_batch_1"]


@pytest.mark.recovery
class TestAgentResiliencePatterns:
    """Test advanced resilience patterns in agent operations."""
    
    @pytest.mark.asyncio
    async def test_agent_bulkhead_isolation(self):
        """Test bulkhead isolation pattern in agent resource management."""
        # Mock resource pools
        resource_pools = {
            "database_pool": {"capacity": 10, "used": 0, "reserved": 2},
            "llm_pool": {"capacity": 5, "used": 0, "reserved": 1}, 
            "processing_pool": {"capacity": 8, "used": 0, "reserved": 2},
            "network_pool": {"capacity": 15, "used": 0, "reserved": 3}
        }
        
        pool_allocations = []
        
        def mock_allocate_from_pool(pool_name, resource_count, operation_type):
            pool = resource_pools.get(pool_name)
            if not pool:
                return {"success": False, "reason": "pool_not_found"}
            
            available = pool["capacity"] - pool["used"] - pool["reserved"]
            if available < resource_count:
                return {"success": False, "reason": "insufficient_capacity"}
            
            pool["used"] += resource_count
            allocation = {
                "pool_name": pool_name,
                "resources_allocated": resource_count,
                "operation_type": operation_type,
                "allocation_id": f"alloc_{len(pool_allocations) + 1}",
                "timestamp": time.time()
            }
            pool_allocations.append(allocation)
            return {"success": True, "allocation_id": allocation["allocation_id"]}
        
        def mock_release_from_pool(allocation_id):
            allocation = next((a for a in pool_allocations if a["allocation_id"] == allocation_id), None)
            if allocation:
                pool = resource_pools[allocation["pool_name"]]
                pool["used"] -= allocation["resources_allocated"]
                return {"success": True}
            return {"success": False}
        
        with patch('netra_backend.app.resilience.bulkhead_manager.allocate', side_effect=mock_allocate_from_pool):
            with patch('netra_backend.app.resilience.bulkhead_manager.release', side_effect=mock_release_from_pool):
                
                agent_state = DeepAgentState(
                    agent_id="bulkhead_agent",
                    session_id="bulkhead_session", 
                    thread_id="bulkhead_thread",
                    context={"bulkhead_isolation": True, "resource_management": "strict"}
                )
                
                agent = SupervisorAgent(
                    agent_id="bulkhead_test",
                    initial_state=agent_state
                )
                
                # Execute operations with different resource requirements
                bulkhead_operations = [
                    {"type": "database_heavy", "pools": [("database_pool", 3), ("processing_pool", 2)]},
                    {"type": "llm_analysis", "pools": [("llm_pool", 2), ("network_pool", 1)]},
                    {"type": "mixed_workload", "pools": [("database_pool", 2), ("llm_pool", 1), ("processing_pool", 3)]},
                    {"type": "network_intensive", "pools": [("network_pool", 5), ("processing_pool", 1)]}
                ]
                
                operation_results = []
                
                for operation in bulkhead_operations:
                    result = await agent._execute_bulkhead_operation(operation)
                    operation_results.append(result)
                
                # Verify resource allocation succeeded for most operations
                successful_operations = [r for r in operation_results if r.get("status") == "completed"]
                assert len(successful_operations) >= 3  # Most operations should succeed
                
                # Check bulkhead isolation
                total_allocations = len(pool_allocations)
                assert total_allocations >= 6  # Multiple pool allocations per operation
                
                # Verify pool capacity limits were respected
                for pool_name, pool_data in resource_pools.items():
                    peak_usage = pool_data["used"]  # Current usage after all operations
                    assert peak_usage <= pool_data["capacity"] - pool_data["reserved"]
                
                # Check that different operation types used appropriate pools
                db_heavy_allocs = [a for a in pool_allocations if "database" in a["pool_name"] and a["operation_type"] == "database_heavy"]
                llm_allocs = [a for a in pool_allocations if "llm" in a["pool_name"] and a["operation_type"] == "llm_analysis"]
                
                assert len(db_heavy_allocs) >= 1
                assert len(llm_allocs) >= 1
    
    @pytest.mark.asyncio
    async def test_agent_adaptive_timeout_management(self):
        """Test adaptive timeout management based on operation patterns."""
        # Mock adaptive timeout manager
        timeout_history = []
        timeout_adjustments = []
        
        def mock_calculate_adaptive_timeout(operation_type, historical_data, current_conditions):
            # Simple adaptive timeout calculation
            base_timeout = {"database": 5.0, "llm": 30.0, "processing": 15.0, "network": 10.0}.get(operation_type, 10.0)
            
            # Adjust based on recent failure rate
            recent_failures = len([h for h in historical_data if not h.get("success", True)])
            failure_rate = recent_failures / max(len(historical_data), 1)
            
            # Increase timeout if high failure rate
            if failure_rate > 0.3:
                adjusted_timeout = base_timeout * (1.5 + failure_rate)
            elif failure_rate < 0.1:
                adjusted_timeout = base_timeout * 0.8  # Decrease if low failure rate
            else:
                adjusted_timeout = base_timeout
            
            # Factor in current system load
            load_factor = current_conditions.get("system_load", 0.5)
            final_timeout = adjusted_timeout * (1 + load_factor * 0.5)
            
            adjustment = {
                "operation_type": operation_type,
                "base_timeout": base_timeout,
                "adjusted_timeout": adjusted_timeout,
                "final_timeout": final_timeout,
                "failure_rate": failure_rate,
                "load_factor": load_factor,
                "timestamp": time.time()
            }
            timeout_adjustments.append(adjustment)
            
            return final_timeout
        
        def mock_record_operation_result(operation_type, duration, success, timeout_used):
            history_entry = {
                "operation_type": operation_type,
                "duration": duration,
                "success": success,
                "timeout_used": timeout_used,
                "timestamp": time.time()
            }
            timeout_history.append(history_entry)
        
        with patch('netra_backend.app.resilience.adaptive_timeout.calculate_timeout', side_effect=mock_calculate_adaptive_timeout):
            with patch('netra_backend.app.resilience.adaptive_timeout.record_result', side_effect=mock_record_operation_result):
                
                agent_state = DeepAgentState(
                    agent_id="adaptive_timeout_agent",
                    session_id="timeout_session",
                    thread_id="timeout_thread",
                    context={"adaptive_timeouts": True, "timeout_learning": True}
                )
                
                agent = SupervisorAgent(
                    agent_id="adaptive_timeout_test",
                    initial_state=agent_state
                )
                
                # Simulate operations with varying success patterns
                operation_patterns = [
                    # Initial operations - establish baseline
                    {"type": "database", "simulate_duration": 2.0, "simulate_success": True},
                    {"type": "database", "simulate_duration": 3.5, "simulate_success": True},
                    {"type": "database", "simulate_duration": 1.8, "simulate_success": True},
                    
                    # Introduce failures - should increase timeouts
                    {"type": "database", "simulate_duration": 7.0, "simulate_success": False},  # Timeout
                    {"type": "database", "simulate_duration": 6.5, "simulate_success": False},  # Timeout
                    {"type": "database", "simulate_duration": 2.2, "simulate_success": True},   # Success with higher timeout
                    
                    # Recovery period - should optimize timeouts
                    {"type": "database", "simulate_duration": 1.5, "simulate_success": True},
                    {"type": "database", "simulate_duration": 2.1, "simulate_success": True},
                    {"type": "database", "simulate_duration": 1.9, "simulate_success": True},
                ]
                
                adaptive_results = []
                
                for pattern in operation_patterns:
                    # Get historical data for this operation type
                    historical_data = [h for h in timeout_history if h["operation_type"] == pattern["type"]]
                    current_conditions = {"system_load": random.uniform(0.2, 0.8)}
                    
                    result = await agent._execute_adaptive_timeout_operation({
                        "operation_type": pattern["type"],
                        "historical_data": historical_data,
                        "current_conditions": current_conditions,
                        "simulate": pattern
                    })
                    adaptive_results.append(result)
                
                # Verify timeout adaptation occurred
                assert len(timeout_adjustments) >= len(operation_patterns)
                
                # Check that timeouts adapted to failure patterns
                early_adjustments = timeout_adjustments[:3]  # Baseline period
                failure_period_adjustments = timeout_adjustments[3:6]  # High failure period
                recovery_adjustments = timeout_adjustments[6:]  # Recovery period
                
                # Timeouts should increase during failure period
                if failure_period_adjustments and early_adjustments:
                    avg_early_timeout = sum(a["final_timeout"] for a in early_adjustments) / len(early_adjustments)
                    avg_failure_timeout = sum(a["final_timeout"] for a in failure_period_adjustments) / len(failure_period_adjustments)
                    assert avg_failure_timeout > avg_early_timeout  # Timeouts increased
                
                # Verify operation results reflect timeout effectiveness
                successful_operations = [r for r in adaptive_results if r.get("status") == "completed"]
                timeout_operations = [r for r in adaptive_results if r.get("status") == "timeout"]
                
                # Should see improvement in success rate as timeouts adapt
                later_operations = adaptive_results[-3:]  # Last 3 operations
                later_successes = [r for r in later_operations if r.get("status") == "completed"]
                assert len(later_successes) >= 2  # Most recent operations should succeed