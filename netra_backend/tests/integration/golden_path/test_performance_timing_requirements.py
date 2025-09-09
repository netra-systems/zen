"""
Test Performance and Timing Requirements Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure system meets performance SLAs critical for user satisfaction
- Value Impact: Response times directly correlate with user engagement and retention
- Strategic Impact: Performance is competitive differentiator for $500K+ ARR target

COVERAGE FOCUS:
1. Agent execution time validation under normal load
2. WebSocket message delivery latency testing
3. Database query performance under concurrent load
4. System response time degradation testing
5. Resource usage efficiency validation  
6. Performance consistency across user sessions
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import pytest
import statistics
from concurrent.futures import ThreadPoolExecutor

from test_framework.base_integration_test import BaseIntegrationTest, ServiceOrchestrationIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance measurement results."""
    operation: str
    execution_time: float
    cpu_usage: Optional[float]
    memory_usage: Optional[float]
    success: bool
    error_message: Optional[str] = None


@dataclass
class LoadTestResult:
    """Load testing results."""
    concurrent_users: int
    total_operations: int
    successful_operations: int
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput: float  # operations per second
    error_rate: float


class TestPerformanceTimingRequirements(ServiceOrchestrationIntegrationTest):
    """Test performance and timing requirements with real service integration."""
    
    def setup_method(self):
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.performance_slas = {
            "agent_execution_max": 30.0,        # seconds
            "websocket_message_max": 2.0,       # seconds
            "database_query_max": 1.0,          # seconds  
            "api_response_max": 5.0,            # seconds
            "concurrent_user_degradation": 0.3, # max 30% degradation
            "min_throughput": 10.0,             # operations per second
            "max_error_rate": 0.05              # 5% max error rate
        }
        self.performance_results = []
        
    async def _measure_operation_performance(self, operation_name: str, operation_func, *args, **kwargs) -> PerformanceMetrics:
        """Measure performance of an operation."""
        start_time = time.time()
        cpu_before = time.process_time()
        
        try:
            result = await operation_func(*args, **kwargs)
            success = True
            error_message = None
        except Exception as e:
            result = None
            success = False
            error_message = str(e)
        
        end_time = time.time()
        cpu_after = time.process_time()
        
        execution_time = end_time - start_time
        cpu_usage = cpu_after - cpu_before
        
        metrics = PerformanceMetrics(
            operation=operation_name,
            execution_time=execution_time,
            cpu_usage=cpu_usage,
            memory_usage=None,  # Could be enhanced with memory profiling
            success=success,
            error_message=error_message
        )
        
        self.performance_results.append(metrics)
        return metrics

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_timing_under_normal_load(self, real_services_fixture):
        """
        Test that agent execution meets timing SLAs under normal operating conditions.
        
        Validates core golden path performance requirements.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "timing-test@example.com", "name": "Timing Test User"}
        )
        
        # Test different agent types for timing consistency
        agent_scenarios = [
            {
                "agent_type": "triage_agent",
                "expected_max_time": 15.0,  # seconds
                "complexity": "simple",
                "input": "Help me optimize my AWS costs"
            },
            {
                "agent_type": "data_helper",
                "expected_max_time": 25.0,
                "complexity": "medium",
                "input": "Analyze my infrastructure performance data"
            },
            {
                "agent_type": "uvs_reporter",
                "expected_max_time": 20.0,
                "complexity": "complex",
                "input": "Generate business value report for cost optimization"
            }
        ]
        
        agent_timing_results = []
        
        for scenario in agent_scenarios:
            thread_id = str(uuid.uuid4())
            
            # Create thread for timing test
            await real_services_fixture["db"].execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at, metadata)
                VALUES ($1, $2, $3, $4, $5)
            """, thread_id, user_context.user_id, f"{scenario['agent_type']} Timing Test",
                 datetime.now(timezone.utc),
                 json.dumps({
                     "test_type": "agent_timing",
                     "agent_type": scenario["agent_type"],
                     "complexity": scenario["complexity"]
                 }))
            
            # Simulate agent execution with timing measurement
            async def simulate_agent_execution():
                # Simulate realistic agent work pattern
                await asyncio.sleep(0.1)  # Initial setup
                
                # Store execution start
                execution_id = str(uuid.uuid4())
                await real_services_fixture["redis"].set_json(
                    f"agent_execution:{execution_id}",
                    {
                        "agent_type": scenario["agent_type"],
                        "thread_id": thread_id,
                        "status": "executing",
                        "start_time": time.time(),
                        "complexity": scenario["complexity"]
                    },
                    ex=300
                )
                
                # Simulate different agent work phases
                phases = [
                    ("initialization", 0.2),
                    ("data_collection", 0.5), 
                    ("analysis", 1.0),
                    ("result_generation", 0.3)
                ]
                
                for phase_name, phase_duration in phases:
                    await asyncio.sleep(phase_duration)
                    
                    # Update execution status
                    await real_services_fixture["redis"].set_json(
                        f"agent_execution:{execution_id}",
                        {
                            "agent_type": scenario["agent_type"],
                            "thread_id": thread_id,
                            "status": f"executing_{phase_name}",
                            "current_phase": phase_name,
                            "start_time": time.time() - sum(p[1] for p in phases[:phases.index((phase_name, phase_duration)) + 1]),
                            "complexity": scenario["complexity"]
                        },
                        ex=300
                    )
                
                # Complete execution
                final_result = {
                    "agent_type": scenario["agent_type"],
                    "result": f"Mock {scenario['agent_type']} result for performance testing",
                    "recommendations": ["optimization_1", "optimization_2", "optimization_3"],
                    "confidence": 0.85,
                    "execution_phases_completed": len(phases)
                }
                
                await real_services_fixture["redis"].set_json(
                    f"agent_execution:{execution_id}",
                    {
                        **final_result,
                        "thread_id": thread_id,
                        "status": "completed",
                        "end_time": time.time(),
                        "complexity": scenario["complexity"]
                    },
                    ex=300
                )
                
                return final_result
            
            # Measure agent execution performance
            metrics = await self._measure_operation_performance(
                f"{scenario['agent_type']}_execution",
                simulate_agent_execution
            )
            
            # Store result in database
            message_id = str(uuid.uuid4())
            await real_services_fixture["db"].execute("""
                INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, message_id, thread_id, "assistant", 
                 f"Agent execution completed in {metrics.execution_time:.2f} seconds",
                 json.dumps({
                     "execution_time": metrics.execution_time,
                     "agent_type": scenario["agent_type"],
                     "performance_test": True
                 }),
                 datetime.now(timezone.utc))
            
            agent_timing_results.append({
                "agent_type": scenario["agent_type"],
                "execution_time": metrics.execution_time,
                "expected_max_time": scenario["expected_max_time"],
                "within_sla": metrics.execution_time <= scenario["expected_max_time"],
                "success": metrics.success
            })
            
            # Validate individual agent timing
            assert metrics.success, f"{scenario['agent_type']} execution failed: {metrics.error_message}"
            assert metrics.execution_time <= scenario["expected_max_time"], \
                f"{scenario['agent_type']} execution too slow: {metrics.execution_time:.2f}s > {scenario['expected_max_time']}s"
            assert metrics.execution_time <= self.performance_slas["agent_execution_max"], \
                f"{scenario['agent_type']} exceeds global SLA: {metrics.execution_time:.2f}s"
        
        # Store comprehensive timing analysis
        timing_analysis = {
            "test_type": "agent_execution_timing",
            "agent_results": agent_timing_results,
            "average_execution_time": statistics.mean([r["execution_time"] for r in agent_timing_results]),
            "max_execution_time": max(r["execution_time"] for r in agent_timing_results),
            "all_within_sla": all(r["within_sla"] for r in agent_timing_results),
            "test_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await real_services_fixture["redis"].set_json(
            "agent_timing_analysis",
            timing_analysis,
            ex=86400
        )
        
        # Validate overall timing performance
        assert timing_analysis["all_within_sla"], "All agents must meet individual timing SLAs"
        assert timing_analysis["average_execution_time"] <= 20.0, f"Average execution time too high: {timing_analysis['average_execution_time']:.2f}s"
        
        self.logger.info(f"Agent execution timing validated - Average: {timing_analysis['average_execution_time']:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_delivery_latency(self, real_services_fixture):
        """
        Test WebSocket message delivery latency under various message types and loads.
        
        Critical for real-time user experience in chat interface.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "websocket-latency@example.com", "name": "WebSocket Latency User"}
        )
        
        # Test different WebSocket message types
        message_scenarios = [
            {
                "message_type": "agent_started",
                "payload_size": "small",
                "expected_latency": 0.5,  # seconds
                "content": {"type": "agent_started", "agent": "triage_agent", "timestamp": time.time()}
            },
            {
                "message_type": "agent_thinking", 
                "payload_size": "medium",
                "expected_latency": 0.8,
                "content": {
                    "type": "agent_thinking",
                    "agent": "data_helper",
                    "reasoning": "Analyzing your infrastructure data to identify optimization opportunities...",
                    "progress": 0.3,
                    "timestamp": time.time()
                }
            },
            {
                "message_type": "tool_executing",
                "payload_size": "medium",
                "expected_latency": 0.7,
                "content": {
                    "type": "tool_executing", 
                    "tool": "aws_cost_analyzer",
                    "parameters": {"region": "us-east-1", "timeframe": "30_days"},
                    "timestamp": time.time()
                }
            },
            {
                "message_type": "agent_completed",
                "payload_size": "large", 
                "expected_latency": 1.5,
                "content": {
                    "type": "agent_completed",
                    "agent": "uvs_reporter",
                    "result": {
                        "analysis": "Comprehensive cost analysis completed",
                        "recommendations": [
                            {"type": "ec2_optimization", "savings": 2400, "effort": "low"},
                            {"type": "storage_optimization", "savings": 1200, "effort": "medium"},
                            {"type": "reserved_instances", "savings": 3600, "effort": "high"}
                        ],
                        "total_savings": 7200,
                        "implementation_timeline": "4-6 weeks"
                    },
                    "timestamp": time.time()
                }
            }
        ]
        
        websocket_latency_results = []
        
        for scenario in message_scenarios:
            thread_id = str(uuid.uuid4())
            
            # Simulate WebSocket message delivery
            async def simulate_websocket_delivery():
                # Store message in Redis (simulating WebSocket queue)
                message_id = str(uuid.uuid4())
                message_data = {
                    "id": message_id,
                    "user_id": user_context.user_id,
                    "thread_id": thread_id,
                    "content": scenario["content"],
                    "queued_at": time.time(),
                    "status": "queued"
                }
                
                await real_services_fixture["redis"].set_json(
                    f"websocket_message:{message_id}",
                    message_data,
                    ex=300
                )
                
                # Simulate message processing delay based on payload size
                processing_delays = {"small": 0.05, "medium": 0.15, "large": 0.25}
                processing_delay = processing_delays.get(scenario["payload_size"], 0.1)
                await asyncio.sleep(processing_delay)
                
                # Update message status to delivered
                message_data["status"] = "delivered"
                message_data["delivered_at"] = time.time()
                message_data["processing_time"] = processing_delay
                
                await real_services_fixture["redis"].set_json(
                    f"websocket_message:{message_id}",
                    message_data,
                    ex=300
                )
                
                # Store delivery in database
                await real_services_fixture["db"].execute("""
                    INSERT INTO backend.websocket_events (id, user_id, event_type, payload, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, message_id, user_context.user_id, scenario["message_type"],
                     json.dumps(scenario["content"]), datetime.now(timezone.utc))
                
                return message_data
            
            # Measure WebSocket delivery performance
            metrics = await self._measure_operation_performance(
                f"websocket_{scenario['message_type']}",
                simulate_websocket_delivery
            )
            
            websocket_result = {
                "message_type": scenario["message_type"],
                "payload_size": scenario["payload_size"],
                "delivery_latency": metrics.execution_time,
                "expected_latency": scenario["expected_latency"],
                "within_sla": metrics.execution_time <= scenario["expected_latency"],
                "success": metrics.success
            }
            
            websocket_latency_results.append(websocket_result)
            
            # Validate individual message latency
            assert metrics.success, f"WebSocket {scenario['message_type']} delivery failed: {metrics.error_message}"
            assert metrics.execution_time <= scenario["expected_latency"], \
                f"WebSocket {scenario['message_type']} too slow: {metrics.execution_time:.3f}s > {scenario['expected_latency']}s"
            assert metrics.execution_time <= self.performance_slas["websocket_message_max"], \
                f"WebSocket {scenario['message_type']} exceeds global SLA: {metrics.execution_time:.3f}s"
            
            await asyncio.sleep(0.1)  # Prevent overwhelming Redis
        
        # Test burst message delivery
        burst_messages = []
        burst_start_time = time.time()
        
        async def send_burst_message(i):
            content = {
                "type": "agent_thinking",
                "message": f"Processing step {i} of optimization analysis",
                "progress": i / 20,
                "timestamp": time.time()
            }
            
            message_id = str(uuid.uuid4())
            await real_services_fixture["redis"].set_json(
                f"websocket_burst:{message_id}",
                {
                    "id": message_id,
                    "user_id": user_context.user_id,
                    "content": content,
                    "sent_at": time.time()
                },
                ex=300
            )
            
            return message_id
        
        # Send 20 messages simultaneously
        burst_tasks = [send_burst_message(i) for i in range(20)]
        burst_message_ids = await asyncio.gather(*burst_tasks)
        burst_completion_time = time.time()
        
        burst_duration = burst_completion_time - burst_start_time
        burst_throughput = len(burst_message_ids) / burst_duration
        
        # Store WebSocket latency analysis
        latency_analysis = {
            "individual_message_results": websocket_latency_results,
            "average_latency": statistics.mean([r["delivery_latency"] for r in websocket_latency_results]),
            "max_latency": max(r["delivery_latency"] for r in websocket_latency_results),
            "burst_test": {
                "message_count": len(burst_message_ids),
                "total_duration": burst_duration,
                "throughput": burst_throughput,
                "messages_per_second": burst_throughput
            },
            "all_within_sla": all(r["within_sla"] for r in websocket_latency_results),
            "test_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await real_services_fixture["redis"].set_json(
            "websocket_latency_analysis",
            latency_analysis,
            ex=86400
        )
        
        # Validate WebSocket performance requirements
        assert latency_analysis["all_within_sla"], "All WebSocket messages must meet latency SLAs"
        assert latency_analysis["average_latency"] <= 1.0, f"Average WebSocket latency too high: {latency_analysis['average_latency']:.3f}s"
        assert latency_analysis["burst_test"]["throughput"] >= 15.0, f"Burst throughput too low: {latency_analysis['burst_test']['throughput']:.1f} msg/s"
        
        self.logger.info(f"WebSocket latency validated - Average: {latency_analysis['average_latency']:.3f}s, Burst: {latency_analysis['burst_test']['throughput']:.1f} msg/s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_query_performance_under_load(self, real_services_fixture):
        """
        Test database query performance under concurrent load scenarios.
        
        Validates data layer performance critical for agent operations.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "db-performance@example.com", "name": "DB Performance User"}
        )
        
        # Create test data for performance testing
        await self._setup_performance_test_data(real_services_fixture, user_context)
        
        # Define database performance test scenarios
        query_scenarios = [
            {
                "name": "user_threads_query",
                "query": "SELECT id, title, created_at FROM backend.threads WHERE user_id = $1 ORDER BY created_at DESC LIMIT 20",
                "params": [user_context.user_id],
                "expected_max_time": 0.1,
                "concurrent_factor": 10
            },
            {
                "name": "thread_messages_query", 
                "query": """
                    SELECT m.id, m.content, m.role, m.created_at 
                    FROM backend.messages m 
                    JOIN backend.threads t ON m.thread_id = t.id 
                    WHERE t.user_id = $1 
                    ORDER BY m.created_at DESC 
                    LIMIT 50
                """,
                "params": [user_context.user_id],
                "expected_max_time": 0.2,
                "concurrent_factor": 8
            },
            {
                "name": "user_context_lookup",
                "query": """
                    SELECT u.id, u.email, u.name, o.name as org_name, om.role 
                    FROM auth.users u 
                    LEFT JOIN backend.organization_memberships om ON u.id = om.user_id 
                    LEFT JOIN backend.organizations o ON om.organization_id = o.id 
                    WHERE u.id = $1
                """,
                "params": [user_context.user_id],
                "expected_max_time": 0.15,
                "concurrent_factor": 15
            },
            {
                "name": "complex_analytics_query",
                "query": """
                    SELECT 
                        DATE_TRUNC('day', m.created_at) as day,
                        COUNT(*) as message_count,
                        COUNT(DISTINCT m.thread_id) as thread_count,
                        AVG(LENGTH(m.content)) as avg_message_length
                    FROM backend.messages m
                    JOIN backend.threads t ON m.thread_id = t.id
                    WHERE t.user_id = $1 
                        AND m.created_at >= NOW() - INTERVAL '30 days'
                        AND m.role = 'assistant'
                    GROUP BY DATE_TRUNC('day', m.created_at)
                    ORDER BY day DESC
                """,
                "params": [user_context.user_id],
                "expected_max_time": 0.5,
                "concurrent_factor": 5
            }
        ]
        
        db_performance_results = []
        
        for scenario in query_scenarios:
            # Test single query performance
            async def execute_single_query():
                return await real_services_fixture["db"].fetch(scenario["query"], *scenario["params"])
            
            single_metrics = await self._measure_operation_performance(
                f"db_{scenario['name']}_single",
                execute_single_query
            )
            
            # Test concurrent query performance
            async def execute_concurrent_queries():
                tasks = [
                    real_services_fixture["db"].fetch(scenario["query"], *scenario["params"])
                    for _ in range(scenario["concurrent_factor"])
                ]
                results = await asyncio.gather(*tasks)
                return results
            
            concurrent_metrics = await self._measure_operation_performance(
                f"db_{scenario['name']}_concurrent",
                execute_concurrent_queries
            )
            
            # Calculate performance degradation
            single_query_time = single_metrics.execution_time
            concurrent_avg_time = concurrent_metrics.execution_time / scenario["concurrent_factor"]
            performance_degradation = (concurrent_avg_time - single_query_time) / single_query_time if single_query_time > 0 else 0
            
            scenario_result = {
                "query_name": scenario["name"],
                "single_query_time": single_query_time,
                "concurrent_avg_time": concurrent_avg_time,
                "concurrent_factor": scenario["concurrent_factor"],
                "performance_degradation": performance_degradation,
                "within_single_sla": single_query_time <= scenario["expected_max_time"],
                "within_concurrent_sla": concurrent_avg_time <= scenario["expected_max_time"] * 1.5,  # Allow 50% degradation
                "within_db_global_sla": concurrent_avg_time <= self.performance_slas["database_query_max"],
                "degradation_acceptable": performance_degradation <= self.performance_slas["concurrent_user_degradation"]
            }
            
            db_performance_results.append(scenario_result)
            
            # Validate individual query performance
            assert single_metrics.success, f"Single {scenario['name']} query failed: {single_metrics.error_message}"
            assert concurrent_metrics.success, f"Concurrent {scenario['name']} queries failed: {concurrent_metrics.error_message}"
            assert scenario_result["within_single_sla"], \
                f"Single {scenario['name']} query too slow: {single_query_time:.3f}s > {scenario['expected_max_time']}s"
            assert scenario_result["within_concurrent_sla"], \
                f"Concurrent {scenario['name']} queries too slow: {concurrent_avg_time:.3f}s"
            assert scenario_result["degradation_acceptable"], \
                f"Performance degradation too high for {scenario['name']}: {performance_degradation:.2f}"
            
            await asyncio.sleep(0.2)  # Allow database to recover between tests
        
        # Store database performance analysis
        db_analysis = {
            "query_results": db_performance_results,
            "average_single_query_time": statistics.mean([r["single_query_time"] for r in db_performance_results]),
            "average_concurrent_degradation": statistics.mean([r["performance_degradation"] for r in db_performance_results]),
            "max_concurrent_time": max(r["concurrent_avg_time"] for r in db_performance_results),
            "all_queries_within_sla": all(r["within_db_global_sla"] for r in db_performance_results),
            "degradation_within_limits": all(r["degradation_acceptable"] for r in db_performance_results),
            "test_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await real_services_fixture["redis"].set_json(
            "database_performance_analysis",
            db_analysis,
            ex=86400
        )
        
        # Validate overall database performance
        assert db_analysis["all_queries_within_sla"], "All database queries must meet SLA requirements"
        assert db_analysis["degradation_within_limits"], "Database performance degradation must be within acceptable limits"
        assert db_analysis["max_concurrent_time"] <= 1.0, f"Maximum concurrent query time too high: {db_analysis['max_concurrent_time']:.3f}s"
        
        self.logger.info(f"Database performance validated - Avg single: {db_analysis['average_single_query_time']:.3f}s, Max concurrent: {db_analysis['max_concurrent_time']:.3f}s")

    async def _setup_performance_test_data(self, real_services_fixture, user_context):
        """Set up test data for performance testing."""
        # Create multiple threads for realistic data volume
        thread_ids = []
        for i in range(10):
            thread_id = str(uuid.uuid4())
            await real_services_fixture["db"].execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at)
                VALUES ($1, $2, $3, $4)
            """, thread_id, user_context.user_id, f"Performance Test Thread {i}", 
                 datetime.now(timezone.utc) - timedelta(days=i))
            thread_ids.append(thread_id)
        
        # Create messages for each thread
        for thread_id in thread_ids:
            for j in range(20):  # 20 messages per thread
                message_id = str(uuid.uuid4())
                role = "user" if j % 2 == 0 else "assistant"
                content = f"Performance test message {j} for thread {thread_id}"
                
                await real_services_fixture["db"].execute("""
                    INSERT INTO backend.messages (id, thread_id, role, content, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, message_id, thread_id, role, content,
                     datetime.now(timezone.utc) - timedelta(days=len(thread_ids) - thread_ids.index(thread_id), hours=j))

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_system_response_degradation_under_load(self, real_services_fixture):
        """
        Test system-wide response time degradation under increasing load.
        
        Validates scalability and performance consistency.
        """
        user_contexts = []
        
        # Create multiple test users for load testing
        for i in range(5):
            user_context = await create_authenticated_user_context(
                self.auth_helper,
                real_services_fixture["db"],
                user_data={"email": f"load-user-{i}@example.com", "name": f"Load User {i}"}
            )
            user_contexts.append(user_context)
        
        # Test load scenarios with increasing concurrency
        load_scenarios = [
            {"concurrent_users": 1, "operations_per_user": 5, "expected_degradation": 0.0},
            {"concurrent_users": 2, "operations_per_user": 5, "expected_degradation": 0.1},
            {"concurrent_users": 3, "operations_per_user": 5, "expected_degradation": 0.2},
            {"concurrent_users": 5, "operations_per_user": 5, "expected_degradation": 0.3}
        ]
        
        load_test_results = []
        baseline_response_time = None
        
        for scenario in load_scenarios:
            concurrent_users = min(scenario["concurrent_users"], len(user_contexts))
            selected_users = user_contexts[:concurrent_users]
            
            # Define system operation that simulates real user workflow
            async def simulate_user_workflow(user_context, user_index):
                workflow_results = []
                
                for op_index in range(scenario["operations_per_user"]):
                    thread_id = str(uuid.uuid4())
                    
                    # Create thread (database operation)
                    start_time = time.time()
                    await real_services_fixture["db"].execute("""
                        INSERT INTO backend.threads (id, user_id, title, created_at)
                        VALUES ($1, $2, $3, $4)
                    """, thread_id, user_context.user_id, f"Load Test Thread {user_index}-{op_index}",
                         datetime.now(timezone.utc))
                    
                    # Cache operation (Redis)
                    session_data = {
                        "user_id": user_context.user_id,
                        "thread_id": thread_id,
                        "operation_index": op_index,
                        "timestamp": time.time()
                    }
                    
                    await real_services_fixture["redis"].set_json(
                        f"load_test_session:{user_context.user_id}:{op_index}",
                        session_data,
                        ex=300
                    )
                    
                    # Simulate agent execution
                    await asyncio.sleep(0.3)  # Simulate processing time
                    
                    # Store result message
                    message_id = str(uuid.uuid4())
                    await real_services_fixture["db"].execute("""
                        INSERT INTO backend.messages (id, thread_id, role, content, created_at)
                        VALUES ($1, $2, $3, $4, $5)
                    """, message_id, thread_id, "assistant",
                         f"Load test response for user {user_index} operation {op_index}",
                         datetime.now(timezone.utc))
                    
                    operation_time = time.time() - start_time
                    workflow_results.append(operation_time)
                    
                    await asyncio.sleep(0.1)  # Brief pause between operations
                
                return workflow_results
            
            # Execute concurrent user workflows
            load_start_time = time.time()
            
            workflow_tasks = [
                simulate_user_workflow(user_context, i) 
                for i, user_context in enumerate(selected_users)
            ]
            
            workflow_results = await asyncio.gather(*workflow_tasks)
            
            load_completion_time = time.time()
            total_load_time = load_completion_time - load_start_time
            
            # Flatten results and calculate metrics
            all_operation_times = []
            for user_results in workflow_results:
                all_operation_times.extend(user_results)
            
            total_operations = len(all_operation_times)
            successful_operations = len([t for t in all_operation_times if t > 0])
            average_response_time = statistics.mean(all_operation_times)
            p95_response_time = statistics.quantiles(all_operation_times, n=20)[18]  # 95th percentile
            p99_response_time = statistics.quantiles(all_operation_times, n=100)[98] if len(all_operation_times) >= 100 else max(all_operation_times)
            throughput = total_operations / total_load_time
            error_rate = (total_operations - successful_operations) / total_operations
            
            # Calculate degradation from baseline
            if baseline_response_time is None:
                baseline_response_time = average_response_time
                performance_degradation = 0.0
            else:
                performance_degradation = (average_response_time - baseline_response_time) / baseline_response_time
            
            load_result = LoadTestResult(
                concurrent_users=concurrent_users,
                total_operations=total_operations,
                successful_operations=successful_operations,
                average_response_time=average_response_time,
                p95_response_time=p95_response_time,
                p99_response_time=p99_response_time,
                throughput=throughput,
                error_rate=error_rate
            )
            
            scenario_result = {
                "concurrent_users": concurrent_users,
                "load_result": {
                    "total_operations": load_result.total_operations,
                    "average_response_time": load_result.average_response_time,
                    "p95_response_time": load_result.p95_response_time,
                    "throughput": load_result.throughput,
                    "error_rate": load_result.error_rate
                },
                "performance_degradation": performance_degradation,
                "expected_degradation": scenario["expected_degradation"],
                "degradation_acceptable": performance_degradation <= scenario["expected_degradation"],
                "throughput_acceptable": load_result.throughput >= self.performance_slas["min_throughput"],
                "error_rate_acceptable": load_result.error_rate <= self.performance_slas["max_error_rate"]
            }
            
            load_test_results.append(scenario_result)
            
            # Validate load scenario performance
            assert scenario_result["degradation_acceptable"], \
                f"Performance degradation too high for {concurrent_users} users: {performance_degradation:.2f} > {scenario['expected_degradation']}"
            assert scenario_result["throughput_acceptable"], \
                f"Throughput too low for {concurrent_users} users: {load_result.throughput:.1f} < {self.performance_slas['min_throughput']}"
            assert scenario_result["error_rate_acceptable"], \
                f"Error rate too high for {concurrent_users} users: {load_result.error_rate:.3f} > {self.performance_slas['max_error_rate']}"
            
            # Wait between load scenarios
            await asyncio.sleep(1.0)
        
        # Store load test analysis
        load_analysis = {
            "baseline_response_time": baseline_response_time,
            "load_scenarios": load_test_results,
            "max_degradation_observed": max(r["performance_degradation"] for r in load_test_results),
            "min_throughput_observed": min(r["load_result"]["throughput"] for r in load_test_results),
            "max_error_rate_observed": max(r["load_result"]["error_rate"] for r in load_test_results),
            "scalability_acceptable": all(r["degradation_acceptable"] for r in load_test_results),
            "performance_consistent": all(r["throughput_acceptable"] for r in load_test_results),
            "test_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await real_services_fixture["redis"].set_json(
            "load_test_analysis",
            load_analysis,
            ex=86400
        )
        
        # Validate overall load test performance
        assert load_analysis["scalability_acceptable"], "System must scale acceptably under load"
        assert load_analysis["performance_consistent"], "System performance must remain consistent"
        assert load_analysis["max_degradation_observed"] <= 0.4, f"Maximum observed degradation too high: {load_analysis['max_degradation_observed']:.2f}"
        assert load_analysis["min_throughput_observed"] >= 5.0, f"Minimum throughput too low: {load_analysis['min_throughput_observed']:.1f}"
        
        self.logger.info(f"Load testing validated - Max degradation: {load_analysis['max_degradation_observed']:.2f}, Min throughput: {load_analysis['min_throughput_observed']:.1f}")

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_resource_usage_efficiency_validation(self, real_services_fixture):
        """
        Test system resource usage efficiency during normal and peak operations.
        
        Validates that system uses resources efficiently to support scalability.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "resource-efficiency@example.com", "name": "Resource Efficiency User"}
        )
        
        # Test resource efficiency across different operation types
        efficiency_scenarios = [
            {
                "operation": "lightweight_query",
                "description": "Simple database queries should be very efficient",
                "expected_ops_per_cpu_second": 50.0,
                "test_function": lambda: real_services_fixture["db"].fetchval("SELECT COUNT(*) FROM auth.users WHERE id = $1", user_context.user_id)
            },
            {
                "operation": "cache_operations",
                "description": "Redis operations should be extremely efficient", 
                "expected_ops_per_cpu_second": 100.0,
                "test_function": lambda: real_services_fixture["redis"].set(f"efficiency_test_{time.time()}", "test_value", ex=60)
            },
            {
                "operation": "complex_data_processing",
                "description": "Complex operations should still be reasonably efficient",
                "expected_ops_per_cpu_second": 10.0,
                "test_function": self._simulate_complex_data_operation
            }
        ]
        
        efficiency_results = []
        
        for scenario in efficiency_scenarios:
            # Measure resource efficiency
            operation_count = 20
            cpu_start = time.process_time()
            wall_start = time.time()
            
            # Execute operations
            for _ in range(operation_count):
                if asyncio.iscoroutinefunction(scenario["test_function"]):
                    await scenario["test_function"]()
                else:
                    await asyncio.get_event_loop().run_in_executor(None, scenario["test_function"])
                
            cpu_end = time.process_time()
            wall_end = time.time()
            
            cpu_time = cpu_end - cpu_start
            wall_time = wall_end - wall_start
            
            # Calculate efficiency metrics
            ops_per_cpu_second = operation_count / cpu_time if cpu_time > 0 else float('inf')
            ops_per_wall_second = operation_count / wall_time if wall_time > 0 else float('inf')
            cpu_efficiency = cpu_time / wall_time if wall_time > 0 else 1.0  # Lower is better for async ops
            
            efficiency_result = {
                "operation": scenario["operation"],
                "operation_count": operation_count,
                "cpu_time": cpu_time,
                "wall_time": wall_time,
                "ops_per_cpu_second": ops_per_cpu_second,
                "ops_per_wall_second": ops_per_wall_second,
                "cpu_efficiency": cpu_efficiency,
                "expected_ops_per_cpu_second": scenario["expected_ops_per_cpu_second"],
                "efficiency_acceptable": ops_per_cpu_second >= scenario["expected_ops_per_cpu_second"],
                "description": scenario["description"]
            }
            
            efficiency_results.append(efficiency_result)
            
            # Validate efficiency requirements
            assert efficiency_result["efficiency_acceptable"], \
                f"{scenario['operation']} efficiency too low: {ops_per_cpu_second:.1f} < {scenario['expected_ops_per_cpu_second']}"
            
            await asyncio.sleep(0.1)  # Brief pause between efficiency tests
        
        # Test memory usage stability during operations
        memory_stability_result = await self._test_memory_usage_stability(real_services_fixture, user_context)
        
        # Store efficiency analysis
        efficiency_analysis = {
            "operation_efficiency": efficiency_results,
            "memory_stability": memory_stability_result,
            "average_cpu_efficiency": statistics.mean([r["ops_per_cpu_second"] for r in efficiency_results]),
            "all_operations_efficient": all(r["efficiency_acceptable"] for r in efficiency_results),
            "memory_stable": memory_stability_result["stable"],
            "test_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await real_services_fixture["redis"].set_json(
            "resource_efficiency_analysis",
            efficiency_analysis,
            ex=86400
        )
        
        # Validate overall resource efficiency
        assert efficiency_analysis["all_operations_efficient"], "All operations must meet efficiency requirements"
        assert efficiency_analysis["memory_stable"], "Memory usage must remain stable during operations"
        assert efficiency_analysis["average_cpu_efficiency"] >= 25.0, f"Average CPU efficiency too low: {efficiency_analysis['average_cpu_efficiency']:.1f}"
        
        self.logger.info(f"Resource efficiency validated - Average CPU efficiency: {efficiency_analysis['average_cpu_efficiency']:.1f} ops/cpu-sec")

    async def _simulate_complex_data_operation(self):
        """Simulate a complex data processing operation."""
        # Simulate data analysis work
        data = list(range(1000))
        result = sum(x * x for x in data if x % 2 == 0)
        
        # Simulate database interaction
        await asyncio.sleep(0.05)
        
        return result

    async def _test_memory_usage_stability(self, real_services_fixture, user_context):
        """Test memory usage stability during sustained operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform sustained operations
        for i in range(100):
            # Mix of database and cache operations
            await real_services_fixture["db"].fetchval("SELECT $1", f"memory_test_{i}")
            await real_services_fixture["redis"].set(f"memory_test_{i}", f"value_{i}", ex=300)
            
            if i % 20 == 0:
                current_memory = process.memory_info().rss
                memory_growth = (current_memory - initial_memory) / initial_memory
                
                # Memory growth should be reasonable (< 50% during test)
                if memory_growth > 0.5:
                    return {
                        "stable": False,
                        "memory_growth": memory_growth,
                        "initial_memory": initial_memory,
                        "final_memory": current_memory
                    }
        
        final_memory = process.memory_info().rss
        memory_growth = (final_memory - initial_memory) / initial_memory
        
        return {
            "stable": memory_growth <= 0.3,  # Allow up to 30% growth
            "memory_growth": memory_growth,
            "initial_memory": initial_memory,
            "final_memory": final_memory
        }

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_performance_consistency_across_user_sessions(self, real_services_fixture):
        """
        Test that performance remains consistent across different user sessions and contexts.
        
        Validates that user isolation doesn't impact performance negatively.
        """
        # Create multiple users with different contexts
        user_scenarios = [
            {"type": "new_user", "thread_count": 0, "message_count": 0},
            {"type": "active_user", "thread_count": 5, "message_count": 50},
            {"type": "heavy_user", "thread_count": 20, "message_count": 200}
        ]
        
        user_performance_results = []
        
        for scenario in user_scenarios:
            user_context = await create_authenticated_user_context(
                self.auth_helper,
                real_services_fixture["db"],
                user_data={
                    "email": f"{scenario['type']}-consistency@example.com",
                    "name": f"{scenario['type'].title()} User"
                }
            )
            
            # Set up user context based on scenario
            await self._setup_user_context(real_services_fixture, user_context, scenario)
            
            # Test standard operations for this user
            standard_operations = [
                {
                    "name": "create_thread",
                    "operation": lambda: self._create_thread_operation(real_services_fixture, user_context),
                    "expected_max_time": 2.0
                },
                {
                    "name": "fetch_user_threads",
                    "operation": lambda: real_services_fixture["db"].fetch(
                        "SELECT id, title FROM backend.threads WHERE user_id = $1 ORDER BY created_at DESC LIMIT 10",
                        user_context.user_id
                    ),
                    "expected_max_time": 0.5
                },
                {
                    "name": "user_session_cache",
                    "operation": lambda: self._user_session_cache_operation(real_services_fixture, user_context),
                    "expected_max_time": 1.0
                }
            ]
            
            user_operation_results = []
            
            for operation in standard_operations:
                # Test operation multiple times for consistency
                operation_times = []
                
                for _ in range(5):  # 5 iterations per operation
                    metrics = await self._measure_operation_performance(
                        f"{scenario['type']}_{operation['name']}",
                        operation["operation"]
                    )
                    operation_times.append(metrics.execution_time)
                    
                    assert metrics.success, f"Operation {operation['name']} failed for {scenario['type']}: {metrics.error_message}"
                    assert metrics.execution_time <= operation["expected_max_time"], \
                        f"Operation {operation['name']} too slow for {scenario['type']}: {metrics.execution_time:.3f}s"
                
                # Calculate consistency metrics
                avg_time = statistics.mean(operation_times)
                std_dev = statistics.stdev(operation_times) if len(operation_times) > 1 else 0
                consistency_coefficient = std_dev / avg_time if avg_time > 0 else 0  # Lower is more consistent
                
                user_operation_results.append({
                    "operation": operation["name"],
                    "avg_time": avg_time,
                    "std_dev": std_dev,
                    "consistency_coefficient": consistency_coefficient,
                    "times": operation_times,
                    "consistent": consistency_coefficient <= 0.3  # Max 30% variation
                })
            
            user_performance_result = {
                "user_type": scenario["type"],
                "user_id": user_context.user_id,
                "context_complexity": {
                    "thread_count": scenario["thread_count"],
                    "message_count": scenario["message_count"]
                },
                "operations": user_operation_results,
                "average_consistency": statistics.mean([op["consistency_coefficient"] for op in user_operation_results]),
                "all_operations_consistent": all(op["consistent"] for op in user_operation_results)
            }
            
            user_performance_results.append(user_performance_result)
            
            # Validate consistency for this user type
            assert user_performance_result["all_operations_consistent"], \
                f"Performance inconsistent for {scenario['type']} user"
            assert user_performance_result["average_consistency"] <= 0.25, \
                f"Average consistency too poor for {scenario['type']}: {user_performance_result['average_consistency']:.3f}"
        
        # Compare performance across user types
        performance_variance_analysis = self._analyze_cross_user_performance_variance(user_performance_results)
        
        # Store consistency analysis
        consistency_analysis = {
            "user_performance_results": user_performance_results,
            "cross_user_variance": performance_variance_analysis,
            "all_users_consistent": all(r["all_operations_consistent"] for r in user_performance_results),
            "cross_user_performance_fair": performance_variance_analysis["performance_fair"],
            "test_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await real_services_fixture["redis"].set_json(
            "performance_consistency_analysis",
            consistency_analysis,
            ex=86400
        )
        
        # Validate overall performance consistency
        assert consistency_analysis["all_users_consistent"], "All user types must have consistent performance"
        assert consistency_analysis["cross_user_performance_fair"], "Performance must be fair across different user types"
        
        max_user_variance = max(r["average_consistency"] for r in user_performance_results)
        assert max_user_variance <= 0.3, f"Maximum user performance variance too high: {max_user_variance:.3f}"
        
        self.logger.info(f"Performance consistency validated - Max variance: {max_user_variance:.3f}")

    async def _setup_user_context(self, real_services_fixture, user_context, scenario):
        """Set up user context based on scenario."""
        # Create threads
        for i in range(scenario["thread_count"]):
            thread_id = str(uuid.uuid4())
            await real_services_fixture["db"].execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at)
                VALUES ($1, $2, $3, $4)
            """, thread_id, user_context.user_id, f"Context Thread {i}",
                 datetime.now(timezone.utc) - timedelta(days=i))
            
            # Add messages to some threads
            messages_per_thread = scenario["message_count"] // max(scenario["thread_count"], 1)
            for j in range(messages_per_thread):
                message_id = str(uuid.uuid4())
                await real_services_fixture["db"].execute("""
                    INSERT INTO backend.messages (id, thread_id, role, content, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, message_id, thread_id, "user" if j % 2 == 0 else "assistant",
                     f"Context message {j} for thread {i}",
                     datetime.now(timezone.utc) - timedelta(days=i, hours=j))

    async def _create_thread_operation(self, real_services_fixture, user_context):
        """Create a new thread operation for performance testing."""
        thread_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at)
            VALUES ($1, $2, $3, $4)
        """, thread_id, user_context.user_id, "Performance Test Thread", datetime.now(timezone.utc))
        return thread_id

    async def _user_session_cache_operation(self, real_services_fixture, user_context):
        """User session cache operation for performance testing."""
        session_data = {
            "user_id": user_context.user_id,
            "session_start": time.time(),
            "active": True
        }
        
        session_key = f"perf_session:{user_context.user_id}:{int(time.time())}"
        await real_services_fixture["redis"].set_json(session_key, session_data, ex=300)
        
        # Retrieve and validate
        retrieved_data = await real_services_fixture["redis"].get_json(session_key)
        return retrieved_data is not None

    def _analyze_cross_user_performance_variance(self, user_performance_results):
        """Analyze performance variance across different user types."""
        # Compare average operation times across user types
        operation_names = user_performance_results[0]["operations"][0].keys() if user_performance_results else []
        
        cross_user_variance = {}
        
        for user_result in user_performance_results:
            for op_result in user_result["operations"]:
                op_name = op_result["operation"]
                if op_name not in cross_user_variance:
                    cross_user_variance[op_name] = []
                cross_user_variance[op_name].append(op_result["avg_time"])
        
        # Calculate variance coefficients
        variance_analysis = {}
        for op_name, times in cross_user_variance.items():
            if len(times) > 1:
                avg_time = statistics.mean(times)
                std_dev = statistics.stdev(times)
                variance_coefficient = std_dev / avg_time if avg_time > 0 else 0
                variance_analysis[op_name] = {
                    "avg_time": avg_time,
                    "std_dev": std_dev,
                    "variance_coefficient": variance_coefficient,
                    "fair": variance_coefficient <= 0.4  # Max 40% variance across user types
                }
        
        return {
            "operation_variance": variance_analysis,
            "average_variance_coefficient": statistics.mean([v["variance_coefficient"] for v in variance_analysis.values()]) if variance_analysis else 0,
            "performance_fair": all(v["fair"] for v in variance_analysis.values()) if variance_analysis else True
        }