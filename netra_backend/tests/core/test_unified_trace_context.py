# REMOVED_SYNTAX_ERROR: '''Comprehensive tests for UnifiedTraceContext with W3C Trace Context support.

# REMOVED_SYNTAX_ERROR: Tests cover:
    # REMOVED_SYNTAX_ERROR: - Context creation and propagation
    # REMOVED_SYNTAX_ERROR: - W3C header serialization and deserialization
    # REMOVED_SYNTAX_ERROR: - Span management
    # REMOVED_SYNTAX_ERROR: - WebSocket event context generation
    # REMOVED_SYNTAX_ERROR: - Parent-child context relationships
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import pytest

    # Skip test if modules have been simplified and classes are missing
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_trace_context import ( )
        # REMOVED_SYNTAX_ERROR: UnifiedTraceContext,
        # REMOVED_SYNTAX_ERROR: TraceFlags,
        # REMOVED_SYNTAX_ERROR: TraceSpan,
        # REMOVED_SYNTAX_ERROR: get_current_trace_context,
        # REMOVED_SYNTAX_ERROR: set_trace_context,
        # REMOVED_SYNTAX_ERROR: clear_trace_context,
        # REMOVED_SYNTAX_ERROR: TraceContextManager,
        # REMOVED_SYNTAX_ERROR: with_trace_context
        
        # REMOVED_SYNTAX_ERROR: except ImportError:
            # REMOVED_SYNTAX_ERROR: pytest.skip("Required trace context classes have been simplified or removed", allow_module_level=True)


# REMOVED_SYNTAX_ERROR: class TestUnifiedTraceContext:
    # REMOVED_SYNTAX_ERROR: """Test UnifiedTraceContext basic functionality."""

# REMOVED_SYNTAX_ERROR: def test_context_creation(self):
    # REMOVED_SYNTAX_ERROR: """Test creating a new trace context."""
    # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread456",
    # REMOVED_SYNTAX_ERROR: correlation_id="corr789"
    

    # REMOVED_SYNTAX_ERROR: assert context.trace_id is not None
    # REMOVED_SYNTAX_ERROR: assert len(context.trace_id) == 32  # 32 hex chars
    # REMOVED_SYNTAX_ERROR: assert context.user_id == "user123"
    # REMOVED_SYNTAX_ERROR: assert context.thread_id == "thread456"
    # REMOVED_SYNTAX_ERROR: assert context.correlation_id == "corr789"
    # REMOVED_SYNTAX_ERROR: assert context.baggage == {}
    # REMOVED_SYNTAX_ERROR: assert context.flags.sampled is True

# REMOVED_SYNTAX_ERROR: def test_trace_id_generation(self):
    # REMOVED_SYNTAX_ERROR: """Test that trace IDs are unique and properly formatted."""
    # REMOVED_SYNTAX_ERROR: context1 = UnifiedTraceContext()
    # REMOVED_SYNTAX_ERROR: context2 = UnifiedTraceContext()

    # REMOVED_SYNTAX_ERROR: assert context1.trace_id != context2.trace_id
    # REMOVED_SYNTAX_ERROR: assert len(context1.trace_id) == 32
    # REMOVED_SYNTAX_ERROR: assert len(context2.trace_id) == 32
    # Should be valid hex
    # REMOVED_SYNTAX_ERROR: int(context1.trace_id, 16)
    # REMOVED_SYNTAX_ERROR: int(context2.trace_id, 16)

# REMOVED_SYNTAX_ERROR: def test_span_id_generation(self):
    # REMOVED_SYNTAX_ERROR: """Test that span IDs are unique and properly formatted."""
    # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext()
    # REMOVED_SYNTAX_ERROR: span_id1 = context._generate_span_id()
    # REMOVED_SYNTAX_ERROR: span_id2 = context._generate_span_id()

    # REMOVED_SYNTAX_ERROR: assert span_id1 != span_id2
    # REMOVED_SYNTAX_ERROR: assert len(span_id1) == 16  # 16 hex chars
    # REMOVED_SYNTAX_ERROR: assert len(span_id2) == 16
    # Should be valid hex
    # REMOVED_SYNTAX_ERROR: int(span_id1, 16)
    # REMOVED_SYNTAX_ERROR: int(span_id2, 16)


# REMOVED_SYNTAX_ERROR: class TestSpanManagement:
    # REMOVED_SYNTAX_ERROR: """Test span creation and management."""

# REMOVED_SYNTAX_ERROR: def test_start_span(self):
    # REMOVED_SYNTAX_ERROR: """Test starting a new span."""
    # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext()

    # REMOVED_SYNTAX_ERROR: span = context.start_span( )
    # REMOVED_SYNTAX_ERROR: operation_name="test_operation",
    # REMOVED_SYNTAX_ERROR: attributes={"key": "value"}
    

    # REMOVED_SYNTAX_ERROR: assert span.operation_name == "test_operation"
    # REMOVED_SYNTAX_ERROR: assert span.attributes == {"key": "value"}
    # REMOVED_SYNTAX_ERROR: assert span.span_id is not None
    # REMOVED_SYNTAX_ERROR: assert span.parent_span_id is None  # First span has no parent
    # REMOVED_SYNTAX_ERROR: assert span.start_time is not None
    # REMOVED_SYNTAX_ERROR: assert span.end_time is None
    # REMOVED_SYNTAX_ERROR: assert context._current_span == span
    # REMOVED_SYNTAX_ERROR: assert span in context.span_stack

# REMOVED_SYNTAX_ERROR: def test_nested_spans(self):
    # REMOVED_SYNTAX_ERROR: """Test creating nested spans."""
    # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext()

    # Start parent span
    # REMOVED_SYNTAX_ERROR: parent_span = context.start_span("parent_operation")
    # REMOVED_SYNTAX_ERROR: parent_id = parent_span.span_id

    # Start child span
    # REMOVED_SYNTAX_ERROR: child_span = context.start_span("child_operation")

    # REMOVED_SYNTAX_ERROR: assert child_span.parent_span_id == parent_id
    # REMOVED_SYNTAX_ERROR: assert context._current_span == child_span
    # REMOVED_SYNTAX_ERROR: assert len(context.span_stack) == 2

# REMOVED_SYNTAX_ERROR: def test_finish_span(self):
    # REMOVED_SYNTAX_ERROR: """Test finishing a span."""
    # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext()

    # REMOVED_SYNTAX_ERROR: span = context.start_span("test_operation")
    # REMOVED_SYNTAX_ERROR: time.sleep(0.01)  # Small delay to ensure duration > 0
    # REMOVED_SYNTAX_ERROR: context.finish_span(span)

    # REMOVED_SYNTAX_ERROR: assert span.end_time is not None
    # REMOVED_SYNTAX_ERROR: assert span.duration_ms is not None
    # REMOVED_SYNTAX_ERROR: assert span.duration_ms > 0

# REMOVED_SYNTAX_ERROR: def test_add_event_to_span(self):
    # REMOVED_SYNTAX_ERROR: """Test adding events to the current span."""
    # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext()

    # REMOVED_SYNTAX_ERROR: span = context.start_span("test_operation")
    # REMOVED_SYNTAX_ERROR: context.add_event("test_event", {"detail": "test_value"})

    # REMOVED_SYNTAX_ERROR: assert len(span.events) == 1
    # REMOVED_SYNTAX_ERROR: event = span.events[0]
    # REMOVED_SYNTAX_ERROR: assert event["name"] == "test_event"
    # REMOVED_SYNTAX_ERROR: assert event["attributes"] == {"detail": "test_value"]
    # REMOVED_SYNTAX_ERROR: assert "timestamp" in event


# REMOVED_SYNTAX_ERROR: class TestContextPropagation:
    # REMOVED_SYNTAX_ERROR: """Test context propagation to child contexts."""

# REMOVED_SYNTAX_ERROR: def test_propagate_to_child(self):
    # REMOVED_SYNTAX_ERROR: """Test creating a child context."""
    # REMOVED_SYNTAX_ERROR: parent = UnifiedTraceContext( )
    # REMOVED_SYNTAX_ERROR: trace_id="parent_trace_id",
    # REMOVED_SYNTAX_ERROR: user_id="user123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread456",
    # REMOVED_SYNTAX_ERROR: correlation_id="corr789",
    # REMOVED_SYNTAX_ERROR: baggage={"key": "value"}
    

    # Start a span in parent
    # REMOVED_SYNTAX_ERROR: parent_span = parent.start_span("parent_op")

    # Create child context
    # REMOVED_SYNTAX_ERROR: child = parent.propagate_to_child()

    # Child should inherit parent's identifiers
    # REMOVED_SYNTAX_ERROR: assert child.trace_id == parent.trace_id
    # REMOVED_SYNTAX_ERROR: assert child.user_id == parent.user_id
    # REMOVED_SYNTAX_ERROR: assert child.thread_id == parent.thread_id
    # REMOVED_SYNTAX_ERROR: assert child.correlation_id == parent.correlation_id
    # REMOVED_SYNTAX_ERROR: assert child.baggage == parent.baggage

    # Child should have parent span as its parent
    # REMOVED_SYNTAX_ERROR: assert child.parent_span_id == parent_span.span_id

    # Child should have its own span stack
    # REMOVED_SYNTAX_ERROR: assert child.span_stack == []
    # REMOVED_SYNTAX_ERROR: assert child._current_span is None


# REMOVED_SYNTAX_ERROR: class TestW3CHeaders:
    # REMOVED_SYNTAX_ERROR: """Test W3C Trace Context header support."""

# REMOVED_SYNTAX_ERROR: def test_to_headers(self):
    # REMOVED_SYNTAX_ERROR: """Test converting context to W3C headers."""
    # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext( )
    # REMOVED_SYNTAX_ERROR: trace_id="00000000000000000000000000000001",
    # REMOVED_SYNTAX_ERROR: user_id="user123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread456",
    # REMOVED_SYNTAX_ERROR: correlation_id="corr789",
    # REMOVED_SYNTAX_ERROR: baggage={"app": "netra", "env": "test"}
    

    # Start a span to get a span ID
    # REMOVED_SYNTAX_ERROR: span = context.start_span("test_op")

    # REMOVED_SYNTAX_ERROR: headers = context.to_headers()

    # Check traceparent header format
    # REMOVED_SYNTAX_ERROR: assert "traceparent" in headers
    # REMOVED_SYNTAX_ERROR: parts = headers["traceparent"].split("-")
    # REMOVED_SYNTAX_ERROR: assert len(parts) == 4
    # REMOVED_SYNTAX_ERROR: assert parts[0] == "00"  # Version
    # REMOVED_SYNTAX_ERROR: assert parts[1] == "00000000000000000000000000000001"  # Trace ID
    # REMOVED_SYNTAX_ERROR: assert len(parts[2]) == 16  # Span ID
    # REMOVED_SYNTAX_ERROR: assert parts[3] == "01"  # Flags (sampled)

    # Check tracestate header
    # REMOVED_SYNTAX_ERROR: assert "tracestate" in headers
    # REMOVED_SYNTAX_ERROR: assert "netra@app=netra" in headers["tracestate"]
    # REMOVED_SYNTAX_ERROR: assert "netra@env=test" in headers["tracestate"]

    # Check custom headers
    # REMOVED_SYNTAX_ERROR: assert headers.get("x-correlation-id") == "corr789"
    # REMOVED_SYNTAX_ERROR: assert headers.get("x-user-id") == "user123"
    # REMOVED_SYNTAX_ERROR: assert headers.get("x-thread-id") == "thread456"

# REMOVED_SYNTAX_ERROR: def test_from_headers(self):
    # REMOVED_SYNTAX_ERROR: """Test reconstructing context from W3C headers."""
    # REMOVED_SYNTAX_ERROR: headers = { )
    # REMOVED_SYNTAX_ERROR: "traceparent": "00-00000000000000000000000000000001-0000000000000002-01",
    # REMOVED_SYNTAX_ERROR: "tracestate": "netra@app=netra,netra@env=test",
    # REMOVED_SYNTAX_ERROR: "x-correlation-id": "corr789",
    # REMOVED_SYNTAX_ERROR: "x-user-id": "user123",
    # REMOVED_SYNTAX_ERROR: "x-thread-id": "thread456",
    # REMOVED_SYNTAX_ERROR: "x-request-id": "req999"
    

    # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext.from_headers(headers)

    # REMOVED_SYNTAX_ERROR: assert context.trace_id == "00000000000000000000000000000001"
    # REMOVED_SYNTAX_ERROR: assert context.parent_span_id == "0000000000000002"
    # REMOVED_SYNTAX_ERROR: assert context.flags.sampled is True
    # REMOVED_SYNTAX_ERROR: assert context.baggage == {"app": "netra", "env": "test"}
    # REMOVED_SYNTAX_ERROR: assert context.correlation_id == "corr789"
    # REMOVED_SYNTAX_ERROR: assert context.user_id == "user123"
    # REMOVED_SYNTAX_ERROR: assert context.thread_id == "thread456"
    # REMOVED_SYNTAX_ERROR: assert context.request_id == "req999"

# REMOVED_SYNTAX_ERROR: def test_round_trip_headers(self):
    # REMOVED_SYNTAX_ERROR: """Test that context survives header serialization/deserialization."""
    # REMOVED_SYNTAX_ERROR: original = UnifiedTraceContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread456",
    # REMOVED_SYNTAX_ERROR: correlation_id="corr789",
    # REMOVED_SYNTAX_ERROR: request_id="req999",
    # REMOVED_SYNTAX_ERROR: baggage={"key1": "value1", "key2": "value2"}
    

    # REMOVED_SYNTAX_ERROR: headers = original.to_headers()
    # REMOVED_SYNTAX_ERROR: reconstructed = UnifiedTraceContext.from_headers(headers)

    # REMOVED_SYNTAX_ERROR: assert reconstructed.trace_id == original.trace_id
    # REMOVED_SYNTAX_ERROR: assert reconstructed.user_id == original.user_id
    # REMOVED_SYNTAX_ERROR: assert reconstructed.thread_id == original.thread_id
    # REMOVED_SYNTAX_ERROR: assert reconstructed.correlation_id == original.correlation_id
    # REMOVED_SYNTAX_ERROR: assert reconstructed.request_id == original.request_id
    # REMOVED_SYNTAX_ERROR: assert reconstructed.baggage == original.baggage


# REMOVED_SYNTAX_ERROR: class TestWebSocketContext:
    # REMOVED_SYNTAX_ERROR: """Test WebSocket event context generation."""

# REMOVED_SYNTAX_ERROR: def test_to_websocket_context(self):
    # REMOVED_SYNTAX_ERROR: """Test converting to WebSocket event context."""
    # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext( )
    # REMOVED_SYNTAX_ERROR: trace_id="test_trace_id",
    # REMOVED_SYNTAX_ERROR: parent_span_id="parent_span",
    # REMOVED_SYNTAX_ERROR: correlation_id="corr789",
    # REMOVED_SYNTAX_ERROR: user_id="user123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread456"
    

    # Start a span
    # REMOVED_SYNTAX_ERROR: span = context.start_span("websocket_op")

    # REMOVED_SYNTAX_ERROR: ws_context = context.to_websocket_context()

    # REMOVED_SYNTAX_ERROR: assert ws_context["trace_id"] == "test_trace_id"
    # REMOVED_SYNTAX_ERROR: assert ws_context["correlation_id"] == "corr789"
    # REMOVED_SYNTAX_ERROR: assert ws_context["user_id"] == "user123"
    # REMOVED_SYNTAX_ERROR: assert ws_context["thread_id"] == "thread456"
    # REMOVED_SYNTAX_ERROR: assert ws_context["span_id"] == span.span_id
    # REMOVED_SYNTAX_ERROR: assert ws_context["parent_span_id"] == "parent_span"


# REMOVED_SYNTAX_ERROR: class TestContextVariables:
    # REMOVED_SYNTAX_ERROR: """Test context variable management."""

# REMOVED_SYNTAX_ERROR: def test_get_current_trace_context(self):
    # REMOVED_SYNTAX_ERROR: """Test getting the current trace context."""
    # Initially should be None
    # REMOVED_SYNTAX_ERROR: assert get_current_trace_context() is None

    # Set a context
    # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext()
    # REMOVED_SYNTAX_ERROR: token = set_trace_context(context)

    # Should now return the context
    # REMOVED_SYNTAX_ERROR: assert get_current_trace_context() == context

    # Clear the context
    # REMOVED_SYNTAX_ERROR: clear_trace_context()
    # REMOVED_SYNTAX_ERROR: assert get_current_trace_context() is None

# REMOVED_SYNTAX_ERROR: def test_context_manager(self):
    # REMOVED_SYNTAX_ERROR: """Test TraceContextManager."""
    # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext()

    # Context should be None initially
    # REMOVED_SYNTAX_ERROR: assert get_current_trace_context() is None

    # REMOVED_SYNTAX_ERROR: with TraceContextManager(context):
        # Context should be set within the block
        # REMOVED_SYNTAX_ERROR: assert get_current_trace_context() == context

        # Context should be cleared after exiting
        # REMOVED_SYNTAX_ERROR: assert get_current_trace_context() is None

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_async_context_manager(self):
            # REMOVED_SYNTAX_ERROR: """Test async TraceContextManager."""
            # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext()

            # Context should be None initially
            # REMOVED_SYNTAX_ERROR: assert get_current_trace_context() is None

            # REMOVED_SYNTAX_ERROR: async with TraceContextManager(context):
                # Context should be set within the block
                # REMOVED_SYNTAX_ERROR: assert get_current_trace_context() == context

                # Context should be cleared after exiting
                # REMOVED_SYNTAX_ERROR: assert get_current_trace_context() is None


# REMOVED_SYNTAX_ERROR: class TestDecorators:
    # REMOVED_SYNTAX_ERROR: """Test trace context decorators."""

# REMOVED_SYNTAX_ERROR: def test_sync_decorator(self):
    # REMOVED_SYNTAX_ERROR: """Test with_trace_context decorator on sync function."""
    # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext(user_id="user123")

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def test_func():
    # REMOVED_SYNTAX_ERROR: current = get_current_trace_context()
    # REMOVED_SYNTAX_ERROR: assert current is not None
    # REMOVED_SYNTAX_ERROR: assert current.user_id == "user123"
    # REMOVED_SYNTAX_ERROR: return "success"

    # Context should be None before call
    # REMOVED_SYNTAX_ERROR: assert get_current_trace_context() is None

    # REMOVED_SYNTAX_ERROR: result = test_func()
    # REMOVED_SYNTAX_ERROR: assert result == "success"

    # Context should be None after call
    # REMOVED_SYNTAX_ERROR: assert get_current_trace_context() is None

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_async_decorator(self):
        # REMOVED_SYNTAX_ERROR: """Test with_trace_context decorator on async function."""
        # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext(user_id="user456")

        # REMOVED_SYNTAX_ERROR: @pytest.fixture
        # Removed problematic line: async def test_func():
            # REMOVED_SYNTAX_ERROR: current = get_current_trace_context()
            # REMOVED_SYNTAX_ERROR: assert current is not None
            # REMOVED_SYNTAX_ERROR: assert current.user_id == "user456"
            # REMOVED_SYNTAX_ERROR: return "async_success"

            # Context should be None before call
            # REMOVED_SYNTAX_ERROR: assert get_current_trace_context() is None

            # REMOVED_SYNTAX_ERROR: result = await test_func()
            # REMOVED_SYNTAX_ERROR: assert result == "async_success"

            # Context should be None after call
            # REMOVED_SYNTAX_ERROR: assert get_current_trace_context() is None

# REMOVED_SYNTAX_ERROR: def test_decorator_without_context(self):
    # REMOVED_SYNTAX_ERROR: """Test decorator creates new context if none provided."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def test_func():
    # REMOVED_SYNTAX_ERROR: current = get_current_trace_context()
    # REMOVED_SYNTAX_ERROR: assert current is not None
    # REMOVED_SYNTAX_ERROR: return current.trace_id

    # REMOVED_SYNTAX_ERROR: trace_id = test_func()
    # REMOVED_SYNTAX_ERROR: assert trace_id is not None
    # REMOVED_SYNTAX_ERROR: assert len(trace_id) == 32


# REMOVED_SYNTAX_ERROR: class TestTraceFlags:
    # REMOVED_SYNTAX_ERROR: """Test W3C Trace Flags."""

# REMOVED_SYNTAX_ERROR: def test_flags_to_byte(self):
    # REMOVED_SYNTAX_ERROR: """Test converting flags to byte representation."""
    # Sampled flag set
    # REMOVED_SYNTAX_ERROR: flags = TraceFlags(sampled=True)
    # REMOVED_SYNTAX_ERROR: assert flags.to_byte() == 0x01

    # Sampled flag not set
    # REMOVED_SYNTAX_ERROR: flags = TraceFlags(sampled=False)
    # REMOVED_SYNTAX_ERROR: assert flags.to_byte() == 0x00

# REMOVED_SYNTAX_ERROR: def test_flags_from_byte(self):
    # REMOVED_SYNTAX_ERROR: """Test creating flags from byte representation."""
    # Sampled flag set
    # REMOVED_SYNTAX_ERROR: flags = TraceFlags.from_byte(0x01)
    # REMOVED_SYNTAX_ERROR: assert flags.sampled is True

    # Sampled flag not set
    # REMOVED_SYNTAX_ERROR: flags = TraceFlags.from_byte(0x00)
    # REMOVED_SYNTAX_ERROR: assert flags.sampled is False

    # Other bits should be ignored
    # REMOVED_SYNTAX_ERROR: flags = TraceFlags.from_byte(0xFF)
    # REMOVED_SYNTAX_ERROR: assert flags.sampled is True


# REMOVED_SYNTAX_ERROR: class TestContextSerialization:
    # REMOVED_SYNTAX_ERROR: """Test context serialization."""

# REMOVED_SYNTAX_ERROR: def test_to_dict(self):
    # REMOVED_SYNTAX_ERROR: """Test converting context to dictionary."""
    # REMOVED_SYNTAX_ERROR: context = UnifiedTraceContext( )
    # REMOVED_SYNTAX_ERROR: trace_id="test_trace",
    # REMOVED_SYNTAX_ERROR: parent_span_id="parent_span",
    # REMOVED_SYNTAX_ERROR: correlation_id="corr123",
    # REMOVED_SYNTAX_ERROR: user_id="user456",
    # REMOVED_SYNTAX_ERROR: thread_id="thread789",
    # REMOVED_SYNTAX_ERROR: request_id="req000",
    # REMOVED_SYNTAX_ERROR: baggage={"key": "value"}
    

    # Start a span
    # REMOVED_SYNTAX_ERROR: span = context.start_span("test_op")

    # REMOVED_SYNTAX_ERROR: data = context.to_dict()

    # REMOVED_SYNTAX_ERROR: assert data["trace_id"] == "test_trace"
    # REMOVED_SYNTAX_ERROR: assert data["parent_span_id"] == "parent_span"
    # REMOVED_SYNTAX_ERROR: assert data["correlation_id"] == "corr123"
    # REMOVED_SYNTAX_ERROR: assert data["user_id"] == "user456"
    # REMOVED_SYNTAX_ERROR: assert data["thread_id"] == "thread789"
    # REMOVED_SYNTAX_ERROR: assert data["request_id"] == "req000"
    # REMOVED_SYNTAX_ERROR: assert data["baggage"] == {"key": "value"]
    # REMOVED_SYNTAX_ERROR: assert data["flags"] == {"sampled": True]
    # REMOVED_SYNTAX_ERROR: assert data["current_span_id"] == span.span_id
    # REMOVED_SYNTAX_ERROR: assert data["span_count"] == 1


# REMOVED_SYNTAX_ERROR: class TestIntegrationScenarios:
    # REMOVED_SYNTAX_ERROR: """Test real-world integration scenarios."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_agent_execution_flow(self):
        # REMOVED_SYNTAX_ERROR: """Test trace context flow through agent execution."""
        # Simulate HTTP request creating initial context
        # REMOVED_SYNTAX_ERROR: root_context = UnifiedTraceContext( )
        # REMOVED_SYNTAX_ERROR: user_id="user123",
        # REMOVED_SYNTAX_ERROR: thread_id="thread456",
        # REMOVED_SYNTAX_ERROR: request_id="req789"
        

        # Start root span for HTTP request
        # REMOVED_SYNTAX_ERROR: http_span = root_context.start_span("http.request", { ))
        # REMOVED_SYNTAX_ERROR: "http.method": "POST",
        # REMOVED_SYNTAX_ERROR: "http.url": "/api/chat"
        

        # Create child context for agent
        # REMOVED_SYNTAX_ERROR: agent_context = root_context.propagate_to_child()
        # REMOVED_SYNTAX_ERROR: agent_span = agent_context.start_span("agent.supervisor", { ))
        # REMOVED_SYNTAX_ERROR: "agent.name": "supervisor",
        # REMOVED_SYNTAX_ERROR: "user.id": "user123"
        

        # Simulate tool execution within agent
        # REMOVED_SYNTAX_ERROR: tool_span = agent_context.start_span("tool.search", { ))
        # REMOVED_SYNTAX_ERROR: "tool.name": "web_search",
        # REMOVED_SYNTAX_ERROR: "tool.query": "test query"
        
        # REMOVED_SYNTAX_ERROR: agent_context.add_event("tool.started")
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)  # Simulate work
        # REMOVED_SYNTAX_ERROR: agent_context.add_event("tool.completed", {"results": 5})
        # REMOVED_SYNTAX_ERROR: agent_context.finish_span(tool_span)

        # Complete agent execution
        # REMOVED_SYNTAX_ERROR: agent_context.finish_span(agent_span)

        # Complete HTTP request
        # REMOVED_SYNTAX_ERROR: root_context.finish_span(http_span)

        # Verify span hierarchy
        # REMOVED_SYNTAX_ERROR: assert len(root_context.span_stack) == 1
        # REMOVED_SYNTAX_ERROR: assert len(agent_context.span_stack) == 2
        # REMOVED_SYNTAX_ERROR: assert agent_context.span_stack[0].parent_span_id == http_span.span_id
        # REMOVED_SYNTAX_ERROR: assert agent_context.span_stack[1].parent_span_id == agent_span.span_id

        # Verify all spans are finished
        # REMOVED_SYNTAX_ERROR: assert all(span.end_time is not None for span in root_context.span_stack)
        # REMOVED_SYNTAX_ERROR: assert all(span.end_time is not None for span in agent_context.span_stack)

# REMOVED_SYNTAX_ERROR: def test_websocket_event_propagation(self):
    # REMOVED_SYNTAX_ERROR: """Test trace context in WebSocket events."""
    # Create context for WebSocket connection
    # REMOVED_SYNTAX_ERROR: ws_context = UnifiedTraceContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread456"
    

    # Simulate agent events
    # REMOVED_SYNTAX_ERROR: events = []

    # Agent started
    # REMOVED_SYNTAX_ERROR: span = ws_context.start_span("agent.execution")
    # REMOVED_SYNTAX_ERROR: ws_data = ws_context.to_websocket_context()
    # REMOVED_SYNTAX_ERROR: events.append({ ))
    # REMOVED_SYNTAX_ERROR: "type": "agent_started",
    # REMOVED_SYNTAX_ERROR: "trace": ws_data
    

    # Agent thinking
    # REMOVED_SYNTAX_ERROR: ws_context.add_event("agent.thinking", {"step": 1})
    # REMOVED_SYNTAX_ERROR: ws_data = ws_context.to_websocket_context()
    # REMOVED_SYNTAX_ERROR: events.append({ ))
    # REMOVED_SYNTAX_ERROR: "type": "agent_thinking",
    # REMOVED_SYNTAX_ERROR: "trace": ws_data
    

    # Agent completed
    # REMOVED_SYNTAX_ERROR: ws_context.finish_span(span)
    # REMOVED_SYNTAX_ERROR: ws_data = ws_context.to_websocket_context()
    # REMOVED_SYNTAX_ERROR: events.append({ ))
    # REMOVED_SYNTAX_ERROR: "type": "agent_completed",
    # REMOVED_SYNTAX_ERROR: "trace": ws_data
    

    # Verify all events have consistent trace IDs
    # REMOVED_SYNTAX_ERROR: trace_ids = [e["trace"]["trace_id"] for e in events]
    # REMOVED_SYNTAX_ERROR: assert len(set(trace_ids)) == 1  # All same trace ID

    # Verify all events have the same correlation ID
    # REMOVED_SYNTAX_ERROR: corr_ids = [e["trace"]["correlation_id"] for e in events]
    # REMOVED_SYNTAX_ERROR: assert len(set(corr_ids)) == 1  # All same correlation ID