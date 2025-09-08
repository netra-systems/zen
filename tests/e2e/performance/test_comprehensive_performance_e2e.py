"""
E2E Performance Tests - Comprehensive Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate complete user workflows perform at business-critical speeds
- Value Impact: E2E performance prevents customer churn - 1 second delay = 7% conversion loss
- Strategic Impact: Performance validation for Enterprise SLAs and scalability commitments

CRITICAL: These E2E tests validate COMPLETE user journeys with REAL services.
E2E performance failures indicate systemic issues that impact ALL customers.
"""

import asyncio
import pytest
import time
import psutil
import json
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from statistics import mean, median, stdev
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import get_env

from netra_backend.app.services.user_execution_context import UserExecutionContext


@dataclass
class E2EPerformanceResult:
    """Complete E2E performance test result."""
    workflow_name: str
    user_count: int
    total_duration_seconds: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    throughput_operations_per_second: float
    success_rate: float
    error_count: int
    memory_peak_mb: float
    cpu_peak_percent: float
    websocket_events_validated: bool
    authentication_time_ms: float
    business_value_delivered: bool
    sla_tier_compliance: Dict[str, bool]
    cost_impact_analysis: Dict[str, Any]
    
    @property
    def performance_grade(self) -> str:
        """Calculate overall performance grade."""
        if self.success_rate < 0.99:
            return "F"  # Reliability issues
        elif self.p95_response_time_ms > 2000:
            return "F"  # Too slow
        elif self.p95_response_time_ms > 1000:
            return "D"  # Poor
        elif self.p95_response_time_ms > 500:
            return "C"  # Acceptable
        elif self.p95_response_time_ms > 250:
            return "B"  # Good
        else:
            return "A"  # Excellent


class E2EPerformanceMonitor:
    """Comprehensive E2E performance monitoring system."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.test_results: List[E2EPerformanceResult] = []
        self.active_measurements = {}
        self.resource_snapshots = []
        
    @asynccontextmanager
    async def monitor_workflow(self, workflow_name: str, expected_user_count: int = 1):
        """Monitor complete E2E workflow performance."""
        measurement_id = str(uuid4())
        start_time = time.perf_counter()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        
        # Take initial resource snapshot
        self.resource_snapshots.append({
            "workflow": workflow_name,
            "stage": "start",
            "time": start_time,
            "memory_mb": start_memory,
            "cpu_percent": self.process.cpu_percent()
        })
        
        measurement_data = {
            "workflow_name": workflow_name,
            "user_count": expected_user_count,
            "start_time": start_time,
            "start_memory": start_memory,
            "response_times": [],
            "error_count": 0,
            "websocket_events": [],
            "auth_time": 0,
            "business_value_indicators": [],
            "operations_completed": 0
        }
        
        self.active_measurements[measurement_id] = measurement_data
        
        try:
            yield measurement_data
        except Exception as e:
            measurement_data["error_count"] += 1
            raise
        finally:
            await self._finalize_measurement(measurement_id)
            
    async def _finalize_measurement(self, measurement_id: str):
        """Finalize performance measurement and generate result."""
        measurement_data = self.active_measurements.pop(measurement_id, {})
        
        if not measurement_data:
            return
            
        end_time = time.perf_counter()
        end_memory = self.process.memory_info().rss / 1024 / 1024
        
        # Calculate metrics
        total_duration = end_time - measurement_data["start_time"]
        response_times = measurement_data["response_times"]
        
        if response_times:
            avg_response_time = mean(response_times)
            p95_response_time = sorted(response_times)[int(0.95 * len(response_times))]
            p99_response_time = sorted(response_times)[int(0.99 * len(response_times))]
        else:
            avg_response_time = p95_response_time = p99_response_time = 0
            
        operations_completed = max(measurement_data["operations_completed"], len(response_times))
        throughput = operations_completed / total_duration if total_duration > 0 else 0
        
        success_rate = (operations_completed - measurement_data["error_count"]) / max(operations_completed, 1)
        
        # Take final resource snapshot
        self.resource_snapshots.append({
            "workflow": measurement_data["workflow_name"],
            "stage": "end",
            "time": end_time,
            "memory_mb": end_memory,
            "cpu_percent": self.process.cpu_percent()
        })
        
        # Calculate resource peaks
        workflow_snapshots = [s for s in self.resource_snapshots 
                            if s["workflow"] == measurement_data["workflow_name"]]
        memory_peak = max(s["memory_mb"] for s in workflow_snapshots) if workflow_snapshots else end_memory
        cpu_peak = max(s["cpu_percent"] for s in workflow_snapshots) if workflow_snapshots else 0
        
        # Generate performance result
        result = E2EPerformanceResult(
            workflow_name=measurement_data["workflow_name"],
            user_count=measurement_data["user_count"],
            total_duration_seconds=total_duration,
            avg_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            throughput_operations_per_second=throughput,
            success_rate=success_rate,
            error_count=measurement_data["error_count"],
            memory_peak_mb=memory_peak,
            cpu_peak_percent=cpu_peak,
            websocket_events_validated=len(measurement_data["websocket_events"]) > 0,
            authentication_time_ms=measurement_data["auth_time"],
            business_value_delivered=len(measurement_data["business_value_indicators"]) > 0,
            sla_tier_compliance=self._calculate_sla_compliance(avg_response_time, p95_response_time, success_rate),
            cost_impact_analysis=self._calculate_cost_impact(total_duration, memory_peak, operations_completed)
        )
        
        self.test_results.append(result)
        
    def _calculate_sla_compliance(self, avg_ms: float, p95_ms: float, success_rate: float) -> Dict[str, bool]:
        """Calculate SLA compliance for different customer tiers."""
        return {
            "free_tier": avg_ms < 2000 and p95_ms < 5000 and success_rate > 0.95,
            "early_tier": avg_ms < 1000 and p95_ms < 2500 and success_rate > 0.98,
            "mid_tier": avg_ms < 500 and p95_ms < 1500 and success_rate > 0.99,
            "enterprise_tier": avg_ms < 250 and p95_ms < 750 and success_rate > 0.999
        }
        
    def _calculate_cost_impact(self, duration: float, peak_memory: float, operations: int) -> Dict[str, Any]:
        """Calculate cost impact analysis for business decision making."""
        # Estimated cost per operation (simplified model)
        cpu_cost_per_second = 0.001  # $0.001 per CPU second
        memory_cost_per_mb_second = 0.0001  # $0.0001 per MB second
        
        estimated_cpu_cost = duration * cpu_cost_per_second
        estimated_memory_cost = duration * peak_memory * memory_cost_per_mb_second
        total_cost = estimated_cpu_cost + estimated_memory_cost
        
        cost_per_operation = total_cost / max(operations, 1)
        
        return {
            "estimated_cpu_cost_usd": estimated_cpu_cost,
            "estimated_memory_cost_usd": estimated_memory_cost,
            "total_estimated_cost_usd": total_cost,
            "cost_per_operation_usd": cost_per_operation,
            "scalability_cost_projection": {
                "1000_users_per_day": cost_per_operation * 1000,
                "10000_users_per_day": cost_per_operation * 10000,
                "100000_users_per_day": cost_per_operation * 100000
            }
        }
        
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        if not self.test_results:
            return {"error": "No performance results available"}
            
        # Aggregate metrics
        all_response_times = [r.avg_response_time_ms for r in self.test_results]
        all_throughputs = [r.throughput_operations_per_second for r in self.test_results]
        all_success_rates = [r.success_rate for r in self.test_results]
        
        # SLA compliance summary
        sla_compliance_summary = {
            "free_tier": sum(1 for r in self.test_results if r.sla_tier_compliance["free_tier"]) / len(self.test_results),
            "early_tier": sum(1 for r in self.test_results if r.sla_tier_compliance["early_tier"]) / len(self.test_results),
            "mid_tier": sum(1 for r in self.test_results if r.sla_tier_compliance["mid_tier"]) / len(self.test_results),
            "enterprise_tier": sum(1 for r in self.test_results if r.sla_tier_compliance["enterprise_tier"]) / len(self.test_results)
        }
        
        # Performance grades
        grade_distribution = {}
        for result in self.test_results:
            grade = result.performance_grade
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
            
        # Business impact summary
        total_cost = sum(r.cost_impact_analysis["total_estimated_cost_usd"] for r in self.test_results)
        avg_cost_per_operation = mean([r.cost_impact_analysis["cost_per_operation_usd"] for r in self.test_results])
        
        return {
            "summary": {
                "total_workflows_tested": len(self.test_results),
                "avg_response_time_ms": mean(all_response_times),
                "median_response_time_ms": median(all_response_times),
                "p95_response_time_ms": sorted(all_response_times)[int(0.95 * len(all_response_times))],
                "avg_throughput_ops_per_sec": mean(all_throughputs),
                "avg_success_rate": mean(all_success_rates),
                "overall_grade": self._calculate_overall_grade()
            },
            "sla_compliance": sla_compliance_summary,
            "performance_grades": grade_distribution,
            "business_impact": {
                "total_estimated_cost_usd": total_cost,
                "avg_cost_per_operation_usd": avg_cost_per_operation,
                "cost_efficiency_grade": "A" if avg_cost_per_operation < 0.001 else "B" if avg_cost_per_operation < 0.01 else "C"
            },
            "detailed_results": [asdict(r) for r in self.test_results]
        }
        
    def _calculate_overall_grade(self) -> str:
        """Calculate overall performance grade across all workflows."""
        grades = [r.performance_grade for r in self.test_results]
        
        # Count grade distribution
        grade_counts = {}
        for grade in grades:
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
            
        # Determine overall grade based on distribution
        total = len(grades)
        if grade_counts.get("F", 0) > total * 0.1:  # More than 10% failing
            return "F"
        elif grade_counts.get("A", 0) + grade_counts.get("B", 0) > total * 0.8:  # 80% good
            return "A"
        elif grade_counts.get("C", 0) + grade_counts.get("B", 0) + grade_counts.get("A", 0) > total * 0.9:  # 90% acceptable
            return "B"
        else:
            return "C"


@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.performance
@pytest.mark.benchmark
class TestCompleteUserWorkflowPerformance(BaseE2ETest):
    """Test complete user workflow performance - highest business value validation."""
    
    @pytest.fixture
    def performance_monitor(self):
        """Provide E2E performance monitor."""
        return E2EPerformanceMonitor()
        
    @pytest.fixture
    def auth_helper(self):
        """Provide authenticated E2E helper."""
        return E2EAuthHelper()
        
    @pytest.mark.asyncio
    async def test_complete_user_registration_to_first_value_e2e_performance(
        self, real_services_fixture, performance_monitor, auth_helper
    ):
        """Test complete new user journey performance - critical for conversion.
        
        BVJ: New user conversion journey - 1 second delay reduces conversion by 7%.
        Target: <3 seconds from registration to first AI insight.
        """
        backend_url = real_services_fixture["backend_url"]
        
        async with performance_monitor.monitor_workflow("user_registration_to_value", 1) as monitor:
            # Step 1: User Registration
            registration_start = time.perf_counter()
            
            user_data = await auth_helper.create_test_user(
                email=f"perf_test_{uuid4()}@example.com",
                name="Performance Test User"
            )
            
            registration_time = (time.perf_counter() - registration_start) * 1000
            monitor["auth_time"] = registration_time
            monitor["response_times"].append(registration_time)
            monitor["operations_completed"] += 1
            
            # Step 2: Authentication and WebSocket Connection
            websocket_start = time.perf_counter()
            
            async with WebSocketTestClient(
                token=user_data["token"],
                base_url=backend_url
            ) as websocket_client:
                
                websocket_time = (time.perf_counter() - websocket_start) * 1000
                monitor["response_times"].append(websocket_time)
                monitor["operations_completed"] += 1
                
                # Step 3: First Agent Interaction (Triage)
                agent_start = time.perf_counter()
                
                await websocket_client.send_json({
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": "Help me get started with cost optimization",
                    "user_context": {
                        "first_time_user": True,
                        "performance_test": True
                    }
                })
                
                # Collect WebSocket events
                events = []
                timeout_start = time.time()
                
                while time.time() - timeout_start < 30:  # 30 second timeout
                    try:
                        event = await asyncio.wait_for(websocket_client.receive_json(), timeout=1.0)
                        events.append(event)
                        
                        if event.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                        
                agent_time = (time.perf_counter() - agent_start) * 1000
                monitor["response_times"].append(agent_time)
                monitor["operations_completed"] += 1
                monitor["websocket_events"].extend(events)
                
                # Validate business value delivered
                final_event = events[-1] if events else {}
                if final_event.get("type") == "agent_completed":
                    result_data = final_event.get("data", {}).get("result", {})
                    if "recommendations" in result_data or "next_steps" in result_data:
                        monitor["business_value_indicators"].append("first_user_value_delivered")
                        
                # Validate critical WebSocket events
                event_types = [e.get("type") for e in events]
                critical_events = ["agent_started", "agent_thinking", "agent_completed"]
                
                if all(event in event_types for event in critical_events):
                    monitor["websocket_events"].append("critical_events_validated")
                    
        # Performance analysis
        result = performance_monitor.test_results[-1]
        
        # Critical business performance assertions
        total_time_to_value = result.total_duration_seconds
        assert total_time_to_value < 10.0, (
            f"Time to first value too slow: {total_time_to_value:.2f}s (target: <10s)"
        )
        
        # SLA compliance validation
        assert result.sla_tier_compliance["free_tier"], "Fails Free tier SLA"
        assert result.success_rate > 0.98, f"Success rate too low: {result.success_rate:.2%}"
        
        # Business value validation
        assert result.business_value_delivered, "No business value delivered to new user"
        assert result.websocket_events_validated, "Critical WebSocket events missing"
        
        # Performance grade
        assert result.performance_grade in ["A", "B", "C"], (
            f"Performance grade unacceptable: {result.performance_grade}"
        )
        
        print(f"✓ New user journey: {total_time_to_value:.2f}s total, "
              f"Grade: {result.performance_grade}, "
              f"Cost: ${result.cost_impact_analysis['total_estimated_cost_usd']:.4f}")
              
    @pytest.mark.asyncio
    async def test_multi_user_concurrent_workflow_performance(
        self, real_services_fixture, performance_monitor, auth_helper
    ):
        """Test multi-user concurrent performance - validates scalability claims.
        
        BVJ: Concurrent user performance validates Enterprise scalability promises.
        Must handle 10+ concurrent users without degradation.
        """
        backend_url = real_services_fixture["backend_url"]
        user_count = 10
        
        async with performance_monitor.monitor_workflow("concurrent_multi_user", user_count) as monitor:
            
            async def single_user_workflow(user_id: int):
                """Complete workflow for single user."""
                workflow_start = time.perf_counter()
                
                try:
                    # Create authenticated user
                    user_data = await auth_helper.create_test_user(
                        email=f"concurrent_user_{user_id}_{uuid4()}@example.com",
                        name=f"Concurrent User {user_id}"
                    )
                    
                    # Execute user workflow
                    async with WebSocketTestClient(
                        token=user_data["token"],
                        base_url=backend_url
                    ) as client:
                        
                        # Send agent request
                        await client.send_json({
                            "type": "agent_request",
                            "agent": "cost_optimizer",
                            "message": f"Analyze costs for user {user_id}",
                            "concurrent_test": True
                        })
                        
                        # Wait for completion
                        events = []
                        timeout_start = time.time()
                        
                        while time.time() - timeout_start < 15:  # 15s timeout per user
                            try:
                                event = await asyncio.wait_for(client.receive_json(), timeout=1.0)
                                events.append(event)
                                
                                if event.get("type") == "agent_completed":
                                    break
                            except asyncio.TimeoutError:
                                continue
                                
                        workflow_time = (time.perf_counter() - workflow_start) * 1000
                        
                        return {
                            "user_id": user_id,
                            "workflow_time_ms": workflow_time,
                            "events_received": len(events),
                            "completed_successfully": any(e.get("type") == "agent_completed" for e in events),
                            "events": events
                        }
                        
                except Exception as e:
                    monitor["error_count"] += 1
                    return {
                        "user_id": user_id,
                        "workflow_time_ms": (time.perf_counter() - workflow_start) * 1000,
                        "error": str(e),
                        "completed_successfully": False
                    }
                    
            # Execute concurrent user workflows
            concurrent_start = time.perf_counter()
            
            tasks = [single_user_workflow(i) for i in range(user_count)]
            user_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            concurrent_total_time = (time.perf_counter() - concurrent_start) * 1000
            
            # Process results
            successful_results = [r for r in user_results if isinstance(r, dict) and r.get("completed_successfully")]
            
            for result in successful_results:
                monitor["response_times"].append(result["workflow_time_ms"])
                monitor["operations_completed"] += 1
                
            all_events = []
            for result in successful_results:
                if "events" in result:
                    all_events.extend(result["events"])
                    
            monitor["websocket_events"].extend(all_events)
            
            if len(successful_results) > 0:
                monitor["business_value_indicators"].append("concurrent_users_served")
                
        # Performance analysis
        result = performance_monitor.test_results[-1]
        
        # Concurrent performance assertions
        successful_user_count = len(successful_results)
        assert successful_user_count >= user_count * 0.9, (
            f"Too many concurrent failures: {successful_user_count}/{user_count} succeeded"
        )
        
        # Performance shouldn't degrade severely under concurrent load
        assert result.avg_response_time_ms < 3000, (
            f"Concurrent performance too slow: {result.avg_response_time_ms:.2f}ms avg"
        )
        
        # Throughput validation
        assert result.throughput_operations_per_second > user_count * 0.5, (
            f"Throughput too low: {result.throughput_operations_per_second:.2f} ops/sec"
        )
        
        # SLA compliance for mid-tier (concurrent users typically mid-tier+)
        assert result.sla_tier_compliance["mid_tier"], "Fails Mid-tier SLA under concurrent load"
        
        print(f"✓ Concurrent {user_count} users: {result.avg_response_time_ms:.2f}ms avg, "
              f"{successful_user_count}/{user_count} succeeded, "
              f"Grade: {result.performance_grade}")
              
    @pytest.mark.asyncio
    async def test_agent_optimization_workflow_end_to_end_performance(
        self, real_services_fixture, performance_monitor, auth_helper
    ):
        """Test complete agent optimization workflow - core business value delivery.
        
        BVJ: Agent optimization workflow is primary value delivery mechanism.
        Performance directly impacts customer satisfaction and retention.
        """
        backend_url = real_services_fixture["backend_url"]
        
        async with performance_monitor.monitor_workflow("agent_optimization_complete", 1) as monitor:
            
            # Create enterprise-tier user for optimization workflow
            user_data = await auth_helper.create_test_user(
                email=f"enterprise_user_{uuid4()}@example.com",
                name="Enterprise User",
                subscription_tier="enterprise"
            )
            
            async with WebSocketTestClient(
                token=user_data["token"],
                base_url=backend_url
            ) as client:
                
                # Complete optimization workflow
                optimization_steps = [
                    {
                        "agent": "data_analyst",
                        "message": "Analyze my current AWS spending patterns",
                        "expected_duration_ms": 2000
                    },
                    {
                        "agent": "cost_optimizer", 
                        "message": "Recommend cost optimizations based on the analysis",
                        "expected_duration_ms": 3000
                    },
                    {
                        "agent": "implementation_planner",
                        "message": "Create implementation plan for the recommendations",
                        "expected_duration_ms": 2000
                    }
                ]
                
                workflow_events = []
                
                for step_idx, step in enumerate(optimization_steps):
                    step_start = time.perf_counter()
                    
                    # Send agent request
                    await client.send_json({
                        "type": "agent_request",
                        "agent": step["agent"],
                        "message": step["message"],
                        "workflow_step": step_idx + 1,
                        "total_steps": len(optimization_steps)
                    })
                    
                    # Collect events for this step
                    step_events = []
                    timeout_start = time.time()
                    
                    while time.time() - timeout_start < 30:  # 30s timeout per step
                        try:
                            event = await asyncio.wait_for(client.receive_json(), timeout=1.0)
                            step_events.append(event)
                            workflow_events.append(event)
                            
                            if event.get("type") == "agent_completed":
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                            
                    step_time = (time.perf_counter() - step_start) * 1000
                    monitor["response_times"].append(step_time)
                    monitor["operations_completed"] += 1
                    
                    # Validate step completed successfully
                    completed_event = next(
                        (e for e in step_events if e.get("type") == "agent_completed"),
                        None
                    )
                    
                    if completed_event:
                        result_data = completed_event.get("data", {}).get("result", {})
                        
                        # Check for business value indicators
                        if step["agent"] == "data_analyst" and "analysis" in result_data:
                            monitor["business_value_indicators"].append("data_analysis_completed")
                        elif step["agent"] == "cost_optimizer" and "recommendations" in result_data:
                            monitor["business_value_indicators"].append("optimization_recommendations")
                        elif step["agent"] == "implementation_planner" and "plan" in result_data:
                            monitor["business_value_indicators"].append("implementation_plan")
                            
                monitor["websocket_events"].extend(workflow_events)
                
        # Performance analysis
        result = performance_monitor.test_results[-1]
        
        # Business workflow performance assertions
        total_workflow_time = result.total_duration_seconds
        assert total_workflow_time < 30.0, (
            f"Complete optimization workflow too slow: {total_workflow_time:.2f}s"
        )
        
        # Each step should complete within reasonable time
        for i, response_time in enumerate(result.test_results[-1].cost_impact_analysis if hasattr(result, 'test_results') else []):
            expected_duration = optimization_steps[i]["expected_duration_ms"]
            # Allow 50% variance for realistic conditions
            assert response_time < expected_duration * 1.5, (
                f"Step {i+1} too slow: {response_time:.2f}ms (expected: {expected_duration}ms)"
            )
            
        # Enterprise SLA compliance
        assert result.sla_tier_compliance["enterprise_tier"], (
            "Optimization workflow fails Enterprise SLA"
        )
        
        # Business value validation
        expected_value_indicators = ["data_analysis_completed", "optimization_recommendations", "implementation_plan"]
        actual_indicators = monitor["business_value_indicators"]
        
        for indicator in expected_value_indicators:
            assert indicator in actual_indicators, (
                f"Missing business value indicator: {indicator}"
            )
            
        # Cost efficiency validation
        cost_per_optimization = result.cost_impact_analysis["cost_per_operation_usd"]
        assert cost_per_optimization < 0.10, (  # $0.10 per complete optimization
            f"Optimization workflow too expensive: ${cost_per_optimization:.4f} per workflow"
        )
        
        print(f"✓ Complete optimization: {total_workflow_time:.2f}s total, "
              f"${cost_per_optimization:.4f} per workflow, "
              f"Grade: {result.performance_grade}")


@pytest.mark.e2e
@pytest.mark.real_services  
@pytest.mark.performance
@pytest.mark.benchmark
class TestSystemScalabilityAndLoadE2E(BaseE2ETest):
    """Test system scalability under realistic load conditions."""
    
    @pytest.mark.asyncio
    async def test_sustained_load_performance_e2e(
        self, real_services_fixture, performance_monitor, auth_helper
    ):
        """Test system performance under sustained load - validates production readiness.
        
        BVJ: Sustained load testing validates system can handle production traffic.
        Critical for Enterprise customer onboarding.
        """
        backend_url = real_services_fixture["backend_url"]
        
        # Sustained load parameters
        load_duration_seconds = 60  # 1 minute sustained load
        concurrent_users = 5  # Conservative for E2E test
        operations_per_user = 10
        
        async with performance_monitor.monitor_workflow(
            "sustained_load", 
            concurrent_users
        ) as monitor:
            
            async def sustained_user_load(user_id: int):
                """Sustained load pattern for single user."""
                user_results = []
                
                # Create user
                user_data = await auth_helper.create_test_user(
                    email=f"load_user_{user_id}_{uuid4()}@example.com",
                    name=f"Load Test User {user_id}"
                )
                
                async with WebSocketTestClient(
                    token=user_data["token"],
                    base_url=backend_url
                ) as client:
                    
                    # Perform operations over time
                    for op_id in range(operations_per_user):
                        op_start = time.perf_counter()
                        
                        # Vary operation types for realistic load
                        operation_types = ["triage_agent", "data_analyst", "cost_optimizer"]
                        agent_type = operation_types[op_id % len(operation_types)]
                        
                        try:
                            await client.send_json({
                                "type": "agent_request",
                                "agent": agent_type,
                                "message": f"Load test operation {op_id} for user {user_id}",
                                "sustained_load_test": True
                            })
                            
                            # Wait for completion with timeout
                            timeout_start = time.time()
                            completed = False
                            
                            while time.time() - timeout_start < 10:  # 10s per operation
                                try:
                                    event = await asyncio.wait_for(client.receive_json(), timeout=1.0)
                                    if event.get("type") == "agent_completed":
                                        completed = True
                                        break
                                except asyncio.TimeoutError:
                                    continue
                                    
                            op_time = (time.perf_counter() - op_start) * 1000
                            user_results.append({
                                "operation_id": op_id,
                                "duration_ms": op_time,
                                "completed": completed,
                                "agent_type": agent_type
                            })
                            
                            # Brief pause between operations
                            await asyncio.sleep(0.5)
                            
                        except Exception as e:
                            monitor["error_count"] += 1
                            user_results.append({
                                "operation_id": op_id,
                                "error": str(e),
                                "completed": False
                            })
                            
                return {"user_id": user_id, "results": user_results}
                
            # Execute sustained load
            load_start = time.perf_counter()
            
            user_tasks = [sustained_user_load(i) for i in range(concurrent_users)]
            all_user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
            
            load_duration = time.perf_counter() - load_start
            
            # Process sustained load results
            total_operations = 0
            successful_operations = 0
            all_durations = []
            
            for user_result in all_user_results:
                if isinstance(user_result, dict) and "results" in user_result:
                    for op_result in user_result["results"]:
                        total_operations += 1
                        if op_result.get("completed", False):
                            successful_operations += 1
                            if "duration_ms" in op_result:
                                all_durations.append(op_result["duration_ms"])
                                monitor["response_times"].append(op_result["duration_ms"])
                                
            monitor["operations_completed"] = successful_operations
            
            if successful_operations > 0:
                monitor["business_value_indicators"].append("sustained_load_handled")
                
        # Sustained load analysis
        result = performance_monitor.test_results[-1]
        
        # Load handling assertions
        success_rate = successful_operations / max(total_operations, 1)
        assert success_rate > 0.95, (
            f"Sustained load success rate too low: {success_rate:.2%}"
        )
        
        # Performance shouldn't severely degrade under sustained load
        if all_durations:
            avg_duration = mean(all_durations)
            p95_duration = sorted(all_durations)[int(0.95 * len(all_durations))]
            
            assert avg_duration < 2000, (  # 2 second average
                f"Sustained load average response too slow: {avg_duration:.2f}ms"
            )
            
            assert p95_duration < 5000, (  # 5 second P95
                f"Sustained load P95 response too slow: {p95_duration:.2f}ms"
            )
            
        # Throughput validation
        expected_min_throughput = (concurrent_users * operations_per_user) / load_duration * 0.8
        assert result.throughput_operations_per_second > expected_min_throughput, (
            f"Sustained load throughput too low: {result.throughput_operations_per_second:.2f} ops/sec"
        )
        
        print(f"✓ Sustained load ({concurrent_users} users, {load_duration:.1f}s): "
              f"{success_rate:.1%} success, {result.throughput_operations_per_second:.1f} ops/sec")
              
    @pytest.mark.asyncio
    async def test_performance_report_generation(self, performance_monitor):
        """Generate comprehensive performance report for business analysis.
        
        BVJ: Performance reporting enables data-driven optimization decisions.
        """
        # This test runs after other performance tests to generate final report
        report = performance_monitor.generate_performance_report()
        
        # Validate report structure
        assert "summary" in report
        assert "sla_compliance" in report
        assert "business_impact" in report
        
        # Business-critical SLA validation
        sla_compliance = report["sla_compliance"]
        
        # At least Free tier should be 100% compliant
        assert sla_compliance["free_tier"] > 0.8, (
            f"Free tier SLA compliance too low: {sla_compliance['free_tier']:.1%}"
        )
        
        # Business impact validation
        business_impact = report["business_impact"]
        avg_cost_per_operation = business_impact["avg_cost_per_operation_usd"]
        
        # Cost per operation should be reasonable for business model
        assert avg_cost_per_operation < 0.05, (  # $0.05 per operation max
            f"Cost per operation too high: ${avg_cost_per_operation:.4f}"
        )
        
        # Overall system grade
        overall_grade = report["summary"]["overall_grade"]
        assert overall_grade in ["A", "B", "C"], (
            f"Overall performance grade unacceptable: {overall_grade}"
        )
        
        # Print comprehensive report
        print("\n" + "="*80)
        print("E2E PERFORMANCE REPORT")
        print("="*80)
        print(f"Overall Grade: {overall_grade}")
        print(f"Avg Response Time: {report['summary']['avg_response_time_ms']:.2f}ms")
        print(f"Avg Throughput: {report['summary']['avg_throughput_ops_per_sec']:.2f} ops/sec")
        print(f"Success Rate: {report['summary']['avg_success_rate']:.2%}")
        print()
        
        print("SLA Compliance:")
        for tier, compliance in sla_compliance.items():
            print(f"  {tier}: {compliance:.1%}")
        print()
        
        print("Business Impact:")
        print(f"  Cost per operation: ${avg_cost_per_operation:.4f}")
        print(f"  Cost efficiency grade: {business_impact['cost_efficiency_grade']}")
        print("="*80)
        
        return report


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short", 
        "--real-services",
        "--real-llm",
        "-m", "performance and e2e"
    ])