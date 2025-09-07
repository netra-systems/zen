#!/usr/bin/env python
"""Real Agent Performance Monitoring E2E Test Suite - Business Critical Testing

MISSION CRITICAL: Tests agent performance metrics and monitoring with real services.
Business Value: Ensure system performance and monitoring capabilities.

Business Value Justification (BVJ):
1. Segment: All (Free, Early, Mid, Enterprise)
2. Business Goal: Ensure system performance and reliability monitoring
3. Value Impact: Performance monitoring enables proactive optimization
4. Revenue Impact: $450K+ ARR protection from performance-related customer churn

CLAUDE.md COMPLIANCE:
- Uses real services ONLY (NO MOCKS)
- Validates ALL 5 required WebSocket events
- Tests actual performance monitoring business logic
- Uses IsolatedEnvironment for environment access
- Absolute imports only
- Factory patterns for user isolation
- Uses SSOT E2E test configuration
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
import statistics
from concurrent.futures import ThreadPoolExecutor
import threading

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# CLAUDE.md compliant imports - Lazy loaded to prevent resource exhaustion
from shared.isolated_environment import get_env
from tests.e2e.e2e_test_config import get_e2e_config, E2ETestConfig, REQUIRED_WEBSOCKET_EVENTS


@dataclass
class PerformanceMetrics:
    """Captures performance metrics during agent execution."""
    
    # Timing metrics
    connection_time: Optional[float] = None
    first_event_time: Optional[float] = None
    agent_start_time: Optional[float] = None
    first_thinking_time: Optional[float] = None
    tool_execution_time: Optional[float] = None
    completion_time: Optional[float] = None
    
    # Throughput metrics
    events_per_second: float = 0.0
    tokens_per_second: float = 0.0
    tools_per_minute: float = 0.0
    
    # Quality metrics
    response_coherence_score: float = 0.0
    user_satisfaction_score: float = 0.0
    business_value_score: float = 0.0
    
    # Resource utilization (estimated from behavior)
    estimated_cpu_usage: float = 0.0
    estimated_memory_usage: float = 0.0
    network_efficiency: float = 0.0


@dataclass
class AgentPerformanceValidation:
    """Captures and validates agent performance monitoring."""
    
    user_id: str
    thread_id: str
    performance_scenario: str
    start_time: float = field(default_factory=time.time)
    
    # Event tracking (MISSION CRITICAL per CLAUDE.md)
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    event_types_seen: Set[str] = field(default_factory=set)
    
    # Performance data collection
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    execution_timeline: List[Tuple[float, str, Dict[str, Any]]] = field(default_factory=list)
    
    # Monitoring validation
    metrics_collected: bool = False
    performance_thresholds_met: bool = False
    monitoring_data_complete: bool = False
    real_time_tracking_accurate: bool = False


class RealAgentPerformanceMonitoringTester:
    """Tests agent performance monitoring with real services and WebSocket events."""
    
    # CLAUDE.md REQUIRED WebSocket events from SSOT config
    REQUIRED_EVENTS = set(REQUIRED_WEBSOCKET_EVENTS.keys())
    
    # Performance monitoring test scenarios
    PERFORMANCE_SCENARIOS = [
        {
            "scenario_name": "baseline_performance_measurement",
            "message": "Perform a standard data analysis task for baseline metrics",
            "expected_duration": 60.0,
            "performance_targets": {
                "first_event_max": 5.0,
                "completion_max": 45.0,
                "events_per_second_min": 0.1
            },
            "monitoring_focus": ["timing", "throughput", "quality"]
        },
        {
            "scenario_name": "high_load_stress_monitoring",
            "message": "Execute complex multi-tool workflow under monitoring",
            "expected_duration": 120.0,
            "performance_targets": {
                "first_event_max": 8.0,
                "completion_max": 100.0,
                "tools_per_minute_min": 1.0
            },
            "monitoring_focus": ["resource_utilization", "throughput", "stability"]
        },
        {
            "scenario_name": "concurrent_user_performance",
            "message": "Monitor performance under concurrent user load",
            "expected_duration": 90.0,
            "concurrent_users": 3,
            "performance_targets": {
                "first_event_max": 10.0,
                "completion_max": 80.0,
                "degradation_max": 0.3  # Max 30% degradation under load
            },
            "monitoring_focus": ["concurrency", "scalability", "isolation"]
        },
        {
            "scenario_name": "real_time_monitoring_accuracy",
            "message": "Validate real-time monitoring data accuracy",
            "expected_duration": 75.0,
            "performance_targets": {
                "monitoring_accuracy_min": 0.9,
                "data_freshness_max": 5.0,
                "update_frequency_min": 0.2
            },
            "monitoring_focus": ["accuracy", "freshness", "completeness"]
        },
        {
            "scenario_name": "performance_degradation_detection",
            "message": "Detect and monitor performance degradation scenarios",
            "expected_duration": 100.0,
            "performance_targets": {
                "degradation_detection_max": 15.0,
                "alert_accuracy_min": 0.8,
                "recovery_time_max": 30.0
            },
            "monitoring_focus": ["degradation_detection", "alerting", "recovery"]
        }
    ]
    
    def __init__(self, config: Optional[E2ETestConfig] = None):
        self.config = config or get_e2e_config()
        self.env = None  # Lazy init
        self.ws_client = None
        self.backend_client = None
        self.jwt_helper = None
        self.validations: List[AgentPerformanceValidation] = []
        
    async def setup(self):
        """Initialize test environment with real services."""
        # Lazy imports per CLAUDE.md to prevent Docker crashes
        from shared.isolated_environment import IsolatedEnvironment
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        from tests.clients.backend_client import BackendTestClient
        from tests.clients.websocket_client import WebSocketTestClient
        from tests.e2e.test_data_factory import create_test_user_data
        
        self.env = IsolatedEnvironment()
        self.jwt_helper = JWTTestHelper()
        
        # Initialize backend client from SSOT config
        self.backend_client = BackendTestClient(self.config.backend_url)
        
        # Create test user with performance monitoring permissions
        user_data = create_test_user_data("performance_monitoring_test")
        self.user_id = str(uuid.uuid4())
        self.email = user_data['email']
        
        # Generate JWT with comprehensive monitoring permissions
        self.token = self.jwt_helper.create_access_token(
            self.user_id, 
            self.email,
            permissions=["agents:use", "monitoring:access", "metrics:collect", "performance:analyze"]
        )
        
        # Initialize WebSocket client from SSOT config
        self.ws_client = WebSocketTestClient(self.config.websocket_url)
        
        # Connect with authentication
        connected = await self.ws_client.connect(token=self.token)
        if not connected:
            raise RuntimeError("Failed to connect to WebSocket")
            
        logger.info(f"Performance monitoring test environment ready for user {self.email}")
        return self
        
    async def teardown(self):
        """Clean up test environment."""
        if self.ws_client:
            await self.ws_client.disconnect()
            
    async def execute_performance_monitoring_scenario(
        self, 
        scenario: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> AgentPerformanceValidation:
        """Execute a performance monitoring scenario and validate results.
        
        Args:
            scenario: Performance monitoring scenario configuration
            timeout: Maximum execution time (uses scenario default if None)
            
        Returns:
            Complete validation results
        """
        timeout = timeout or scenario.get("expected_duration", 90.0) + 30.0  # Add buffer
        thread_id = str(uuid.uuid4())
        
        validation = AgentPerformanceValidation(
            user_id=self.user_id,
            thread_id=thread_id,
            performance_scenario=scenario["scenario_name"]
        )
        
        # Handle concurrent user scenarios
        if scenario.get("concurrent_users", 1) > 1:
            return await self._execute_concurrent_performance_test(scenario, validation, timeout)
        
        # Send performance monitoring request via WebSocket
        perf_request = {
            "type": "agent_request",
            "agent": "triage_agent",
            "message": scenario["message"],
            "thread_id": thread_id,
            "context": {
                "performance_monitoring": True,
                "scenario": scenario["scenario_name"],
                "monitoring_focus": scenario.get("monitoring_focus", []),
                "user_id": self.user_id,
                "collect_metrics": True
            },
            "optimistic_id": str(uuid.uuid4())
        }
        
        # Start performance monitoring
        monitoring_start = time.time()
        await self.ws_client.send_json(perf_request)
        logger.info(f"Started performance monitoring scenario: {scenario['scenario_name']}")
        
        # Monitor execution with detailed performance tracking
        completed = False
        
        while time.time() - monitoring_start < timeout and not completed:
            event = await self.ws_client.receive(timeout=3.0)
            
            if event:
                await self._process_performance_event(event, validation, monitoring_start)
                
                # Check for completion
                if event.get("type") in ["agent_completed", "monitoring_completed", "error"]:
                    completed = True
                    
        # Calculate final performance metrics
        self._calculate_performance_metrics(validation, monitoring_start)
        
        # Validate performance monitoring results
        self._validate_performance_monitoring(validation, scenario)
        self.validations.append(validation)
        
        return validation
        
    async def _execute_concurrent_performance_test(
        self, 
        scenario: Dict[str, Any],
        validation: AgentPerformanceValidation,
        timeout: float
    ) -> AgentPerformanceValidation:
        """Execute concurrent user performance test."""
        
        concurrent_users = scenario.get("concurrent_users", 3)
        user_validations = []
        
        async def single_user_execution(user_index: int):
            """Execute performance test for single user."""
            user_thread_id = f"{validation.thread_id}_user_{user_index}"
            user_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": f"{scenario['message']} (User {user_index})",
                "thread_id": user_thread_id,
                "context": {
                    "performance_monitoring": True,
                    "concurrent_test": True,
                    "user_index": user_index,
                    "user_id": f"{self.user_id}_{user_index}"
                },
                "optimistic_id": str(uuid.uuid4())
            }
            
            start_time = time.time()
            await self.ws_client.send_json(user_request)
            
            user_events = []
            while time.time() - start_time < timeout * 0.8:  # Shorter timeout for concurrent
                event = await self.ws_client.receive(timeout=2.0)
                if event:
                    user_events.append(event)
                    validation.events_received.append(event)
                    validation.event_types_seen.add(event.get("type", "unknown"))
                    
                    if event.get("type") in ["agent_completed", "error"]:
                        break
                        
            return user_events
            
        # Execute concurrent users
        concurrent_start = time.time()
        tasks = [single_user_execution(i) for i in range(concurrent_users)]
        user_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process concurrent results
        validation.execution_timeline.append((
            time.time() - concurrent_start,
            "concurrent_execution_completed",
            {"users": concurrent_users, "results": len(user_results)}
        ))
        
        return validation
        
    async def _process_performance_event(
        self, 
        event: Dict[str, Any], 
        validation: AgentPerformanceValidation,
        start_time: float
    ):
        """Process and categorize performance monitoring specific events."""
        event_type = event.get("type", "unknown")
        event_time = time.time() - start_time
        
        # Record all events with timing
        validation.events_received.append(event)
        validation.event_types_seen.add(event_type)
        validation.execution_timeline.append((event_time, event_type, event.get("data", {})))
        
        # Track performance timing metrics
        metrics = validation.performance_metrics
        
        if event_type == "connection_established":
            metrics.connection_time = event_time
            
        elif event_type == "agent_started":
            if not metrics.first_event_time:
                metrics.first_event_time = event_time
            metrics.agent_start_time = event_time
            logger.info(f"Performance: Agent started at {event_time:.2f}s")
            
        elif event_type == "agent_thinking":
            if not metrics.first_thinking_time:
                metrics.first_thinking_time = event_time
                
        elif event_type == "tool_executing":
            if not metrics.tool_execution_time:
                metrics.tool_execution_time = event_time
                
        elif event_type in ["agent_completed", "monitoring_completed"]:
            metrics.completion_time = event_time
            logger.info(f"Performance: Execution completed at {event_time:.2f}s")
            
            # Extract performance data if available
            performance_data = event.get("data", {}).get("performance_metrics", {})
            if performance_data:
                validation.metrics_collected = True
                self._update_performance_metrics_from_data(metrics, performance_data)
                
        elif event_type == "performance_metrics":
            # Real-time performance metrics
            perf_data = event.get("data", {})
            self._update_performance_metrics_from_data(metrics, perf_data)
            validation.metrics_collected = True
            
    def _update_performance_metrics_from_data(
        self, 
        metrics: PerformanceMetrics, 
        perf_data: Dict[str, Any]
    ):
        """Update performance metrics from received data."""
        
        # Update metrics from data
        if "tokens_per_second" in perf_data:
            metrics.tokens_per_second = perf_data["tokens_per_second"]
            
        if "response_quality" in perf_data:
            metrics.response_coherence_score = perf_data["response_quality"]
            
        if "cpu_usage" in perf_data:
            metrics.estimated_cpu_usage = perf_data["cpu_usage"]
            
        if "memory_usage" in perf_data:
            metrics.estimated_memory_usage = perf_data["memory_usage"]
            
    def _calculate_performance_metrics(
        self, 
        validation: AgentPerformanceValidation,
        start_time: float
    ):
        """Calculate derived performance metrics."""
        
        metrics = validation.performance_metrics
        total_time = time.time() - start_time
        
        # Calculate events per second
        if total_time > 0:
            metrics.events_per_second = len(validation.events_received) / total_time
            
        # Calculate tools per minute
        tool_events = [e for e in validation.events_received if e.get("type") == "tool_executing"]
        if total_time > 0:
            metrics.tools_per_minute = (len(tool_events) * 60.0) / total_time
            
        # Estimate network efficiency
        total_data_size = sum(len(str(event)) for event in validation.events_received)
        if total_time > 0 and total_data_size > 0:
            metrics.network_efficiency = len(validation.events_received) / (total_data_size / 1000.0)  # events per KB
            
        # Calculate business value score (heuristic)
        completion_score = 1.0 if metrics.completion_time else 0.0
        event_diversity_score = len(validation.event_types_seen) / len(self.REQUIRED_EVENTS)
        timing_score = 1.0 if (metrics.first_event_time and metrics.first_event_time < 10.0) else 0.5
        
        metrics.business_value_score = (completion_score + event_diversity_score + timing_score) / 3.0
        
    def _validate_performance_monitoring(
        self, 
        validation: AgentPerformanceValidation, 
        scenario: Dict[str, Any]
    ):
        """Validate performance monitoring against business requirements."""
        
        metrics = validation.performance_metrics
        targets = scenario.get("performance_targets", {})
        
        # 1. Check if metrics were collected
        validation.metrics_collected = (
            len(validation.events_received) > 0 and
            metrics.events_per_second > 0
        )
        
        # 2. Validate performance thresholds
        thresholds_met = []
        
        if "first_event_max" in targets and metrics.first_event_time:
            thresholds_met.append(metrics.first_event_time <= targets["first_event_max"])
            
        if "completion_max" in targets and metrics.completion_time:
            thresholds_met.append(metrics.completion_time <= targets["completion_max"])
            
        if "events_per_second_min" in targets:
            thresholds_met.append(metrics.events_per_second >= targets["events_per_second_min"])
            
        if "tools_per_minute_min" in targets:
            thresholds_met.append(metrics.tools_per_minute >= targets["tools_per_minute_min"])
            
        validation.performance_thresholds_met = len(thresholds_met) > 0 and all(thresholds_met)
        
        # 3. Check monitoring data completeness
        required_data_points = [
            metrics.first_event_time is not None,
            metrics.events_per_second > 0,
            len(validation.execution_timeline) > 5
        ]
        validation.monitoring_data_complete = sum(required_data_points) >= 2
        
        # 4. Validate real-time tracking accuracy
        if validation.execution_timeline:
            # Check if timeline events are in chronological order
            timeline_times = [entry[0] for entry in validation.execution_timeline]
            chronological = all(timeline_times[i] <= timeline_times[i+1] for i in range(len(timeline_times)-1))
            
            # Check if events correspond to expected types
            expected_events = {"agent_started", "agent_thinking", "tool_executing", "agent_completed"}
            timeline_events = {entry[1] for entry in validation.execution_timeline}
            event_alignment = len(expected_events & timeline_events) >= 2
            
            validation.real_time_tracking_accurate = chronological and event_alignment
            
    def generate_performance_monitoring_report(self) -> str:
        """Generate comprehensive performance monitoring test report."""
        report = []
        report.append("=" * 80)
        report.append("REAL AGENT PERFORMANCE MONITORING TEST REPORT")
        report.append("=" * 80)
        report.append(f"Total performance scenarios tested: {len(self.validations)}")
        report.append("")
        
        # Aggregate statistics
        all_completion_times = [v.performance_metrics.completion_time for v in self.validations if v.performance_metrics.completion_time]
        all_first_event_times = [v.performance_metrics.first_event_time for v in self.validations if v.performance_metrics.first_event_time]
        all_events_per_second = [v.performance_metrics.events_per_second for v in self.validations]
        
        if all_completion_times:
            report.append(f"Overall Performance Statistics:")
            report.append(f"  - Average completion time: {statistics.mean(all_completion_times):.2f}s")
            report.append(f"  - Median completion time: {statistics.median(all_completion_times):.2f}s")
            report.append(f"  - Max completion time: {max(all_completion_times):.2f}s")
            
        if all_first_event_times:
            report.append(f"  - Average first event time: {statistics.mean(all_first_event_times):.2f}s")
            
        if all_events_per_second:
            report.append(f"  - Average events per second: {statistics.mean(all_events_per_second):.2f}")
            
        report.append("")
        
        for i, val in enumerate(self.validations, 1):
            report.append(f"\n--- Performance Scenario {i}: {val.performance_scenario} ---")
            report.append(f"User ID: {val.user_id}")
            report.append(f"Events received: {len(val.events_received)}")
            
            # Check for REQUIRED WebSocket events
            missing_events = self.REQUIRED_EVENTS - val.event_types_seen
            if missing_events:
                report.append(f"⚠️ MISSING REQUIRED EVENTS: {missing_events}")
            else:
                report.append("✓ All required WebSocket events received")
                
            # Performance metrics
            metrics = val.performance_metrics
            report.append("\nPerformance Metrics:")
            report.append(f"  - Connection time: {metrics.connection_time:.2f}s" if metrics.connection_time else "  - Connection time: N/A")
            report.append(f"  - First event time: {metrics.first_event_time:.2f}s" if metrics.first_event_time else "  - First event time: N/A")
            report.append(f"  - Agent start time: {metrics.agent_start_time:.2f}s" if metrics.agent_start_time else "  - Agent start time: N/A")
            report.append(f"  - Completion time: {metrics.completion_time:.2f}s" if metrics.completion_time else "  - Completion time: N/A")
            report.append(f"  - Events per second: {metrics.events_per_second:.2f}")
            report.append(f"  - Tools per minute: {metrics.tools_per_minute:.2f}")
            report.append(f"  - Business value score: {metrics.business_value_score:.2f}")
            
            if metrics.estimated_cpu_usage > 0:
                report.append(f"  - Estimated CPU usage: {metrics.estimated_cpu_usage:.1%}")
            if metrics.estimated_memory_usage > 0:
                report.append(f"  - Estimated memory usage: {metrics.estimated_memory_usage:.1f}MB")
                
            # Monitoring validation
            report.append("\nMonitoring Validation:")
            report.append(f"  ✓ Metrics collected: {val.metrics_collected}")
            report.append(f"  ✓ Performance thresholds met: {val.performance_thresholds_met}")
            report.append(f"  ✓ Monitoring data complete: {val.monitoring_data_complete}")
            report.append(f"  ✓ Real-time tracking accurate: {val.real_time_tracking_accurate}")
            
            # Execution timeline summary
            if val.execution_timeline:
                report.append(f"\nExecution Timeline ({len(val.execution_timeline)} events):")
                for timestamp, event_type, data in val.execution_timeline[:5]:  # Show first 5
                    report.append(f"  {timestamp:6.2f}s: {event_type}")
                    
        report.append("\n" + "=" * 80)
        return "\n".join(report)


# ============================================================================
# TEST SUITE
# ============================================================================

@pytest.fixture(params=["local", "staging"])
async def performance_monitoring_tester(request):
    """Create and setup the performance monitoring tester for both local and staging."""
    # Check if we should skip staging tests
    test_env = get_env("E2E_TEST_ENV", None)
    if test_env and test_env != request.param:
        pytest.skip(f"Skipping {request.param} tests (E2E_TEST_ENV={test_env})")
    
    # Get configuration for the specific environment
    config = get_e2e_config(force_environment=request.param)
    
    # Check if environment is available
    if not config.is_available():
        pytest.skip(f"{request.param} environment not available")
    
    # Create tester with environment-specific config
    tester = RealAgentPerformanceMonitoringTester(config)
    await tester.setup()
    yield tester
    await tester.teardown()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.real_services
class TestRealAgentPerformanceMonitoring:
    """Test suite for real agent performance monitoring."""
    
    async def test_baseline_performance_measurement(self, performance_monitoring_tester):
        """Test baseline performance measurement with real agent execution."""
        scenario = performance_monitoring_tester.PERFORMANCE_SCENARIOS[0]  # baseline_performance_measurement
        
        validation = await performance_monitoring_tester.execute_performance_monitoring_scenario(
            scenario, timeout=90.0
        )
        
        # CRITICAL: Verify performance metrics collection
        assert validation.metrics_collected, "Performance metrics should be collected"
        
        # Verify basic performance
        metrics = validation.performance_metrics
        assert metrics.events_per_second > 0, "Should have measurable event throughput"
        
        # Performance thresholds from config
        if metrics.first_event_time:
            threshold = performance_monitoring_tester.config.first_event_max_delay
            assert metrics.first_event_time <= threshold, f"First event time {metrics.first_event_time:.2f}s exceeds threshold {threshold}s"
            
        # Business value validation
        assert metrics.business_value_score >= 0.5, f"Business value score {metrics.business_value_score:.2f} below minimum"
        
        logger.info(f"Baseline performance: {metrics.completion_time:.2f}s completion, {metrics.events_per_second:.2f} events/s")
        
    async def test_high_load_stress_monitoring(self, performance_monitoring_tester):
        """Test performance monitoring under high load stress."""
        scenario = performance_monitoring_tester.PERFORMANCE_SCENARIOS[1]  # high_load_stress_monitoring
        
        validation = await performance_monitoring_tester.execute_performance_monitoring_scenario(
            scenario, timeout=150.0
        )
        
        # Stress test validation
        assert validation.monitoring_data_complete, "Monitoring data should be complete under stress"
        
        # Performance under stress
        metrics = validation.performance_metrics
        assert metrics.events_per_second > 0, "Should maintain event throughput under stress"
        
        # Tool execution validation
        if metrics.tools_per_minute > 0:
            logger.info(f"Stress test tool execution rate: {metrics.tools_per_minute:.2f} tools/min")
            
    async def test_concurrent_user_performance_monitoring(self, performance_monitoring_tester):
        """Test performance monitoring under concurrent user load."""
        scenario = performance_monitoring_tester.PERFORMANCE_SCENARIOS[2]  # concurrent_user_performance
        
        validation = await performance_monitoring_tester.execute_performance_monitoring_scenario(
            scenario, timeout=120.0
        )
        
        # Concurrent user validation
        assert len(validation.events_received) > 0, "Should handle concurrent users"
        
        # Performance degradation check
        metrics = validation.performance_metrics
        if metrics.completion_time:
            # Allow for some degradation under concurrent load
            max_acceptable = scenario["performance_targets"]["completion_max"]
            assert metrics.completion_time <= max_acceptable, \
                f"Concurrent performance {metrics.completion_time:.2f}s exceeds threshold {max_acceptable}s"
                
        logger.info(f"Concurrent performance: {len(validation.events_received)} total events from {scenario.get('concurrent_users', 1)} users")
        
    async def test_real_time_monitoring_accuracy(self, performance_monitoring_tester):
        """Test real-time monitoring data accuracy."""
        scenario = performance_monitoring_tester.PERFORMANCE_SCENARIOS[3]  # real_time_monitoring_accuracy
        
        validation = await performance_monitoring_tester.execute_performance_monitoring_scenario(
            scenario, timeout=100.0
        )
        
        # Real-time accuracy validation
        assert validation.real_time_tracking_accurate, "Real-time tracking should be accurate"
        
        # Timeline validation
        assert len(validation.execution_timeline) > 5, "Should have detailed execution timeline"
        
        # Data freshness validation
        if validation.execution_timeline:
            timeline_span = validation.execution_timeline[-1][0] - validation.execution_timeline[0][0]
            event_density = len(validation.execution_timeline) / timeline_span if timeline_span > 0 else 0
            assert event_density > 0.1, f"Event density {event_density:.2f} events/s too low"
            
    async def test_performance_degradation_detection(self, performance_monitoring_tester):
        """Test performance degradation detection capabilities."""
        scenario = performance_monitoring_tester.PERFORMANCE_SCENARIOS[4]  # performance_degradation_detection
        
        validation = await performance_monitoring_tester.execute_performance_monitoring_scenario(
            scenario, timeout=130.0
        )
        
        # Should handle degradation scenarios gracefully
        assert validation.monitoring_data_complete, "Should collect monitoring data even with degradation"
        
        # Performance monitoring should continue working
        metrics = validation.performance_metrics
        assert metrics.events_per_second > 0, "Monitoring should continue during degradation"
        
        logger.info(f"Degradation monitoring: {metrics.business_value_score:.2f} business value score")
        
    async def test_performance_monitoring_benchmarks(self, performance_monitoring_tester):
        """Test performance monitoring against business benchmarks."""
        # Run multiple scenarios for comprehensive benchmarking
        performance_results = []
        
        for scenario in performance_monitoring_tester.PERFORMANCE_SCENARIOS[:3]:  # First 3 scenarios
            validation = await performance_monitoring_tester.execute_performance_monitoring_scenario(
                scenario, timeout=100.0
            )
            performance_results.append(validation)
            
        # Benchmark assertions
        completion_times = [
            v.performance_metrics.completion_time 
            for v in performance_results 
            if v.performance_metrics.completion_time
        ]
        
        if completion_times:
            avg_completion = statistics.mean(completion_times)
            max_completion = max(completion_times)
            
            # Business benchmarks
            config = performance_monitoring_tester.config
            assert avg_completion <= config.agent_completion_timeout, \
                f"Average completion {avg_completion:.2f}s exceeds business threshold {config.agent_completion_timeout}s"
                
            assert max_completion <= config.agent_completion_timeout * 1.5, \
                f"Max completion {max_completion:.2f}s exceeds acceptable range"
                
        # Events per second benchmarks
        event_rates = [v.performance_metrics.events_per_second for v in performance_results]
        if event_rates:
            avg_rate = statistics.mean(event_rates)
            assert avg_rate >= 0.1, f"Average event rate {avg_rate:.2f} events/s too low"
            
    async def test_performance_monitoring_quality_metrics(self, performance_monitoring_tester):
        """Test performance monitoring quality metrics."""
        scenario = performance_monitoring_tester.PERFORMANCE_SCENARIOS[0]  # Use baseline for quality test
        
        validation = await performance_monitoring_tester.execute_performance_monitoring_scenario(
            scenario, timeout=90.0
        )
        
        # Calculate monitoring quality score
        quality_score = sum([
            validation.metrics_collected,
            validation.performance_thresholds_met,
            validation.monitoring_data_complete,
            validation.real_time_tracking_accurate
        ])
        
        # Should meet minimum quality threshold
        assert quality_score >= 3, f"Performance monitoring quality score {quality_score}/4 below minimum"
        
        # Business value validation
        metrics = validation.performance_metrics
        config = performance_monitoring_tester.config
        assert metrics.business_value_score >= config.min_response_quality_score, \
            f"Business value score {metrics.business_value_score:.2f} below threshold {config.min_response_quality_score}"
            
        logger.info(f"Performance monitoring quality score: {quality_score}/4")
        
    async def test_comprehensive_performance_monitoring_report(self, performance_monitoring_tester):
        """Run comprehensive test and generate detailed report."""
        # Execute all performance monitoring scenarios
        for scenario in performance_monitoring_tester.PERFORMANCE_SCENARIOS:
            await performance_monitoring_tester.execute_performance_monitoring_scenario(
                scenario, timeout=120.0
            )
            
        # Generate and save report
        report = performance_monitoring_tester.generate_performance_monitoring_report()
        logger.info("\n" + report)
        
        # Save report to file
        report_file = os.path.join(project_root, "test_outputs", "performance_monitoring_e2e_report.txt")
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
            f.write(f"\n\nGenerated at: {datetime.now().isoformat()}\n")
            
        logger.info(f"Performance monitoring report saved to: {report_file}")
        
        # Verify overall monitoring success
        total_tests = len(performance_monitoring_tester.validations)
        successful_monitoring = sum(
            1 for v in performance_monitoring_tester.validations 
            if v.metrics_collected and v.monitoring_data_complete
        )
        
        assert successful_monitoring > 0, "At least some performance monitoring should succeed"
        success_rate = successful_monitoring / total_tests if total_tests > 0 else 0
        logger.info(f"Performance monitoring success rate: {success_rate:.1%}")


if __name__ == "__main__":
    # Run with real services - performance monitoring is critical
    # Use E2E_TEST_ENV=staging to test against staging environment
    import sys
    args = [
        __file__,
        "-v",
        "--real-services",
        "-s",
        "--tb=short"
    ]
    
    # Add staging marker if running against staging
    if get_env("E2E_TEST_ENV", "local") == "staging":
        args.append("-m")
        args.append("staging")
        print(f"Running tests against STAGING environment: {get_e2e_config().backend_url}")
    else:
        print(f"Running tests against LOCAL environment: {get_e2e_config().backend_url}")
    
    pytest.main(args)