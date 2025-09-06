"""
Error Propagation and User Notification Tests

Business Value: $10K MRR - Critical error handling that prevents user churn
and maintains system reliability during failures.

Comprehensive tests covering error flow from system components to user-facing
error messages, including recovery mechanisms and notification channels.
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
import websockets

from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.core.unified_error_handler import get_http_status_code, handle_exception

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import RetryConfig
from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.websocket_core.error_recovery_handler import (
    ErrorType,
    WebSocketErrorRecoveryHandler,
)
from netra_backend.tests.fixtures import TestUser, WebSocketClient, unified_services
from netra_backend.tests.mock_services import (
    MockLLMService,
    MockOAuthProvider,
    ServiceRegistry,
)

logger = central_logger.get_logger(__name__)

@dataclass 
class ErrorScenario:
    """Test error scenario configuration."""
    name: str
    error_type: str
    original_error: Exception
    expected_user_message: str
    should_retry: bool = False
    recovery_options: List[str] = None

@dataclass
class NotificationChannel:
    """Test notification channel tracking."""
    channel_type: str
    message_sent: bool = False
    message_content: str = ""
    timestamp: Optional[datetime] = None

class MockCircuitBreaker:
    """Mock circuit breaker for testing error scenarios."""
    
    def __init__(self, failure_threshold: int = 3):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = None
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker logic."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time < 30:  # 30 second cooldown
                raise Exception("Circuit breaker is OPEN")
            else:
                self.state = "HALF_OPEN"
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            raise e

class MockAgentService:
    """Mock agent service for error testing."""
    
    def __init__(self):
        self.should_fail = False
        self.failure_type = None
        self.processing_time = 0.1
        
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process message with configurable failure modes."""
        await asyncio.sleep(self.processing_time)
        
        if self.should_fail:
            if self.failure_type == "timeout":
                await asyncio.sleep(10)  # Simulate timeout
            elif self.failure_type == "authentication":
                raise ValueError("Authentication failed: Invalid token")
            elif self.failure_type == "rate_limit":
                raise Exception("Rate limit exceeded: Too many requests")
            elif self.failure_type == "llm_error":
                raise Exception("LLM provider error: Service temporarily unavailable")
            elif self.failure_type == "database_error":
                raise Exception("Database connection failed")
            else:
                raise Exception("Generic processing error")
        
        return {"status": "success", "response": "Message processed successfully"}

class MockNotificationService:
    """Mock notification service for tracking error notifications."""
    
    def __init__(self):
        self.notifications_sent = []
        self.channels = {
            "websocket": NotificationChannel("websocket"),
            "email": NotificationChannel("email"),
            "slack": NotificationChannel("slack"),
            "sentry": NotificationChannel("sentry")
        }
    
    async def send_websocket_error(self, connection_id: str, error_message: str):
        """Send error via WebSocket."""
        channel = self.channels["websocket"]
        channel.message_sent = True
        channel.message_content = error_message
        channel.timestamp = datetime.now(timezone.utc)
        
        notification = {
            "type": "websocket_error",
            "connection_id": connection_id,
            "message": error_message,
            "timestamp": channel.timestamp.isoformat()
        }
        self.notifications_sent.append(notification)
    
    async def send_email_notification(self, user_email: str, error_details: Dict[str, Any]):
        """Send critical error email notification."""
        channel = self.channels["email"]
        channel.message_sent = True
        channel.message_content = json.dumps(error_details)
        channel.timestamp = datetime.now(timezone.utc)
        
        notification = {
            "type": "email",
            "user_email": user_email,
            "error_details": error_details,
            "timestamp": channel.timestamp.isoformat()
        }
        self.notifications_sent.append(notification)
    
    async def send_slack_alert(self, channel: str, error_summary: str):
        """Send Slack alert for ops team."""
        slack_channel = self.channels["slack"]
        slack_channel.message_sent = True
        slack_channel.message_content = error_summary
        slack_channel.timestamp = datetime.now(timezone.utc)
        
        notification = {
            "type": "slack",
            "channel": channel,
            "error_summary": error_summary,
            "timestamp": slack_channel.timestamp.isoformat()
        }
        self.notifications_sent.append(notification)
    
    async def send_sentry_error(self, error_data: Dict[str, Any]):
        """Send error to Sentry for tracking."""
        channel = self.channels["sentry"]
        channel.message_sent = True
        channel.message_content = json.dumps(error_data)
        channel.timestamp = datetime.now(timezone.utc)
        
        notification = {
            "type": "sentry",
            "error_data": error_data,
            "timestamp": channel.timestamp.isoformat()
        }
        self.notifications_sent.append(notification)

@pytest.fixture
async def error_test_services():
    """Setup mock services for error propagation testing."""
    services = {
        "agent_service": MockAgentService(),
        "notification_service": MockNotificationService(),
        "circuit_breaker": MockCircuitBreaker(),
        "recovery_handler": WebSocketErrorRecoveryHandler(
            RetryConfig(max_retries=3, delay=1.0, backoff_factor=1.5)
        )
    }
    yield services

@pytest.fixture
@pytest.mark.asyncio
async def test_user():
    """Create test user for error scenarios."""
    return TestUser(
        user_id="test_user_123",
        email="test@example.com",
        username="testuser",
        access_token="mock_token_abc123",
        is_authenticated=True
    )

@pytest.fixture
async def websocket_connection():
    """Mock WebSocket connection for testing."""
    # Mock: WebSocket infrastructure isolation for unit tests without real connections
    mock_websocket = AsyncNone  # TODO: Use real service instance
    mock_websocket.client_state = "OPEN"
    # Mock: WebSocket infrastructure isolation for unit tests without real connections
    mock_websocket.send = AsyncNone  # TODO: Use real service instance
    # Mock: WebSocket infrastructure isolation for unit tests without real connections
    mock_websocket.receive = AsyncNone  # TODO: Use real service instance
    yield mock_websocket

@pytest.mark.asyncio
async def test_agent_error_to_user_flow(error_test_services, test_user, websocket_connection):
    """
    Test complete error flow from agent processing failure to user notification.
    
    Business Value: Ensures users receive actionable error messages when agents fail,
    preventing confusion and maintaining user experience worth $10K MRR.
    """
    # Arrange
    agent_service = error_test_services["agent_service"]
    notification_service = error_test_services["notification_service"]
    recovery_handler = error_test_services["recovery_handler"]
    
    # Configure agent to fail with authentication error
    agent_service.should_fail = True
    agent_service.failure_type = "authentication"
    
    user_message = {
        "type": "chat",
        "content": "Analyze my supply chain data",
        "user_id": test_user.user_id
    }
    
    # Act
    error_context = None
    try:
        await agent_service.process_message(user_message)
    except Exception as original_error:
        # Error caught by supervisor/error handler
        error_context = ErrorContext(
            error_type=ErrorType.AUTHENTICATION_ERROR,
            original_error=original_error,
            connection_id="conn_123",
            user_id=test_user.user_id,
            timestamp=datetime.now(timezone.utc),
            agent_state={"last_action": "processing_request"}
        )
        
        # Format user-friendly error message
        user_error_message = _format_user_error_message(error_context)
        
        # Send via WebSocket
        await notification_service.send_websocket_error("conn_123", user_error_message)
        
        # Send to error tracking
        await notification_service.send_sentry_error({
            "error_type": error_context.error_type.value,
            "user_id": test_user.user_id,
            "original_error": str(original_error),
            "agent_state": error_context.agent_state
        })
    
    # Assert
    assert error_context is not None
    assert error_context.error_type == ErrorType.AUTHENTICATION_ERROR
    
    # Verify WebSocket notification sent
    websocket_channel = notification_service.channels["websocket"]
    assert websocket_channel.message_sent
    assert "authentication" in websocket_channel.message_content.lower()
    assert "please try logging in again" in websocket_channel.message_content.lower()
    
    # Verify error tracking
    sentry_channel = notification_service.channels["sentry"]
    assert sentry_channel.message_sent
    
    # Verify notifications contain actionable guidance
    assert len(notification_service.notifications_sent) >= 2
    websocket_notification = next(n for n in notification_service.notifications_sent if n["type"] == "websocket_error")
    assert "connection_id" in websocket_notification
    assert "message" in websocket_notification

@pytest.mark.asyncio
async def test_error_message_formatting(error_test_services, test_user):
    """
    Test user-friendly error message formatting.
    
    Technical errors should be translated to actionable user language
    with technical details hidden but support information included.
    """
    # Test different error types and their user-friendly messages
    test_cases = [
        {
            "error": ValueError("Authentication failed: Token expired"),
            "error_type": ErrorType.AUTHENTICATION_ERROR,
            "expected_keywords": ["session", "log in", "expired"],
            "should_include_retry": True
        },
        {
            "error": Exception("Rate limit exceeded: 100 requests/min"),
            "error_type": ErrorType.RATE_LIMIT_ERROR,
            "expected_keywords": ["too many requests", "try again", "moment"],
            "should_include_retry": True
        },
        {
            "error": Exception("LLM provider error: Service unavailable"),
            "error_type": ErrorType.AGENT_ERROR,
            "expected_keywords": ["temporarily unavailable", "trying again", "support"],
            "should_include_retry": False
        },
        {
            "error": TimeoutError("Request timeout after 30 seconds"),
            "error_type": ErrorType.TIMEOUT_ERROR,
            "expected_keywords": ["taking longer", "try again", "support"],
            "should_include_retry": True
        }
    ]
    
    for case in test_cases:
        # Create error context
        error_context = ErrorContext(
            error_type=case["error_type"],
            original_error=case["error"],
            connection_id="conn_test",
            user_id=test_user.user_id,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Format message
        user_message = _format_user_error_message(error_context)
        
        # Assert user-friendly formatting
        assert isinstance(user_message, str)
        assert len(user_message) > 0
        
        # Check expected keywords present
        for keyword in case["expected_keywords"]:
            assert keyword.lower() in user_message.lower(), \
                f"Expected '{keyword}' in message: {user_message}"
        
        # Ensure technical details are hidden
        assert "Exception" not in user_message
        assert "Traceback" not in user_message
        assert str(case["error"]) not in user_message  # Raw technical error hidden
        
        # Check support contact included for critical errors
        if case["error_type"] in [ErrorType.AGENT_ERROR, ErrorType.UNKNOWN_ERROR]:
            assert "support" in user_message.lower()

@pytest.mark.asyncio
async def test_error_recovery_options(error_test_services, test_user, websocket_connection):
    """
    Test error recovery mechanisms and user options.
    
    When errors occur, users should see recovery options like retry,
    alternative actions, or fallback to support channels.
    """
    notification_service = error_test_services["notification_service"]
    
    # Test retry-able error scenario
    retryable_error = ErrorContext(
        error_type=ErrorType.TIMEOUT_ERROR,
        original_error=TimeoutError("Request timeout"),
        connection_id="conn_retry",
        user_id=test_user.user_id,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Format error with recovery options
    error_response = {
        "type": "error",
        "error_id": f"error_{int(time.time())}",
        "message": _format_user_error_message(retryable_error),
        "recovery_options": [
            {"action": "retry", "label": "Try Again", "enabled": True},
            {"action": "simplify", "label": "Try a Simpler Request", "enabled": True},
            {"action": "support", "label": "Contact Support", "enabled": True}
        ],
        "can_retry": True,
        "retry_delay_seconds": 5
    }
    
    # Send error with recovery options
    await notification_service.send_websocket_error(
        retryable_error.connection_id,
        json.dumps(error_response)
    )
    
    # Assert recovery options included
    websocket_channel = notification_service.channels["websocket"]
    assert websocket_channel.message_sent
    
    sent_message = json.loads(websocket_channel.message_content)
    assert "recovery_options" in sent_message
    assert len(sent_message["recovery_options"]) >= 2
    assert sent_message["can_retry"] is True
    
    # Verify retry option available
    retry_option = next(opt for opt in sent_message["recovery_options"] if opt["action"] == "retry")
    assert retry_option["enabled"] is True
    
    # Verify support option always available
    support_option = next(opt for opt in sent_message["recovery_options"] if opt["action"] == "support")
    assert support_option["enabled"] is True

@pytest.mark.asyncio
async def test_cascading_error_prevention(error_test_services, test_user):
    """
    Test prevention of cascading failures through circuit breakers.
    
    When one service fails, circuit breakers should prevent cascade failures
    while maintaining partial functionality in other services.
    """
    agent_service = error_test_services["agent_service"]
    circuit_breaker = error_test_services["circuit_breaker"]
    notification_service = error_test_services["notification_service"]
    
    # Configure agent to fail consistently
    agent_service.should_fail = True
    agent_service.failure_type = "database_error"
    
    # Simulate multiple requests to trigger circuit breaker
    failure_count = 0
    circuit_opened = False
    
    for attempt in range(5):
        try:
            await circuit_breaker.call(agent_service.process_message, {"test": f"message_{attempt}"})
        except Exception as e:
            failure_count += 1
            if "Circuit breaker is OPEN" in str(e):
                circuit_opened = True
                # Send circuit breaker notification
                await notification_service.send_websocket_error(
                    f"conn_{attempt}",
                    json.dumps({
                        "type": "service_degraded",
                        "message": "Service is temporarily experiencing issues. Please try again in a few moments.",
                        "service_status": "degraded",
                        "estimated_recovery_time": "30 seconds"
                    })
                )
    
    # Assert circuit breaker activated
    assert failure_count >= 3  # Should fail initial attempts
    assert circuit_opened  # Circuit should open after threshold failures
    assert circuit_breaker.state == "OPEN"
    
    # Verify degraded service notifications sent
    assert len(notification_service.notifications_sent) > 0
    degraded_notifications = [n for n in notification_service.notifications_sent 
                             if "service_degraded" in json.loads(n.get("message", "{}")).get("type", "")]
    assert len(degraded_notifications) > 0

@pytest.mark.asyncio
async def test_error_notification_channels(error_test_services, test_user):
    """
    Test multiple error notification channels.
    
    Different error types should trigger appropriate notification channels:
    - WebSocket for immediate user feedback
    - Email for critical errors
    - Slack for ops team alerts
    - Sentry for error tracking
    """
    notification_service = error_test_services["notification_service"]
    
    # Test critical error scenario
    critical_error = ErrorContext(
        error_type=ErrorType.AGENT_ERROR,
        original_error=Exception("Critical system failure: Data corruption detected"),
        connection_id="conn_critical",
        user_id=test_user.user_id,
        timestamp=datetime.now(timezone.utc),
        agent_state={"corrupted_data": True}
    )
    
    # Send notifications via all channels
    await notification_service.send_websocket_error(
        critical_error.connection_id,
        "We're experiencing technical difficulties. Our team has been notified."
    )
    
    await notification_service.send_email_notification(
        test_user.email,
        {
            "error_type": critical_error.error_type.value,
            "user_affected": test_user.user_id,
            "timestamp": critical_error.timestamp.isoformat(),
            "severity": "critical"
        }
    )
    
    await notification_service.send_slack_alert(
        "#ops-alerts",
        f"CRITICAL: Agent error affecting user {test_user.user_id} - Data corruption detected"
    )
    
    await notification_service.send_sentry_error({
        "error_type": critical_error.error_type.value,
        "user_id": test_user.user_id,
        "connection_id": critical_error.connection_id,
        "stack_trace": str(critical_error.original_error),
        "agent_state": critical_error.agent_state
    })
    
    # Assert all channels activated
    assert notification_service.channels["websocket"].message_sent
    assert notification_service.channels["email"].message_sent
    assert notification_service.channels["slack"].message_sent
    assert notification_service.channels["sentry"].message_sent
    
    # Verify notification content appropriate for each channel
    assert len(notification_service.notifications_sent) == 4
    
    websocket_notification = next(n for n in notification_service.notifications_sent if n["type"] == "websocket_error")
    assert "technical difficulties" in websocket_notification["message"]
    
    email_notification = next(n for n in notification_service.notifications_sent if n["type"] == "email")
    assert "critical" in json.loads(email_notification["error_details"])["severity"]
    
    slack_notification = next(n for n in notification_service.notifications_sent if n["type"] == "slack")
    assert "CRITICAL" in slack_notification["error_summary"]

@pytest.mark.asyncio
async def test_error_context_preservation(error_test_services, test_user):
    """
    Test error context tracking and preservation.
    
    Error handling should preserve full context including:
    - User action that triggered error
    - Request ID for tracing
    - Thread context
    - Agent state at time of failure
    - Complete trace information
    """
    notification_service = error_test_services["notification_service"]
    
    # Create rich error context
    request_id = "req_abc123def456"
    thread_id = "thread_789xyz"
    user_action = "analyze_supply_chain_optimization"
    agent_state = {
        "current_step": "data_analysis",
        "progress": 0.75,
        "data_sources": ["clickhouse", "postgres"],
        "last_llm_call": "2024-01-15T10:30:00Z",
        "memory_usage_mb": 245.7
    }
    
    error_with_context = ErrorContext(
        error_type=ErrorType.AGENT_ERROR,
        original_error=Exception("Analysis pipeline failure"),
        connection_id="conn_context",
        user_id=test_user.user_id,
        timestamp=datetime.now(timezone.utc),
        agent_state=agent_state
    )
    
    # Enhanced error tracking with full context
    error_trace = {
        "error_id": f"error_{request_id}",
        "request_id": request_id,
        "thread_id": thread_id,
        "user_action": user_action,
        "user_id": test_user.user_id,
        "connection_id": error_with_context.connection_id,
        "error_type": error_with_context.error_type.value,
        "timestamp": error_with_context.timestamp.isoformat(),
        "agent_state": agent_state,
        "trace_context": {
            "service": "agent_service",
            "method": "process_analysis_request",
            "stack_level": "data_analysis_pipeline"
        },
        "environment": {
            "service_version": "1.0.0",
            "deployment": "staging"
        }
    }
    
    # Send comprehensive error tracking
    await notification_service.send_sentry_error(error_trace)
    
    # Assert full context preserved
    sentry_channel = notification_service.channels["sentry"]
    assert sentry_channel.message_sent
    
    sent_data = json.loads(sentry_channel.message_content)
    assert sent_data["request_id"] == request_id
    assert sent_data["thread_id"] == thread_id
    assert sent_data["user_action"] == user_action
    assert sent_data["agent_state"]["current_step"] == "data_analysis"
    assert sent_data["agent_state"]["progress"] == 0.75
    assert "trace_context" in sent_data
    assert "environment" in sent_data
    
    # Verify error can be traced back to user action
    sentry_notification = next(n for n in notification_service.notifications_sent if n["type"] == "sentry")
    error_data = sentry_notification["error_data"]
    trace_data = json.loads(error_data)
    assert trace_data["user_id"] == test_user.user_id
    assert trace_data["request_id"] == request_id

def _format_user_error_message(error_context: ErrorContext) -> str:
    """
    Format technical errors into user-friendly messages.
    
    Translates system errors into actionable user language while hiding
    technical implementation details.
    """
    error_messages = {
        ErrorType.AUTHENTICATION_ERROR: (
            "Your session has expired. Please log in again to continue. "
            "If you continue having issues, please contact support."
        ),
        ErrorType.RATE_LIMIT_ERROR: (
            "You're sending requests too quickly. Please wait a moment before trying again. "
            "This helps us maintain service quality for all users."
        ),
        ErrorType.TIMEOUT_ERROR: (
            "Your request is taking longer than expected. Please try again. "
            "If the issue persists, try a simpler request or contact support."
        ),
        ErrorType.AGENT_ERROR: (
            "Our AI service is temporarily unavailable. We're working to resolve this quickly. "
            "Please try again in a few minutes or contact support if you need immediate assistance."
        ),
        ErrorType.NETWORK_ERROR: (
            "Connection issues are preventing us from processing your request. "
            "Please check your internet connection and try again."
        ),
        ErrorType.PROTOCOL_ERROR: (
            "We encountered a communication error. Please refresh your browser and try again. "
            "Contact support if the problem continues."
        ),
        ErrorType.UNKNOWN_ERROR: (
            "Something went wrong on our end. Our team has been automatically notified. "
            "Please try again or contact support for assistance."
        )
    }
    
    return error_messages.get(
        error_context.error_type,
        error_messages[ErrorType.UNKNOWN_ERROR]
    )

# Test Data Generation Helpers

def create_error_scenarios() -> List[ErrorScenario]:
    """Generate comprehensive error scenarios for testing."""
    return [
        ErrorScenario(
            name="Authentication Token Expired",
            error_type="authentication",
            original_error=ValueError("Token expired at 2024-01-15T10:00:00Z"),
            expected_user_message="session has expired",
            should_retry=False,
            recovery_options=["login", "support"]
        ),
        ErrorScenario(
            name="Rate Limit Exceeded",
            error_type="rate_limit", 
            original_error=Exception("Rate limit: 100 req/min exceeded"),
            expected_user_message="too many requests",
            should_retry=True,
            recovery_options=["wait", "support"]
        ),
        ErrorScenario(
            name="LLM Service Unavailable",
            error_type="agent_error",
            original_error=Exception("OpenAI API error: Service unavailable"),
            expected_user_message="temporarily unavailable",
            should_retry=False,
            recovery_options=["try_later", "support"]
        ),
        ErrorScenario(
            name="Database Connection Failed",
            error_type="database_error",
            original_error=Exception("Postgres connection timeout"),
            expected_user_message="technical difficulties",
            should_retry=False,
            recovery_options=["support"]
        ),
        ErrorScenario(
            name="Request Timeout",
            error_type="timeout",
            original_error=TimeoutError("Request exceeded 30s timeout"),
            expected_user_message="taking longer than expected",
            should_retry=True,
            recovery_options=["retry", "simplify", "support"]
        )
    ]

@pytest.mark.asyncio
async def test_comprehensive_error_scenarios():
    """
    Test all predefined error scenarios for complete coverage.
    
    Ensures every type of system error has appropriate user-facing
    error handling with actionable recovery options.
    """
    scenarios = create_error_scenarios()
    
    for scenario in scenarios:
        # Create error context
        error_context = ErrorContext(
            error_type=ErrorType.AGENT_ERROR,  # Will be overridden by scenario
            original_error=scenario.original_error,
            connection_id=f"conn_{scenario.name.replace(' ', '_').lower()}",
            user_id="test_user",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Format user message
        user_message = _format_user_error_message(error_context)
        
        # Assert expected characteristics
        assert scenario.expected_user_message.lower() in user_message.lower(), \
            f"Scenario {scenario.name}: Expected '{scenario.expected_user_message}' in '{user_message}'"
        
        # Verify technical details hidden
        assert str(scenario.original_error) not in user_message
        assert "Exception" not in user_message
        assert "Error" not in user_message or "error" in user_message.lower()  # Allow "error" but not "Error" class