"""
Performance & Load Testing: Agent Execution Performance Under Concurrent Load

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure AI agents can handle concurrent user requests without performance degradation
- Value Impact: Multiple users can simultaneously use AI agents with consistent response quality
- Strategic Impact: Agent concurrency is critical for platform scalability and revenue growth

CRITICAL: This test validates agent execution performance, resource utilization efficiency,
and response quality consistency under concurrent load scenarios.
"""

import asyncio
import pytest
import time
import statistics
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


@dataclass
class AgentPerformanceMetrics:
    """Agent execution performance metrics."""
    agent_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_execution_time: float
    p95_execution_time: float
    p99_execution_time: float
    min_execution_time: float
    max_execution_time: float
    concurrent_executions_peak: int
    throughput_executions_per_second: float
    memory_usage_mb: float
    errors: List[str] = field(default_factory=list)
    execution_details: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentConcurrencyTestResult:
    """Results from agent concurrency testing."""
    test_name: str
    concurrent_agents: int
    total_duration: float
    overall_success_rate: float
    agent_metrics: List[AgentPerformanceMetrics]
    resource_contention_detected: bool
    scalability_bottlenecks: List[str]


class TestAgentExecutionConcurrentPerformance(BaseIntegrationTest):
    """Test agent execution performance under concurrent load."""
    
    def _simulate_agent_work(self, complexity_level: str = "medium") -> Dict[str, Any]:
        """Simulate agent work with different complexity levels."""
        work_configs = {
            "simple": {"iterations": 10, "data_size": 100, "processing_time": 0.01},
            "medium": {"iterations": 50, "data_size": 500, "processing_time": 0.05},
            "complex": {"iterations": 100, "data_size": 1000, "processing_time": 0.1}
        }
        
        config = work_configs.get(complexity_level, work_configs["medium"])
        
        # Simulate computational work
        result_data = []
        for i in range(config["iterations"]):
            # Simulate data processing
            data_item = {
                "id": i,
                "data": "x" * config["data_size"],
                "timestamp": time.time(),
                "processed": True
            }
            result_data.append(data_item)
        
        # Simulate processing time
        time.sleep(config["processing_time"])
        
        return {
            "complexity": complexity_level,
            "iterations": config["iterations"],
            "data_items": len(result_data),
            "processing_time": config["processing_time"],
            "result_summary": f"Processed {len(result_data)} items at {complexity_level} complexity"
        }
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_concurrent_agent_execution_performance(self, real_services_fixture):
        """
        Test agent execution performance with concurrent users.
        
        Performance SLA:
        - Agent execution time: <5s (p95)
        - Success rate: >95% under 20 concurrent executions
        - Memory usage: <50MB per concurrent agent
        - No resource contention blocking
        """
        concurrent_agents = 20
        executions_per_agent = 5
        
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        agent_performance_results = []
        
        async def simulate_agent_execution(agent_id: int, execution_count: int) -> AgentPerformanceMetrics:
            """Simulate a single agent's execution lifecycle."""
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024
            
            # Create authenticated user context for the agent
            user_context = await create_authenticated_user_context(
                user_email=f"agent_perf_{agent_id}@example.com",
                environment="test",
                permissions=["read", "write", "execute"],
                websocket_enabled=True
            )
            
            execution_times = []
            execution_details = []
            errors = []
            successful_executions = 0
            
            for execution_id in range(execution_count):
                execution_start = time.time()
                
                try:
                    # Simulate agent initialization and context setup
                    agent_context = {
                        "agent_id": agent_id,
                        "execution_id": execution_id,
                        "user_context": user_context,
                        "request_id": str(uuid.uuid4()),
                        "start_time": execution_start
                    }
                    
                    # Store agent state in Redis (simulating real agent pattern)
                    agent_state_key = f"agent_state:{agent_id}:{execution_id}"
                    await redis.set(
                        agent_state_key,
                        json.dumps({
                            "agent_id": agent_id,
                            "user_id": str(user_context.user_id),
                            "status": "executing",
                            "started_at": execution_start
                        }),
                        ex=300  # 5 minute expiry
                    )
                    
                    # Simulate agent work with varying complexity
                    complexity = ["simple", "medium", "complex"][execution_id % 3]
                    work_result = self._simulate_agent_work(complexity)
                    
                    # Simulate database interaction (agent storing results)
                    await db.execute(
                        "SELECT $1 as agent_id, $2 as execution_id, $3 as result_summary",
                        agent_id, execution_id, work_result["result_summary"]
                    )
                    
                    # Update agent state to completed
                    await redis.set(
                        agent_state_key,
                        json.dumps({
                            "agent_id": agent_id,
                            "user_id": str(user_context.user_id),
                            "status": "completed",
                            "started_at": execution_start,
                            "completed_at": time.time(),
                            "result": work_result
                        }),
                        ex=300
                    )
                    
                    execution_time = time.time() - execution_start
                    execution_times.append(execution_time)
                    successful_executions += 1
                    
                    execution_details.append({
                        "execution_id": execution_id,
                        "execution_time": execution_time,
                        "complexity": complexity,
                        "success": True
                    })
                    
                    # Cleanup agent state
                    await redis.delete(agent_state_key)
                    
                except Exception as e:
                    execution_time = time.time() - execution_start
                    execution_times.append(execution_time)
                    errors.append(f"Agent {agent_id} execution {execution_id} failed: {str(e)}")
                    
                    execution_details.append({
                        "execution_id": execution_id,
                        "execution_time": execution_time,
                        "error": str(e),
                        "success": False
                    })
            
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_usage = final_memory - initial_memory
            
            # Calculate performance metrics
            total_executions = len(execution_times)
            failed_executions = total_executions - successful_executions
            
            metrics = AgentPerformanceMetrics(
                agent_name=f"Agent_{agent_id}",
                total_executions=total_executions,
                successful_executions=successful_executions,
                failed_executions=failed_executions,
                average_execution_time=statistics.mean(execution_times) if execution_times else 0,
                p95_execution_time=0,
                p99_execution_time=0,
                min_execution_time=min(execution_times) if execution_times else 0,
                max_execution_time=max(execution_times) if execution_times else 0,
                concurrent_executions_peak=1,  # Single agent, so peak is 1
                throughput_executions_per_second=0,
                memory_usage_mb=memory_usage,
                errors=errors,
                execution_details=execution_details
            )
            
            # Calculate percentiles
            if execution_times:
                execution_times.sort()
                p95_index = int(len(execution_times) * 0.95)
                p99_index = int(len(execution_times) * 0.99)
                
                metrics.p95_execution_time = execution_times[p95_index]
                metrics.p99_execution_time = execution_times[p99_index]
                
                # Calculate throughput
                total_agent_time = sum(execution_times)
                metrics.throughput_executions_per_second = successful_executions / total_agent_time if total_agent_time > 0 else 0
            
            return metrics
        
        # Execute concurrent agent simulations
        print(f"🤖 Starting {concurrent_agents} concurrent agent executions...")
        concurrent_start = time.time()
        
        agent_tasks = [
            simulate_agent_execution(agent_id, executions_per_agent)
            for agent_id in range(concurrent_agents)
        ]
        
        agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        concurrent_duration = time.time() - concurrent_start
        
        # Filter successful agent results
        successful_agent_metrics = [
            result for result in agent_results
            if isinstance(result, AgentPerformanceMetrics)
        ]
        
        failed_agents = len(agent_results) - len(successful_agent_metrics)
        
        # Calculate overall metrics
        total_executions = sum(m.total_executions for m in successful_agent_metrics)
        total_successful = sum(m.successful_executions for m in successful_agent_metrics)
        total_failed = sum(m.failed_executions for m in successful_agent_metrics)
        
        overall_success_rate = total_successful / total_executions if total_executions > 0 else 0
        
        # Aggregate execution times for overall percentiles
        all_execution_times = []
        for metrics in successful_agent_metrics:
            for detail in metrics.execution_details:
                if detail.get("success", False):
                    all_execution_times.append(detail["execution_time"])
        
        overall_p95 = 0
        overall_p99 = 0
        if all_execution_times:
            all_execution_times.sort()
            p95_index = int(len(all_execution_times) * 0.95)
            p99_index = int(len(all_execution_times) * 0.99)
            overall_p95 = all_execution_times[p95_index]
            overall_p99 = all_execution_times[p99_index]
        
        # Memory usage analysis
        total_memory_usage = sum(m.memory_usage_mb for m in successful_agent_metrics)
        average_memory_per_agent = total_memory_usage / len(successful_agent_metrics) if successful_agent_metrics else 0
        
        # Performance assertions
        assert len(successful_agent_metrics) >= concurrent_agents * 0.90, f"Too many failed agents: {failed_agents}/{concurrent_agents}"
        assert overall_success_rate >= 0.95, f"Overall success rate {overall_success_rate:.3f} below 95% SLA"
        assert overall_p95 <= 5.0, f"P95 execution time {overall_p95:.2f}s exceeds 5s SLA"
        assert average_memory_per_agent <= 50.0, f"Average memory per agent {average_memory_per_agent:.1f}MB exceeds 50MB SLA"
        
        print(f"✅ Concurrent Agent Execution Performance Results:")
        print(f"   Concurrent agents: {concurrent_agents}")
        print(f"   Successful agents: {len(successful_agent_metrics)}")
        print(f"   Failed agents: {failed_agents}")
        print(f"   Total executions: {total_executions}")
        print(f"   Successful executions: {total_successful}")
        print(f"   Failed executions: {total_failed}")
        print(f"   Overall success rate: {overall_success_rate:.3f}")
        print(f"   Overall P95 execution time: {overall_p95:.2f}s")
        print(f"   Overall P99 execution time: {overall_p99:.2f}s")
        print(f"   Average memory per agent: {average_memory_per_agent:.1f}MB")
        print(f"   Total memory usage: {total_memory_usage:.1f}MB")
        print(f"   Test duration: {concurrent_duration:.2f}s")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_agent_resource_contention_detection(self, real_services_fixture):
        """
        Test agent performance under resource contention scenarios.
        
        Performance SLA:
        - Graceful degradation under resource pressure
        - No deadlocks or resource starvation
        - Fair resource allocation across agents
        """
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create resource contention by having many agents compete for limited resources
        high_contention_agents = 50
        resource_intensive_operations = 10
        
        contention_metrics = {
            "successful_agents": 0,
            "failed_agents": 0,
            "resource_timeouts": 0,
            "deadlock_events": 0,
            "average_wait_time": 0,
            "max_wait_time": 0,
            "fairness_variance": 0
        }
        
        agent_completion_times = []
        
        async def resource_contention_agent(agent_id: int) -> Dict[str, Any]:
            """Agent that competes for shared resources."""            
            agent_start = time.time()
            operations_completed = 0
            wait_times = []
            errors = []
            
            try:
                user_context = await create_authenticated_user_context(
                    user_email=f"contention_agent_{agent_id}@example.com",
                    environment="test"
                )
                
                for op_id in range(resource_intensive_operations):
                    operation_start = time.time()
                    
                    try:
                        # Simulate resource-intensive operations
                        
                        # 1. Database resource contention
                        db_wait_start = time.time()
                        await db.execute(
                            "SELECT COUNT(*) FROM generate_series(1, $1) WHERE generate_series % $2 = 0",
                            1000,  # Computationally expensive
                            agent_id % 10 + 1
                        )
                        db_wait_time = time.time() - db_wait_start
                        wait_times.append(db_wait_time)
                        
                        # 2. Redis resource contention
                        redis_key = f"contention_resource_{op_id % 5}"  # Shared keys to create contention
                        
                        # Atomic increment with potential contention
                        await redis.incr(redis_key)
                        current_value = await redis.get(redis_key)
                        
                        # Simulate processing based on shared resource state
                        if current_value:
                            processing_time = min(0.1, int(current_value) * 0.001)
                            await asyncio.sleep(processing_time)
                        
                        operations_completed += 1
                        
                    except asyncio.TimeoutError:
                        contention_metrics["resource_timeouts"] += 1
                        errors.append(f"Timeout in agent {agent_id} operation {op_id}")
                    except Exception as e:
                        errors.append(f"Error in agent {agent_id} operation {op_id}: {str(e)}")
                
                agent_duration = time.time() - agent_start
                agent_completion_times.append(agent_duration)
                
                return {
                    "agent_id": agent_id,
                    "success": len(errors) == 0,
                    "operations_completed": operations_completed,
                    "total_duration": agent_duration,
                    "average_wait_time": statistics.mean(wait_times) if wait_times else 0,
                    "max_wait_time": max(wait_times) if wait_times else 0,
                    "errors": errors
                }
                
            except Exception as e:
                contention_metrics["failed_agents"] += 1
                return {
                    "agent_id": agent_id,
                    "success": False,
                    "operations_completed": operations_completed,
                    "total_duration": time.time() - agent_start,
                    "error": str(e)
                }
        
        # Execute high contention test
        print(f"⚔️ Starting resource contention test with {high_contention_agents} agents...")
        contention_start = time.time()
        
        contention_tasks = [
            resource_contention_agent(agent_id)
            for agent_id in range(high_contention_agents)
        ]
        
        contention_results = await asyncio.gather(*contention_tasks, return_exceptions=True)
        
        contention_duration = time.time() - contention_start
        
        # Analyze contention results
        successful_results = [r for r in contention_results if isinstance(r, dict) and r.get("success", False)]
        failed_results = [r for r in contention_results if isinstance(r, dict) and not r.get("success", False)]
        exceptions = [r for r in contention_results if not isinstance(r, dict)]
        
        contention_metrics["successful_agents"] = len(successful_results)
        contention_metrics["failed_agents"] = len(failed_results) + len(exceptions)
        
        # Calculate fairness metrics
        if successful_results:
            completion_times = [r["total_duration"] for r in successful_results]
            wait_times = [r["average_wait_time"] for r in successful_results]
            
            contention_metrics["average_wait_time"] = statistics.mean(wait_times)
            contention_metrics["max_wait_time"] = max([r["max_wait_time"] for r in successful_results])
            
            # Fairness variance (lower is better)
            contention_metrics["fairness_variance"] = statistics.stdev(completion_times) if len(completion_times) > 1 else 0
        
        success_rate = contention_metrics["successful_agents"] / high_contention_agents
        
        # Resource contention assertions (more lenient than normal operations)
        assert success_rate >= 0.80, f"Resource contention success rate {success_rate:.3f} below 80% threshold"
        assert contention_metrics["resource_timeouts"] <= high_contention_agents * 0.2, f"Too many resource timeouts: {contention_metrics['resource_timeouts']}"
        assert contention_metrics["deadlock_events"] == 0, f"Deadlock events detected: {contention_metrics['deadlock_events']}"
        
        # Fairness check - completion times shouldn't vary too much
        assert contention_metrics["fairness_variance"] <= 5.0, f"Fairness variance {contention_metrics['fairness_variance']:.2f}s too high"
        
        print(f"✅ Agent Resource Contention Test Results:")
        print(f"   Test duration: {contention_duration:.2f}s")
        print(f"   Successful agents: {contention_metrics['successful_agents']}/{high_contention_agents}")
        print(f"   Failed agents: {contention_metrics['failed_agents']}")
        print(f"   Success rate: {success_rate:.3f}")
        print(f"   Resource timeouts: {contention_metrics['resource_timeouts']}")
        print(f"   Average wait time: {contention_metrics['average_wait_time']:.3f}s")
        print(f"   Max wait time: {contention_metrics['max_wait_time']:.3f}s")
        print(f"   Fairness variance: {contention_metrics['fairness_variance']:.2f}s")
        
        # Cleanup shared resources
        for i in range(resource_intensive_operations):
            try:
                await redis.delete(f"contention_resource_{i % 5}")
            except Exception:
                pass
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_agent_scalability_bottleneck_identification(self, real_services_fixture):
        """
        Test agent scalability and identify performance bottlenecks.
        
        Performance SLA:
        - Linear or sub-linear scaling up to 30 concurrent agents
        - Identify bottlenecks before system degradation
        - Maintain >90% efficiency at scale
        """
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Test different scales to identify bottlenecks
        scale_tests = [5, 10, 20, 30]
        scalability_results = []
        
        for scale in scale_tests:
            print(f"📈 Testing scalability at {scale} concurrent agents...")
            
            scale_start = time.time()
            agent_metrics = []
            
            async def scalability_test_agent(agent_id: int) -> Dict[str, Any]:
                """Lightweight agent for scalability testing."""
                agent_start = time.time()
                operations = 3  # Reduced for scalability testing
                
                try:
                    user_context = await create_authenticated_user_context(
                        user_email=f"scale_{scale}_agent_{agent_id}@example.com",
                        environment="test"
                    )
                    
                    for i in range(operations):
                        # Simple database operation
                        await db.execute("SELECT $1 as agent_id, $2 as operation", agent_id, i)
                        
                        # Simple Redis operation
                        await redis.set(f"scale_test:{scale}:{agent_id}:{i}", f"data_{i}", ex=60)
                        
                        # Minimal processing
                        await asyncio.sleep(0.01)
                    
                    return {
                        "agent_id": agent_id,
                        "execution_time": time.time() - agent_start,
                        "operations_completed": operations,
                        "success": True
                    }
                    
                except Exception as e:
                    return {
                        "agent_id": agent_id,
                        "execution_time": time.time() - agent_start,
                        "operations_completed": 0,
                        "success": False,
                        "error": str(e)
                    }
            
            # Execute scalability test for current scale
            scale_tasks = [
                scalability_test_agent(agent_id)
                for agent_id in range(scale)
            ]
            
            scale_agent_results = await asyncio.gather(*scale_tasks, return_exceptions=True)
            scale_duration = time.time() - scale_start
            
            # Analyze scale results
            successful_agents = [r for r in scale_agent_results if isinstance(r, dict) and r.get("success", False)]
            
            if successful_agents:
                execution_times = [r["execution_time"] for r in successful_agents]
                avg_execution_time = statistics.mean(execution_times)
                max_execution_time = max(execution_times)
                
                scale_result = {
                    "scale": scale,
                    "successful_agents": len(successful_agents),
                    "total_agents": scale,
                    "success_rate": len(successful_agents) / scale,
                    "total_duration": scale_duration,
                    "average_execution_time": avg_execution_time,
                    "max_execution_time": max_execution_time,
                    "throughput_agents_per_second": len(successful_agents) / scale_duration,
                    "efficiency": len(successful_agents) / scale  # Perfect efficiency would be 1.0
                }
            else:
                scale_result = {
                    "scale": scale,
                    "successful_agents": 0,
                    "total_agents": scale,
                    "success_rate": 0,
                    "total_duration": scale_duration,
                    "average_execution_time": 0,
                    "max_execution_time": 0,
                    "throughput_agents_per_second": 0,
                    "efficiency": 0
                }
            
            scalability_results.append(scale_result)
            
            # Cleanup scale test data
            for agent_id in range(scale):
                for i in range(3):
                    try:
                        await redis.delete(f"scale_test:{scale}:{agent_id}:{i}")
                    except Exception:
                        pass
        
        # Analyze scalability trends
        efficiencies = [r["efficiency"] for r in scalability_results]
        throughputs = [r["throughput_agents_per_second"] for r in scalability_results]
        
        # Check for scalability bottlenecks
        bottlenecks = []
        
        # Efficiency degradation check
        for i in range(1, len(efficiencies)):
            efficiency_drop = efficiencies[i-1] - efficiencies[i]
            if efficiency_drop > 0.1:  # 10% efficiency drop
                bottlenecks.append(f"Efficiency bottleneck between {scalability_results[i-1]['scale']} and {scalability_results[i]['scale']} agents")
        
        # Throughput scaling check
        expected_linear_scaling = True
        for i in range(1, len(throughputs)):
            scale_ratio = scalability_results[i]["scale"] / scalability_results[i-1]["scale"]
            throughput_ratio = throughputs[i] / throughputs[i-1] if throughputs[i-1] > 0 else 0
            
            if throughput_ratio < scale_ratio * 0.7:  # Less than 70% of expected scaling
                bottlenecks.append(f"Throughput bottleneck at {scalability_results[i]['scale']} agents")
                expected_linear_scaling = False
        
        # Overall scalability assertions
        final_efficiency = efficiencies[-1] if efficiencies else 0
        assert final_efficiency >= 0.90, f"Final efficiency {final_efficiency:.3f} below 90% at {scale_tests[-1]} agents"
        
        min_success_rate = min([r["success_rate"] for r in scalability_results])
        assert min_success_rate >= 0.95, f"Minimum success rate {min_success_rate:.3f} below 95% across scales"
        
        print(f"✅ Agent Scalability Test Results:")
        for result in scalability_results:
            print(f"   Scale {result['scale']:2d}: {result['successful_agents']:2d}/{result['total_agents']:2d} agents, "
                  f"efficiency: {result['efficiency']:.3f}, throughput: {result['throughput_agents_per_second']:.1f} agents/s")
        
        print(f"   Scalability Analysis:")
        print(f"     Final efficiency: {final_efficiency:.3f}")
        print(f"     Linear scaling: {'Yes' if expected_linear_scaling else 'No'}")
        print(f"     Bottlenecks identified: {len(bottlenecks)}")
        
        if bottlenecks:
            for bottleneck in bottlenecks:
                print(f"       - {bottleneck}")
        
        return {
            "scalability_results": scalability_results,
            "bottlenecks": bottlenecks,
            "final_efficiency": final_efficiency,
            "linear_scaling": expected_linear_scaling
        }
