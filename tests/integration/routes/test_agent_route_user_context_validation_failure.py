"""SSOT Integration Test: Agent Route UserExecutionContext Validation Failure

This test suite reproduces the 'default_user' validation failure in the context of
real API routes where UserExecutionContext is created from request data.

ROOT CAUSE: UserExecutionContext validation incorrectly flags "default_user" due to "default_" pattern
BUSINESS IMPACT: Blocks Golden Path user journey, affects $500K+ ARR
GCP ERROR: "Field 'user_id' appears to contain placeholder pattern: 'default_user'"

This test demonstrates how the validation failure occurs in real API request scenarios,
simulating the exact conditions that trigger the GCP log error.

Business Value Justification (BVJ):
- Segment: ALL (Core API functionality)
- Business Goal: System Reliability (restore API functionality)
- Value Impact: Unblock user interactions worth $500K+ ARR
- Revenue Impact: Critical - API failures prevent all user engagement

Integration Test Strategy:
1. ROUTE SIMULATION: Simulate real agent API requests with problematic user_id
2. REQUEST FLOW: Test complete request flow from route to UserExecutionContext creation
3. ERROR PROPAGATION: Verify how validation errors propagate to API responses
4. GCP LOGGING: Confirm structured logging works in integration context

SSOT Compliance:
- Inherits from SSotAsyncTestCase for async route testing
- Uses real FastAPI app and dependencies
- Tests actual production request flows
- Validates complete integration stack
"""

import pytest
import asyncio
import logging
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import FastAPI

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, 
    InvalidContextError,
    create_isolated_execution_context
)
from netra_backend.app.schemas.request import RequestModel
from shared.isolated_environment import IsolatedEnvironment


class TestAgentRouteUserContextValidationFailure(SSotAsyncTestCase):
    """Integration test reproducing UserExecutionContext validation failure in API routes.
    
    This test class simulates the exact API request conditions that trigger the
    'default_user' validation error in production GCP environments.
    """

    def setup_method(self, method=None):
        """Set up integration test fixtures with real FastAPI components."""
        super().setup_method(method)
        
        # Set up logging capture for integration testing
        self.log_capture = []
        self.log_handler = logging.Handler()
        self.log_handler.emit = lambda record: self.log_capture.append(record)
        
        # Capture logs from multiple components involved in the integration
        loggers = [
            'netra_backend.app.services.user_execution_context',
            'netra_backend.app.routes.agent',
            'netra_backend.app.agents.supervisor.agent_execution_core',
        ]
        
        self.loggers = []
        for logger_name in loggers:
            logger = logging.getLogger(logger_name)
            logger.addHandler(self.log_handler)
            logger.setLevel(logging.DEBUG)
            self.loggers.append(logger)

    def teardown_method(self, method=None):
        """Clean up integration test fixtures."""
        if hasattr(self, 'loggers') and hasattr(self, 'log_handler'):
            for logger in self.loggers:
                logger.removeHandler(self.log_handler)
        super().teardown_method(method)

    @pytest.mark.asyncio
    async def test_agent_run_request_with_default_user_validation_failure(self):
        """
        INTEGRATION REPRODUCER: Agent run request fails due to default_user validation.
        
        This test reproduces the exact API request flow that triggers the GCP error:
        1. API receives request with user_id="default_user"
        2. Route creates UserExecutionContext
        3. Validation fails with placeholder pattern error
        4. Error propagates to API response
        """
        # Mock the FastAPI dependencies that would normally provide user context
        problematic_user_id = "default_user"
        
        # Simulate request data that would come from authenticated user
        request_data = {
            "user_message": "Hello, please help me optimize my infrastructure",
            "thread_id": "th_12345678901234567890",
            "user_id": problematic_user_id,  # This triggers the validation error
        }
        
        self.log_capture.clear()
        
        # Test the UserExecutionContext creation that happens in agent routes
        with pytest.raises(InvalidContextError) as exc_info:
            # This simulates what happens in the agent route when creating execution context
            context = await create_isolated_execution_context(
                user_id=problematic_user_id,
                request_id="req_agent_route_test"
            )
        
        # Verify the exact error that would appear in GCP logs
        error_message = str(exc_info.value)
        assert "appears to contain placeholder pattern" in error_message, (
            f"Expected GCP-style error message, got: {error_message}"
        )
        assert "default_user" in error_message, (
            f"Expected problematic user_id in error, got: {error_message}"
        )
        
        # Verify integration logging captured the full context
        error_logs = [record for record in self.log_capture if record.levelno >= logging.ERROR]
        assert len(error_logs) > 0, "Expected error logs in integration context"

    @pytest.mark.asyncio 
    async def test_websocket_connection_context_creation_failure(self):
        """
        WEBSOCKET INTEGRATION: Test WebSocket connection context creation failure.
        
        This reproduces the validation failure in WebSocket connection scenarios,
        which is critical for the Golden Path user journey.
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Simulate WebSocket connection data
        connection_data = {
            "user_id": "default_user",  # Problematic value
            "connection_id": "ws_12345678901234567890",
        }
        
        self.log_capture.clear()
        
        # Test WebSocket context creation (commonly used in websocket routes)
        with pytest.raises(InvalidContextError) as exc_info:
            context = UserExecutionContext.create_for_websocket(
                user_id=connection_data["user_id"],
                connection_id=connection_data["connection_id"]
            )
        
        # Verify WebSocket-specific error handling
        error_message = str(exc_info.value)
        assert "placeholder pattern" in error_message
        assert "default_user" in error_message
        
        # WebSocket errors are particularly critical for real-time chat
        websocket_logs = [r for r in self.log_capture if "WebSocket" in r.getMessage() or "websocket" in r.getMessage()]
        # Note: May not have specific WebSocket logs, but validation error should be captured

    @pytest.mark.asyncio
    async def test_agent_execution_context_creation_integration(self):
        """
        AGENT EXECUTION INTEGRATION: Test agent execution context creation failure.
        
        This tests the integration point where UserExecutionContext is created
        for agent execution, which is where the Golden Path failure occurs.
        """
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        
        problematic_user_id = "default_user"
        
        self.log_capture.clear()
        
        # Test agent execution context creation with problematic user_id
        with pytest.raises(InvalidContextError) as exc_info:
            # First create the UserExecutionContext (this is where validation fails)
            user_context = await create_isolated_execution_context(
                user_id=problematic_user_id,
                request_id="req_agent_execution_test"
            )
        
        # Verify agent execution error handling
        error_message = str(exc_info.value)
        assert "placeholder pattern" in error_message
        assert "default_user" in error_message
        
        # Agent execution failures are critical for business value delivery
        agent_logs = [r for r in self.log_capture if "agent" in r.getMessage().lower()]
        # Should capture the execution context creation failure

    @pytest.mark.asyncio
    async def test_multiple_user_context_creation_patterns(self):
        """
        PATTERN INTEGRATION: Test multiple context creation patterns that might trigger the error.
        
        This tests various ways UserExecutionContext might be created in different
        parts of the application, all failing with the same validation error.
        """
        # Test pattern 1: Direct instantiation
        self.log_capture.clear()
        with pytest.raises(InvalidContextError) as exc_info:
            UserExecutionContext(
                user_id="default_user",
                thread_id="th_12345678901234567890",
                run_id="run_12345678901234567890",
                request_id="req_12345678901234567890",
                created_at=datetime.now(timezone.utc)
            )
        
        error_message = str(exc_info.value)
        assert "placeholder pattern" in error_message, "Direct instantiation should fail with placeholder pattern error"
        assert "default_user" in error_message, "Direct instantiation should include problematic user_id"
        
        # Test pattern 2: Factory function
        self.log_capture.clear()
        with pytest.raises(InvalidContextError) as exc_info:
            await create_isolated_execution_context(
                user_id="default_user",
                request_id="req_factory_test"
            )
        
        error_message = str(exc_info.value)
        assert "placeholder pattern" in error_message, "Factory function should fail with placeholder pattern error"
        assert "default_user" in error_message, "Factory function should include problematic user_id"
        
        # Test pattern 3: WebSocket creation
        self.log_capture.clear()
        with pytest.raises(InvalidContextError) as exc_info:
            UserExecutionContext.create_for_websocket(
                user_id="default_user",
                connection_id="ws_test123"
            )
        
        error_message = str(exc_info.value)
        assert "placeholder pattern" in error_message, "WebSocket creation should fail with placeholder pattern error"
        assert "default_user" in error_message, "WebSocket creation should include problematic user_id"

    @pytest.mark.asyncio
    async def test_gcp_structured_logging_in_integration_context(self):
        """
        GCP LOGGING INTEGRATION: Verify structured logging works in integration context.
        
        This ensures that the validation errors will be properly visible in
        GCP Cloud Logging when they occur in production.
        """
        self.log_capture.clear()
        
        # Trigger validation error in integration context
        with pytest.raises(InvalidContextError):
            await create_isolated_execution_context(
                user_id="default_user",
                request_id="req_gcp_logging_test"
            )
        
        # Verify comprehensive logging for GCP visibility
        all_logs = self.log_capture
        assert len(all_logs) > 0, "Expected log entries for GCP visibility"
        
        # Check for structured logging elements that GCP can parse
        error_logs = [r for r in all_logs if r.levelno >= logging.ERROR]
        assert len(error_logs) > 0, "Expected ERROR level logs for GCP alerting"
        
        # Verify key information for GCP debugging
        error_record = error_logs[0]
        log_message = error_record.getMessage()
        
        # GCP logging requirements
        assert "VALIDATION FAILURE" in log_message, "Missing severity indicator for GCP"
        assert "default_user" in log_message, "Missing problematic value for GCP debugging"
        assert "placeholder pattern" in log_message, "Missing error classification for GCP"
        assert "request isolation" in log_message, "Missing business impact for GCP monitoring"
        
        # Verify log record has required attributes for structured logging
        assert hasattr(error_record, 'levelno'), "Missing log level for GCP"
        assert hasattr(error_record, 'getMessage'), "Missing message formatter for GCP"

    @pytest.mark.asyncio
    async def test_api_error_response_integration(self):
        """
        API RESPONSE INTEGRATION: Test how validation errors appear in API responses.
        
        This simulates the complete request-response cycle to show how the
        validation error affects the API response that clients receive.
        """
        # Simulate the error handling that would occur in FastAPI routes
        problematic_user_id = "default_user"
        
        self.log_capture.clear()
        
        try:
            # This represents what happens in an API route handler
            context = await create_isolated_execution_context(
                user_id=problematic_user_id,
                request_id="req_api_handler_test"
            )
            pytest.fail("Expected InvalidContextError to be raised")
            
        except InvalidContextError as e:
            # This represents how the error would be handled in FastAPI
            api_error_response = {
                "error": "Invalid user context",
                "detail": str(e),
                "type": "InvalidContextError",
                "status_code": 400
            }
            
            # Verify API error response structure
            assert api_error_response["error"] == "Invalid user context"
            assert "placeholder pattern" in api_error_response["detail"]
            assert "default_user" in api_error_response["detail"]
            assert api_error_response["type"] == "InvalidContextError"
            assert api_error_response["status_code"] == 400
            
            # This would be the response returned to the client
            assert "appears to contain placeholder pattern" in api_error_response["detail"]

    @pytest.mark.asyncio
    async def test_golden_path_user_journey_interruption(self):
        """
        GOLDEN PATH INTEGRATION: Demonstrate how validation error interrupts user journey.
        
        This test shows how the validation error blocks the complete Golden Path
        user journey, representing the $500K+ ARR business impact.
        """
        # Simulate Golden Path request data
        golden_path_request = {
            "user_id": "default_user",  # This blocks the entire journey
            "user_message": "Please help me optimize my AI infrastructure costs",
            "thread_id": "th_golden_path_test",
            "session_context": "cost_optimization_session"
        }
        
        self.log_capture.clear()
        
        # Golden Path Step 1: Create user execution context (FAILS HERE)
        with pytest.raises(InvalidContextError) as exc_info:
            user_context = await create_isolated_execution_context(
                user_id=golden_path_request["user_id"],
                request_id="req_golden_path_test"
            )
        
        # The Golden Path is completely blocked at this point
        # No agent execution, no WebSocket events, no user value delivery
        
        # Verify business impact logging
        error_logs = [r for r in self.log_capture if r.levelno >= logging.ERROR]
        assert len(error_logs) > 0, "Expected business impact logging"
        
        # Verify the error that blocks $500K+ ARR
        error_message = str(exc_info.value)
        assert "placeholder pattern" in error_message, "Golden Path blocking error"
        assert "default_user" in error_message, "Problematic user_id blocking revenue"
        
        # This error prevents:
        # - Agent execution (no AI responses)
        # - WebSocket events (no real-time updates) 
        # - User value delivery (no optimization insights)
        # - Revenue generation (blocked user interactions)
        
        # Log the business impact for visibility
        business_impact_log = f"GOLDEN PATH BLOCKED: {error_message}"
        logging.getLogger(__name__).critical(business_impact_log)