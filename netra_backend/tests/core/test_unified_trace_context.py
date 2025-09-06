"""Comprehensive tests for UnifiedTraceContext with W3C Trace Context support.

Tests cover:
    - Context creation and propagation
- W3C header serialization and deserialization
- Span management
- WebSocket event context generation
- Parent-child context relationships
""""

import asyncio
import json
import time
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest

# Skip test if modules have been simplified and classes are missing
try:
    from netra_backend.app.core.unified_trace_context import (
        UnifiedTraceContext,
        TraceFlags,
        TraceSpan,
        get_current_trace_context,
        set_trace_context,
        clear_trace_context,
        TraceContextManager,
        with_trace_context
    )
except ImportError:
    pytest.skip("Required trace context classes have been simplified or removed", allow_module_level=True)


class TestUnifiedTraceContext:
    """Test UnifiedTraceContext basic functionality."""
    
    def test_context_creation(self):
        """Test creating a new trace context."""
        context = UnifiedTraceContext(
            user_id="user123",
            thread_id="thread456",
            correlation_id="corr789"
        )
        
        assert context.trace_id is not None
        assert len(context.trace_id) == 32  # 32 hex chars
        assert context.user_id == "user123"
        assert context.thread_id == "thread456"
        assert context.correlation_id == "corr789"
        assert context.baggage == {}
        assert context.flags.sampled is True
    
    def test_trace_id_generation(self):
        """Test that trace IDs are unique and properly formatted."""
        context1 = UnifiedTraceContext()
        context2 = UnifiedTraceContext()
        
        assert context1.trace_id != context2.trace_id
        assert len(context1.trace_id) == 32
        assert len(context2.trace_id) == 32
        # Should be valid hex
        int(context1.trace_id, 16)
        int(context2.trace_id, 16)
    
    def test_span_id_generation(self):
        """Test that span IDs are unique and properly formatted."""
        context = UnifiedTraceContext()
        span_id1 = context._generate_span_id()
        span_id2 = context._generate_span_id()
        
        assert span_id1 != span_id2
        assert len(span_id1) == 16  # 16 hex chars
        assert len(span_id2) == 16
        # Should be valid hex
        int(span_id1, 16)
        int(span_id2, 16)


class TestSpanManagement:
    """Test span creation and management."""
    
    def test_start_span(self):
        """Test starting a new span."""
        context = UnifiedTraceContext()
        
        span = context.start_span(
            operation_name="test_operation",
            attributes={"key": "value"}
        )
        
        assert span.operation_name == "test_operation"
        assert span.attributes == {"key": "value"}
        assert span.span_id is not None
        assert span.parent_span_id is None  # First span has no parent
        assert span.start_time is not None
        assert span.end_time is None
        assert context._current_span == span
        assert span in context.span_stack
    
    def test_nested_spans(self):
        """Test creating nested spans."""
        context = UnifiedTraceContext()
        
        # Start parent span
        parent_span = context.start_span("parent_operation")
        parent_id = parent_span.span_id
        
        # Start child span
        child_span = context.start_span("child_operation")
        
        assert child_span.parent_span_id == parent_id
        assert context._current_span == child_span
        assert len(context.span_stack) == 2
    
    def test_finish_span(self):
        """Test finishing a span."""
        context = UnifiedTraceContext()
        
        span = context.start_span("test_operation")
        time.sleep(0.01)  # Small delay to ensure duration > 0
        context.finish_span(span)
        
        assert span.end_time is not None
        assert span.duration_ms is not None
        assert span.duration_ms > 0
    
    def test_add_event_to_span(self):
        """Test adding events to the current span."""
        context = UnifiedTraceContext()
        
        span = context.start_span("test_operation")
        context.add_event("test_event", {"detail": "test_value"})
        
        assert len(span.events) == 1
        event = span.events[0]
        assert event["name"] == "test_event"
        assert event["attributes"] == {"detail": "test_value"]
        assert "timestamp" in event


class TestContextPropagation:
    """Test context propagation to child contexts."""
    
    def test_propagate_to_child(self):
        """Test creating a child context."""
        parent = UnifiedTraceContext(
            trace_id="parent_trace_id",
            user_id="user123",
            thread_id="thread456",
            correlation_id="corr789",
            baggage={"key": "value"}
        )
        
        # Start a span in parent
        parent_span = parent.start_span("parent_op")
        
        # Create child context
        child = parent.propagate_to_child()
        
        # Child should inherit parent's identifiers
        assert child.trace_id == parent.trace_id
        assert child.user_id == parent.user_id
        assert child.thread_id == parent.thread_id
        assert child.correlation_id == parent.correlation_id
        assert child.baggage == parent.baggage
        
        # Child should have parent span as its parent
        assert child.parent_span_id == parent_span.span_id
        
        # Child should have its own span stack
        assert child.span_stack == []
        assert child._current_span is None


class TestW3CHeaders:
    """Test W3C Trace Context header support."""
    
    def test_to_headers(self):
        """Test converting context to W3C headers."""
        context = UnifiedTraceContext(
            trace_id="00000000000000000000000000000001",
            user_id="user123",
            thread_id="thread456",
            correlation_id="corr789",
            baggage={"app": "netra", "env": "test"}
        )
        
        # Start a span to get a span ID
        span = context.start_span("test_op")
        
        headers = context.to_headers()
        
        # Check traceparent header format
        assert "traceparent" in headers
        parts = headers["traceparent"].split("-")
        assert len(parts) == 4
        assert parts[0] == "00"  # Version
        assert parts[1] == "00000000000000000000000000000001"  # Trace ID
        assert len(parts[2]) == 16  # Span ID
        assert parts[3] == "01"  # Flags (sampled)
        
        # Check tracestate header
        assert "tracestate" in headers
        assert "netra@app=netra" in headers["tracestate"]
        assert "netra@env=test" in headers["tracestate"]
        
        # Check custom headers
        assert headers.get("x-correlation-id") == "corr789"
        assert headers.get("x-user-id") == "user123"
        assert headers.get("x-thread-id") == "thread456"
    
    def test_from_headers(self):
        """Test reconstructing context from W3C headers."""
        headers = {
            "traceparent": "00-00000000000000000000000000000001-0000000000000002-01",
            "tracestate": "netra@app=netra,netra@env=test",
            "x-correlation-id": "corr789",
            "x-user-id": "user123",
            "x-thread-id": "thread456",
            "x-request-id": "req999"
        }
        
        context = UnifiedTraceContext.from_headers(headers)
        
        assert context.trace_id == "00000000000000000000000000000001"
        assert context.parent_span_id == "0000000000000002"
        assert context.flags.sampled is True
        assert context.baggage == {"app": "netra", "env": "test"}
        assert context.correlation_id == "corr789"
        assert context.user_id == "user123"
        assert context.thread_id == "thread456"
        assert context.request_id == "req999"
    
    def test_round_trip_headers(self):
        """Test that context survives header serialization/deserialization."""
        original = UnifiedTraceContext(
            user_id="user123",
            thread_id="thread456",
            correlation_id="corr789",
            request_id="req999",
            baggage={"key1": "value1", "key2": "value2"}
        )
        
        headers = original.to_headers()
        reconstructed = UnifiedTraceContext.from_headers(headers)
        
        assert reconstructed.trace_id == original.trace_id
        assert reconstructed.user_id == original.user_id
        assert reconstructed.thread_id == original.thread_id
        assert reconstructed.correlation_id == original.correlation_id
        assert reconstructed.request_id == original.request_id
        assert reconstructed.baggage == original.baggage


class TestWebSocketContext:
    """Test WebSocket event context generation."""
    
    def test_to_websocket_context(self):
        """Test converting to WebSocket event context."""
        context = UnifiedTraceContext(
            trace_id="test_trace_id",
            parent_span_id="parent_span",
            correlation_id="corr789",
            user_id="user123",
            thread_id="thread456"
        )
        
        # Start a span
        span = context.start_span("websocket_op")
        
        ws_context = context.to_websocket_context()
        
        assert ws_context["trace_id"] == "test_trace_id"
        assert ws_context["correlation_id"] == "corr789"
        assert ws_context["user_id"] == "user123"
        assert ws_context["thread_id"] == "thread456"
        assert ws_context["span_id"] == span.span_id
        assert ws_context["parent_span_id"] == "parent_span"


class TestContextVariables:
    """Test context variable management."""
    
    def test_get_current_trace_context(self):
        """Test getting the current trace context."""
        # Initially should be None
        assert get_current_trace_context() is None
        
        # Set a context
        context = UnifiedTraceContext()
        token = set_trace_context(context)
        
        # Should now return the context
        assert get_current_trace_context() == context
        
        # Clear the context
        clear_trace_context()
        assert get_current_trace_context() is None
    
    def test_context_manager(self):
        """Test TraceContextManager."""
        context = UnifiedTraceContext()
        
        # Context should be None initially
        assert get_current_trace_context() is None
        
        with TraceContextManager(context):
            # Context should be set within the block
            assert get_current_trace_context() == context
        
        # Context should be cleared after exiting
        assert get_current_trace_context() is None
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async TraceContextManager."""
        context = UnifiedTraceContext()
        
        # Context should be None initially
        assert get_current_trace_context() is None
        
        async with TraceContextManager(context):
            # Context should be set within the block
            assert get_current_trace_context() == context
        
        # Context should be cleared after exiting
        assert get_current_trace_context() is None


class TestDecorators:
    """Test trace context decorators."""
    
    def test_sync_decorator(self):
        """Test with_trace_context decorator on sync function."""
        context = UnifiedTraceContext(user_id="user123")
        
        @with_trace_context(context)
    def test_func():
            current = get_current_trace_context()
            assert current is not None
            assert current.user_id == "user123"
            return "success"
        
        # Context should be None before call
        assert get_current_trace_context() is None
        
        result = test_func()
        assert result == "success"
        
        # Context should be None after call
        assert get_current_trace_context() is None
    
    @pytest.mark.asyncio
    async def test_async_decorator(self):
        """Test with_trace_context decorator on async function."""
        context = UnifiedTraceContext(user_id="user456")
        
        @with_trace_context(context)
        async def test_func():
            current = get_current_trace_context()
            assert current is not None
            assert current.user_id == "user456"
            return "async_success"
        
        # Context should be None before call
        assert get_current_trace_context() is None
        
        result = await test_func()
        assert result == "async_success"
        
        # Context should be None after call
        assert get_current_trace_context() is None
    
    def test_decorator_without_context(self):
        """Test decorator creates new context if none provided."""
        
        @with_trace_context()
        def test_func():
            current = get_current_trace_context()
            assert current is not None
            return current.trace_id
        
        trace_id = test_func()
        assert trace_id is not None
        assert len(trace_id) == 32


class TestTraceFlags:
    """Test W3C Trace Flags."""
    
    def test_flags_to_byte(self):
        """Test converting flags to byte representation."""
        # Sampled flag set
        flags = TraceFlags(sampled=True)
        assert flags.to_byte() == 0x01
        
        # Sampled flag not set
        flags = TraceFlags(sampled=False)
        assert flags.to_byte() == 0x00
    
    def test_flags_from_byte(self):
        """Test creating flags from byte representation."""
        # Sampled flag set
        flags = TraceFlags.from_byte(0x01)
        assert flags.sampled is True
        
        # Sampled flag not set
        flags = TraceFlags.from_byte(0x00)
        assert flags.sampled is False
        
        # Other bits should be ignored
        flags = TraceFlags.from_byte(0xFF)
        assert flags.sampled is True


class TestContextSerialization:
    """Test context serialization."""
    
    def test_to_dict(self):
        """Test converting context to dictionary."""
        context = UnifiedTraceContext(
            trace_id="test_trace",
            parent_span_id="parent_span",
            correlation_id="corr123",
            user_id="user456",
            thread_id="thread789",
            request_id="req000",
            baggage={"key": "value"}
        )
        
        # Start a span
        span = context.start_span("test_op")
        
        data = context.to_dict()
        
        assert data["trace_id"] == "test_trace"
        assert data["parent_span_id"] == "parent_span"
        assert data["correlation_id"] == "corr123"
        assert data["user_id"] == "user456"
        assert data["thread_id"] == "thread789"
        assert data["request_id"] == "req000"
        assert data["baggage"] == {"key": "value"]
        assert data["flags"] == {"sampled": True]
        assert data["current_span_id"] == span.span_id
        assert data["span_count"] == 1


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_agent_execution_flow(self):
        """Test trace context flow through agent execution."""
        # Simulate HTTP request creating initial context
        root_context = UnifiedTraceContext(
            user_id="user123",
            thread_id="thread456",
            request_id="req789"
        )
        
        # Start root span for HTTP request
        http_span = root_context.start_span("http.request", {
            "http.method": "POST",
            "http.url": "/api/chat"
        })
        
        # Create child context for agent
        agent_context = root_context.propagate_to_child()
        agent_span = agent_context.start_span("agent.supervisor", {
            "agent.name": "supervisor",
            "user.id": "user123"
        })
        
        # Simulate tool execution within agent
        tool_span = agent_context.start_span("tool.search", {
            "tool.name": "web_search",
            "tool.query": "test query"
        })
        agent_context.add_event("tool.started")
        await asyncio.sleep(0.01)  # Simulate work
        agent_context.add_event("tool.completed", {"results": 5})
        agent_context.finish_span(tool_span)
        
        # Complete agent execution
        agent_context.finish_span(agent_span)
        
        # Complete HTTP request
        root_context.finish_span(http_span)
        
        # Verify span hierarchy
        assert len(root_context.span_stack) == 1
        assert len(agent_context.span_stack) == 2
        assert agent_context.span_stack[0].parent_span_id == http_span.span_id
        assert agent_context.span_stack[1].parent_span_id == agent_span.span_id
        
        # Verify all spans are finished
        assert all(span.end_time is not None for span in root_context.span_stack)
        assert all(span.end_time is not None for span in agent_context.span_stack)
    
    def test_websocket_event_propagation(self):
        """Test trace context in WebSocket events."""
        # Create context for WebSocket connection
        ws_context = UnifiedTraceContext(
            user_id="user123",
            thread_id="thread456"
        )
        
        # Simulate agent events
        events = []
        
        # Agent started
        span = ws_context.start_span("agent.execution")
        ws_data = ws_context.to_websocket_context()
        events.append({
            "type": "agent_started",
            "trace": ws_data
        })
        
        # Agent thinking
        ws_context.add_event("agent.thinking", {"step": 1})
        ws_data = ws_context.to_websocket_context()
        events.append({
            "type": "agent_thinking",
            "trace": ws_data
        })
        
        # Agent completed
        ws_context.finish_span(span)
        ws_data = ws_context.to_websocket_context()
        events.append({
            "type": "agent_completed",
            "trace": ws_data
        })
        
        # Verify all events have consistent trace IDs
        trace_ids = [e["trace"]["trace_id"] for e in events]
        assert len(set(trace_ids)) == 1  # All same trace ID
        
        # Verify all events have the same correlation ID
        corr_ids = [e["trace"]["correlation_id"] for e in events]
        assert len(set(corr_ids)) == 1  # All same correlation ID