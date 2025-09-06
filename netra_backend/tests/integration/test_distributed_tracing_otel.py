from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: L3-13: Distributed Tracing with Real OpenTelemetry Integration Test

# REMOVED_SYNTAX_ERROR: BVJ: Essential for debugging and performance monitoring in microservices.
# REMOVED_SYNTAX_ERROR: Enables rapid troubleshooting and performance optimization of AI workloads.

# REMOVED_SYNTAX_ERROR: Tests distributed tracing with real OpenTelemetry and Jaeger containers.
""

import sys
from pathlib import Path
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

import aiohttp
import docker
import pytest
# REMOVED_SYNTAX_ERROR: try:
    # REMOVED_SYNTAX_ERROR: from opentelemetry import trace
    # REMOVED_SYNTAX_ERROR: from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    # REMOVED_SYNTAX_ERROR: from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
    # REMOVED_SYNTAX_ERROR: from opentelemetry.sdk.trace import TracerProvider
    # REMOVED_SYNTAX_ERROR: from opentelemetry.sdk.trace.export import BatchSpanProcessor
    # REMOVED_SYNTAX_ERROR: except ImportError:
        # Mock OpenTelemetry components if not available
        # Mock: Generic component isolation for controlled unit testing
        # REMOVED_SYNTAX_ERROR: trace = MagicMock()  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: JaegerExporter = MagicMock
        # REMOVED_SYNTAX_ERROR: AioHttpClientInstrumentor = MagicMock
        # REMOVED_SYNTAX_ERROR: TracerProvider = MagicMock
        # REMOVED_SYNTAX_ERROR: BatchSpanProcessor = MagicMock
        # Comment out missing tracing imports - these modules don't exist
        # from tracing.span_processor import CustomSpanProcessor
        # from tracing.tracer_manager import TracerManager

        # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
# REMOVED_SYNTAX_ERROR: class TestDistributedTracingOtelL3:
    # REMOVED_SYNTAX_ERROR: """Test distributed tracing with real OpenTelemetry."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def docker_client(self):
    # REMOVED_SYNTAX_ERROR: """Docker client for container management."""
    # REMOVED_SYNTAX_ERROR: client = docker.from_env()
    # REMOVED_SYNTAX_ERROR: yield client
    # REMOVED_SYNTAX_ERROR: client.close()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def jaeger_container(self, docker_client):
    # REMOVED_SYNTAX_ERROR: """Start Jaeger container for trace collection."""
    # REMOVED_SYNTAX_ERROR: container = docker_client.containers.run( )
    # REMOVED_SYNTAX_ERROR: "jaegertracing/all-in-one:latest",
    # REMOVED_SYNTAX_ERROR: ports={ )
    # REMOVED_SYNTAX_ERROR: '16686/tcp': None,  # Jaeger UI
    # REMOVED_SYNTAX_ERROR: '14268/tcp': None,  # HTTP collector
    # REMOVED_SYNTAX_ERROR: '6831/udp': None,   # UDP agent
    # REMOVED_SYNTAX_ERROR: '6832/udp': None    # UDP agent
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: environment={ )
    # REMOVED_SYNTAX_ERROR: "COLLECTOR_OTLP_ENABLED": "true"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: detach=True,
    # REMOVED_SYNTAX_ERROR: name="jaeger_test_container"
    

    # Get assigned ports
    # REMOVED_SYNTAX_ERROR: container.reload()
    # REMOVED_SYNTAX_ERROR: ui_port = container.attrs['NetworkSettings']['Ports']['16686/tcp'][0]['HostPort']
    # REMOVED_SYNTAX_ERROR: collector_port = container.attrs['NetworkSettings']['Ports']['14268/tcp'][0]['HostPort']

    # Wait for Jaeger to be ready
    # REMOVED_SYNTAX_ERROR: await self._wait_for_jaeger(ui_port)

    # REMOVED_SYNTAX_ERROR: jaeger_config = { )
    # REMOVED_SYNTAX_ERROR: "ui_port": int(ui_port),
    # REMOVED_SYNTAX_ERROR: "collector_port": int(collector_port),
    # REMOVED_SYNTAX_ERROR: "ui_url": "formatted_string",
    # REMOVED_SYNTAX_ERROR: "collector_url": "formatted_string"
    

    # REMOVED_SYNTAX_ERROR: yield jaeger_config

    # REMOVED_SYNTAX_ERROR: container.stop()
    # REMOVED_SYNTAX_ERROR: container.remove()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_service_containers(self, docker_client):
        # REMOVED_SYNTAX_ERROR: """Start test service containers for distributed tracing."""
        # REMOVED_SYNTAX_ERROR: services = {}

        # Service A (nginx)
        # REMOVED_SYNTAX_ERROR: service_a = docker_client.containers.run( )
        # REMOVED_SYNTAX_ERROR: "nginx:alpine",
        # REMOVED_SYNTAX_ERROR: ports={'80/tcp': None},
        # REMOVED_SYNTAX_ERROR: detach=True,
        # REMOVED_SYNTAX_ERROR: name="trace_service_a"
        

        # REMOVED_SYNTAX_ERROR: service_a.reload()
        # REMOVED_SYNTAX_ERROR: service_a_port = service_a.attrs['NetworkSettings']['Ports']['80/tcp'][0]['HostPort']

        # REMOVED_SYNTAX_ERROR: services["service_a"] = { )
        # REMOVED_SYNTAX_ERROR: "container": service_a,
        # REMOVED_SYNTAX_ERROR: "url": "formatted_string",
        # REMOVED_SYNTAX_ERROR: "port": int(service_a_port)
        

        # Service B (echo service)
        # REMOVED_SYNTAX_ERROR: service_b = docker_client.containers.run( )
        # REMOVED_SYNTAX_ERROR: "hashicorp/http-echo:latest",
        # REMOVED_SYNTAX_ERROR: command=["-text=Service B response"],
        # REMOVED_SYNTAX_ERROR: ports={'5678/tcp': None},
        # REMOVED_SYNTAX_ERROR: detach=True,
        # REMOVED_SYNTAX_ERROR: name="trace_service_b"
        

        # REMOVED_SYNTAX_ERROR: service_b.reload()
        # REMOVED_SYNTAX_ERROR: service_b_port = service_b.attrs['NetworkSettings']['Ports']['5678/tcp'][0]['HostPort']

        # REMOVED_SYNTAX_ERROR: services["service_b"] = { )
        # REMOVED_SYNTAX_ERROR: "container": service_b,
        # REMOVED_SYNTAX_ERROR: "url": "formatted_string",
        # REMOVED_SYNTAX_ERROR: "port": int(service_b_port)
        

        # Wait for services to be ready
        # REMOVED_SYNTAX_ERROR: await self._wait_for_service(services["service_a"]["url"])
        # REMOVED_SYNTAX_ERROR: await self._wait_for_service(services["service_b"]["url"])

        # REMOVED_SYNTAX_ERROR: yield services

        # Cleanup
        # REMOVED_SYNTAX_ERROR: for service_name, service_info in services.items():
            # REMOVED_SYNTAX_ERROR: service_info["container"].stop()
            # REMOVED_SYNTAX_ERROR: service_info["container"].remove()

# REMOVED_SYNTAX_ERROR: async def _wait_for_jaeger(self, port: str, timeout: int = 60):
    # REMOVED_SYNTAX_ERROR: """Wait for Jaeger to be available."""
    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: while time.time() - start_time < timeout:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: async with aiohttp.ClientSession() as session:
                # REMOVED_SYNTAX_ERROR: async with session.get( )
                # REMOVED_SYNTAX_ERROR: "formatted_string",
                # REMOVED_SYNTAX_ERROR: timeout=aiohttp.ClientTimeout(total=2)
                # REMOVED_SYNTAX_ERROR: ) as response:
                    # REMOVED_SYNTAX_ERROR: if response.status == 200:
                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                        # REMOVED_SYNTAX_ERROR: return
                        # REMOVED_SYNTAX_ERROR: except:
                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(1)
                            # REMOVED_SYNTAX_ERROR: raise TimeoutError("formatted_string")

# REMOVED_SYNTAX_ERROR: async def _wait_for_service(self, url: str, timeout: int = 30):
    # REMOVED_SYNTAX_ERROR: """Wait for service to be available."""
    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: while time.time() - start_time < timeout:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: async with aiohttp.ClientSession() as session:
                # REMOVED_SYNTAX_ERROR: async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as response:
                    # REMOVED_SYNTAX_ERROR: if response.status == 200:
                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                        # REMOVED_SYNTAX_ERROR: return
                        # REMOVED_SYNTAX_ERROR: except:
                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.5)
                            # REMOVED_SYNTAX_ERROR: raise TimeoutError("formatted_string")

                            # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def tracer_manager(self, jaeger_container):
    # REMOVED_SYNTAX_ERROR: """Create tracer manager with Jaeger backend."""
    # REMOVED_SYNTAX_ERROR: manager = TracerManager( )
    # REMOVED_SYNTAX_ERROR: service_name="test_service",
    # REMOVED_SYNTAX_ERROR: jaeger_config=jaeger_container
    
    # REMOVED_SYNTAX_ERROR: await manager.initialize()
    # REMOVED_SYNTAX_ERROR: yield manager
    # REMOVED_SYNTAX_ERROR: await manager.cleanup()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def instrumented_http_client(self, tracer_manager):
    # REMOVED_SYNTAX_ERROR: """Create HTTP client with tracing instrumentation."""
    # Initialize HTTP client instrumentation
    # REMOVED_SYNTAX_ERROR: AioHttpClientInstrumentor().instrument()

    # REMOVED_SYNTAX_ERROR: session = aiohttp.ClientSession()
    # REMOVED_SYNTAX_ERROR: yield session

    # REMOVED_SYNTAX_ERROR: await session.close()
    # REMOVED_SYNTAX_ERROR: AioHttpClientInstrumentor().uninstrument()

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_basic_span_creation_and_export( )
    # REMOVED_SYNTAX_ERROR: self,
    # REMOVED_SYNTAX_ERROR: tracer_manager,
    # REMOVED_SYNTAX_ERROR: jaeger_container
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: """Test basic span creation and export to Jaeger."""
        # REMOVED_SYNTAX_ERROR: tracer = tracer_manager.get_tracer("test_basic_spans")

        # Create a simple span
        # REMOVED_SYNTAX_ERROR: with tracer.start_as_current_span("test_operation") as span:
            # REMOVED_SYNTAX_ERROR: span.set_attribute("test.attribute", "test_value")
            # REMOVED_SYNTAX_ERROR: span.add_event("test_event", {"event.data": "test_data"})

            # Simulate some work
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

            # REMOVED_SYNTAX_ERROR: span.set_status(trace.Status(trace.StatusCode.OK))

            # Force flush to export spans
            # REMOVED_SYNTAX_ERROR: await tracer_manager.force_flush()

            # Wait for export
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(2)

            # Verify span was exported to Jaeger
            # REMOVED_SYNTAX_ERROR: traces = await self._get_jaeger_traces(jaeger_container, "test_service")

            # REMOVED_SYNTAX_ERROR: assert len(traces) > 0

            # Find our test span
            # REMOVED_SYNTAX_ERROR: test_spans = []
            # REMOVED_SYNTAX_ERROR: for trace_data in traces:
                # REMOVED_SYNTAX_ERROR: for span in trace_data.get("spans", []):
                    # REMOVED_SYNTAX_ERROR: if span.get("operationName") == "test_operation":
                        # REMOVED_SYNTAX_ERROR: test_spans.append(span)

                        # REMOVED_SYNTAX_ERROR: assert len(test_spans) >= 1
                        # REMOVED_SYNTAX_ERROR: test_span = test_spans[0]

                        # Verify span attributes
                        # REMOVED_SYNTAX_ERROR: tags = {tag["key"]: tag["value"] for tag in test_span.get("tags", [])]
                        # REMOVED_SYNTAX_ERROR: assert tags.get("test.attribute") == "test_value"

# REMOVED_SYNTAX_ERROR: async def _get_jaeger_traces(self, jaeger_config, service_name):
    # REMOVED_SYNTAX_ERROR: """Get traces from Jaeger API."""
    # REMOVED_SYNTAX_ERROR: async with aiohttp.ClientSession() as session:
        # REMOVED_SYNTAX_ERROR: url = "formatted_string"data", [])
                # REMOVED_SYNTAX_ERROR: return []

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_distributed_trace_across_services( )
                # REMOVED_SYNTAX_ERROR: self,
                # REMOVED_SYNTAX_ERROR: tracer_manager,
                # REMOVED_SYNTAX_ERROR: instrumented_http_client,
                # REMOVED_SYNTAX_ERROR: test_service_containers,
                # REMOVED_SYNTAX_ERROR: jaeger_container
                # REMOVED_SYNTAX_ERROR: ):
                    # REMOVED_SYNTAX_ERROR: """Test distributed tracing across multiple services."""
                    # REMOVED_SYNTAX_ERROR: tracer = tracer_manager.get_tracer("test_distributed")

                    # Create parent span
                    # REMOVED_SYNTAX_ERROR: with tracer.start_as_current_span("distributed_operation") as parent_span:
                        # REMOVED_SYNTAX_ERROR: parent_span.set_attribute("operation.type", "distributed")

                        # Make HTTP call to service A (should create child span)
                        # REMOVED_SYNTAX_ERROR: with tracer.start_as_current_span("call_service_a") as service_a_span:
                            # REMOVED_SYNTAX_ERROR: service_a_span.set_attribute("service.name", "service_a")

                            # REMOVED_SYNTAX_ERROR: async with instrumented_http_client.get( )
                            # REMOVED_SYNTAX_ERROR: test_service_containers["service_a"]["url"]
                            # REMOVED_SYNTAX_ERROR: ) as response:
                                # REMOVED_SYNTAX_ERROR: service_a_span.set_attribute("http.status_code", response.status)
                                # REMOVED_SYNTAX_ERROR: service_a_data = await response.text()

                                # Make HTTP call to service B
                                # REMOVED_SYNTAX_ERROR: with tracer.start_as_current_span("call_service_b") as service_b_span:
                                    # REMOVED_SYNTAX_ERROR: service_b_span.set_attribute("service.name", "service_b")

                                    # REMOVED_SYNTAX_ERROR: async with instrumented_http_client.get( )
                                    # REMOVED_SYNTAX_ERROR: test_service_containers["service_b"]["url"]
                                    # REMOVED_SYNTAX_ERROR: ) as response:
                                        # REMOVED_SYNTAX_ERROR: service_b_span.set_attribute("http.status_code", response.status)
                                        # REMOVED_SYNTAX_ERROR: service_b_data = await response.text()

                                        # REMOVED_SYNTAX_ERROR: parent_span.set_attribute("services.called", 2)
                                        # REMOVED_SYNTAX_ERROR: parent_span.set_status(trace.Status(trace.StatusCode.OK))

                                        # Force flush and wait for export
                                        # REMOVED_SYNTAX_ERROR: await tracer_manager.force_flush()
                                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(3)

                                        # Verify distributed trace structure
                                        # REMOVED_SYNTAX_ERROR: traces = await self._get_jaeger_traces(jaeger_container, "test_service")

                                        # Find our distributed trace
                                        # REMOVED_SYNTAX_ERROR: distributed_traces = []
                                        # REMOVED_SYNTAX_ERROR: for trace_data in traces:
                                            # REMOVED_SYNTAX_ERROR: spans = trace_data.get("spans", [])
                                            # REMOVED_SYNTAX_ERROR: operation_names = [span.get("operationName") for span in spans]

                                            # REMOVED_SYNTAX_ERROR: if "distributed_operation" in operation_names:
                                                # REMOVED_SYNTAX_ERROR: distributed_traces.append(trace_data)

                                                # REMOVED_SYNTAX_ERROR: assert len(distributed_traces) >= 1
                                                # REMOVED_SYNTAX_ERROR: trace_data = distributed_traces[0]
                                                # REMOVED_SYNTAX_ERROR: spans = trace_data["spans"]

                                                # Verify parent-child relationships
                                                # REMOVED_SYNTAX_ERROR: parent_spans = [item for item in []]
                                                # REMOVED_SYNTAX_ERROR: child_spans = [item for item in []]]

                                                # REMOVED_SYNTAX_ERROR: assert len(parent_spans) == 1
                                                # REMOVED_SYNTAX_ERROR: assert len(child_spans) >= 2

                                                # Verify parent-child relationship
                                                # REMOVED_SYNTAX_ERROR: parent_span = parent_spans[0]
                                                # REMOVED_SYNTAX_ERROR: for child_span in child_spans:
                                                    # REMOVED_SYNTAX_ERROR: assert child_span.get("traceID") == parent_span.get("traceID")

                                                    # Removed problematic line: @pytest.mark.asyncio
                                                    # Removed problematic line: async def test_error_span_tracking( )
                                                    # REMOVED_SYNTAX_ERROR: self,
                                                    # REMOVED_SYNTAX_ERROR: tracer_manager,
                                                    # REMOVED_SYNTAX_ERROR: jaeger_container
                                                    # REMOVED_SYNTAX_ERROR: ):
                                                        # REMOVED_SYNTAX_ERROR: """Test error tracking in spans."""
                                                        # REMOVED_SYNTAX_ERROR: tracer = tracer_manager.get_tracer("test_errors")

                                                        # Create span with error
                                                        # REMOVED_SYNTAX_ERROR: with tracer.start_as_current_span("error_operation") as span:
                                                            # REMOVED_SYNTAX_ERROR: span.set_attribute("operation.type", "error_test")

                                                            # REMOVED_SYNTAX_ERROR: try:
                                                                # Simulate an error
                                                                # REMOVED_SYNTAX_ERROR: raise ValueError("Test error for tracing")
                                                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                    # REMOVED_SYNTAX_ERROR: span.record_exception(e)
                                                                    # REMOVED_SYNTAX_ERROR: span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))

                                                                    # Force flush
                                                                    # REMOVED_SYNTAX_ERROR: await tracer_manager.force_flush()
                                                                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(2)

                                                                    # Verify error span in Jaeger
                                                                    # REMOVED_SYNTAX_ERROR: traces = await self._get_jaeger_traces(jaeger_container, "test_service")

                                                                    # REMOVED_SYNTAX_ERROR: error_spans = []
                                                                    # REMOVED_SYNTAX_ERROR: for trace_data in traces:
                                                                        # REMOVED_SYNTAX_ERROR: for span in trace_data.get("spans", []):
                                                                            # REMOVED_SYNTAX_ERROR: if span.get("operationName") == "error_operation":
                                                                                # REMOVED_SYNTAX_ERROR: error_spans.append(span)

                                                                                # REMOVED_SYNTAX_ERROR: assert len(error_spans) >= 1
                                                                                # REMOVED_SYNTAX_ERROR: error_span = error_spans[0]

                                                                                # Verify error tags
                                                                                # REMOVED_SYNTAX_ERROR: tags = {tag["key"]: tag["value"] for tag in error_span.get("tags", [])]
                                                                                # REMOVED_SYNTAX_ERROR: assert tags.get("error") == "true"
                                                                                # REMOVED_SYNTAX_ERROR: assert "Test error for tracing" in str(tags.get("error.message", ""))

                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                # Removed problematic line: async def test_custom_span_processor( )
                                                                                # REMOVED_SYNTAX_ERROR: self,
                                                                                # REMOVED_SYNTAX_ERROR: tracer_manager,
                                                                                # REMOVED_SYNTAX_ERROR: jaeger_container
                                                                                # REMOVED_SYNTAX_ERROR: ):
                                                                                    # REMOVED_SYNTAX_ERROR: """Test custom span processor functionality."""
                                                                                    # REMOVED_SYNTAX_ERROR: processed_spans = []

# REMOVED_SYNTAX_ERROR: class TestSpanProcessor(CustomSpanProcessor):
# REMOVED_SYNTAX_ERROR: def on_start(self, span, parent_context):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: super().on_start(span, parent_context)
    # Add custom attributes on span start
    # REMOVED_SYNTAX_ERROR: span.set_attribute("processor.custom", "true")

# REMOVED_SYNTAX_ERROR: async def on_end(self, span):
    # REMOVED_SYNTAX_ERROR: super().on_end(span)
    # REMOVED_SYNTAX_ERROR: processed_spans.append(span.name)

    # Add custom processor
    # REMOVED_SYNTAX_ERROR: custom_processor = TestSpanProcessor()
    # REMOVED_SYNTAX_ERROR: tracer_manager.add_span_processor(custom_processor)

    # REMOVED_SYNTAX_ERROR: tracer = tracer_manager.get_tracer("test_custom_processor")

    # Create spans to test processor
    # REMOVED_SYNTAX_ERROR: operations = ["operation_1", "operation_2", "operation_3"]
    # REMOVED_SYNTAX_ERROR: for operation in operations:
        # REMOVED_SYNTAX_ERROR: with tracer.start_as_current_span(operation) as span:
            # REMOVED_SYNTAX_ERROR: span.set_attribute("operation.number", operation.split("_")[1])
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.05)

            # Force flush
            # REMOVED_SYNTAX_ERROR: await tracer_manager.force_flush()
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(2)

            # Verify custom processor was called
            # REMOVED_SYNTAX_ERROR: assert len(processed_spans) >= 3
            # REMOVED_SYNTAX_ERROR: for operation in operations:
                # REMOVED_SYNTAX_ERROR: assert operation in processed_spans

                # Verify custom attributes were added
                # REMOVED_SYNTAX_ERROR: traces = await self._get_jaeger_traces(jaeger_container, "test_service")

                # REMOVED_SYNTAX_ERROR: custom_spans = []
                # REMOVED_SYNTAX_ERROR: for trace_data in traces:
                    # REMOVED_SYNTAX_ERROR: for span in trace_data.get("spans", []):
                        # REMOVED_SYNTAX_ERROR: if span.get("operationName") in operations:
                            # REMOVED_SYNTAX_ERROR: custom_spans.append(span)

                            # REMOVED_SYNTAX_ERROR: assert len(custom_spans) >= 3

                            # REMOVED_SYNTAX_ERROR: for span in custom_spans:
                                # REMOVED_SYNTAX_ERROR: tags = {tag["key"]: tag["value"] for tag in span.get("tags", [])]
                                # REMOVED_SYNTAX_ERROR: assert tags.get("processor.custom") == "true"

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_sampling_configuration( )
                                # REMOVED_SYNTAX_ERROR: self,
                                # REMOVED_SYNTAX_ERROR: tracer_manager,
                                # REMOVED_SYNTAX_ERROR: jaeger_container
                                # REMOVED_SYNTAX_ERROR: ):
                                    # REMOVED_SYNTAX_ERROR: """Test trace sampling configuration."""
                                    # Configure different sampling rates
                                    # REMOVED_SYNTAX_ERROR: high_sample_tracer = tracer_manager.get_tracer( )
                                    # REMOVED_SYNTAX_ERROR: "high_sample_tracer",
                                    # REMOVED_SYNTAX_ERROR: sampling_rate=1.0  # 100% sampling
                                    

                                    # REMOVED_SYNTAX_ERROR: low_sample_tracer = tracer_manager.get_tracer( )
                                    # REMOVED_SYNTAX_ERROR: "low_sample_tracer",
                                    # REMOVED_SYNTAX_ERROR: sampling_rate=0.1   # 10% sampling
                                    

                                    # Generate spans with high sampling
                                    # REMOVED_SYNTAX_ERROR: high_sample_spans = 0
                                    # REMOVED_SYNTAX_ERROR: for i in range(10):
                                        # REMOVED_SYNTAX_ERROR: with high_sample_tracer.start_as_current_span("formatted_string") as span:
                                            # REMOVED_SYNTAX_ERROR: span.set_attribute("sample.rate", "high")
                                            # REMOVED_SYNTAX_ERROR: high_sample_spans += 1

                                            # Generate spans with low sampling
                                            # REMOVED_SYNTAX_ERROR: low_sample_spans = 0
                                            # REMOVED_SYNTAX_ERROR: for i in range(100):
                                                # REMOVED_SYNTAX_ERROR: with low_sample_tracer.start_as_current_span("formatted_string") as span:
                                                    # REMOVED_SYNTAX_ERROR: span.set_attribute("sample.rate", "low")
                                                    # REMOVED_SYNTAX_ERROR: low_sample_spans += 1

                                                    # Force flush
                                                    # REMOVED_SYNTAX_ERROR: await tracer_manager.force_flush()
                                                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(3)

                                                    # Verify sampling behavior
                                                    # REMOVED_SYNTAX_ERROR: traces = await self._get_jaeger_traces(jaeger_container, "test_service")

                                                    # REMOVED_SYNTAX_ERROR: high_sampled = 0
                                                    # REMOVED_SYNTAX_ERROR: low_sampled = 0

                                                    # REMOVED_SYNTAX_ERROR: for trace_data in traces:
                                                        # REMOVED_SYNTAX_ERROR: for span in trace_data.get("spans", []):
                                                            # REMOVED_SYNTAX_ERROR: tags = {tag["key"]: tag["value"] for tag in span.get("tags", [])]
                                                            # REMOVED_SYNTAX_ERROR: if tags.get("sample.rate") == "high":
                                                                # REMOVED_SYNTAX_ERROR: high_sampled += 1
                                                                # REMOVED_SYNTAX_ERROR: elif tags.get("sample.rate") == "low":
                                                                    # REMOVED_SYNTAX_ERROR: low_sampled += 1

                                                                    # High sampling should capture most/all spans
                                                                    # REMOVED_SYNTAX_ERROR: assert high_sampled >= 8  # Allow some variance

                                                                    # Low sampling should capture significantly fewer spans
                                                                    # REMOVED_SYNTAX_ERROR: assert low_sampled < high_sampled

                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                    # Removed problematic line: async def test_trace_context_propagation( )
                                                                    # REMOVED_SYNTAX_ERROR: self,
                                                                    # REMOVED_SYNTAX_ERROR: tracer_manager,
                                                                    # REMOVED_SYNTAX_ERROR: instrumented_http_client,
                                                                    # REMOVED_SYNTAX_ERROR: test_service_containers,
                                                                    # REMOVED_SYNTAX_ERROR: jaeger_container
                                                                    # REMOVED_SYNTAX_ERROR: ):
                                                                        # REMOVED_SYNTAX_ERROR: """Test trace context propagation across service boundaries."""
                                                                        # REMOVED_SYNTAX_ERROR: tracer = tracer_manager.get_tracer("test_context_propagation")

                                                                        # Create parent span
                                                                        # REMOVED_SYNTAX_ERROR: with tracer.start_as_current_span("parent_operation") as parent_span:
                                                                            # REMOVED_SYNTAX_ERROR: parent_trace_id = parent_span.get_span_context().trace_id
                                                                            # REMOVED_SYNTAX_ERROR: parent_span.set_attribute("trace.role", "parent")

                                                                            # Make nested HTTP calls that should propagate context
                                                                            # REMOVED_SYNTAX_ERROR: async with instrumented_http_client.get( )
                                                                            # REMOVED_SYNTAX_ERROR: test_service_containers["service_a"]["url"],
                                                                            # REMOVED_SYNTAX_ERROR: headers={"X-Custom-Header": "test"}
                                                                            # REMOVED_SYNTAX_ERROR: ) as response_a:
                                                                                # REMOVED_SYNTAX_ERROR: assert response_a.status == 200

                                                                                # Create child span manually
                                                                                # REMOVED_SYNTAX_ERROR: with tracer.start_as_current_span("manual_child") as child_span:
                                                                                    # REMOVED_SYNTAX_ERROR: child_trace_id = child_span.get_span_context().trace_id
                                                                                    # REMOVED_SYNTAX_ERROR: child_span.set_attribute("trace.role", "child")

                                                                                    # HTTP call within child span
                                                                                    # REMOVED_SYNTAX_ERROR: async with instrumented_http_client.get( )
                                                                                    # REMOVED_SYNTAX_ERROR: test_service_containers["service_b"]["url"]
                                                                                    # REMOVED_SYNTAX_ERROR: ) as response_b:
                                                                                        # REMOVED_SYNTAX_ERROR: assert response_b.status == 200

                                                                                        # Force flush
                                                                                        # REMOVED_SYNTAX_ERROR: await tracer_manager.force_flush()
                                                                                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(3)

                                                                                        # Verify context propagation
                                                                                        # REMOVED_SYNTAX_ERROR: traces = await self._get_jaeger_traces(jaeger_container, "test_service")

                                                                                        # REMOVED_SYNTAX_ERROR: parent_trace = None
                                                                                        # REMOVED_SYNTAX_ERROR: for trace_data in traces:
                                                                                            # REMOVED_SYNTAX_ERROR: spans = trace_data.get("spans", [])
                                                                                            # REMOVED_SYNTAX_ERROR: for span in spans:
                                                                                                # REMOVED_SYNTAX_ERROR: tags = {tag["key"]: tag["value"] for tag in span.get("tags", [])]
                                                                                                # REMOVED_SYNTAX_ERROR: if tags.get("trace.role") == "parent":
                                                                                                    # REMOVED_SYNTAX_ERROR: parent_trace = trace_data
                                                                                                    # REMOVED_SYNTAX_ERROR: break

                                                                                                    # REMOVED_SYNTAX_ERROR: assert parent_trace is not None

                                                                                                    # Verify all spans in the trace share the same trace ID
                                                                                                    # REMOVED_SYNTAX_ERROR: spans = parent_trace["spans"]
                                                                                                    # REMOVED_SYNTAX_ERROR: trace_ids = set(span["traceID"] for span in spans)
                                                                                                    # REMOVED_SYNTAX_ERROR: assert len(trace_ids) == 1  # All spans should have same trace ID

                                                                                                    # Verify parent-child relationships exist
                                                                                                    # REMOVED_SYNTAX_ERROR: span_references = []
                                                                                                    # REMOVED_SYNTAX_ERROR: for span in spans:
                                                                                                        # REMOVED_SYNTAX_ERROR: references = span.get("references", [])
                                                                                                        # REMOVED_SYNTAX_ERROR: span_references.extend(references)

                                                                                                        # Should have child-of references
                                                                                                        # REMOVED_SYNTAX_ERROR: child_of_refs = [item for item in []]
                                                                                                        # REMOVED_SYNTAX_ERROR: assert len(child_of_refs) > 0