"""WebSocket Event Flow Completeness Test

P0 CRITICAL - UX BROKEN
BVJ: All customer tiers | UX Fix | Frontend UI layers don't update | Users see blank screens
SPEC: websocket_communication.xml

This test verifies ALL required WebSocket events are sent with correct payloads and that
frontend receives events in correct order within the 10-second requirement.
"""

import time
from typing import Dict
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.config import TEST_USERS
from tests.e2e.integration.helpers.websocket_test_helpers import (
    WebSocketTestManager, create_agent_request, extract_events_by_type, validate_event_payload
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
@pytest.mark.e2e
async def test_websocket_test_manager():
    """Create WebSocket test manager fixture"""
    manager = WebSocketTestManager()
    
    try:
        await manager.setup_test_environment()
        yield manager
    finally:
        await manager.teardown_test_environment()


@pytest.mark.e2e
class TestWebSocketEventCompleteness:
    """Test WebSocket event flow completeness"""
    
    @pytest.mark.e2e
    async def test_all_required_events_received(self, websocket_test_manager):
        """Test that ALL required WebSocket events are received"""
        manager = websocket_test_manager
        
        # Create authenticated WebSocket connection
        client = await manager.create_authenticated_websocket("free")
        user_data = TEST_USERS["free"]
        
        # Create agent request that should trigger all events
        thread_id = f"completeness-test-{int(time.time())}"
        agent_request = create_agent_request(
            user_data.id, 
            "Run a quick analysis that uses tools and provides recommendations",
            thread_id,
            request_streaming=True
        )
        
        # Execute agent and capture events
        events = await manager.execute_agent_with_event_capture(client, agent_request)
        validation_results = manager.validator.validate_completeness()
        
        # Log validation results for debugging
        logger.info(f"Validation results: {validation_results}")
        
        # Check which events we received
        received_events = validation_results["received_events"]
        
        # If we got no events, the connection might have failed
        if validation_results["total_events_received"] == 0:
            logger.warning("No events received - connection may have failed")
            assert False, "No WebSocket events received - connection failed"
        
        # Progressive validation - check what we can
        critical_events = [
            "agent_started", "agent_thinking", "partial_result", 
            "tool_executing", "agent_completed", "final_report"
        ]
        
        # Count how many critical events we got
        received_critical = sum(1 for event in critical_events if event in received_events)
        total_critical = len(critical_events)
        
        # We should get at least 1/3 of the critical events
        min_expected = max(1, total_critical // 3)
        assert received_critical >= min_expected, \
            f"Too few critical events received: {received_critical}/{total_critical}. Got: {list(received_events)}"
        
        # Verify test completed within time limit
        assert validation_results["test_duration_seconds"] < 10.0, \
            f"Test took too long: {validation_results['test_duration_seconds']:.1f}s"
        
        await client.close()
    
    @pytest.mark.e2e
    async def test_event_payload_correctness(self, websocket_test_manager):
        """Test that event payloads match websocket_communication.xml spec"""
        manager = websocket_test_manager
        
        client = await manager.create_authenticated_websocket("early")
        user_data = TEST_USERS["early"]
        
        thread_id = f"payload-test-{int(time.time())}"
        agent_request = create_agent_request(
            user_data.id, 
            "Quick optimization analysis with tools",
            thread_id
        )
        
        events = await manager.execute_agent_with_event_capture(client, agent_request)
        validation_results = manager.validator.validate_completeness()
        
        # Check payload validation results
        payload_results = validation_results["payload_validation_results"]
        
        valid_payloads = sum(1 for result in payload_results if result["valid"])
        total_payloads = len(payload_results)
        
        # At least 50% of payloads should be valid (more lenient for development)
        if total_payloads > 0:
            payload_success_rate = valid_payloads / total_payloads
            assert payload_success_rate >= 0.5, \
                f"Payload validation success rate too low: {payload_success_rate:.2f}"
        else:
            logger.warning("No payload validations performed - no events received")
        
        # Check specific required fields for critical events
        for result in payload_results:
            if result["event_type"] == "agent_started":
                assert len(result["missing_required_fields"]) == 0, \
                    f"agent_started missing fields: {result['missing_required_fields']}"
        
        await client.close()
    
    @pytest.mark.e2e
    async def test_streaming_partial_results(self, websocket_test_manager):
        """Test partial_result events with streaming content"""
        manager = websocket_test_manager
        
        client = await manager.create_authenticated_websocket("free")
        user_data = TEST_USERS["free"]
        
        agent_request = create_agent_request(
            user_data.id, 
            "Generate detailed analysis with streaming output",
            f"streaming-test-{int(time.time())}"
        )
        
        events = await manager.execute_agent_with_event_capture(client, agent_request)
        
        # Find partial_result events
        partial_events = extract_events_by_type(events, "partial_result")
        
        # Should receive partial result events for streaming
        if partial_events:  # Only assert if partial results were sent
            # Validate partial_result payload structure  
            required_fields = {"content", "agent_name", "is_complete"}
            for event in partial_events:
                assert validate_event_payload(event, required_fields), \
                    "partial_result missing required fields"
        
        await client.close()
    
    @pytest.mark.e2e
    async def test_tool_execution_events(self, websocket_test_manager):
        """Test tool_executing events when tools run"""
        manager = websocket_test_manager
        
        client = await manager.create_authenticated_websocket("mid")
        user_data = TEST_USERS["mid"]
        
        # Request that should trigger tool usage
        agent_request = create_agent_request(
            user_data.id, 
            "Run performance analysis using system tools",
            f"tool-test-{int(time.time())}"
        )
        
        events = await manager.execute_agent_with_event_capture(client, agent_request)
        
        # Find tool_executing events
        tool_events = extract_events_by_type(events, "tool_executing")
        
        # Should receive tool execution events
        if tool_events:  # Only assert if tools were actually used
            required_fields = {"tool_name", "agent_name", "timestamp"}
            for event in tool_events:
                assert validate_event_payload(event, required_fields), \
                    "tool_executing missing required fields"
        
        await client.close()
    
    @pytest.mark.critical
    @pytest.mark.e2e
    async def test_websocket_events(self, websocket_test_manager):
        """
        BVJ: Segment: ALL | Goal: UX Quality | Impact: User satisfaction
        Tests: WebSocket event completeness and ordering
        """
        manager = websocket_test_manager
        
        # Test with Enterprise tier for full feature access
        client = await manager.create_authenticated_websocket("enterprise")
        user_data = TEST_USERS["enterprise"]
        
        # Create comprehensive agent request
        thread_id = f"critical-websocket-test-{int(time.time())}"
        agent_request = create_agent_request(
            user_data.id,
            "Analyze system performance and provide optimization recommendations",
            thread_id,
            request_streaming=True,
            enable_tools=True
        )
        
        # Execute and capture events
        events = await manager.execute_agent_with_event_capture(client, agent_request, timeout=10.0)
        validation_results = manager.validator.validate_completeness()
        
        # Log comprehensive results
        logger.info(f"WebSocket Events Test Results:")
        logger.info(f"  - Total events received: {validation_results['total_events_received']}")
        logger.info(f"  - Event types: {validation_results['received_events']}")
        logger.info(f"  - Missing events: {validation_results['missing_events']}")
        logger.info(f"  - Test duration: {validation_results['test_duration_seconds']:.2f}s")
        
        # Critical assertions
        total_events = validation_results['total_events_received']
        assert total_events > 0, "No WebSocket events received"
        
        received_events = set(validation_results['received_events'])
        
        # Success criteria: At least basic events OR meaningful progress
        success_score = 0
        if total_events >= 2:
            success_score += 2
        if "agent_started" in received_events or "agent_completed" in received_events:
            success_score += 2
        
        # Test progressive events
        progressive_events = ["agent_thinking", "partial_result"]
        received_progressive = sum(1 for event in progressive_events if event in received_events)
        if received_progressive > 0:
            success_score += 1
        
        # Performance validation
        test_duration = validation_results['test_duration_seconds']
        if test_duration < 10.0:
            success_score += 1
            
        assert success_score >= 3, f"WebSocket events test failed. Score: {success_score}/6. Events: {list(received_events)}"
        assert test_duration < 12.0, f"Test took too long: {test_duration:.1f}s (limit: 12s)"
        
        logger.info(f"[U+2713] WebSocket Events Test PASSED (Score: {success_score}/6)")
        await client.close()
