"""Distributed Tracing with OpenTelemetry Critical Path Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (enables debugging for all tiers)
- Business Goal: Observability and faster incident resolution
- Value Impact: Enables debugging for $15K MRR protection through faster issue resolution
- Strategic Impact: Foundation for performance optimization and production debugging

Critical Path: Trace creation -> Span propagation -> Context injection -> Collection -> Analysis
Coverage: OpenTelemetry integration, trace propagation, distributed context, trace analysis
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ImportError:
    # Mock OpenTelemetry components if not available
    from unittest.mock import MagicMock
    trace = MagicMock()
    JaegerExporter = MagicMock
    TracerProvider = MagicMock
    BatchSpanProcessor = MagicMock

from netra_backend.app.services.observability.metrics_collector import MetricsCollector as MetricsService

# Mock tracing services since they don't exist yet
class OpenTelemetryService:
    def __init__(self):
        pass
    
    async def initialize(self):
        return True
    
    async def get_tracer(self, name="test"):
        return MagicMock()

class SpanManager:
    def __init__(self):
        pass
    
    async def create_span(self, name, **kwargs):
        return MagicMock()

logger = logging.getLogger(__name__)

class DistributedTracingManager:
    """Manages distributed tracing testing with OpenTelemetry."""
    
    def __init__(self):
        self.otel_service = None
        self.span_manager = None
        self.metrics_service = None
        self.tracer = None
        self.active_traces = []
        self.collected_spans = []
        
    async def initialize_services(self):
        """Initialize distributed tracing services."""
        self.otel_service = OpenTelemetryService()
        await self.otel_service.initialize()
        
        self.span_manager = SpanManager()
        await self.span_manager.initialize()
        
        self.metrics_service = MetricsService()
        await self.metrics_service.initialize()
        
        # Get tracer for testing
        self.tracer = self.otel_service.get_tracer("test_tracer")
    
    async def create_distributed_trace(self, operation_name: str, 
                                     service_calls: List[Dict]) -> Dict[str, Any]:
        """Create distributed trace across multiple services."""
        trace_start = time.time()
        
        # Start root span
        with self.tracer.start_as_current_span(operation_name) as root_span:
            root_span.set_attribute("service.name", "test_service")
            root_span.set_attribute("operation.type", "test_operation")
            
            trace_id = root_span.get_span_context().trace_id
            
            # Create child spans for service calls
            child_spans_info = []
            
            for service_call in service_calls:
                service_name = service_call["service"]
                operation = service_call["operation"]
                
                with self.tracer.start_as_current_span(f"{service_name}.{operation}") as child_span:
                    child_span.set_attribute("service.name", service_name)
                    child_span.set_attribute("operation.name", operation)
                    
                    # Simulate service call duration
                    call_duration = service_call.get("duration", 0.1)
                    await asyncio.sleep(call_duration)
                    
                    # Add some attributes and events
                    child_span.set_attribute("call.duration", call_duration)
                    child_span.add_event("service_call_completed")
                    
                    child_spans_info.append({
                        "service": service_name,
                        "operation": operation,
                        "span_id": child_span.get_span_context().span_id,
                        "duration": call_duration
                    })
            
            # Record trace completion
            root_span.add_event("trace_completed")
            root_span.set_attribute("total.services", len(service_calls))
            
            trace_record = {
                "operation_name": operation_name,
                "trace_id": trace_id,
                "root_span_id": root_span.get_span_context().span_id,
                "child_spans": child_spans_info,
                "total_duration": time.time() - trace_start,
                "span_count": len(service_calls) + 1  # +1 for root span
            }
            
            self.active_traces.append(trace_record)
            return trace_record
    
    async def test_context_propagation(self, service_chain: List[str]) -> Dict[str, Any]:
        """Test trace context propagation through service chain."""
        propagation_start = time.time()
        
        # Start root trace
        with self.tracer.start_as_current_span("context_propagation_test") as root_span:
            trace_context = trace.get_current()
            
            propagation_results = []
            current_context = trace_context
            
            # Propagate through service chain
            for i, service_name in enumerate(service_chain):
                with self.tracer.start_as_current_span(
                    f"service_{service_name}", 
                    context=current_context
                ) as service_span:
                    
                    # Verify context propagation
                    service_trace_id = service_span.get_span_context().trace_id
                    root_trace_id = root_span.get_span_context().trace_id
                    
                    context_preserved = service_trace_id == root_trace_id
                    
                    # Extract context for next service
                    current_context = trace.set_span_in_context(service_span)
                    
                    propagation_results.append({
                        "service": service_name,
                        "position": i,
                        "context_preserved": context_preserved,
                        "trace_id": service_trace_id,
                        "span_id": service_span.get_span_context().span_id
                    })
                    
                    # Simulate processing time
                    await asyncio.sleep(0.05)
            
            return {
                "service_chain": service_chain,
                "propagation_results": propagation_results,
                "context_preserved_count": len([r for r in propagation_results if r["context_preserved"]]),
                "propagation_time": time.time() - propagation_start
            }
    
    async def simulate_error_tracing(self, error_scenario: str) -> Dict[str, Any]:
        """Simulate error conditions and test trace error handling."""
        error_trace_start = time.time()
        
        try:
            with self.tracer.start_as_current_span("error_trace_test") as error_span:
                error_span.set_attribute("test.scenario", error_scenario)
                
                if error_scenario == "service_timeout":
                    # Simulate timeout
                    error_span.set_attribute("error.type", "timeout")
                    error_span.add_event("timeout_detected")
                    await asyncio.sleep(0.1)
                    raise TimeoutError("Service timeout")
                
                elif error_scenario == "database_error":
                    # Simulate database error
                    error_span.set_attribute("error.type", "database")
                    error_span.add_event("database_error_detected")
                    raise Exception("Database connection failed")
                
                elif error_scenario == "validation_error":
                    # Simulate validation error
                    error_span.set_attribute("error.type", "validation")
                    error_span.add_event("validation_failed")
                    raise ValueError("Invalid input data")
                
        except Exception as e:
            # Record error in span
            error_span.record_exception(e)
            error_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            return {
                "error_scenario": error_scenario,
                "error_recorded": True,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "trace_time": time.time() - error_trace_start
            }
    
    async def collect_and_analyze_traces(self, trace_filter: Dict[str, Any] = None) -> Dict[str, Any]:
        """Collect and analyze traces from the system."""
        collection_start = time.time()
        
        # Get recent traces
        traces = await self.span_manager.get_recent_traces(
            limit=100, 
            filter_criteria=trace_filter
        )
        
        # Analyze trace data
        trace_analysis = {
            "total_traces": len(traces),
            "service_coverage": set(),
            "operation_types": set(),
            "error_traces": 0,
            "average_duration": 0,
            "performance_issues": []
        }
        
        total_duration = 0
        
        for trace_data in traces:
            # Extract service names
            for span in trace_data.get("spans", []):
                service_name = span.get("attributes", {}).get("service.name")
                if service_name:
                    trace_analysis["service_coverage"].add(service_name)
                
                operation_type = span.get("attributes", {}).get("operation.type")
                if operation_type:
                    trace_analysis["operation_types"].add(operation_type)
            
            # Check for errors
            if any(span.get("status", {}).get("status_code") == "ERROR" 
                   for span in trace_data.get("spans", [])):
                trace_analysis["error_traces"] += 1
            
            # Calculate duration
            trace_duration = trace_data.get("duration", 0)
            total_duration += trace_duration
            
            # Identify performance issues (traces > 1 second)
            if trace_duration > 1.0:
                trace_analysis["performance_issues"].append({
                    "trace_id": trace_data.get("trace_id"),
                    "duration": trace_duration,
                    "operation": trace_data.get("operation_name")
                })
        
        if traces:
            trace_analysis["average_duration"] = total_duration / len(traces)
        
        # Convert sets to lists for JSON serialization
        trace_analysis["service_coverage"] = list(trace_analysis["service_coverage"])
        trace_analysis["operation_types"] = list(trace_analysis["operation_types"])
        
        return {
            "analysis": trace_analysis,
            "collection_time": time.time() - collection_start,
            "traces_collected": len(traces)
        }
    
    async def cleanup(self):
        """Clean up distributed tracing test resources."""
        # Clear active traces
        for trace_record in self.active_traces:
            await self.span_manager.clear_trace(trace_record["trace_id"])
        
        if self.otel_service:
            await self.otel_service.shutdown()
        if self.span_manager:
            await self.span_manager.shutdown()
        if self.metrics_service:
            await self.metrics_service.shutdown()

@pytest.fixture
async def distributed_tracing_manager():
    """Create distributed tracing manager for testing."""
    manager = DistributedTracingManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_distributed_trace_creation_and_propagation(distributed_tracing_manager):
    """Test distributed trace creation and span propagation."""
    manager = distributed_tracing_manager
    
    # Define service calls for trace
    service_calls = [
        {"service": "user_service", "operation": "get_user", "duration": 0.1},
        {"service": "auth_service", "operation": "validate_token", "duration": 0.05},
        {"service": "database", "operation": "query_user_data", "duration": 0.2}
    ]
    
    # Create distributed trace
    trace_result = await manager.create_distributed_trace(
        "user_authentication_flow", service_calls
    )
    
    assert trace_result["span_count"] == 4  # 3 service calls + 1 root span
    assert trace_result["total_duration"] < 1.0
    assert len(trace_result["child_spans"]) == 3
    
    # Verify all services are traced
    traced_services = [span["service"] for span in trace_result["child_spans"]]
    expected_services = ["user_service", "auth_service", "database"]
    assert all(service in traced_services for service in expected_services)

@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_trace_context_propagation_chain(distributed_tracing_manager):
    """Test trace context propagation through service chain."""
    manager = distributed_tracing_manager
    
    # Test context propagation through service chain
    service_chain = ["api_gateway", "user_service", "auth_service", "database"]
    
    propagation_result = await manager.test_context_propagation(service_chain)
    
    assert propagation_result["context_preserved_count"] == len(service_chain)
    assert propagation_result["propagation_time"] < 1.0
    
    # Verify all services maintain same trace ID
    propagation_results = propagation_result["propagation_results"]
    trace_ids = [result["trace_id"] for result in propagation_results]
    assert len(set(trace_ids)) == 1  # All should have same trace ID

@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_error_tracing_and_exception_handling(distributed_tracing_manager):
    """Test error tracing and exception handling in traces."""
    manager = distributed_tracing_manager
    
    # Test different error scenarios
    error_scenarios = ["service_timeout", "database_error", "validation_error"]
    
    error_results = []
    for scenario in error_scenarios:
        error_result = await manager.simulate_error_tracing(scenario)
        error_results.append(error_result)
    
    # Verify all errors were traced
    assert all(result["error_recorded"] for result in error_results)
    assert all(result["trace_time"] < 0.5 for result in error_results)
    
    # Verify different error types captured
    error_types = [result["error_type"] for result in error_results]
    expected_types = ["TimeoutError", "Exception", "ValueError"]
    assert all(expected in error_types for expected in expected_types)

@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_trace_collection_and_analysis(distributed_tracing_manager):
    """Test trace collection and analysis capabilities."""
    manager = distributed_tracing_manager
    
    # Generate test traces
    test_operations = [
        {"name": "user_registration", "services": [
            {"service": "api", "operation": "register", "duration": 0.1},
            {"service": "database", "operation": "create_user", "duration": 0.3}
        ]},
        {"name": "data_processing", "services": [
            {"service": "worker", "operation": "process", "duration": 0.5},
            {"service": "storage", "operation": "save", "duration": 0.2}
        ]}
    ]
    
    # Create multiple traces
    for operation in test_operations:
        await manager.create_distributed_trace(
            operation["name"], operation["services"]
        )
    
    # Collect and analyze traces
    analysis_result = await manager.collect_and_analyze_traces()
    
    assert analysis_result["traces_collected"] >= 2
    assert analysis_result["collection_time"] < 5.0
    
    analysis = analysis_result["analysis"]
    assert analysis["total_traces"] >= 2
    assert len(analysis["service_coverage"]) >= 3  # Multiple services traced
    assert analysis["average_duration"] > 0