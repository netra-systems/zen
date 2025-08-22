"""
L3-13: Distributed Tracing with Real OpenTelemetry Integration Test

BVJ: Essential for debugging and performance monitoring in microservices.
Enables rapid troubleshooting and performance optimization of AI workloads.

Tests distributed tracing with real OpenTelemetry and Jaeger containers.
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

import aiohttp
import docker
import pytest
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from tracing.span_processor import CustomSpanProcessor
from tracing.tracer_manager import TracerManager

@pytest.mark.L3
class TestDistributedTracingOtelL3:
    """Test distributed tracing with real OpenTelemetry."""
    
    @pytest.fixture(scope="class")
    async def docker_client(self):
        """Docker client for container management."""
        client = docker.from_env()
        yield client
        client.close()
    
    @pytest.fixture(scope="class")
    async def jaeger_container(self, docker_client):
        """Start Jaeger container for trace collection."""
        container = docker_client.containers.run(
            "jaegertracing/all-in-one:latest",
            ports={
                '16686/tcp': None,  # Jaeger UI
                '14268/tcp': None,  # HTTP collector
                '6831/udp': None,   # UDP agent
                '6832/udp': None    # UDP agent
            },
            environment={
                "COLLECTOR_OTLP_ENABLED": "true"
            },
            detach=True,
            name="jaeger_test_container"
        )
        
        # Get assigned ports
        container.reload()
        ui_port = container.attrs['NetworkSettings']['Ports']['16686/tcp'][0]['HostPort']
        collector_port = container.attrs['NetworkSettings']['Ports']['14268/tcp'][0]['HostPort']
        
        # Wait for Jaeger to be ready
        await self._wait_for_jaeger(ui_port)
        
        jaeger_config = {
            "ui_port": int(ui_port),
            "collector_port": int(collector_port),
            "ui_url": f"http://localhost:{ui_port}",
            "collector_url": f"http://localhost:{collector_port}"
        }
        
        yield jaeger_config
        
        container.stop()
        container.remove()
    
    @pytest.fixture(scope="class")
    async def test_service_containers(self, docker_client):
        """Start test service containers for distributed tracing."""
        services = {}
        
        # Service A (nginx)
        service_a = docker_client.containers.run(
            "nginx:alpine",
            ports={'80/tcp': None},
            detach=True,
            name="trace_service_a"
        )
        
        service_a.reload()
        service_a_port = service_a.attrs['NetworkSettings']['Ports']['80/tcp'][0]['HostPort']
        
        services["service_a"] = {
            "container": service_a,
            "url": f"http://localhost:{service_a_port}",
            "port": int(service_a_port)
        }
        
        # Service B (echo service)
        service_b = docker_client.containers.run(
            "hashicorp/http-echo:latest",
            command=["-text=Service B response"],
            ports={'5678/tcp': None},
            detach=True,
            name="trace_service_b"
        )
        
        service_b.reload()
        service_b_port = service_b.attrs['NetworkSettings']['Ports']['5678/tcp'][0]['HostPort']
        
        services["service_b"] = {
            "container": service_b,
            "url": f"http://localhost:{service_b_port}",
            "port": int(service_b_port)
        }
        
        # Wait for services to be ready
        await self._wait_for_service(services["service_a"]["url"])
        await self._wait_for_service(services["service_b"]["url"])
        
        yield services
        
        # Cleanup
        for service_name, service_info in services.items():
            service_info["container"].stop()
            service_info["container"].remove()
    
    async def _wait_for_jaeger(self, port: str, timeout: int = 60):
        """Wait for Jaeger to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://localhost:{port}/api/services",
                        timeout=aiohttp.ClientTimeout(total=2)
                    ) as response:
                        if response.status == 200:
                            return
            except:
                pass
            await asyncio.sleep(1)
        raise TimeoutError(f"Jaeger not ready within {timeout}s")
    
    async def _wait_for_service(self, url: str, timeout: int = 30):
        """Wait for service to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as response:
                        if response.status == 200:
                            return
            except:
                pass
            await asyncio.sleep(0.5)
        raise TimeoutError(f"Service at {url} not ready within {timeout}s")
    
    @pytest.fixture
    async def tracer_manager(self, jaeger_container):
        """Create tracer manager with Jaeger backend."""
        manager = TracerManager(
            service_name="test_service",
            jaeger_config=jaeger_container
        )
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    async def instrumented_http_client(self, tracer_manager):
        """Create HTTP client with tracing instrumentation."""
        # Initialize HTTP client instrumentation
        AioHttpClientInstrumentor().instrument()
        
        session = aiohttp.ClientSession()
        yield session
        
        await session.close()
        AioHttpClientInstrumentor().uninstrument()
    
    @pytest.mark.asyncio
    async def test_basic_span_creation_and_export(
        self, 
        tracer_manager, 
        jaeger_container
    ):
        """Test basic span creation and export to Jaeger."""
        tracer = tracer_manager.get_tracer("test_basic_spans")
        
        # Create a simple span
        with tracer.start_as_current_span("test_operation") as span:
            span.set_attribute("test.attribute", "test_value")
            span.add_event("test_event", {"event.data": "test_data"})
            
            # Simulate some work
            await asyncio.sleep(0.1)
            
            span.set_status(trace.Status(trace.StatusCode.OK))
        
        # Force flush to export spans
        await tracer_manager.force_flush()
        
        # Wait for export
        await asyncio.sleep(2)
        
        # Verify span was exported to Jaeger
        traces = await self._get_jaeger_traces(jaeger_container, "test_service")
        
        assert len(traces) > 0
        
        # Find our test span
        test_spans = []
        for trace_data in traces:
            for span in trace_data.get("spans", []):
                if span.get("operationName") == "test_operation":
                    test_spans.append(span)
        
        assert len(test_spans) >= 1
        test_span = test_spans[0]
        
        # Verify span attributes
        tags = {tag["key"]: tag["value"] for tag in test_span.get("tags", [])}
        assert tags.get("test.attribute") == "test_value"
    
    async def _get_jaeger_traces(self, jaeger_config, service_name):
        """Get traces from Jaeger API."""
        async with aiohttp.ClientSession() as session:
            url = f"{jaeger_config['ui_url']}/api/traces"
            params = {"service": service_name, "limit": 100}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                return []
    
    @pytest.mark.asyncio
    async def test_distributed_trace_across_services(
        self, 
        tracer_manager, 
        instrumented_http_client,
        test_service_containers,
        jaeger_container
    ):
        """Test distributed tracing across multiple services."""
        tracer = tracer_manager.get_tracer("test_distributed")
        
        # Create parent span
        with tracer.start_as_current_span("distributed_operation") as parent_span:
            parent_span.set_attribute("operation.type", "distributed")
            
            # Make HTTP call to service A (should create child span)
            with tracer.start_as_current_span("call_service_a") as service_a_span:
                service_a_span.set_attribute("service.name", "service_a")
                
                async with instrumented_http_client.get(
                    test_service_containers["service_a"]["url"]
                ) as response:
                    service_a_span.set_attribute("http.status_code", response.status)
                    service_a_data = await response.text()
            
            # Make HTTP call to service B
            with tracer.start_as_current_span("call_service_b") as service_b_span:
                service_b_span.set_attribute("service.name", "service_b")
                
                async with instrumented_http_client.get(
                    test_service_containers["service_b"]["url"]
                ) as response:
                    service_b_span.set_attribute("http.status_code", response.status)
                    service_b_data = await response.text()
            
            parent_span.set_attribute("services.called", 2)
            parent_span.set_status(trace.Status(trace.StatusCode.OK))
        
        # Force flush and wait for export
        await tracer_manager.force_flush()
        await asyncio.sleep(3)
        
        # Verify distributed trace structure
        traces = await self._get_jaeger_traces(jaeger_container, "test_service")
        
        # Find our distributed trace
        distributed_traces = []
        for trace_data in traces:
            spans = trace_data.get("spans", [])
            operation_names = [span.get("operationName") for span in spans]
            
            if "distributed_operation" in operation_names:
                distributed_traces.append(trace_data)
        
        assert len(distributed_traces) >= 1
        trace_data = distributed_traces[0]
        spans = trace_data["spans"]
        
        # Verify parent-child relationships
        parent_spans = [s for s in spans if s.get("operationName") == "distributed_operation"]
        child_spans = [s for s in spans if s.get("operationName") in ["call_service_a", "call_service_b"]]
        
        assert len(parent_spans) == 1
        assert len(child_spans) >= 2
        
        # Verify parent-child relationship
        parent_span = parent_spans[0]
        for child_span in child_spans:
            assert child_span.get("traceID") == parent_span.get("traceID")
    
    @pytest.mark.asyncio
    async def test_error_span_tracking(
        self, 
        tracer_manager, 
        jaeger_container
    ):
        """Test error tracking in spans."""
        tracer = tracer_manager.get_tracer("test_errors")
        
        # Create span with error
        with tracer.start_as_current_span("error_operation") as span:
            span.set_attribute("operation.type", "error_test")
            
            try:
                # Simulate an error
                raise ValueError("Test error for tracing")
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        
        # Force flush
        await tracer_manager.force_flush()
        await asyncio.sleep(2)
        
        # Verify error span in Jaeger
        traces = await self._get_jaeger_traces(jaeger_container, "test_service")
        
        error_spans = []
        for trace_data in traces:
            for span in trace_data.get("spans", []):
                if span.get("operationName") == "error_operation":
                    error_spans.append(span)
        
        assert len(error_spans) >= 1
        error_span = error_spans[0]
        
        # Verify error tags
        tags = {tag["key"]: tag["value"] for tag in error_span.get("tags", [])}
        assert tags.get("error") == "true"
        assert "Test error for tracing" in str(tags.get("error.message", ""))
    
    @pytest.mark.asyncio
    async def test_custom_span_processor(
        self, 
        tracer_manager, 
        jaeger_container
    ):
        """Test custom span processor functionality."""
        processed_spans = []
        
        class TestSpanProcessor(CustomSpanProcessor):
            def on_start(self, span, parent_context):
                super().on_start(span, parent_context)
                # Add custom attributes on span start
                span.set_attribute("processor.custom", "true")
            
            def on_end(self, span):
                super().on_end(span)
                processed_spans.append(span.name)
        
        # Add custom processor
        custom_processor = TestSpanProcessor()
        tracer_manager.add_span_processor(custom_processor)
        
        tracer = tracer_manager.get_tracer("test_custom_processor")
        
        # Create spans to test processor
        operations = ["operation_1", "operation_2", "operation_3"]
        for operation in operations:
            with tracer.start_as_current_span(operation) as span:
                span.set_attribute("operation.number", operation.split("_")[1])
                await asyncio.sleep(0.05)
        
        # Force flush
        await tracer_manager.force_flush()
        await asyncio.sleep(2)
        
        # Verify custom processor was called
        assert len(processed_spans) >= 3
        for operation in operations:
            assert operation in processed_spans
        
        # Verify custom attributes were added
        traces = await self._get_jaeger_traces(jaeger_container, "test_service")
        
        custom_spans = []
        for trace_data in traces:
            for span in trace_data.get("spans", []):
                if span.get("operationName") in operations:
                    custom_spans.append(span)
        
        assert len(custom_spans) >= 3
        
        for span in custom_spans:
            tags = {tag["key"]: tag["value"] for tag in span.get("tags", [])}
            assert tags.get("processor.custom") == "true"
    
    @pytest.mark.asyncio
    async def test_sampling_configuration(
        self, 
        tracer_manager, 
        jaeger_container
    ):
        """Test trace sampling configuration."""
        # Configure different sampling rates
        high_sample_tracer = tracer_manager.get_tracer(
            "high_sample_tracer",
            sampling_rate=1.0  # 100% sampling
        )
        
        low_sample_tracer = tracer_manager.get_tracer(
            "low_sample_tracer", 
            sampling_rate=0.1   # 10% sampling
        )
        
        # Generate spans with high sampling
        high_sample_spans = 0
        for i in range(10):
            with high_sample_tracer.start_as_current_span(f"high_sample_{i}") as span:
                span.set_attribute("sample.rate", "high")
                high_sample_spans += 1
        
        # Generate spans with low sampling
        low_sample_spans = 0
        for i in range(100):
            with low_sample_tracer.start_as_current_span(f"low_sample_{i}") as span:
                span.set_attribute("sample.rate", "low")
                low_sample_spans += 1
        
        # Force flush
        await tracer_manager.force_flush()
        await asyncio.sleep(3)
        
        # Verify sampling behavior
        traces = await self._get_jaeger_traces(jaeger_container, "test_service")
        
        high_sampled = 0
        low_sampled = 0
        
        for trace_data in traces:
            for span in trace_data.get("spans", []):
                tags = {tag["key"]: tag["value"] for tag in span.get("tags", [])}
                if tags.get("sample.rate") == "high":
                    high_sampled += 1
                elif tags.get("sample.rate") == "low":
                    low_sampled += 1
        
        # High sampling should capture most/all spans
        assert high_sampled >= 8  # Allow some variance
        
        # Low sampling should capture significantly fewer spans
        assert low_sampled < high_sampled
    
    @pytest.mark.asyncio
    async def test_trace_context_propagation(
        self, 
        tracer_manager, 
        instrumented_http_client,
        test_service_containers,
        jaeger_container
    ):
        """Test trace context propagation across service boundaries."""
        tracer = tracer_manager.get_tracer("test_context_propagation")
        
        # Create parent span
        with tracer.start_as_current_span("parent_operation") as parent_span:
            parent_trace_id = parent_span.get_span_context().trace_id
            parent_span.set_attribute("trace.role", "parent")
            
            # Make nested HTTP calls that should propagate context
            async with instrumented_http_client.get(
                test_service_containers["service_a"]["url"],
                headers={"X-Custom-Header": "test"}
            ) as response_a:
                assert response_a.status == 200
            
            # Create child span manually
            with tracer.start_as_current_span("manual_child") as child_span:
                child_trace_id = child_span.get_span_context().trace_id
                child_span.set_attribute("trace.role", "child")
                
                # HTTP call within child span
                async with instrumented_http_client.get(
                    test_service_containers["service_b"]["url"]
                ) as response_b:
                    assert response_b.status == 200
        
        # Force flush
        await tracer_manager.force_flush()
        await asyncio.sleep(3)
        
        # Verify context propagation
        traces = await self._get_jaeger_traces(jaeger_container, "test_service")
        
        parent_trace = None
        for trace_data in traces:
            spans = trace_data.get("spans", [])
            for span in spans:
                tags = {tag["key"]: tag["value"] for tag in span.get("tags", [])}
                if tags.get("trace.role") == "parent":
                    parent_trace = trace_data
                    break
        
        assert parent_trace is not None
        
        # Verify all spans in the trace share the same trace ID
        spans = parent_trace["spans"]
        trace_ids = set(span["traceID"] for span in spans)
        assert len(trace_ids) == 1  # All spans should have same trace ID
        
        # Verify parent-child relationships exist
        span_references = []
        for span in spans:
            references = span.get("references", [])
            span_references.extend(references)
        
        # Should have child-of references
        child_of_refs = [ref for ref in span_references if ref.get("refType") == "CHILD_OF"]
        assert len(child_of_refs) > 0