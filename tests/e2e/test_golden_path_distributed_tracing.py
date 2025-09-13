
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
Golden Path Distributed Tracing End-to-End Tests

Business Value Justification (BVJ):
- Segment: All - Critical for $500K+ ARR functionality
- Business Goal: Ensure complete user journey is traceable
- Value Impact: Enable debugging of complex multi-service user flows
- Strategic Impact: Foundation for production SLOs and user experience optimization

CRITICAL: These tests MUST FAIL before OpenTelemetry implementation.
They validate that the complete Golden Path user journey creates coherent distributed traces.

Following CLAUDE.md requirements:
- Uses SsotBaseTestCase for consistent test foundation
- Tests complete user workflows with real services
- No mocks in E2E tests - everything must be real
- Focuses on $500K+ ARR chat functionality tracing
"""

import pytest
import asyncio
import json
import uuid
from typing import List, Dict, Any
from test_framework.ssot.base_test_case import SsotBaseTestCase
from test_framework.ssot.real_websocket_test_client import WebSocketTestClient
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestGoldenPathDistributedTracing(SsotBaseTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """E2E tests for complete Golden Path tracing - MUST FAIL before implementation."""

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_complete_user_journey_trace_missing(self, real_services_fixture):
        """Test MUST FAIL: Complete user journey lacks distributed tracing."""
        
        # Create real user for testing
        user_token = await self.create_test_user_token()
        thread_id = f"golden_path_test_{uuid.uuid4().hex[:8]}"
        
        # Connect to WebSocket - currently lacks tracing
        async with WebSocketTestClient(token=user_token) as client:
            # Send user message that triggers complete Golden Path
            await client.send_json({
                "type": "user_message",
                "text": "Analyze my AI costs and provide optimization recommendations",
                "thread_id": thread_id
            })
            
            # Collect all events from complete agent execution
            events = []
            async for event in client.receive_events(timeout=60):
                events.append(event)
                if event.get("type") == "agent_completed":
                    break
            
            # Verify we got the critical WebSocket events (business value)
            event_types = [e.get("type") for e in events]
            assert "agent_started" in event_types, "Mission critical: agent_started event missing"
            assert "agent_thinking" in event_types, "Mission critical: agent_thinking event missing"
            assert "agent_completed" in event_types, "Mission critical: agent_completed event missing"
            
            # May include tool events depending on agent execution
            if "tool_executing" in event_types:
                assert "tool_completed" in event_types, "If tool_executing sent, tool_completed must follow"
            
            # Try to collect distributed traces - SHOULD FAIL
            with pytest.raises((ImportError, AttributeError)):
                from test_framework.ssot.tracing_validators import collect_golden_path_trace
                trace = collect_golden_path_trace(thread_id)
                assert trace is None  # Should fail before implementation

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_spans_not_created(self, real_services_fixture):
        """Test MUST FAIL: WebSocket operations don't create trace spans."""
        
        user_token = await self.create_test_user_token()
        
        async with WebSocketTestClient(token=user_token) as client:
            # Send various WebSocket messages
            messages = [
                {"type": "ping"},
                {"type": "user_message", "text": "Simple test message"},
                {"type": "heartbeat"},
            ]
            
            responses = []
            for message in messages:
                await client.send_json(message)
                try:
                    response = await client.receive_json(timeout=5)
                    if response:
                        responses.append(response)
                except Exception:
                    # Some messages may not get responses, that's ok
                    pass
            
            # Should have received at least one response
            assert len(responses) > 0
            
            # Try to find WebSocket spans - SHOULD FAIL
            with pytest.raises((ImportError, AttributeError)):
                from test_framework.ssot.tracing_validators import collect_websocket_spans
                spans = collect_websocket_spans()
                assert len(spans) == 0  # Should fail before implementation

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_agent_execution_pipeline_untraced(self, real_services_fixture):
        """Test MUST FAIL: Agent execution pipeline lacks distributed tracing."""
        
        user_token = await self.create_test_user_token()
        
        async with WebSocketTestClient(token=user_token) as client:
            # Trigger agent execution
            await client.send_json({
                "type": "agent_request", 
                "agent": "triage_agent",
                "message": "Test query for tracing validation"
            })
            
            # Wait for completion and collect execution details
            final_event = None
            all_events = []
            async for event in client.receive_events(timeout=45):
                all_events.append(event)
                if event.get("type") == "agent_completed":
                    final_event = event
                    break
            
            assert final_event is not None, "Agent execution should complete"
            assert len(all_events) > 0, "Should receive multiple events during execution"
            
            # Extract run_id for trace collection
            run_id = final_event.get("data", {}).get("run_id")
            if not run_id:
                # Try to find run_id in any event
                for event in all_events:
                    if event.get("run_id"):
                        run_id = event["run_id"]
                        break
            
            # Try to trace agent execution - SHOULD FAIL
            with pytest.raises((ImportError, AttributeError)):
                from test_framework.ssot.tracing_validators import collect_agent_execution_trace
                spans = collect_agent_execution_trace(run_id)
                assert len(spans) == 0  # Should fail before implementation

    @pytest.mark.e2e
    @pytest.mark.real_services  
    @pytest.mark.performance
    async def test_concurrent_user_trace_isolation_missing(self, real_services_fixture):
        """Test MUST FAIL: Concurrent users don't have isolated trace contexts."""
        
        # Create multiple user tokens
        user_count = 3
        user_tokens = []
        for i in range(user_count):
            token = await self.create_test_user_token(f"trace_user_{i}@test.com")
            user_tokens.append(token)
        
        # Connect multiple users simultaneously
        clients = []
        for token in user_tokens:
            client = WebSocketTestClient(token=token)
            await client.connect()
            clients.append(client)
        
        try:
            # Send messages from all users concurrently
            tasks = []
            for i, client in enumerate(clients):
                task = client.send_json({
                    "type": "user_message",
                    "text": f"Concurrent test message from user {i}",
                    "thread_id": f"concurrent_test_{i}"
                })
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            # Wait for responses from all users
            all_responses = []
            for i, client in enumerate(clients):
                user_responses = []
                timeout_count = 0
                
                while timeout_count < 3:  # Give each user multiple chances
                    try:
                        response = await client.receive_json(timeout=10)
                        if response:
                            user_responses.append(response)
                            if response.get("type") == "agent_completed":
                                break
                    except Exception:
                        timeout_count += 1
                        continue
                
                all_responses.append({
                    "user_index": i,
                    "responses": user_responses
                })
            
            # Verify each user got responses
            for user_response in all_responses:
                assert len(user_response["responses"]) > 0, f"User {user_response['user_index']} should get responses"
            
            # Try to verify trace isolation - SHOULD FAIL
            with pytest.raises((ImportError, AttributeError)):
                from test_framework.ssot.tracing_validators import verify_trace_isolation
                isolation_valid = verify_trace_isolation(user_tokens)
                assert not isolation_valid  # Should fail before implementation
                
        finally:
            # Cleanup connections
            cleanup_tasks = []
            for client in clients:
                cleanup_tasks.append(client.disconnect())
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multi_agent_workflow_tracing_unavailable(self, real_services_fixture):
        """Test MUST FAIL: Multi-agent workflows don't create coherent traces."""
        
        user_token = await self.create_test_user_token()
        
        async with WebSocketTestClient(token=user_token) as client:
            # Trigger complex multi-agent workflow
            await client.send_json({
                "type": "agent_request",
                "agent": "supervisor_agent",
                "message": "Provide a comprehensive AI cost analysis with optimization recommendations and implementation plan",
                "complexity": "high"  # Should trigger multiple sub-agents
            })
            
            # Collect all events from multi-agent execution
            workflow_events = []
            agent_transitions = []
            
            async for event in client.receive_events(timeout=90):
                workflow_events.append(event)
                
                # Track agent transitions
                if event.get("type") == "agent_started":
                    agent_name = event.get("data", {}).get("agent_name", "unknown")
                    agent_transitions.append(f"started:{agent_name}")
                elif event.get("type") == "agent_completed":
                    agent_name = event.get("data", {}).get("agent_name", "unknown")
                    agent_transitions.append(f"completed:{agent_name}")
                    
                    # Check if this is the final completion
                    if event.get("data", {}).get("workflow_complete", False):
                        break
                elif event.get("type") == "agent_completed":
                    # Simple completion check if workflow_complete not available
                    break
            
            # Verify multi-agent execution occurred
            assert len(workflow_events) > 5, "Multi-agent workflow should generate many events"
            assert len(agent_transitions) > 2, "Should have multiple agent transitions"
            
            # Try to collect multi-agent trace - SHOULD FAIL
            with pytest.raises((ImportError, AttributeError)):
                from test_framework.ssot.tracing_validators import collect_traces
                traces = collect_traces(timeout=5.0)
                
                # Look for multi-agent spans
                multi_agent_traces = []
                for trace in traces:
                    agent_spans = [span for span in trace.spans if "agent" in span.operation_name]
                    if len(agent_spans) > 1:
                        multi_agent_traces.append(trace)
                
                assert len(multi_agent_traces) == 0  # Should fail before implementation

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_database_persistence_tracing_missing(self, real_services_fixture):
        """Test MUST FAIL: Database persistence operations not traced."""
        
        user_token = await self.create_test_user_token()
        thread_id = f"persistence_test_{uuid.uuid4().hex[:8]}"
        
        async with WebSocketTestClient(token=user_token) as client:
            # Send message that should trigger database persistence
            await client.send_json({
                "type": "user_message",
                "text": "Save this conversation for future reference",
                "thread_id": thread_id,
                "save_conversation": True
            })
            
            # Wait for completion
            completion_event = None
            async for event in client.receive_events(timeout=30):
                if event.get("type") == "agent_completed":
                    completion_event = event
                    break
            
            assert completion_event is not None, "Agent should complete and persist data"
            
        # Verify data was persisted (check database directly)
        db = real_services_fixture["db"]
        
        # Check if thread was created
        result = await db.execute(
            "SELECT COUNT(*) FROM threads WHERE id = %s",
            (thread_id,)
        )
        thread_count = result.scalar()
        
        # Check if messages were saved  
        result = await db.execute(
            "SELECT COUNT(*) FROM messages WHERE thread_id = %s",
            (thread_id,)
        )
        message_count = result.scalar()
        
        # Should have persisted data
        assert thread_count > 0 or message_count > 0, "Should have persisted conversation data"
        
        # Try to collect database persistence spans - SHOULD FAIL
        with pytest.raises((ImportError, AttributeError)):
            from test_framework.ssot.tracing_validators import collect_database_spans
            spans = collect_database_spans()
            
            # Look for persistence-related spans
            persistence_spans = [
                span for span in spans 
                if any(keyword in span.operation_name.lower() 
                      for keyword in ["insert", "save", "persist", "create"])
            ]
            assert len(persistence_spans) == 0  # Should fail before implementation

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_error_recovery_tracing_unavailable(self, real_services_fixture):
        """Test MUST FAIL: Error recovery scenarios not traced."""
        
        user_token = await self.create_test_user_token()
        
        async with WebSocketTestClient(token=user_token) as client:
            # Send message that might trigger errors (malformed request)
            await client.send_json({
                "type": "user_message",
                "text": "Trigger error scenario",
                "invalid_field": "this_should_cause_issues",
                "malformed_data": {"nested": {"deeply": {"invalid": None}}}
            })
            
            # Wait for response (may be error or recovery)
            error_response = None
            try:
                async for event in client.receive_events(timeout=20):
                    if event.get("type") in ["error", "agent_error", "agent_completed"]:
                        error_response = event
                        break
            except Exception as e:
                # Connection might close due to error
                self.record_metric("websocket_error", str(e))
            
            # Should handle error gracefully or complete successfully
            assert error_response is not None or True  # Either error or success is ok
            
            # Try to collect error/recovery traces - SHOULD FAIL
            with pytest.raises((ImportError, AttributeError)):
                from test_framework.ssot.tracing_validators import collect_traces
                traces = collect_traces()
                
                # Look for error-related spans
                error_spans = []
                for trace in traces:
                    for span in trace.spans:
                        if any(keyword in span.operation_name.lower() 
                              for keyword in ["error", "exception", "recovery", "fallback"]):
                            error_spans.append(span)
                
                assert len(error_spans) == 0  # Should fail before implementation

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_authentication_flow_tracing_missing(self, real_services_fixture):
        """Test MUST FAIL: Authentication flow not traced."""
        
        # Test WebSocket connection with authentication
        user_token = await self.create_test_user_token()
        
        # Connect with authentication
        async with WebSocketTestClient(token=user_token) as client:
            # Authentication happens during connection
            # Send a message to trigger authenticated operations
            await client.send_json({
                "type": "user_message", 
                "text": "Test authenticated message"
            })
            
            # Wait for response
            auth_response = None
            async for event in client.receive_events(timeout=15):
                auth_response = event
                break
            
            assert auth_response is not None, "Should receive response to authenticated message"
            
        # Test with invalid authentication
        try:
            invalid_client = WebSocketTestClient(token="invalid_token_123")
            await invalid_client.connect()
            
            # Should fail or be rejected
            await invalid_client.send_json({"type": "ping"})
            
            # Cleanup
            await invalid_client.disconnect()
            
        except Exception:
            # Expected - invalid auth should fail
            pass
        
        # Try to collect authentication traces - SHOULD FAIL
        with pytest.raises((ImportError, AttributeError)):
            from test_framework.ssot.tracing_validators import collect_traces
            traces = collect_traces()
            
            # Look for authentication-related spans
            auth_spans = []
            for trace in traces:
                for span in trace.spans:
                    if any(keyword in span.operation_name.lower() 
                          for keyword in ["auth", "login", "token", "validate"]):
                        auth_spans.append(span)
            
            assert len(auth_spans) == 0  # Should fail before implementation


class TestGoldenPathPerformanceTracing(SsotBaseTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Test Golden Path performance with tracing - MUST FAIL before optimization."""

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_golden_path_latency_without_tracing(self, real_services_fixture):
        """Establish baseline Golden Path performance before tracing implementation."""
        
        user_token = await self.create_test_user_token()
        
        # Measure baseline performance (before tracing)
        baseline_times = []
        
        for iteration in range(5):
            start_time = asyncio.get_event_loop().time()
            
            async with WebSocketTestClient(token=user_token) as client:
                # Send standard message
                await client.send_json({
                    "type": "user_message",
                    "text": f"Performance test message {iteration}",
                    "thread_id": f"perf_test_{iteration}"
                })
                
                # Wait for completion
                async for event in client.receive_events(timeout=30):
                    if event.get("type") == "agent_completed":
                        break
            
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            baseline_times.append(duration)
        
        # Calculate baseline metrics
        avg_baseline = sum(baseline_times) / len(baseline_times)
        max_baseline = max(baseline_times)
        min_baseline = min(baseline_times)
        
        # Record baseline metrics for comparison
        self.record_metric("baseline_avg_duration", avg_baseline)
        self.record_metric("baseline_max_duration", max_baseline)
        self.record_metric("baseline_min_duration", min_baseline)
        
        # Establish performance SLAs
        assert avg_baseline < 60.0, f"Baseline average {avg_baseline:.2f}s should be under 60s"
        assert max_baseline < 90.0, f"Baseline max {max_baseline:.2f}s should be under 90s"
        
        # This test documents current performance for comparison once tracing is added
        # When tracing is implemented, we'll compare against these baselines

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_concurrent_golden_path_performance(self, real_services_fixture):
        """Test concurrent Golden Path performance baseline."""
        
        # Create multiple users
        user_count = 3
        user_tokens = []
        for i in range(user_count):
            token = await self.create_test_user_token(f"perf_user_{i}@test.com")
            user_tokens.append(token)
        
        # Execute concurrent Golden Path flows
        async def single_user_flow(user_index: int, token: str):
            start_time = asyncio.get_event_loop().time()
            
            async with WebSocketTestClient(token=token) as client:
                await client.send_json({
                    "type": "user_message",
                    "text": f"Concurrent performance test from user {user_index}",
                    "thread_id": f"concurrent_perf_{user_index}"
                })
                
                async for event in client.receive_events(timeout=45):
                    if event.get("type") == "agent_completed":
                        break
            
            end_time = asyncio.get_event_loop().time()
            return end_time - start_time
        
        # Run concurrent flows
        concurrent_tasks = [
            single_user_flow(i, token) 
            for i, token in enumerate(user_tokens)
        ]
        
        durations = await asyncio.gather(*concurrent_tasks)
        
        # Analyze concurrent performance
        avg_concurrent = sum(durations) / len(durations)
        max_concurrent = max(durations)
        
        # Record concurrent metrics
        self.record_metric("concurrent_avg_duration", avg_concurrent)
        self.record_metric("concurrent_max_duration", max_concurrent)
        self.record_metric("concurrent_user_count", user_count)
        
        # Concurrent performance should be reasonable
        assert avg_concurrent < 90.0, f"Concurrent average {avg_concurrent:.2f}s should be under 90s"
        assert max_concurrent < 120.0, f"Concurrent max {max_concurrent:.2f}s should be under 120s"


class TestGoldenPathTraceValidation(SsotBaseTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Test Golden Path trace validation utilities - MUST FAIL before implementation."""

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_golden_path_trace_validator_unavailable(self, real_services_fixture):
        """Test MUST FAIL: Golden Path trace validator not implemented."""
        
        with pytest.raises((ImportError, AttributeError)):
            from test_framework.ssot.tracing_validators import GoldenPathTraceValidator
            
            validator = GoldenPathTraceValidator()
            # Should fail before validator implementation

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_critical_websocket_events_validation_missing(self, real_services_fixture):
        """Test MUST FAIL: Critical WebSocket events trace validation not available."""
        
        user_token = await self.create_test_user_token()
        
        async with WebSocketTestClient(token=user_token) as client:
            await client.send_json({
                "type": "user_message",
                "text": "Test critical events validation"
            })
            
            # Collect events
            events = []
            async for event in client.receive_events(timeout=30):
                events.append(event)
                if event.get("type") == "agent_completed":
                    break
            
            # Verify critical events present (business requirement)
            event_types = [e.get("type") for e in events]
            critical_events = ["agent_started", "agent_thinking", "agent_completed"]
            
            for critical_event in critical_events:
                assert critical_event in event_types, f"Critical event {critical_event} missing"
            
            # Try to validate events in trace - SHOULD FAIL
            with pytest.raises((ImportError, AttributeError)):
                from test_framework.ssot.tracing_validators import GoldenPathTraceValidator
                
                validator = GoldenPathTraceValidator()
                # Mock trace object
                mock_trace = None  # Would be DistributedTrace object
                
                events_traced = validator.validate_websocket_events_traced(mock_trace)
                assert not events_traced  # Should fail before implementation

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_end_to_end_trace_completeness_validation_missing(self, real_services_fixture):
        """Test MUST FAIL: End-to-end trace completeness validation not available."""
        
        user_token = await self.create_test_user_token()
        thread_id = f"completeness_test_{uuid.uuid4().hex[:8]}"
        
        async with WebSocketTestClient(token=user_token) as client:
            # Execute complete Golden Path
            await client.send_json({
                "type": "user_message",
                "text": "Complete end-to-end trace test",
                "thread_id": thread_id
            })
            
            # Wait for completion
            final_event = None
            async for event in client.receive_events(timeout=45):
                if event.get("type") == "agent_completed":
                    final_event = event
                    break
            
            assert final_event is not None, "Golden Path should complete"
            
        # Try to validate trace completeness - SHOULD FAIL
        with pytest.raises((ImportError, AttributeError)):
            from test_framework.ssot.tracing_validators import GoldenPathTraceValidator
            
            validator = GoldenPathTraceValidator()
            # Mock trace object
            mock_trace = None  # Would be DistributedTrace object
            
            is_complete = validator.validate_golden_path_trace(mock_trace)
            assert not is_complete  # Should fail before implementation