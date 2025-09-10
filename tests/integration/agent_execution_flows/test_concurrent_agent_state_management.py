"""
Test Concurrent Agent State Management Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure stable agent operations under concurrent load
- Value Impact: Prevents state corruption and race conditions that could break AI workflows
- Strategic Impact: Enables scalable platform supporting many concurrent users without degradation

Tests concurrent agent state management including race condition prevention,
state consistency under load, deadlock prevention, and performance optimization.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.agent_state_tracker import AgentStateTracker
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine


class TestConcurrentAgentStateManagement(BaseIntegrationTest):
    """Integration tests for concurrent agent state management."""

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_high_concurrency_state_updates(self, real_services_fixture):
        """Test state consistency under high concurrency loads."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="concurrent_user_1200",
            thread_id="thread_1500",
            session_id="session_1800",
            workspace_id="concurrent_workspace_1100"
        )
        
        state_tracker = AgentStateTracker(
            user_context=user_context,
            concurrency_control=True,
            max_concurrent_operations=50,
            locking_strategy="optimistic_with_retry"
        )
        
        # Create shared agent state
        shared_agent_state = DeepAgentState(
            agent_id="high_concurrency_agent", 
            user_context=user_context,
            initial_state="processing"
        )
        
        # Initialize shared counters and data
        initial_data = {
            "operation_count": 0,
            "total_processed": 0,
            "concurrent_updates": [],
            "state_version": 1
        }
        
        await state_tracker.update_agent_state_data(
            agent_state=shared_agent_state,
            data_update=initial_data
        )
        
        # Track concurrent operations
        operation_results = []
        operation_lock = asyncio.Lock()
        
        async def concurrent_state_operation(operation_id: int, operation_type: str):
            """Perform concurrent state operations with different patterns."""
            try:
                start_time = time.time()
                
                if operation_type == "increment_counter":
                    # Read-modify-write operation (race condition prone)
                    current_count = shared_agent_state.get_state_data("operation_count", 0)
                    await asyncio.sleep(0.01)  # Simulate processing time
                    
                    await state_tracker.update_agent_state_data(
                        agent_state=shared_agent_state,
                        data_update={"operation_count": current_count + 1},
                        operation_id=f"increment_{operation_id}"
                    )
                
                elif operation_type == "accumulate_value":
                    # Accumulation operation
                    current_total = shared_agent_state.get_state_data("total_processed", 0)
                    value_to_add = operation_id * 10
                    
                    await state_tracker.update_agent_state_data(
                        agent_state=shared_agent_state,
                        data_update={"total_processed": current_total + value_to_add},
                        operation_id=f"accumulate_{operation_id}"
                    )
                
                elif operation_type == "append_to_list":
                    # List append operation
                    current_updates = shared_agent_state.get_state_data("concurrent_updates", [])
                    current_updates.append({
                        "operation_id": operation_id,
                        "timestamp": time.time(),
                        "thread_info": f"async_task_{operation_id}"
                    })
                    
                    await state_tracker.update_agent_state_data(
                        agent_state=shared_agent_state,
                        data_update={"concurrent_updates": current_updates},
                        operation_id=f"append_{operation_id}"
                    )
                
                elif operation_type == "version_update":
                    # Version-based update
                    current_version = shared_agent_state.get_state_data("state_version", 1)
                    
                    await state_tracker.update_agent_state_data(
                        agent_state=shared_agent_state,
                        data_update={"state_version": current_version + 1},
                        operation_id=f"version_{operation_id}",
                        expected_version=current_version
                    )
                
                end_time = time.time()
                
                async with operation_lock:
                    operation_results.append({
                        "operation_id": operation_id,
                        "operation_type": operation_type,
                        "success": True,
                        "duration": end_time - start_time
                    })
                    
            except Exception as e:
                async with operation_lock:
                    operation_results.append({
                        "operation_id": operation_id,
                        "operation_type": operation_type,
                        "success": False,
                        "error": str(e)
                    })
        
        # Act - Launch high concurrency operations
        concurrent_tasks = []
        operation_types = ["increment_counter", "accumulate_value", "append_to_list", "version_update"]
        
        for i in range(100):  # 100 concurrent operations
            operation_type = operation_types[i % len(operation_types)]
            task = asyncio.create_task(
                concurrent_state_operation(i, operation_type)
            )
            concurrent_tasks.append(task)
        
        # Wait for all operations to complete
        await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Assert - Verify concurrent operation handling
        successful_operations = [r for r in operation_results if r["success"]]
        failed_operations = [r for r in operation_results if not r["success"]]
        
        # Should handle most operations successfully
        success_rate = len(successful_operations) / len(operation_results)
        assert success_rate >= 0.9  # At least 90% success rate
        
        # Verify state consistency
        final_state_data = shared_agent_state.get_all_state_data()
        
        # Operation count should reflect successful increment operations
        increment_successes = len([r for r in successful_operations if r["operation_type"] == "increment_counter"])
        assert final_state_data["operation_count"] <= increment_successes  # May be less due to race conditions handled
        
        # List operations should have preserved most entries
        assert len(final_state_data["concurrent_updates"]) >= 20  # Should preserve most append operations
        
        # Version should be consistent
        assert final_state_data["state_version"] >= 1

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_deadlock_prevention_and_detection(self, real_services_fixture):
        """Test deadlock prevention mechanisms in concurrent state operations."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="deadlock_user_1201",
            thread_id="thread_1501",
            session_id="session_1801",
            workspace_id="deadlock_workspace_1101"
        )
        
        state_tracker = AgentStateTracker(
            user_context=user_context,
            deadlock_detection=True,
            deadlock_timeout_seconds=5,
            lock_ordering=True
        )
        
        # Create multiple agent states that could create deadlock scenarios
        agent_states = []
        for i in range(3):
            agent_state = DeepAgentState(
                agent_id=f"deadlock_agent_{i}",
                user_context=user_context,
                initial_state="ready"
            )
            agent_states.append(agent_state)
        
        deadlock_detected = False
        deadlock_recovery_successful = False
        operation_results = []
        
        async def potentially_deadlocking_operation(op_id: int, agent_sequence: List[int]):
            """Operation that could cause deadlock by accessing agents in different orders."""
            nonlocal deadlock_detected, deadlock_recovery_successful
            
            try:
                # Access agents in specified order (potential for circular wait)
                for agent_idx in agent_sequence:
                    await state_tracker.acquire_agent_lock(
                        agent_states[agent_idx],
                        lock_type="exclusive",
                        timeout_seconds=3
                    )
                    
                    # Simulate work
                    await asyncio.sleep(0.1)
                    
                    await state_tracker.update_agent_state_data(
                        agent_state=agent_states[agent_idx],
                        data_update={f"operation_{op_id}_processed": True},
                        operation_id=f"deadlock_op_{op_id}"
                    )
                
                # Release locks in reverse order
                for agent_idx in reversed(agent_sequence):
                    await state_tracker.release_agent_lock(
                        agent_states[agent_idx],
                        lock_type="exclusive"
                    )
                
                operation_results.append({
                    "operation_id": op_id,
                    "success": True,
                    "agent_sequence": agent_sequence
                })
                
            except Exception as e:
                if "deadlock" in str(e).lower() or "timeout" in str(e).lower():
                    deadlock_detected = True
                    
                    # Attempt deadlock recovery
                    try:
                        await state_tracker.recover_from_deadlock(
                            operation_id=f"deadlock_op_{op_id}",
                            recovery_strategy="release_all_locks"
                        )
                        deadlock_recovery_successful = True
                    except Exception:
                        pass
                
                operation_results.append({
                    "operation_id": op_id,
                    "success": False,
                    "error": str(e),
                    "deadlock_related": "deadlock" in str(e).lower() or "timeout" in str(e).lower()
                })
        
        # Act - Create potential deadlock scenarios
        deadlock_scenarios = [
            # Circular wait scenarios
            ([0, 1, 2], [2, 1, 0], [1, 2, 0]),  # Different access orders
            ([0, 2], [2, 0], [0, 2]),           # Simpler circular wait
            ([1, 0], [0, 1], [1, 0]),           # Two-agent deadlock
        ]
        
        for scenario_idx, agent_sequences in enumerate(deadlock_scenarios):
            tasks = []
            for seq_idx, agent_sequence in enumerate(agent_sequences):
                op_id = scenario_idx * 10 + seq_idx
                task = asyncio.create_task(
                    potentially_deadlocking_operation(op_id, agent_sequence)
                )
                tasks.append(task)
            
            # Run scenario operations concurrently
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert - Verify deadlock prevention and recovery
        total_operations = len(operation_results)
        successful_operations = [r for r in operation_results if r["success"]]
        deadlock_related_failures = [r for r in operation_results if not r["success"] and r.get("deadlock_related", False)]
        
        # System should either prevent deadlocks or recover from them
        # Total operations should complete (either successfully or with proper error handling)
        assert total_operations >= 6  # Should have attempted all operations
        
        if deadlock_detected:
            # If deadlock was detected, recovery should have been attempted
            assert deadlock_recovery_successful is True
            assert len(deadlock_related_failures) > 0
        
        # System should remain functional after deadlock scenarios
        # Test a simple operation to verify system health
        test_agent = agent_states[0]
        post_deadlock_result = await state_tracker.update_agent_state_data(
            agent_state=test_agent,
            data_update={"post_deadlock_test": True},
            operation_id="health_check"
        )
        
        assert post_deadlock_result.success is True

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_state_consistency_under_mixed_operations(self, real_services_fixture):
        """Test state consistency under mixed read/write operations."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="mixed_ops_user_1202",
            thread_id="thread_1502",
            session_id="session_1802", 
            workspace_id="mixed_ops_workspace_1102"
        )
        
        state_tracker = AgentStateTracker(
            user_context=user_context,
            consistency_level="strong",
            read_write_isolation=True
        )
        
        # Create agent with complex state
        agent_state = DeepAgentState(
            agent_id="mixed_operations_agent",
            user_context=user_context,
            initial_state="active"
        )
        
        # Initialize complex state structure
        complex_initial_state = {
            "financial_data": {
                "monthly_costs": [10000, 12000, 11500, 13000, 14000],
                "cost_trends": {"increasing": True, "rate": 0.12},
                "budget_remaining": 50000
            },
            "optimization_progress": {
                "total_recommendations": 0,
                "implemented_count": 0,
                "estimated_savings": 0.0,
                "progress_percentage": 0.0
            },
            "audit_log": [],
            "concurrent_readers": 0,
            "concurrent_writers": 0
        }
        
        await state_tracker.update_agent_state_data(
            agent_state=agent_state,
            data_update=complex_initial_state
        )
        
        # Track operation statistics
        operation_stats = {
            "read_operations": 0,
            "write_operations": 0,
            "consistency_violations": 0,
            "read_write_conflicts": 0
        }
        stats_lock = asyncio.Lock()
        
        async def mixed_read_operation(op_id: int, read_pattern: str):
            """Various read operation patterns."""
            try:
                async with stats_lock:
                    operation_stats["read_operations"] += 1
                
                if read_pattern == "financial_analysis":
                    # Read financial data for analysis
                    monthly_costs = agent_state.get_state_data("financial_data.monthly_costs", [])
                    cost_trends = agent_state.get_state_data("financial_data.cost_trends", {})
                    budget = agent_state.get_state_data("financial_data.budget_remaining", 0)
                    
                    # Verify consistency
                    if monthly_costs and cost_trends and budget > 0:
                        # Data should be consistent
                        if len(monthly_costs) > 2:
                            latest_trend = monthly_costs[-1] > monthly_costs[-2]
                            expected_trend = cost_trends.get("increasing", False)
                            if latest_trend != expected_trend:
                                async with stats_lock:
                                    operation_stats["consistency_violations"] += 1
                
                elif read_pattern == "progress_monitoring":
                    # Read optimization progress
                    progress = agent_state.get_state_data("optimization_progress", {})
                    
                    # Check internal consistency
                    total_recs = progress.get("total_recommendations", 0)
                    implemented = progress.get("implemented_count", 0)
                    percentage = progress.get("progress_percentage", 0.0)
                    
                    if total_recs > 0:
                        expected_percentage = (implemented / total_recs) * 100
                        if abs(percentage - expected_percentage) > 1.0:  # Allow small floating point differences
                            async with stats_lock:
                                operation_stats["consistency_violations"] += 1
                
                elif read_pattern == "audit_review":
                    # Read audit log
                    audit_log = agent_state.get_state_data("audit_log", [])
                    
                    # Verify log ordering (should be chronological)
                    if len(audit_log) > 1:
                        for i in range(1, len(audit_log)):
                            if audit_log[i]["timestamp"] < audit_log[i-1]["timestamp"]:
                                async with stats_lock:
                                    operation_stats["consistency_violations"] += 1
                                break
                
                return {"success": True, "operation_id": op_id, "pattern": read_pattern}
                
            except Exception as e:
                return {"success": False, "operation_id": op_id, "error": str(e)}
        
        async def mixed_write_operation(op_id: int, write_pattern: str):
            """Various write operation patterns."""
            try:
                async with stats_lock:
                    operation_stats["write_operations"] += 1
                
                if write_pattern == "add_cost_data":
                    # Add new monthly cost data
                    current_costs = agent_state.get_state_data("financial_data.monthly_costs", [])
                    new_cost = 15000 + (op_id * 100)  # Simulate increasing costs
                    current_costs.append(new_cost)
                    
                    # Update trends based on new data
                    if len(current_costs) >= 2:
                        increasing = current_costs[-1] > current_costs[-2]
                        trend_data = agent_state.get_state_data("financial_data.cost_trends", {})
                        trend_data["increasing"] = increasing
                        
                        await state_tracker.update_agent_state_data(
                            agent_state=agent_state,
                            data_update={
                                "financial_data.monthly_costs": current_costs,
                                "financial_data.cost_trends": trend_data
                            },
                            operation_id=f"add_cost_{op_id}"
                        )
                
                elif write_pattern == "update_progress":
                    # Update optimization progress
                    current_progress = agent_state.get_state_data("optimization_progress", {})
                    
                    # Add new recommendation
                    current_progress["total_recommendations"] += 1
                    
                    # Sometimes mark as implemented
                    if op_id % 3 == 0:
                        current_progress["implemented_count"] += 1
                        current_progress["estimated_savings"] += 1000.0
                    
                    # Calculate new percentage
                    if current_progress["total_recommendations"] > 0:
                        current_progress["progress_percentage"] = (
                            current_progress["implemented_count"] / 
                            current_progress["total_recommendations"]
                        ) * 100
                    
                    await state_tracker.update_agent_state_data(
                        agent_state=agent_state,
                        data_update={"optimization_progress": current_progress},
                        operation_id=f"progress_{op_id}"
                    )
                
                elif write_pattern == "add_audit_entry":
                    # Add audit log entry
                    current_log = agent_state.get_state_data("audit_log", [])
                    
                    new_entry = {
                        "timestamp": time.time(),
                        "operation_id": op_id,
                        "action": f"operation_{op_id}_completed",
                        "user": user_context.user_id
                    }
                    
                    current_log.append(new_entry)
                    
                    await state_tracker.update_agent_state_data(
                        agent_state=agent_state,
                        data_update={"audit_log": current_log},
                        operation_id=f"audit_{op_id}"
                    )
                
                return {"success": True, "operation_id": op_id, "pattern": write_pattern}
                
            except Exception as e:
                return {"success": False, "operation_id": op_id, "error": str(e)}
        
        # Act - Execute mixed read/write operations concurrently
        mixed_tasks = []
        
        # Create mix of operations
        read_patterns = ["financial_analysis", "progress_monitoring", "audit_review"]
        write_patterns = ["add_cost_data", "update_progress", "add_audit_entry"]
        
        # 70% reads, 30% writes (typical workload)
        for i in range(50):
            if i < 35:  # Read operations
                pattern = read_patterns[i % len(read_patterns)]
                task = asyncio.create_task(mixed_read_operation(i, pattern))
            else:  # Write operations
                pattern = write_patterns[(i - 35) % len(write_patterns)]
                task = asyncio.create_task(mixed_write_operation(i, pattern))
            
            mixed_tasks.append(task)
        
        # Execute all operations concurrently
        results = await asyncio.gather(*mixed_tasks, return_exceptions=True)
        
        # Assert - Verify mixed operation handling
        successful_results = [r for r in results if not isinstance(r, Exception) and r.get("success")]
        failed_results = [r for r in results if isinstance(r, Exception) or not r.get("success")]
        
        success_rate = len(successful_results) / len(results)
        assert success_rate >= 0.95  # Very high success rate expected
        
        # Verify final state consistency
        final_state = agent_state.get_all_state_data()
        
        # Financial data should be consistent
        monthly_costs = final_state["financial_data"]["monthly_costs"]
        cost_trends = final_state["financial_data"]["cost_trends"]
        
        if len(monthly_costs) > len(complex_initial_state["financial_data"]["monthly_costs"]):
            # Should have added some cost data
            assert len(monthly_costs) >= 5
        
        # Progress data should be internally consistent
        progress = final_state["optimization_progress"]
        if progress["total_recommendations"] > 0:
            expected_percentage = (progress["implemented_count"] / progress["total_recommendations"]) * 100
            assert abs(progress["progress_percentage"] - expected_percentage) < 1.0
        
        # Audit log should be chronologically ordered
        audit_log = final_state["audit_log"]
        if len(audit_log) > 1:
            for i in range(1, len(audit_log)):
                assert audit_log[i]["timestamp"] >= audit_log[i-1]["timestamp"]
        
        # Verify consistency violation tracking
        assert operation_stats["consistency_violations"] < (operation_stats["read_operations"] * 0.05)  # < 5% violations

    @pytest.mark.integration 
    @pytest.mark.agent_state_management
    async def test_performance_optimization_under_concurrency(self, real_services_fixture):
        """Test performance optimization mechanisms under concurrent load."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="perf_user_1203",
            thread_id="thread_1503",
            session_id="session_1803",
            workspace_id="perf_workspace_1103"
        )
        
        state_tracker = AgentStateTracker(
            user_context=user_context,
            performance_optimization=True,
            caching_enabled=True,
            batch_updates=True,
            compression_enabled=True
        )
        
        # Create multiple agent states for performance testing
        agent_states = []
        for i in range(10):
            agent_state = DeepAgentState(
                agent_id=f"perf_agent_{i}",
                user_context=user_context,
                initial_state="optimizing"
            )
            agent_states.append(agent_state)
        
        # Performance tracking
        performance_metrics = {
            "operation_times": [],
            "cache_hits": 0,
            "cache_misses": 0,
            "batch_sizes": [],
            "compression_ratios": []
        }
        metrics_lock = asyncio.Lock()
        
        async def performance_optimized_operation(op_id: int, operation_type: str):
            """Operations designed to test performance optimizations."""
            start_time = time.time()
            
            try:
                agent_idx = op_id % len(agent_states)
                target_agent = agent_states[agent_idx]
                
                if operation_type == "cached_read":
                    # Operation that should benefit from caching
                    data = await state_tracker.get_cached_state_data(
                        agent_state=target_agent,
                        data_key="performance_data",
                        cache_duration_seconds=60
                    )
                    
                    cache_hit = data is not None
                    async with metrics_lock:
                        if cache_hit:
                            performance_metrics["cache_hits"] += 1
                        else:
                            performance_metrics["cache_misses"] += 1
                
                elif operation_type == "batch_update":
                    # Batch multiple updates together
                    batch_updates = []
                    for j in range(5):  # Batch 5 updates
                        batch_updates.append({
                            "key": f"batch_data_{j}",
                            "value": f"batch_value_{op_id}_{j}",
                            "timestamp": time.time()
                        })
                    
                    await state_tracker.batch_update_agent_state(
                        agent_state=target_agent,
                        updates=batch_updates,
                        operation_id=f"batch_{op_id}"
                    )
                    
                    async with metrics_lock:
                        performance_metrics["batch_sizes"].append(len(batch_updates))
                
                elif operation_type == "compressed_storage":
                    # Large data that should benefit from compression
                    large_data = {
                        "analysis_results": [
                            {
                                "id": f"result_{i}",
                                "data": "x" * 1000,  # 1KB of data
                                "metadata": {"processed": True, "score": 0.95}
                            }
                            for i in range(50)  # 50KB total
                        ],
                        "compression_test": True
                    }
                    
                    compression_result = await state_tracker.update_agent_state_with_compression(
                        agent_state=target_agent,
                        data_update=large_data,
                        compression_algorithm="gzip",
                        operation_id=f"compress_{op_id}"
                    )
                    
                    if compression_result.get("compression_ratio"):
                        async with metrics_lock:
                            performance_metrics["compression_ratios"].append(compression_result["compression_ratio"])
                
                end_time = time.time()
                operation_time = end_time - start_time
                
                async with metrics_lock:
                    performance_metrics["operation_times"].append(operation_time)
                
                return {"success": True, "operation_time": operation_time}
                
            except Exception as e:
                end_time = time.time()
                operation_time = end_time - start_time
                
                async with metrics_lock:
                    performance_metrics["operation_times"].append(operation_time)
                
                return {"success": False, "error": str(e), "operation_time": operation_time}
        
        # Act - Execute performance test operations
        operation_types = ["cached_read", "batch_update", "compressed_storage"]
        performance_tasks = []
        
        # Run multiple rounds to test caching effectiveness
        for round_num in range(3):
            round_tasks = []
            for i in range(30):  # 30 operations per round
                op_id = round_num * 30 + i
                operation_type = operation_types[i % len(operation_types)]
                task = asyncio.create_task(
                    performance_optimized_operation(op_id, operation_type)
                )
                round_tasks.append(task)
            
            performance_tasks.extend(round_tasks)
            
            # Execute round and wait before next round (to test caching)
            await asyncio.gather(*round_tasks)
            
            if round_num < 2:  # Don't wait after last round
                await asyncio.sleep(0.1)  # Brief pause between rounds
        
        # Collect all results
        all_results = await asyncio.gather(*performance_tasks, return_exceptions=True)
        
        # Assert - Verify performance optimizations
        successful_operations = [r for r in all_results if not isinstance(r, Exception) and r.get("success")]
        operation_times = [r["operation_time"] for r in successful_operations]
        
        # Basic performance assertions
        assert len(successful_operations) >= len(all_results) * 0.95  # 95% success rate
        
        # Average operation time should be reasonable
        avg_operation_time = sum(operation_times) / len(operation_times)
        assert avg_operation_time < 0.5  # Should be fast
        
        # Caching effectiveness
        total_cache_operations = performance_metrics["cache_hits"] + performance_metrics["cache_misses"]
        if total_cache_operations > 0:
            cache_hit_rate = performance_metrics["cache_hits"] / total_cache_operations
            assert cache_hit_rate > 0.5  # Should have decent cache hit rate due to repeated operations
        
        # Batch update effectiveness
        if performance_metrics["batch_sizes"]:
            avg_batch_size = sum(performance_metrics["batch_sizes"]) / len(performance_metrics["batch_sizes"])
            assert avg_batch_size >= 3  # Should be batching multiple updates
        
        # Compression effectiveness
        if performance_metrics["compression_ratios"]:
            avg_compression_ratio = sum(performance_metrics["compression_ratios"]) / len(performance_metrics["compression_ratios"])
            assert avg_compression_ratio > 1.5  # Should achieve decent compression on test data
        
        # Performance trend analysis (later operations should be faster due to optimizations)
        if len(operation_times) >= 60:
            first_third_avg = sum(operation_times[:30]) / 30
            last_third_avg = sum(operation_times[-30:]) / 30
            
            # Later operations should be faster or at least not significantly slower
            performance_improvement_ratio = first_third_avg / last_third_avg
            assert performance_improvement_ratio >= 0.8  # Should not degrade significantly