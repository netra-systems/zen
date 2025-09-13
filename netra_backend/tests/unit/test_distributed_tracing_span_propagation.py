"""
Test iteration 61: Distributed tracing span propagation validation.
Tests span context preservation across service boundaries and async operations.
"""
import pytest
import asyncio
from shared.isolated_environment import IsolatedEnvironment

# Handle optional OpenTelemetry dependency
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    # Mock OpenTelemetry components if not available
    OPENTELEMETRY_AVAILABLE = False
    trace = trace_instance  # Initialize appropriate service
    TracerProvider = Mock
    TraceContextTextMapPropagator = Mock


    class TestDistributedTracingSpanPropagation:
        """Validates span context propagation across distributed operations."""

        @pytest.fixture
        def tracer_setup(self):
            """Use real service instance."""
        # TODO: Initialize real service
            """Setup OpenTelemetry tracer for testing."""
            if not OPENTELEMETRY_AVAILABLE:
                pytest.skip("OpenTelemetry not available - skipping tracing tests", allow_module_level=True)
                tracer_provider = TracerProvider()
                trace.set_tracer_provider(tracer_provider)
                return trace.get_tracer(__name__)

            @pytest.mark.skipif(not OPENTELEMETRY_AVAILABLE, reason="OpenTelemetry not available")
            def test_span_context_preservation_across_services(self, tracer_setup):
                """Ensures span context is preserved when crossing service boundaries."""
                tracer = tracer_setup
                propagator = TraceContextTextMapPropagator()

                with tracer.start_as_current_span("parent_operation") as parent_span:
            # Simulate service boundary crossing
                    headers = {}
                    propagator.inject(headers)

            # Verify trace context headers are present
                    assert "traceparent" in headers
                    assert len(headers["traceparent"]) > 0

            # Extract context on receiving service
                    context = propagator.extract(headers)
                    with tracer.start_as_current_span("child_operation", context=context) as child_span:
                # Verify parent-child relationship
                        parent_context = parent_span.get_span_context()
                        child_context = child_span.get_span_context()
                        assert parent_context.trace_id == child_context.trace_id

                        @pytest.mark.asyncio
                        @pytest.mark.skipif(not OPENTELEMETRY_AVAILABLE, reason="OpenTelemetry not available")
                        async def test_async_span_context_preservation(self, tracer_setup):
                            """Validates span context preservation in async operations."""
                            tracer = tracer_setup

                            async def async_operation():
            # Verify context is preserved across await boundaries
                                current_span = trace.get_current_span()
                                await asyncio.sleep(0.001)
                                post_await_span = trace.get_current_span()
                                assert current_span.get_span_context().span_id == post_await_span.get_span_context().span_id
                                await asyncio.sleep(0)
                                return "success"

                            with tracer.start_as_current_span("async_parent") as span:
                                result = await async_operation()
                                assert result == "success"
                                assert span.get_span_context().trace_id is not None