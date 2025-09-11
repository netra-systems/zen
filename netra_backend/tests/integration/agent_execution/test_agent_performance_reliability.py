"""
Agent Performance & Reliability Integration Tests

These tests validate agent execution under load, memory management, concurrent execution isolation,
failure recovery, and performance degradation detection without external dependencies.

Business Value Focus:
- Agent execution performance under realistic load conditions
- Memory usage and resource management for production scalability
- Concurrent agent execution isolation prevents cross-user issues
- Agent recovery from failures maintains business continuity
- Performance degradation detection prevents service quality issues

CRITICAL: Tests real agent performance patterns with controlled load simulation.
"""

import asyncio
import gc
import time
import threading
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import pytest
from unittest.mock import AsyncMock

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.tests.integration.agent_execution.base_agent_execution_test import BaseAgentExecutionTest


class PerformanceTrackingAgent(BaseAgent):
    """Agent that tracks detailed performance metrics during execution."""
    
    def __init__(self, agent_name: str, base_execution_time: float = 0.5, 
                 memory_intensive: bool = False, cpu_intensive: bool = False):
        super().__init__(llm_manager=None, name=agent_name, description=f"Performance tracking {agent_name}")
        self.base_execution_time = base_execution_time
        self.memory_intensive = memory_intensive
        self.cpu_intensive = cpu_intensive
        self.execution_history = []
        self.memory_snapshots = []
        self.performance_degradation = 0.0
        
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with detailed performance tracking."""
        execution_start = time.time()
        execution_id = len(self.execution_history)
        
        # Take initial memory snapshot
        import sys
        initial_objects = len(gc.get_objects())
        
        try:
            # Simulate realistic agent workload
            await self._simulate_agent_workload(context, execution_id)
            
            # Calculate actual execution time with degradation
            actual_execution_time = self.base_execution_time + self.performance_degradation
            await asyncio.sleep(actual_execution_time)
            
            # Take final memory snapshot
            final_objects = len(gc.get_objects())
            memory_growth = final_objects - initial_objects
            
            execution_end = time.time()
            total_execution_time = execution_end - execution_start
            
            # Track performance metrics
            performance_metrics = {
                "execution_id": execution_id,
                "execution_time": total_execution_time,
                "expected_time": actual_execution_time,
                "timing_variance": abs(total_execution_time - actual_execution_time),
                "memory_growth": memory_growth,
                "objects_created": memory_growth,
                "performance_degradation": self.performance_degradation,
                "timestamp": execution_end
            }
            
            self.execution_history.append(performance_metrics)
            self.memory_snapshots.append({
                "execution_id": execution_id,
                "initial_objects": initial_objects,
                "final_objects": final_objects,
                "growth": memory_growth
            })
            
            # Simulate gradual performance degradation over time
            if len(self.execution_history) > 5:
                self.performance_degradation += 0.01  # 10ms degradation per execution after warmup
            
            # Generate realistic business result
            result = {
                "status": "completed",
                "agent_name": self.name,
                "execution_id": execution_id,
                "performance_metrics": performance_metrics,
                "business_output": {
                    "insights": [
                        f"Performance insight {i+1} from execution {execution_id}" 
                        for i in range(3)
                    ],
                    "recommendations": [
                        f"Performance recommendation {i+1} for execution {execution_id}"
                        for i in range(2)
                    ],
                    "processing_stats": {
                        "items_processed": 100 + execution_id * 10,
                        "processing_efficiency": max(0.5, 1.0 - self.performance_degradation),
                        "resource_utilization": min(1.0, 0.7 + execution_id * 0.05)
                    }
                },
                "resource_usage": {
                    "memory_growth_objects": memory_growth,
                    "execution_time_sec": total_execution_time,
                    "cpu_intensive": self.cpu_intensive,
                    "memory_intensive": self.memory_intensive
                }
            }
            
            return result
            
        except Exception as e:
            # Track failed executions
            failure_metrics = {
                "execution_id": execution_id,
                "failure_reason": str(e),
                "execution_time": time.time() - execution_start,
                "timestamp": time.time()
            }
            self.execution_history.append(failure_metrics)
            raise
    
    async def _simulate_agent_workload(self, context: UserExecutionContext, execution_id: int):
        """Simulate realistic agent computational workload."""
        
        # Memory intensive workload
        if self.memory_intensive:
            # Create temporary data structures
            temp_data = []
            for i in range(1000 + execution_id * 100):
                temp_data.append({
                    "id": i,
                    "data": f"memory_intensive_data_{i}",
                    "context": context.user_id,
                    "execution": execution_id
                })
            
            # Process data (simulate business logic)
            processed_count = 0
            for item in temp_data:
                if item["id"] % 10 == 0:
                    processed_count += 1
            
            # Cleanup (simulate garbage collection opportunity)
            del temp_data
        
        # CPU intensive workload  
        if self.cpu_intensive:
            # Simulate computational work
            computation_result = 0
            iterations = 10000 + execution_id * 1000
            
            for i in range(iterations):
                computation_result += i ** 0.5 + len(context.user_id)
                
                # Yield control occasionally for better concurrency
                if i % 1000 == 0:
                    await asyncio.sleep(0.001)
            
            # Store result to prevent optimization
            self.last_computation = computation_result
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        if not self.execution_history:
            return {"no_executions": True}
        
        execution_times = [e.get("execution_time", 0) for e in self.execution_history if "execution_time" in e]
        memory_growths = [e.get("memory_growth", 0) for e in self.execution_history if "memory_growth" in e]
        
        return {
            "total_executions": len(self.execution_history),
            "successful_executions": sum(1 for e in self.execution_history if e.get("status") != "failed"),
            "average_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
            "min_execution_time": min(execution_times) if execution_times else 0,
            "max_execution_time": max(execution_times) if execution_times else 0,
            "total_memory_growth": sum(memory_growths),
            "average_memory_growth": sum(memory_growths) / len(memory_growths) if memory_growths else 0,
            "current_performance_degradation": self.performance_degradation,
            "memory_intensive": self.memory_intensive,
            "cpu_intensive": self.cpu_intensive
        }


class TestAgentPerformanceReliability(BaseAgentExecutionTest):
    """Test agent performance and reliability under various load conditions."""

    @pytest.mark.asyncio
    async def test_agent_execution_under_load(self):
        """Test agent execution performance under sustained load conditions.
        
        Validates:
        - Agent performance remains acceptable under load
        - Response times stay within business requirements
        - Throughput meets minimum performance standards
        - System handles sustained execution load
        """
        # Create load test scenario
        context = self.create_user_execution_context(
            user_request="Execute sustained load test with performance monitoring",
            additional_metadata={
                "load_test": True,
                "performance_requirements": {
                    "max_response_time": 2.0,
                    "min_throughput": 5.0,  # executions per second
                    "max_memory_growth": 1000  # objects
                },
                "load_parameters": {
                    "total_executions": 20,
                    "concurrency_level": 4
                }
            }
        )
        
        # Create performance tracking agent
        load_agent = PerformanceTrackingAgent(
            agent_name="load_test_agent",
            base_execution_time=0.3,
            memory_intensive=True,
            cpu_intensive=False
        )
        
        # Execute sustained load test
        load_start_time = time.time()
        load_results = []
        
        # Run multiple execution cycles
        total_executions = context.metadata["load_parameters"]["total_executions"]
        concurrency_level = context.metadata["load_parameters"]["concurrency_level"]
        
        # Execute in batches for controlled concurrency
        for batch_start in range(0, total_executions, concurrency_level):
            batch_end = min(batch_start + concurrency_level, total_executions)
            batch_size = batch_end - batch_start
            
            # Create concurrent tasks for this batch
            batch_tasks = []
            for i in range(batch_size):
                # Create unique context for each execution to simulate different users
                exec_context = context.create_child_context(
                    operation_name=f"load_execution_{batch_start + i}",
                    additional_agent_context={"execution_index": batch_start + i}
                )
                
                task = asyncio.create_task(load_agent.execute(exec_context, stream_updates=True))
                batch_tasks.append(task)
            
            # Wait for batch completion
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process batch results
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    load_results.append({
                        "status": "failed",
                        "execution_index": batch_start + i,
                        "error": str(result)
                    })
                else:
                    load_results.append(result)
            
            # Small delay between batches to prevent overwhelming
            await asyncio.sleep(0.1)
        
        load_end_time = time.time()
        total_load_time = load_end_time - load_start_time
        
        # Validate load test results
        successful_results = [r for r in load_results if r.get("status") == "completed"]
        failed_results = [r for r in load_results if r.get("status") == "failed"]
        
        success_rate = len(successful_results) / len(load_results)
        assert success_rate >= 0.95, f"Load test success rate {success_rate:.2%} should be >= 95%"
        
        # Validate performance requirements
        performance_reqs = context.metadata["performance_requirements"]
        
        # Check response times
        response_times = [r["performance_metrics"]["execution_time"] for r in successful_results]
        max_response_time = max(response_times) if response_times else 0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        assert max_response_time <= performance_reqs["max_response_time"], \
            f"Max response time {max_response_time:.3f}s exceeds requirement {performance_reqs['max_response_time']}s"
        
        # Check throughput
        actual_throughput = len(successful_results) / total_load_time
        assert actual_throughput >= performance_reqs["min_throughput"], \
            f"Throughput {actual_throughput:.2f} exec/sec below requirement {performance_reqs['min_throughput']} exec/sec"
        
        # Check memory growth
        memory_growths = [r["performance_metrics"]["memory_growth"] for r in successful_results]
        max_memory_growth = max(memory_growths) if memory_growths else 0
        avg_memory_growth = sum(memory_growths) / len(memory_growths) if memory_growths else 0
        
        assert avg_memory_growth <= performance_reqs["max_memory_growth"], \
            f"Average memory growth {avg_memory_growth:.0f} objects exceeds requirement {performance_reqs['max_memory_growth']}"
        
        # Validate business output consistency under load
        insights_per_execution = [len(r["business_output"]["insights"]) for r in successful_results]
        assert all(count >= 3 for count in insights_per_execution), "All executions should provide minimum business insights"
        
        recommendations_per_execution = [len(r["business_output"]["recommendations"]) for r in successful_results]
        assert all(count >= 2 for count in recommendations_per_execution), "All executions should provide minimum recommendations"
        
        # Get agent performance summary
        performance_summary = load_agent.get_performance_summary()
        
        # Validate performance degradation is controlled
        assert performance_summary["current_performance_degradation"] < 0.5, \
            "Performance degradation should be controlled under load"
        
        # Log performance results
        self.logger.info(f"Load test completed: {len(successful_results)}/{len(load_results)} successful")
        self.logger.info(f"Throughput: {actual_throughput:.2f} exec/sec, Avg response: {avg_response_time:.3f}s")

    @pytest.mark.asyncio
    async def test_memory_usage_and_resource_management(self):
        """Test agent memory usage patterns and resource management.
        
        Validates:
        - Memory usage grows within acceptable bounds
        - Resources are properly cleaned up after execution
        - Memory leaks don't accumulate over multiple executions
        - Garbage collection opportunities are utilized
        """
        context = self.create_user_execution_context(
            user_request="Test memory usage and resource management patterns",
            additional_metadata={
                "memory_test": True,
                "resource_monitoring": True,
                "gc_testing": True,
                "memory_thresholds": {
                    "max_growth_per_execution": 500,  # objects
                    "max_cumulative_growth": 2000,
                    "gc_effectiveness_threshold": 0.7
                }
            }
        )
        
        # Create memory-intensive agent
        memory_agent = PerformanceTrackingAgent(
            agent_name="memory_test_agent",
            base_execution_time=0.2,
            memory_intensive=True,
            cpu_intensive=False
        )
        
        # Baseline memory measurement
        gc.collect()  # Force garbage collection for baseline
        baseline_objects = len(gc.get_objects())
        
        # Execute multiple cycles with memory monitoring
        execution_cycles = 10
        memory_measurements = []
        
        for cycle in range(execution_cycles):
            # Pre-execution memory snapshot
            pre_execution_objects = len(gc.get_objects())
            
            # Execute agent
            cycle_context = context.create_child_context(
                operation_name=f"memory_cycle_{cycle}",
                additional_agent_context={"cycle": cycle}
            )
            
            result = await memory_agent.execute(cycle_context, stream_updates=True)
            
            # Post-execution memory snapshot
            post_execution_objects = len(gc.get_objects())
            
            # Force garbage collection and measure cleanup effectiveness
            gc.collect()
            post_gc_objects = len(gc.get_objects())
            
            # Calculate memory metrics
            execution_growth = post_execution_objects - pre_execution_objects
            gc_cleaned = post_execution_objects - post_gc_objects
            gc_effectiveness = gc_cleaned / max(execution_growth, 1)
            
            memory_measurement = {
                "cycle": cycle,
                "pre_execution_objects": pre_execution_objects,
                "post_execution_objects": post_execution_objects,
                "post_gc_objects": post_gc_objects,
                "execution_growth": execution_growth,
                "gc_cleaned": gc_cleaned,
                "gc_effectiveness": gc_effectiveness,
                "cumulative_growth": post_gc_objects - baseline_objects,
                "business_value_maintained": len(result["business_output"]["insights"]) >= 3
            }
            
            memory_measurements.append(memory_measurement)
            
            # Validate business output wasn't compromised by memory management
            assert result["status"] == "completed", f"Execution {cycle} should complete despite memory operations"
            assert memory_measurement["business_value_maintained"], "Business value should be maintained"
        
        # Validate memory usage patterns
        memory_thresholds = context.metadata["memory_thresholds"]
        
        # Check per-execution memory growth
        execution_growths = [m["execution_growth"] for m in memory_measurements]
        max_execution_growth = max(execution_growths)
        avg_execution_growth = sum(execution_growths) / len(execution_growths)
        
        assert max_execution_growth <= memory_thresholds["max_growth_per_execution"], \
            f"Max execution memory growth {max_execution_growth} exceeds threshold {memory_thresholds['max_growth_per_execution']}"
        
        # Check cumulative memory growth
        final_measurement = memory_measurements[-1]
        cumulative_growth = final_measurement["cumulative_growth"]
        
        assert cumulative_growth <= memory_thresholds["max_cumulative_growth"], \
            f"Cumulative memory growth {cumulative_growth} exceeds threshold {memory_thresholds['max_cumulative_growth']}"
        
        # Check garbage collection effectiveness
        gc_effectiveness_values = [m["gc_effectiveness"] for m in memory_measurements if m["execution_growth"] > 10]
        if gc_effectiveness_values:  # Only check if we had significant growth
            avg_gc_effectiveness = sum(gc_effectiveness_values) / len(gc_effectiveness_values)
            assert avg_gc_effectiveness >= memory_thresholds["gc_effectiveness_threshold"], \
                f"GC effectiveness {avg_gc_effectiveness:.2f} below threshold {memory_thresholds['gc_effectiveness_threshold']}"
        
        # Validate memory growth trend (should not continuously increase)
        if len(memory_measurements) >= 5:
            recent_growths = [m["cumulative_growth"] for m in memory_measurements[-5:]]
            growth_trend = recent_growths[-1] - recent_growths[0]
            max_acceptable_trend = memory_thresholds["max_growth_per_execution"] * 5
            
            assert growth_trend <= max_acceptable_trend, \
                f"Memory growth trend {growth_trend} indicates potential leak"
        
        # Get agent performance summary
        performance_summary = memory_agent.get_performance_summary()
        
        # Validate resource management metrics
        assert performance_summary["total_memory_growth"] >= 0, "Memory tracking should work correctly"
        assert performance_summary["successful_executions"] == execution_cycles, "All executions should succeed"
        
        # Log memory analysis results
        self.logger.info(f"Memory test completed: {execution_cycles} cycles")
        self.logger.info(f"Avg execution growth: {avg_execution_growth:.0f} objects")
        self.logger.info(f"Cumulative growth: {cumulative_growth} objects")
        if gc_effectiveness_values:
            self.logger.info(f"Avg GC effectiveness: {avg_gc_effectiveness:.2%}")

    @pytest.mark.asyncio
    async def test_concurrent_agent_execution_isolation(self):
        """Test that concurrent agent executions maintain proper isolation.
        
        Validates:
        - Concurrent executions don't interfere with each other
        - Performance isolation between different user contexts
        - Resource contention handling
        - State isolation and data integrity
        """
        # Create multiple isolated contexts for concurrent testing
        concurrent_contexts = []
        num_concurrent_agents = 6
        
        for i in range(num_concurrent_agents):
            context = self.create_user_execution_context(
                user_request=f"Concurrent execution test for agent {i}",
                additional_metadata={
                    "concurrent_test": True,
                    "agent_index": i,
                    "isolation_validation": True,
                    "expected_business_outputs": 3,
                    "performance_tier": "high" if i < 2 else "normal"
                }
            )
            concurrent_contexts.append(context)
        
        # Create agents with different performance characteristics
        concurrent_agents = []
        for i, context in enumerate(concurrent_contexts):
            # Vary agent characteristics to test isolation
            memory_intensive = i % 2 == 0
            cpu_intensive = i % 3 == 0
            base_time = 0.3 + (i * 0.1)  # Different execution times
            
            agent = PerformanceTrackingAgent(
                agent_name=f"concurrent_agent_{i}",
                base_execution_time=base_time,
                memory_intensive=memory_intensive,
                cpu_intensive=cpu_intensive
            )
            concurrent_agents.append(agent)
        
        # Execute all agents concurrently
        concurrent_start_time = time.time()
        isolation_metrics = []
        
        # Create tasks for concurrent execution
        concurrent_tasks = []
        for i, (agent, context) in enumerate(zip(concurrent_agents, concurrent_contexts)):
            task = asyncio.create_task(
                agent.execute(context, stream_updates=True),
                name=f"concurrent_agent_{i}"
            )
            concurrent_tasks.append((i, task, agent, context))
        
        # Wait for all concurrent executions to complete
        concurrent_results = []
        for i, task, agent, context in concurrent_tasks:
            try:
                result = await task
                concurrent_results.append((i, result, agent, context, None))
            except Exception as e:
                concurrent_results.append((i, None, agent, context, e))
        
        concurrent_end_time = time.time()
        total_concurrent_time = concurrent_end_time - concurrent_start_time
        
        # Validate concurrent execution isolation
        successful_executions = [r for r in concurrent_results if r[1] is not None and r[4] is None]
        failed_executions = [r for r in concurrent_results if r[1] is None or r[4] is not None]
        
        success_rate = len(successful_executions) / len(concurrent_results)
        assert success_rate >= 0.9, f"Concurrent execution success rate {success_rate:.2%} should be >= 90%"
        
        # Validate execution isolation
        for i, result, agent, context, error in successful_executions:
            # Each agent should have its own performance profile
            agent_summary = agent.get_performance_summary()
            assert agent_summary["total_executions"] == 1, f"Agent {i} should have executed exactly once"
            
            # Validate context isolation
            assert result["agent_name"] == f"concurrent_agent_{i}", "Agent should maintain its identity"
            assert result["business_output"]["insights"][0].endswith(str(0)), "First execution should be index 0"
            
            # Validate performance isolation
            execution_time = result["performance_metrics"]["execution_time"]
            expected_time = agent.base_execution_time
            timing_variance = abs(execution_time - expected_time)
            
            # Allow for some variance due to concurrency overhead
            max_acceptable_variance = expected_time * 0.5  # 50% variance acceptable under concurrency
            assert timing_variance <= max_acceptable_variance, \
                f"Agent {i} timing variance {timing_variance:.3f}s too high, suggests isolation failure"
        
        # Validate no cross-contamination in business outputs
        agent_insights = {}
        for i, result, agent, context, error in successful_executions:
            insights = result["business_output"]["insights"]
            agent_insights[i] = insights
            
            # Each agent should have unique insights
            for insight in insights:
                assert f"execution {0}" in insight, f"Agent {i} insights should reference its own execution"
        
        # Check for cross-contamination between agents
        all_insights = [insight for insights_list in agent_insights.values() for insight in insights_list]
        unique_insights = set(all_insights)
        
        # Should have unique insights per agent (no duplication indicating shared state)
        expected_unique_count = len(successful_executions) * 3  # 3 insights per agent
        actual_unique_count = len(unique_insights)
        
        contamination_rate = 1 - (actual_unique_count / len(all_insights))
        assert contamination_rate <= 0.1, f"Cross-contamination rate {contamination_rate:.2%} too high"
        
        # Validate concurrent performance efficiency
        # Estimate sequential execution time
        sequential_estimate = sum(agent.base_execution_time for _, _, agent, _, _ in successful_executions)
        parallel_efficiency = sequential_estimate / total_concurrent_time
        
        assert parallel_efficiency >= 2.0, \
            f"Concurrent execution efficiency {parallel_efficiency:.2f}x should demonstrate parallelism benefits"
        
        # Validate resource isolation (memory)
        memory_usage_by_agent = {}
        for i, result, agent, context, error in successful_executions:
            memory_growth = result["performance_metrics"]["memory_growth"]
            memory_usage_by_agent[i] = memory_growth
        
        # Memory usage should vary based on agent characteristics
        memory_intensive_agents = [i for i, (_, _, agent, _, _) in enumerate(successful_executions) if agent.memory_intensive]
        normal_agents = [i for i, (_, _, agent, _, _) in enumerate(successful_executions) if not agent.memory_intensive]
        
        if memory_intensive_agents and normal_agents:
            avg_memory_intensive = sum(memory_usage_by_agent.get(i, 0) for i in memory_intensive_agents) / len(memory_intensive_agents)
            avg_normal = sum(memory_usage_by_agent.get(i, 0) for i in normal_agents) / len(normal_agents)
            
            # Memory-intensive agents should use more memory, confirming isolation
            assert avg_memory_intensive > avg_normal, "Memory isolation should preserve agent characteristics"

    @pytest.mark.asyncio
    async def test_agent_recovery_from_failures(self):
        """Test agent recovery mechanisms from various failure scenarios.
        
        Validates:
        - Agents recover gracefully from transient failures
        - Business continuity is maintained during recovery
        - Recovery mechanisms don't degrade performance significantly
        - State consistency is preserved during recovery
        """
        context = self.create_user_execution_context(
            user_request="Test agent recovery from various failure scenarios",
            additional_metadata={
                "recovery_test": True,
                "failure_scenarios": [
                    "transient_network_error",
                    "temporary_resource_exhaustion", 
                    "intermittent_processing_failure"
                ],
                "recovery_requirements": {
                    "max_recovery_attempts": 3,
                    "max_recovery_time": 5.0,
                    "business_continuity_required": True
                }
            }
        )
        
        # Create failure-prone agent for recovery testing
        recovery_agent = PerformanceTrackingAgent(
            agent_name="recovery_test_agent",
            base_execution_time=0.4,
            memory_intensive=False,
            cpu_intensive=False
        )
        
        # Track recovery statistics
        recovery_stats = {
            "total_attempts": 0,
            "failures": [],
            "recoveries": [],
            "final_success": False,
            "business_value_maintained": False
        }
        
        # Override execute method to simulate failures and recovery
        original_execute = recovery_agent.execute
        failure_scenarios = context.metadata["failure_scenarios"]
        current_scenario_index = 0
        
        async def failing_execute(exec_context: UserExecutionContext, stream_updates: bool = False):
            nonlocal current_scenario_index
            recovery_stats["total_attempts"] += 1
            
            # Simulate failures for first few attempts
            if recovery_stats["total_attempts"] <= len(failure_scenarios):
                scenario = failure_scenarios[current_scenario_index]
                current_scenario_index = min(current_scenario_index + 1, len(failure_scenarios) - 1)
                
                failure_info = {
                    "attempt": recovery_stats["total_attempts"],
                    "scenario": scenario,
                    "timestamp": time.time()
                }
                recovery_stats["failures"].append(failure_info)
                
                # Different failure types
                if scenario == "transient_network_error":
                    raise ConnectionError("Simulated network timeout during agent execution")
                elif scenario == "temporary_resource_exhaustion":
                    raise RuntimeError("Simulated temporary resource exhaustion")
                elif scenario == "intermittent_processing_failure":
                    raise ValueError("Simulated intermittent processing failure")
            
            # Success after failures
            result = await original_execute(exec_context, stream_updates)
            recovery_stats["final_success"] = True
            recovery_stats["business_value_maintained"] = len(result["business_output"]["insights"]) >= 3
            
            recovery_info = {
                "success_attempt": recovery_stats["total_attempts"],
                "timestamp": time.time(),
                "business_output_quality": len(result["business_output"]["insights"])
            }
            recovery_stats["recoveries"].append(recovery_info)
            
            return result
        
        recovery_agent.execute = failing_execute
        
        # Execute with retry logic
        max_attempts = context.metadata["recovery_requirements"]["max_recovery_attempts"]
        max_recovery_time = context.metadata["recovery_requirements"]["max_recovery_time"]
        
        recovery_start_time = time.time()
        final_result = None
        recovery_successful = False
        
        for attempt in range(max_attempts):
            try:
                attempt_context = context.create_child_context(
                    operation_name=f"recovery_attempt_{attempt + 1}",
                    additional_agent_context={"recovery_attempt": attempt + 1}
                )
                
                final_result = await recovery_agent.execute(attempt_context, stream_updates=True)
                recovery_successful = True
                break
                
            except Exception as e:
                # Log failure and continue to next attempt
                self.logger.info(f"Recovery attempt {attempt + 1} failed: {e}")
                
                if attempt < max_attempts - 1:
                    # Exponential backoff between retries
                    backoff_delay = min(0.5 * (2 ** attempt), 2.0)
                    await asyncio.sleep(backoff_delay)
                else:
                    # Final attempt failed
                    self.logger.error(f"All {max_attempts} recovery attempts failed")
        
        recovery_end_time = time.time()
        total_recovery_time = recovery_end_time - recovery_start_time
        
        # Validate recovery mechanisms
        recovery_requirements = context.metadata["recovery_requirements"]
        
        assert recovery_successful, "Agent should eventually recover from failures"
        assert final_result is not None, "Recovery should produce valid business result"
        assert recovery_stats["final_success"], "Recovery statistics should confirm success"
        
        # Validate recovery timing
        assert total_recovery_time <= recovery_requirements["max_recovery_time"], \
            f"Recovery time {total_recovery_time:.3f}s exceeds maximum {recovery_requirements['max_recovery_time']}s"
        
        # Validate business continuity
        if recovery_requirements["business_continuity_required"]:
            assert recovery_stats["business_value_maintained"], "Business value should be maintained after recovery"
            
            business_output = final_result["business_output"]
            assert len(business_output["insights"]) >= 3, "Should maintain minimum business insights"
            assert len(business_output["recommendations"]) >= 2, "Should maintain minimum business recommendations"
        
        # Validate recovery attempt efficiency
        total_failures = len(recovery_stats["failures"])
        successful_recoveries = len(recovery_stats["recoveries"])
        
        assert total_failures >= 1, "Should have experienced simulated failures"
        assert successful_recoveries >= 1, "Should have achieved successful recovery"
        assert recovery_stats["total_attempts"] <= max_attempts, "Should not exceed max attempts"
        
        # Validate failure scenario coverage
        failure_scenarios_tested = set(f["scenario"] for f in recovery_stats["failures"])
        expected_scenarios = set(failure_scenarios[:total_failures])
        
        assert failure_scenarios_tested == expected_scenarios, "Should test expected failure scenarios"
        
        # Validate performance impact of recovery
        if final_result and "performance_metrics" in final_result:
            recovery_execution_time = final_result["performance_metrics"]["execution_time"]
            baseline_time = recovery_agent.base_execution_time
            
            # Recovery should not cause excessive performance degradation
            performance_impact = (recovery_execution_time - baseline_time) / baseline_time
            max_acceptable_impact = 0.5  # 50% degradation acceptable for recovery scenario
            
            assert performance_impact <= max_acceptable_impact, \
                f"Recovery performance impact {performance_impact:.2%} too high"
        
        # Log recovery analysis
        self.logger.info(f"Recovery test completed: {total_failures} failures, {successful_recoveries} recoveries")
        self.logger.info(f"Total recovery time: {total_recovery_time:.3f}s")

    @pytest.mark.asyncio
    async def test_performance_degradation_detection(self):
        """Test detection of performance degradation over time.
        
        Validates:
        - Performance degradation is detected accurately
        - Degradation patterns are identified before critical impact
        - Business impact correlation with performance metrics
        - Early warning system effectiveness
        """
        context = self.create_user_execution_context(
            user_request="Test performance degradation detection and monitoring",
            additional_metadata={
                "degradation_test": True,
                "monitoring_enabled": True,
                "degradation_thresholds": {
                    "warning_threshold": 0.1,  # 10% degradation
                    "critical_threshold": 0.3,  # 30% degradation
                    "business_impact_threshold": 0.2  # 20% business output reduction
                },
                "baseline_executions": 5,
                "degradation_executions": 15
            }
        )
        
        # Create agent that will experience performance degradation
        degrading_agent = PerformanceTrackingAgent(
            agent_name="degradation_test_agent",
            base_execution_time=0.3,
            memory_intensive=True,
            cpu_intensive=True
        )
        
        # Track performance over time
        performance_timeline = []
        business_impact_timeline = []
        degradation_alerts = []
        
        # Baseline executions (no degradation)
        baseline_executions = context.metadata["baseline_executions"]
        degradation_executions = context.metadata["degradation_executions"]
        total_executions = baseline_executions + degradation_executions
        
        degradation_thresholds = context.metadata["degradation_thresholds"]
        
        for execution_index in range(total_executions):
            # Execute agent
            exec_context = context.create_child_context(
                operation_name=f"degradation_execution_{execution_index}",
                additional_agent_context={
                    "execution_index": execution_index,
                    "baseline_phase": execution_index < baseline_executions
                }
            )
            
            execution_start = time.time()
            result = await degrading_agent.execute(exec_context, stream_updates=True)
            execution_end = time.time()
            
            # Calculate performance metrics
            actual_execution_time = execution_end - execution_start
            performance_metrics = result["performance_metrics"]
            
            # Calculate business impact metrics
            business_output = result["business_output"]
            business_score = (
                len(business_output["insights"]) * 1.0 +
                len(business_output["recommendations"]) * 1.5 +
                business_output["processing_stats"]["processing_efficiency"] * 2.0
            )
            
            timeline_entry = {
                "execution_index": execution_index,
                "execution_time": actual_execution_time,
                "expected_time": degrading_agent.base_execution_time,
                "performance_degradation": performance_metrics["performance_degradation"],
                "memory_growth": performance_metrics["memory_growth"],
                "business_score": business_score,
                "timestamp": execution_end,
                "baseline_phase": execution_index < baseline_executions
            }
            
            performance_timeline.append(timeline_entry)
            
            # Performance degradation detection
            if execution_index >= baseline_executions:  # Only monitor after baseline
                baseline_avg_time = sum(e["execution_time"] for e in performance_timeline[:baseline_executions]) / baseline_executions
                current_degradation = (actual_execution_time - baseline_avg_time) / baseline_avg_time
                
                # Check degradation thresholds
                if current_degradation >= degradation_thresholds["critical_threshold"]:
                    alert = {
                        "level": "critical",
                        "execution_index": execution_index,
                        "degradation": current_degradation,
                        "threshold": degradation_thresholds["critical_threshold"],
                        "timestamp": execution_end
                    }
                    degradation_alerts.append(alert)
                elif current_degradation >= degradation_thresholds["warning_threshold"]:
                    alert = {
                        "level": "warning", 
                        "execution_index": execution_index,
                        "degradation": current_degradation,
                        "threshold": degradation_thresholds["warning_threshold"],
                        "timestamp": execution_end
                    }
                    degradation_alerts.append(alert)
                    
                # Business impact detection
                if execution_index >= baseline_executions + 2:  # Need some data for trend
                    recent_business_scores = [e["business_score"] for e in performance_timeline[-3:]]
                    baseline_business_scores = [e["business_score"] for e in performance_timeline[:baseline_executions]]
                    
                    baseline_avg_business = sum(baseline_business_scores) / len(baseline_business_scores)
                    recent_avg_business = sum(recent_business_scores) / len(recent_business_scores)
                    
                    business_impact = (baseline_avg_business - recent_avg_business) / baseline_avg_business
                    
                    if business_impact >= degradation_thresholds["business_impact_threshold"]:
                        business_impact_timeline.append({
                            "execution_index": execution_index,
                            "business_impact": business_impact,
                            "baseline_score": baseline_avg_business,
                            "current_score": recent_avg_business,
                            "timestamp": execution_end
                        })
            
            # Small delay between executions
            await asyncio.sleep(0.05)
        
        # Validate degradation detection
        assert len(performance_timeline) == total_executions, "Should track all executions"
        
        # Validate baseline vs degraded performance
        baseline_entries = [e for e in performance_timeline if e["baseline_phase"]]
        degraded_entries = [e for e in performance_timeline if not e["baseline_phase"]]
        
        baseline_avg_time = sum(e["execution_time"] for e in baseline_entries) / len(baseline_entries)
        degraded_avg_time = sum(e["execution_time"] for e in degraded_entries) / len(degraded_entries)
        
        actual_degradation = (degraded_avg_time - baseline_avg_time) / baseline_avg_time
        
        # Should detect significant performance degradation
        assert actual_degradation > degradation_thresholds["warning_threshold"], \
            f"Actual degradation {actual_degradation:.2%} should exceed warning threshold"
        
        # Should generate appropriate alerts
        warning_alerts = [a for a in degradation_alerts if a["level"] == "warning"]
        critical_alerts = [a for a in degradation_alerts if a["level"] == "critical"]
        
        assert len(warning_alerts) > 0, "Should generate warning alerts for degradation"
        
        if actual_degradation > degradation_thresholds["critical_threshold"]:
            assert len(critical_alerts) > 0, "Should generate critical alerts for severe degradation"
        
        # Validate business impact detection
        if len(business_impact_timeline) > 0:
            significant_business_impact = any(
                bi["business_impact"] >= degradation_thresholds["business_impact_threshold"]
                for bi in business_impact_timeline
            )
            assert significant_business_impact, "Should detect business impact from performance degradation"
        
        # Validate early detection (alerts should come before severe degradation)
        if critical_alerts:
            first_critical_alert = min(a["execution_index"] for a in critical_alerts)
            last_execution_index = max(e["execution_index"] for e in performance_timeline)
            
            early_detection_ratio = first_critical_alert / last_execution_index
            assert early_detection_ratio < 0.8, "Should detect critical degradation before end of execution timeline"
        
        # Validate monitoring effectiveness
        detection_accuracy = len(degradation_alerts) / max(len(degraded_entries), 1)
        assert detection_accuracy > 0.2, "Degradation detection should be reasonably sensitive"
        
        # Get final agent performance summary
        final_summary = degrading_agent.get_performance_summary()
        
        assert final_summary["total_executions"] == total_executions, "Should track all executions"
        assert final_summary["current_performance_degradation"] > 0, "Should show accumulated degradation"
        
        # Log degradation analysis results
        self.logger.info(f"Degradation test completed: {actual_degradation:.2%} degradation detected")
        self.logger.info(f"Generated {len(warning_alerts)} warnings, {len(critical_alerts)} critical alerts")
        if business_impact_timeline:
            max_business_impact = max(bi["business_impact"] for bi in business_impact_timeline)
            self.logger.info(f"Maximum business impact: {max_business_impact:.2%}")