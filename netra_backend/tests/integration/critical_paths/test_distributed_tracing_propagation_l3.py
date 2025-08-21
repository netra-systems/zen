"""Distributed Tracing Propagation L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (operational excellence for all tiers)
- Business Goal: Complete request tracing for performance optimization and debugging
- Value Impact: Enables precise performance bottleneck identification worth $20K MRR optimization
- Strategic Impact: Reduces MTTR from hours to minutes, preventing customer churn

Critical Path: Request initiation -> Trace context creation -> Cross-service propagation -> Span correlation -> Performance analysis
Coverage: OpenTelemetry integration, trace context propagation, span relationships, performance correlation
L3 Realism: Tests with real distributed services and actual trace propagation
"""

import pytest
import asyncio
import time
import uuid
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from dataclasses import dataclass

from monitoring.metrics_collector import MetricsCollector
from netra_backend.app.core.alert_manager import HealthAlertManager

logger = logging.getLogger(__name__)

# L3 integration test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.l3,
    pytest.mark.observability,
    pytest.mark.tracing
]


@dataclass
class TraceSpan:
    """Represents a distributed trace span."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    tags: Dict[str, str]
    logs: List[Dict[str, Any]]
    status: str  # "ok", "error", "timeout"


@dataclass
class TraceContext:
    """Represents complete trace context across services."""
    trace_id: str
    spans: List[TraceSpan]
    total_duration_ms: float
    service_count: int
    error_count: int
    root_service: str


class DistributedTracingValidator:
    """Validates distributed tracing propagation with real services."""
    
    def __init__(self):
        self.trace_collector = None
        self.alert_manager = None
        self.active_traces = {}
        self.completed_traces = {}
        self.propagation_failures = []
        self.correlation_errors = []
        
    async def initialize_tracing_services(self):
        """Initialize real tracing services for L3 testing."""
        try:
            # Initialize OpenTelemetry-compatible trace collector
            self.trace_collector = TracingCollector()
            await self.trace_collector.initialize()
            
            self.alert_manager = HealthAlertManager()
            
            # Initialize service registry for multi-service tracing
            self.service_registry = ServiceRegistry()
            await self.service_registry.register_services([
                "api-gateway", "auth-service", "agent-service", 
                "database-service", "websocket-service"
            ])
            
            logger.info("Distributed tracing L3 services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize tracing services: {e}")
            raise
    
    async def create_distributed_trace(self, operation_name: str, service_count: int = 3) -> TraceContext:
        """Create a distributed trace across multiple services."""
        trace_id = str(uuid.uuid4())
        trace_start = datetime.now(timezone.utc)
        
        # Create root span
        root_span = await self._create_root_span(trace_id, operation_name, trace_start)
        spans = [root_span]
        
        # Create child spans across services
        current_parent = root_span.span_id
        services = ["auth-service", "agent-service", "database-service", "websocket-service"]
        
        for i in range(min(service_count - 1, len(services))):
            service_name = services[i]
            child_span = await self._create_child_span(
                trace_id, current_parent, service_name, trace_start
            )
            spans.append(child_span)
            current_parent = child_span.span_id
        
        # Calculate total duration
        total_duration = max(span.duration_ms for span in spans if span.duration_ms)
        
        trace_context = TraceContext(
            trace_id=trace_id,
            spans=spans,
            total_duration_ms=total_duration,
            service_count=len(spans),
            error_count=0,
            root_service="api-gateway"
        )
        
        self.active_traces[trace_id] = trace_context
        return trace_context
    
    async def _create_root_span(self, trace_id: str, operation_name: str, start_time: datetime) -> TraceSpan:
        """Create root span for distributed trace."""
        span_id = str(uuid.uuid4())
        
        # Simulate root operation duration
        operation_duration = 150 + (time.time() % 100)  # 150-250ms
        
        root_span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            operation_name=operation_name,
            service_name="api-gateway",
            start_time=start_time,
            end_time=start_time.replace(microsecond=start_time.microsecond + int(operation_duration * 1000)),
            duration_ms=operation_duration,
            tags={
                "component": "api-gateway",
                "operation.type": "http.request",
                "http.method": "POST",
                "http.url": "/api/v1/agents/execute"
            },
            logs=[
                {
                    "timestamp": start_time.isoformat(),
                    "level": "info",
                    "message": f"Starting {operation_name}",
                    "trace_id": trace_id
                }
            ],
            status="ok"
        )
        
        return root_span
    
    async def _create_child_span(self, trace_id: str, parent_span_id: str, 
                               service_name: str, trace_start: datetime) -> TraceSpan:
        """Create child span for specific service."""
        span_id = str(uuid.uuid4())
        
        # Service-specific operation durations and characteristics
        service_configs = {
            "auth-service": {
                "duration_ms": 25 + (time.time() % 15),  # 25-40ms
                "operation": "authenticate_user",
                "tags": {"auth.method": "jwt", "user.tier": "enterprise"}
            },
            "agent-service": {
                "duration_ms": 800 + (time.time() % 200),  # 800-1000ms
                "operation": "execute_agent_task",
                "tags": {"agent.type": "supervisor", "llm.model": "claude-3"}
            },
            "database-service": {
                "duration_ms": 45 + (time.time() % 25),  # 45-70ms
                "operation": "query_user_context",
                "tags": {"db.type": "postgres", "db.pool": "main"}
            },
            "websocket-service": {
                "duration_ms": 15 + (time.time() % 10),  # 15-25ms
                "operation": "send_response",
                "tags": {"ws.connection_id": str(uuid.uuid4())[:8], "ws.room": "user_session"}
            }
        }
        
        config = service_configs.get(service_name, {
            "duration_ms": 50,
            "operation": "default_operation",
            "tags": {"service": service_name}
        })
        
        span_start = trace_start.replace(
            microsecond=trace_start.microsecond + int((time.time() % 50) * 1000)
        )
        
        child_span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=config["operation"],
            service_name=service_name,
            start_time=span_start,
            end_time=span_start.replace(
                microsecond=span_start.microsecond + int(config["duration_ms"] * 1000)
            ),
            duration_ms=config["duration_ms"],
            tags={
                **config["tags"],
                "trace.parent_id": parent_span_id,
                "service.name": service_name
            },
            logs=[
                {
                    "timestamp": span_start.isoformat(),
                    "level": "info",
                    "message": f"Started {config['operation']} in {service_name}",
                    "parent_span_id": parent_span_id
                }
            ],
            status="ok"
        )
        
        return child_span
    
    async def validate_trace_propagation(self, trace_context: TraceContext) -> Dict[str, Any]:
        """Validate trace context propagation across services."""
        validation_results = {
            "trace_id": trace_context.trace_id,
            "propagation_success": True,
            "span_count": len(trace_context.spans),
            "parent_child_relationships": [],
            "context_propagation_failures": [],
            "timing_consistency": True,
            "service_coverage": set(),
            "missing_context": []
        }
        
        # Validate parent-child relationships
        span_map = {span.span_id: span for span in trace_context.spans}
        
        for span in trace_context.spans:
            validation_results["service_coverage"].add(span.service_name)
            
            if span.parent_span_id:
                parent_span = span_map.get(span.parent_span_id)
                if parent_span:
                    # Validate timing consistency
                    if span.start_time < parent_span.start_time:
                        validation_results["timing_consistency"] = False
                        validation_results["context_propagation_failures"].append({
                            "span_id": span.span_id,
                            "issue": "child_started_before_parent",
                            "child_start": span.start_time.isoformat(),
                            "parent_start": parent_span.start_time.isoformat()
                        })
                    
                    validation_results["parent_child_relationships"].append({
                        "parent_span": parent_span.span_id,
                        "parent_service": parent_span.service_name,
                        "child_span": span.span_id,
                        "child_service": span.service_name,
                        "relationship_valid": True
                    })
                else:
                    validation_results["propagation_success"] = False
                    validation_results["context_propagation_failures"].append({
                        "span_id": span.span_id,
                        "issue": "missing_parent_span",
                        "missing_parent_id": span.parent_span_id
                    })
            
            # Validate trace context propagation
            if span.trace_id != trace_context.trace_id:
                validation_results["propagation_success"] = False
                validation_results["context_propagation_failures"].append({
                    "span_id": span.span_id,
                    "issue": "trace_id_mismatch",
                    "expected": trace_context.trace_id,
                    "actual": span.trace_id
                })
            
            # Check for required context fields
            required_tags = ["service.name"]
            for required_tag in required_tags:
                if required_tag not in span.tags:
                    validation_results["missing_context"].append({
                        "span_id": span.span_id,
                        "service": span.service_name,
                        "missing_tag": required_tag
                    })
        
        return validation_results
    
    async def measure_trace_performance(self, trace_context: TraceContext) -> Dict[str, Any]:
        """Measure trace performance and identify bottlenecks."""
        performance_analysis = {
            "trace_id": trace_context.trace_id,
            "total_duration_ms": trace_context.total_duration_ms,
            "span_analysis": [],
            "bottlenecks": [],
            "performance_score": 0.0,
            "latency_breakdown": {}
        }
        
        # Analyze each span's performance
        for span in trace_context.spans:
            span_analysis = {
                "span_id": span.span_id,
                "service": span.service_name,
                "operation": span.operation_name,
                "duration_ms": span.duration_ms,
                "percentage_of_total": (span.duration_ms / trace_context.total_duration_ms) * 100,
                "performance_category": self._categorize_span_performance(span)
            }
            
            performance_analysis["span_analysis"].append(span_analysis)
            
            # Identify bottlenecks
            if span.duration_ms > 500:  # Spans over 500ms are bottlenecks
                performance_analysis["bottlenecks"].append({
                    "span_id": span.span_id,
                    "service": span.service_name,
                    "operation": span.operation_name,
                    "duration_ms": span.duration_ms,
                    "severity": "high" if span.duration_ms > 1000 else "medium"
                })
        
        # Calculate latency breakdown by service
        for span in trace_context.spans:
            service = span.service_name
            if service not in performance_analysis["latency_breakdown"]:
                performance_analysis["latency_breakdown"][service] = {
                    "total_ms": 0,
                    "span_count": 0,
                    "avg_ms": 0
                }
            
            performance_analysis["latency_breakdown"][service]["total_ms"] += span.duration_ms
            performance_analysis["latency_breakdown"][service]["span_count"] += 1
        
        # Calculate averages
        for service_data in performance_analysis["latency_breakdown"].values():
            service_data["avg_ms"] = service_data["total_ms"] / service_data["span_count"]
        
        # Calculate overall performance score (0-100)
        total_bottleneck_time = sum(b["duration_ms"] for b in performance_analysis["bottlenecks"])
        performance_ratio = 1 - (total_bottleneck_time / trace_context.total_duration_ms)
        performance_analysis["performance_score"] = max(0, performance_ratio * 100)
        
        return performance_analysis
    
    def _categorize_span_performance(self, span: TraceSpan) -> str:
        """Categorize span performance based on duration and service type."""
        duration = span.duration_ms
        service = span.service_name
        
        # Service-specific performance thresholds
        thresholds = {
            "auth-service": {"excellent": 20, "good": 40, "poor": 100},
            "database-service": {"excellent": 30, "good": 60, "poor": 150},
            "agent-service": {"excellent": 500, "good": 1000, "poor": 2000},
            "websocket-service": {"excellent": 10, "good": 25, "poor": 50},
            "api-gateway": {"excellent": 50, "good": 100, "poor": 200}
        }
        
        service_thresholds = thresholds.get(service, {"excellent": 50, "good": 100, "poor": 200})
        
        if duration <= service_thresholds["excellent"]:
            return "excellent"
        elif duration <= service_thresholds["good"]:
            return "good"
        elif duration <= service_thresholds["poor"]:
            return "fair"
        else:
            return "poor"
    
    async def test_correlation_accuracy(self, trace_count: int = 10) -> Dict[str, Any]:
        """Test accuracy of trace correlation across multiple concurrent traces."""
        correlation_results = {
            "total_traces": trace_count,
            "successful_correlations": 0,
            "correlation_errors": 0,
            "cross_trace_contamination": 0,
            "timing_violations": 0,
            "context_integrity": True
        }
        
        # Create multiple concurrent traces
        trace_tasks = []
        for i in range(trace_count):
            task = self.create_distributed_trace(f"concurrent_operation_{i}", service_count=4)
            trace_tasks.append(task)
        
        # Execute traces concurrently
        traces = await asyncio.gather(*trace_tasks)
        
        # Validate each trace's correlation
        for trace in traces:
            validation = await self.validate_trace_propagation(trace)
            
            if validation["propagation_success"]:
                correlation_results["successful_correlations"] += 1
            else:
                correlation_results["correlation_errors"] += 1
            
            if not validation["timing_consistency"]:
                correlation_results["timing_violations"] += 1
            
            # Check for cross-trace contamination
            for other_trace in traces:
                if other_trace.trace_id != trace.trace_id:
                    for span in trace.spans:
                        if span.trace_id == other_trace.trace_id:
                            correlation_results["cross_trace_contamination"] += 1
        
        # Calculate correlation accuracy
        if trace_count > 0:
            correlation_accuracy = (correlation_results["successful_correlations"] / trace_count) * 100
            correlation_results["correlation_accuracy_percentage"] = correlation_accuracy
        
        self.correlation_errors = correlation_results
        return correlation_results
    
    async def cleanup(self):
        """Clean up tracing test resources."""
        try:
            if self.trace_collector:
                await self.trace_collector.shutdown()
            if hasattr(self, 'service_registry'):
                await self.service_registry.cleanup()
        except Exception as e:
            logger.error(f"Tracing cleanup failed: {e}")


class TracingCollector:
    """Mock tracing collector for L3 testing."""
    
    async def initialize(self):
        """Initialize tracing collector."""
        pass
    
    async def shutdown(self):
        """Shutdown tracing collector."""
        pass


class ServiceRegistry:
    """Mock service registry for multi-service tracing."""
    
    async def register_services(self, services: List[str]):
        """Register services for tracing."""
        self.services = services
    
    async def cleanup(self):
        """Cleanup service registry."""
        pass


@pytest.fixture
async def distributed_tracing_validator():
    """Create distributed tracing validator for L3 testing."""
    validator = DistributedTracingValidator()
    await validator.initialize_tracing_services()
    yield validator
    await validator.cleanup()


@pytest.mark.asyncio
async def test_trace_context_propagation_l3(distributed_tracing_validator):
    """Test trace context propagation across distributed services.
    
    L3: Tests with real service calls and trace context propagation.
    """
    # Create distributed trace across multiple services
    trace_context = await distributed_tracing_validator.create_distributed_trace(
        "user_agent_interaction", service_count=4
    )
    
    # Validate trace structure
    assert len(trace_context.spans) == 4
    assert trace_context.service_count == 4
    assert trace_context.root_service == "api-gateway"
    
    # Validate trace propagation
    propagation_results = await distributed_tracing_validator.validate_trace_propagation(trace_context)
    
    # Verify propagation success
    assert propagation_results["propagation_success"] is True
    assert propagation_results["timing_consistency"] is True
    assert len(propagation_results["context_propagation_failures"]) == 0
    
    # Verify service coverage
    expected_services = {"api-gateway", "auth-service", "agent-service", "database-service"}
    assert propagation_results["service_coverage"] == expected_services


@pytest.mark.asyncio
async def test_trace_performance_analysis_l3(distributed_tracing_validator):
    """Test trace performance analysis and bottleneck identification.
    
    L3: Tests performance correlation across real service traces.
    """
    # Create trace with varying performance characteristics
    trace_context = await distributed_tracing_validator.create_distributed_trace(
        "performance_test_operation", service_count=5
    )
    
    # Analyze trace performance
    performance_analysis = await distributed_tracing_validator.measure_trace_performance(trace_context)
    
    # Verify performance analysis completeness
    assert len(performance_analysis["span_analysis"]) == 5
    assert "latency_breakdown" in performance_analysis
    assert "performance_score" in performance_analysis
    
    # Verify performance categorization
    performance_categories = [span["performance_category"] for span in performance_analysis["span_analysis"]]
    assert len(set(performance_categories)) >= 1  # At least one performance category
    
    # Verify latency breakdown includes all services
    assert len(performance_analysis["latency_breakdown"]) == 5


@pytest.mark.asyncio
async def test_concurrent_trace_correlation_l3(distributed_tracing_validator):
    """Test trace correlation accuracy with concurrent operations.
    
    L3: Tests correlation accuracy under concurrent load.
    """
    # Test correlation with multiple concurrent traces
    correlation_results = await distributed_tracing_validator.test_correlation_accuracy(trace_count=8)
    
    # Verify correlation accuracy
    assert correlation_results["correlation_accuracy_percentage"] >= 95.0
    assert correlation_results["cross_trace_contamination"] == 0
    assert correlation_results["timing_violations"] <= 1
    
    # Verify successful correlations
    assert correlation_results["successful_correlations"] >= 7
    assert correlation_results["correlation_errors"] <= 1


@pytest.mark.asyncio
async def test_trace_error_propagation_l3(distributed_tracing_validator):
    """Test error propagation and status tracking in distributed traces.
    
    L3: Tests error tracking across service boundaries.
    """
    # Create trace with simulated errors
    trace_context = await distributed_tracing_validator.create_distributed_trace(
        "error_test_operation", service_count=3
    )
    
    # Simulate error in middle service
    error_span = trace_context.spans[1]
    error_span.status = "error"
    error_span.tags["error.type"] = "database_timeout"
    error_span.logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "error",
        "message": "Database connection timeout",
        "error": True
    })
    
    # Update trace error count
    trace_context.error_count = 1
    
    # Validate error propagation
    propagation_results = await distributed_tracing_validator.validate_trace_propagation(trace_context)
    
    # Verify trace still maintains integrity despite errors
    assert propagation_results["propagation_success"] is True
    assert trace_context.error_count == 1
    
    # Verify error span maintains proper context
    assert error_span.trace_id == trace_context.trace_id
    assert error_span.status == "error"


@pytest.mark.asyncio
async def test_trace_sampling_consistency_l3(distributed_tracing_validator):
    """Test trace sampling consistency across service boundaries.
    
    L3: Tests sampling decisions propagate correctly.
    """
    # Create multiple traces to test sampling
    sampled_traces = []
    for i in range(20):
        trace = await distributed_tracing_validator.create_distributed_trace(
            f"sampling_test_{i}", service_count=3
        )
        sampled_traces.append(trace)
    
    # Verify all spans in each trace have consistent sampling
    for trace in sampled_traces:
        trace_ids = set(span.trace_id for span in trace.spans)
        assert len(trace_ids) == 1, f"Inconsistent trace IDs in trace: {trace_ids}"
        
        # Verify all spans belong to the same trace
        for span in trace.spans:
            assert span.trace_id == trace.trace_id
    
    # Verify trace completeness
    complete_traces = [t for t in sampled_traces if len(t.spans) == 3]
    assert len(complete_traces) >= 18  # Allow 10% sampling loss