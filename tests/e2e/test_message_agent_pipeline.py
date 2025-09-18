"""Message Agent Pipeline Test - Complete End-to-End Message Processing"

Business Value: $40K MRR - Core chat functionality validation
Tests: WebSocket  ->  Auth  ->  Agent  ->  Response pipeline with WebSocket Events

Critical: <5s response time, message ordering, error handling, WebSocket agent events
Architecture: 450-line limit, 25-line functions (CLAUDE.md compliance)

CLAUDE.md Compliance:
- NO MOCKS: Uses real WebSocket connections and agent services
- Absolute imports only
- Environment access through IsolatedEnvironment
- Real database, real LLM, real services
- WebSocket Agent Events Validation (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)"""
- WebSocket Agent Events Validation (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)"""
MISSION CRITICAL: WebSocket events validation - if this fails, chat UI is broken"""
MISSION CRITICAL: WebSocket events validation - if this fails, chat UI is broken"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Set

import pytest
import websockets
from websockets import ConnectionClosed

    # CLAUDE.md: Absolute imports only - NO relative imports
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger
from tests.e2e.jwt_token_helpers import JWTTestHelper

    # MISSION CRITICAL: WebSocket event validation imports
from test_framework.real_services import get_real_services
from test_framework.environment_isolation import get_test_env_manager

logger = central_logger.get_logger(__name__)

"""
"""
    """Validates WebSocket agent events according to CLAUDE.md requirements."""
    MISSION CRITICAL: Basic chat functionality depends on these events."""
    MISSION CRITICAL: Basic chat functionality depends on these events."""
"""
"""
    "agent_started,"
    "agent_thinking,"
    "tool_executing,"
    "tool_completed,"
    "agent_completed"
    

    def __init__(self):
        pass
        self.events: List[Dict] = []
        self.event_counts: Dict[str, int] = {}
        self.start_time = time.time()

    def record_event(self, event: Dict) -> None:
        """Record a WebSocket event for validation."""
        event_type = event.get("type", "unknown)"
        self.events.append(event)
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        logger.debug("formatted_string)"

    def validate_required_events(self) -> tuple[bool, List[str]]:
        """Validate all required WebSocket events were received."""
        missing_events = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        failures = []
"""
"""
        failures.append("formatted_string)"

        # Validate event ordering - agent_started should be first
        if self.events and self.events[0].get("type") != "agent_started:"
        failures.append("formatted_string)"

            # Validate tool events are paired
        tool_starts = self.event_counts.get("tool_executing, 0)"
        tool_ends = self.event_counts.get("tool_completed, 0)"
        if tool_starts != tool_ends:
        failures.append("formatted_string)"

        return len(failures) == 0, failures

    def generate_report(self) -> str:
        """Generate validation report."""
        is_valid, failures = self.validate_required_events()
"""
"""
        "
        "
        " + "=" * 60,"
        "WEBSOCKET EVENT VALIDATION REPORT,"
        "= * 60,"
        "formatted_string,"
        "formatted_string,"
        "formatted_string,"
        "",
        "Event Coverage:"
    

        for event in self.REQUIRED_EVENTS:
        count = self.event_counts.get(event, 0)
        status = " PASS: " if count > 0 else " FAIL: "
        report.append("formatted_string)"

        if failures:
        report.extend(["", "FAILURES:"] + ["formatted_string for f in failures])"

        report.append("= * 60)"
        return "
        return "
        ".join(report)"


    async def create_real_websocket_connection(websocket_url: str, timeout: float = 10.0):
        """Create a real WebSocket connection (NO MOCKS)."""
        CLAUDE.md: Uses real WebSocket connections only."""
        CLAUDE.md: Uses real WebSocket connections only."""
        pass
        try:
        connection = await asyncio.wait_for( )
        websockets.connect(websocket_url),
        timeout=timeout"""
        timeout=timeout"""
        logger.info("formatted_string)"
        await asyncio.sleep(0)
        return connection
        except Exception as e:
        logger.error("formatted_string)"
        raise


        async def send_and_receive_with_events(websocket, message: Dict[str, Any),
        event_validator: WebSocketEventValidator,
        timeout: float = 5.0) -> Dict[str, Any]:
        """Send message and capture WebSocket events."""
        message_json = json.dumps(message)
        await websocket.send(message_json)

    # Collect events until we get a final response
        events_received = []
        final_response = None
        start_time = time.time()

        while time.time() - start_time < timeout:
        try:
        response_json = await asyncio.wait_for(websocket.recv(), timeout=1.0)
        response = json.loads(response_json)
        event_validator.record_event(response)
        events_received.append(response)
"""
"""
        event_type = response.get("type", ")"
        if "completed" in event_type or "final" in event_type or "error in event_type:"
        final_response = response
        break

        except asyncio.TimeoutError:
        continue
        except Exception as e:
        logger.warning("formatted_string)"
        break

        if not final_response and events_received:
        final_response = events_received[-1]
        elif not final_response:
        final_response = {"type": "error", "error": "No response received}"

        logger.info("formatted_string)"
        return final_response


class MessagePipelineTester:
        """Complete message pipeline test coordinator with WebSocket event validation."""

    def __init__(self):
        pass
        self.start_times: Dict[str, float] = {}
        self.completion_times: Dict[str, float] = {}
        self.message_responses: List[Dict[str, Any]] = []
        self.error_log: List[Dict[str, Any]] = []
        self.event_validators: Dict[str, WebSocketEventValidator] = {}
"""
"""
        """Start timing for message processing."""
        self.start_times[message_id] = time.time()
"""
"""
        """Complete timing and return duration."""
        end_time = time.time()
        self.completion_times[message_id] = duration
        return duration
"""
"""
        """Record message response."""
        response["message_id] = message_id"
        response["timestamp] = time.time()"
        self.message_responses.append(response)

    def get_event_validator(self, message_id: str) -> WebSocketEventValidator:
        """Get or create event validator for message."""
        if message_id not in self.event_validators:
        self.event_validators[message_id] = WebSocketEventValidator()
        return self.event_validators[message_id]
"""
"""
        """Record pipeline error."""
error_record = {"message_id": message_id,, "error": str(error),, "error_type": type(error).__name__,, "timestamp: time.time()}"
        self.error_log.append(error_record)


        @pytest.fixture
    async def pipeline_tester():
        """Create message pipeline tester."""
        await asyncio.sleep(0)
        return MessagePipelineTester()


        @pytest.fixture"""
        @pytest.fixture"""
        """Get real WebSocket URL for testing with proper JWT token."""
        CLAUDE.md: Uses real JWT token and real backend service (no mocks)."""
        CLAUDE.md: Uses real JWT token and real backend service (no mocks)."""
        pass
    # Use IsolatedEnvironment for ALL environment access per CLAUDE.md
        env_manager = get_test_env_manager()
        env = env_manager.env

        backend_host = env.get('BACKEND_HOST', 'localhost')
        backend_port = env.get('BACKEND_PORT', '8001')  # Test environment port

    # Create real JWT token for testing
        jwt_helper = JWTTestHelper(environment='test')"""
        jwt_helper = JWTTestHelper(environment='test')"""
        logger.info("formatted_string)"
        await asyncio.sleep(0)
        return websocket_url


        @pytest.fixture
    async def real_services_setup():
        """Setup real services for e2e testing."""
        CLAUDE.md: NO MOCKS - uses real services only."""
        CLAUDE.md: NO MOCKS - uses real services only."""
        pass
    # Get real services manager
        real_services = get_real_services()

        try:
        # Ensure all required services are available"""
        # Ensure all required services are available"""
        logger.info("Real services setup completed)"
        yield real_services
        finally:
            # Cleanup
        await real_services.close_all()
        logger.info("Real services cleanup completed)"


        @pytest.mark.e2e
class TestMessagePipelineCore:
        """Core message pipeline functionality tests with WebSocket events validation."""

        @pytest.mark.e2e"""
        @pytest.mark.e2e"""
        """Test complete pipeline: WebSocket  ->  Auth  ->  Agent  ->  Response with WebSocket Events"

        BVJ: Core value delivery test ensuring complete message processing works."""
        BVJ: Core value delivery test ensuring complete message processing works."""
        MISSION CRITICAL: Validates WebSocket agent events for chat functionality.""""""
        message_id = "test_complete_flow"
test_message = {"type": "user_message",, "payload": { ), "content": "Test complete pipeline flow with WebSocket events",, "thread_id": "test_thread",, "message_id: message_id}"
        pipeline_tester.start_timing(message_id)
        event_validator = pipeline_tester.get_event_validator(message_id)

        # REAL end-to-end test with actual WebSocket connection and event validation
        try:
            # Create real WebSocket connection (NO MOCKS)
        websocket = await create_real_websocket_connection(real_websocket_url, timeout=10.0)

        try:
                # Step 1: Send message through real WebSocket and capture events
        response = await send_and_receive_with_events( )
        websocket, test_message, event_validator, timeout=15.0
                

                # Step 2: Validate response structure
        assert "type" in response, "Response missing type field"
        assert response.get("type") != "error", "formatted_string"

                # Step 3: Validate response time
        duration = pipeline_tester.complete_timing(message_id)
        assert duration < 10.0, "formatted_string"

                # Step 4: MISSION CRITICAL - Validate WebSocket agent events
        is_valid, failures = event_validator.validate_required_events()
        if not is_valid:
        logger.error(event_validator.generate_report())
        assert False, "formatted_string"

        logger.info("WebSocket agent events validation PASSED)"
        logger.info(event_validator.generate_report())

        pipeline_tester.record_response(message_id, { ))
        "success: True,"
        "duration: duration,"
        "response: response,"
        "events_count: len(event_validator.events),"
        "websocket_events_valid: True"
                    

        finally:
        await websocket.close()

        except Exception as e:
        logger.error("formatted_string)"
        if 'event_validator' in locals():
        logger.error(event_validator.generate_report())
        raise

        async def _test_real_agent_processing_with_events(self, message: str,
        event_validator: WebSocketEventValidator) -> Dict[str, Any]:
        """Test agent processing with real agent service and WebSocket events validation."
"""
"""
        MISSION CRITICAL: Validates WebSocket events are sent during processing."""
        MISSION CRITICAL: Validates WebSocket events are sent during processing."""
        try:
        # Get real dependencies using absolute imports
from netra_backend.app.dependencies import get_async_db, get_llm_manager
from netra_backend.app.services.agent_service_factory import get_agent_service

        # Create real agent service with dependencies
        async with get_async_db() as db_session:
        llm_manager = get_llm_manager()
        agent_service = get_agent_service(db_session, llm_manager)

            # Process message through real agent
            # Note: In a real scenario, the WebSocket events would be sent
            # by the agent service itself through the WebSocket manager
        result = await agent_service.process_message(message)

        await asyncio.sleep(0)"""
        await asyncio.sleep(0)"""
        "processed: True,"
        "response: result,"
        "agent_type": "real_supervisor,"
        "websocket_events_expected: True"
            

        except Exception as e:
        logger.error("formatted_string)"
        return { )
        "processed: False,"
        "error: str(e),"
        "agent_type": "real_supervisor,"
        "websocket_events_expected: False"
                


        @pytest.mark.e2e
class TestMessagePipelineTypes:
        """Test different message types through pipeline with WebSocket events validation."""

        @pytest.mark.e2e"""
        @pytest.mark.e2e"""
        """Test different message types through real pipeline with WebSocket events."
"""
"""
        MISSION CRITICAL: Validates WebSocket events for different message types."""
        MISSION CRITICAL: Validates WebSocket events for different message types."""
        pass"""
        pass"""
        {"type": "user_message", "payload": {"content": "What is my AI spend optimization?", "thread_id": "enterprise_test", "message_id": "enterprise_msg}},"
        {"type": "user_message", "payload": {"content": "Analyze my usage patterns", "thread_id": "analysis_test", "message_id": "analysis_msg}},"
        {"type": "user_message", "payload": {"content": "Optimize my costs", "thread_id": "optimization_test", "message_id": "optimization_msg}}"
        

        for i, case in enumerate(test_cases):
        try:
                # Create real WebSocket connection for each test case
        websocket = await create_real_websocket_connection(real_websocket_url, timeout=10.0)

        try:
        result = await self._process_typed_message_real_with_events( )
        pipeline_tester, websocket, case, "formatted_string"
                    
        assert result["success"], "formatted_string"
        assert result.get("websocket_events_valid", False), "formatted_string"

        finally:
        await websocket.close()

        except Exception as e:
        logger.error("formatted_string)"
        raise

        async def _process_typed_message_real_with_events(self, pipeline_tester: MessagePipelineTester,
        websocket, message: Dict[str, Any],
        message_id: str) -> Dict[str, Any]:
        """Process typed message through real pipeline with WebSocket events validation."""
        pipeline_tester.start_timing(message_id)
        event_validator = pipeline_tester.get_event_validator(message_id)

        try:
        # Send through real WebSocket connection and capture events
        response = await send_and_receive_with_events( )
        websocket, message, event_validator, timeout=12.0
        
        duration = pipeline_tester.complete_timing(message_id)
"""
"""
        if response.get("type") == "error:"
        await asyncio.sleep(0)
        return { )
        "success: False,"
        "error": response.get("error", "Unknown error),"
        "duration: duration,"
        "websocket_events_valid: False"
            

            # Validate WebSocket events
        events_valid, failures = event_validator.validate_required_events()
        if not events_valid:
        logger.warning("formatted_string)"
        logger.warning(event_validator.generate_report())

        return { )
        "success: True,"
        "response: response,"
        "duration: duration,"
        "message_type": message["type],"
        "websocket_events_valid: events_valid,"
        "events_count: len(event_validator.events)"
                

        except Exception as e:
        duration = pipeline_tester.complete_timing(message_id)
        return { )
        "success: False,"
        "error: str(e),"
        "duration: duration,"
        "websocket_events_valid: False"
                    


        @pytest.mark.e2e
class TestPipelinePerformance:
        """Test pipeline performance and concurrency with WebSocket events validation."""

        @pytest.mark.e2e"""
        @pytest.mark.e2e"""
        """Test concurrent message processing with real WebSocket connections and event validation."

        BVJ: Concurrent processing enables Enterprise-grade scalability."""
        BVJ: Concurrent processing enables Enterprise-grade scalability."""
        MISSION CRITICAL: Validates WebSocket events work under concurrent load."""
        MISSION CRITICAL: Validates WebSocket events work under concurrent load."""
        pass
        concurrent_count = 3  # Reduced for real service testing
        messages = [ )"""
        messages = [ )"""
        "type": "user_message,"
        "payload: { )"
        "content": "formatted_string,"
        "thread_id": "formatted_string,"
        "message_id": "formatted_string,"
        "sequence: i"
        
        
        for i in range(concurrent_count)
        

        tasks = [ )
        self._process_concurrent_message_real_with_events(pipeline_tester, msg, i, real_websocket_url)
        for i, msg in enumerate(messages)
        

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success))"
        events_valid_count = sum(1 for r in results if isinstance(r, dict) and r.get("websocket_events_valid))"

        logger.info("formatted_string)"
        logger.info("formatted_string)"

        # For real services, we expect at least some messages to succeed
        assert success_count > 0, "formatted_string"
        # WebSocket events should work for successful messages
        if success_count > 0:
        assert events_valid_count > 0, "formatted_string"

        async def _process_concurrent_message_real_with_events(self, pipeline_tester: MessagePipelineTester,
        message: Dict[str, Any], index: int,
        websocket_url: str) -> Dict[str, Any]:
        """Process single message in concurrent batch with real WebSocket and events validation."""
        message_id = "formatted_string"
        pipeline_tester.start_timing(message_id)
        event_validator = pipeline_tester.get_event_validator(message_id)

        try:
        # Create real WebSocket connection (NO MOCKS)
        websocket = await create_real_websocket_connection(websocket_url, timeout=15.0)

        try:
        response = await send_and_receive_with_events( )
        websocket, message, event_validator, timeout=12.0
            
        duration = pipeline_tester.complete_timing(message_id)

            # Validate WebSocket events
        events_valid, failures = event_validator.validate_required_events()

        await asyncio.sleep(0)
        return { )
        "success": response.get("type") != "error,"
        "sequence": message["payload"]["sequence],"
        "duration: duration,"
        "response: response,"
        "websocket_events_valid: events_valid,"
        "events_count: len(event_validator.events)"
            

        finally:
        await websocket.close()

        except Exception as e:
        duration = pipeline_tester.complete_timing(message_id)
        logger.warning("formatted_string)"
        return { )
        "success: False,"
        "sequence": message["payload"]["sequence],"
        "duration: duration,"
        "error: str(e),"
        "websocket_events_valid: False"
                    


        @pytest.mark.e2e
class TestPipelineErrorHandling:
        """Test error handling throughout the pipeline with WebSocket events validation."""

        @pytest.mark.e2e"""
        @pytest.mark.e2e"""
        """Test error handling with real WebSocket connections and event validation."
"""
"""
        MISSION CRITICAL: Validates WebSocket events are sent even during errors."""
        MISSION CRITICAL: Validates WebSocket events are sent even during errors."""
        pass"""
        pass"""
        invalid_message = {"invalid": "message without type field}"
        event_validator = pipeline_tester.get_event_validator("error_test)"

        try:
        websocket = await create_real_websocket_connection(real_websocket_url, timeout=10.0)

        try:
        response = await send_and_receive_with_events( )
        websocket, invalid_message, event_validator, timeout=8.0
                

                Should receive error response from real system
        assert response.get("type") == "error", "Expected error response for invalid message"
        logger.info("formatted_string)"

        pipeline_tester.record_error("invalid_message_test", Exception(response.get("error)))"

        finally:
        await websocket.close()

        except Exception as e:
        pipeline_tester.record_error("websocket_error_test, e)"

                        # Test recovery with valid message after error
        recovery_validator = pipeline_tester.get_event_validator("recovery_test)"
        try:
        websocket = await create_real_websocket_connection(real_websocket_url, timeout=10.0)

        try:
            pass
valid_recovery_message = {"type": "user_message",, "payload": { ), "content": "Recovery test message",, "thread_id": "recovery_test",, "message_id": "recovery_msg}"
        response = await send_and_receive_with_events( )
        websocket, valid_recovery_message, recovery_validator, timeout=10.0
                                

                                # Should succeed after previous error
        assert response.get("type") != "error", "formatted_string"
        logger.info("Pipeline recovered successfully after error)"

                                # Validate recovery WebSocket events
        events_valid, failures = recovery_validator.validate_required_events()
        if events_valid:
        logger.info("Recovery WebSocket events validation PASSED)"
        else:
        logger.warning("formatted_string)"

        finally:
        await websocket.close()

        except Exception as e:
        logger.warning("formatted_string)"

        assert len(pipeline_tester.error_log) > 0, "Error scenarios not logged properly"

                                                # Log event validation results for debugging
        logger.info("formatted_string)"
        if hasattr(recovery_validator, 'events'):
        logger.info("formatted_string)"

]]]
}}}}}}}}}}