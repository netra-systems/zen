"""User-Friendly Error Mapper Service

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Improve user experience and reduce support burden
- Value Impact: Users receive actionable error messages instead of technical jargon
- Strategic Impact: Professional error handling improves platform credibility and user satisfaction

This service converts technical error messages into user-friendly, actionable error messages
that provide clear guidance without exposing internal implementation details.
"""

import time
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from uuid import uuid4

from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.websocket_core.error_recovery_handler import ErrorType, RecoveryStrategy

logger = get_logger(__name__)


class ErrorCategory(str, Enum):
    """User-facing error categories."""
    RATE_LIMITING = "rate_limiting"
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    WEBSOCKET = "websocket"
    AGENT_EXECUTION = "agent_execution"
    GENERAL = "general"


class ErrorSeverity(str, Enum):
    """Error severity levels for user display."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class UserFriendlyErrorMessage:
    """User-friendly error message with actionable guidance."""
    user_message: str
    category: ErrorCategory
    severity: ErrorSeverity
    actionable_advice: List[str]
    timestamp: datetime
    technical_reference_id: str


class UserFriendlyErrorMapper:
    """Service for converting technical errors to user-friendly messages.

    This service provides:
    - Mapping of technical error types to user-friendly categories
    - Removal of technical jargon and internal implementation details
    - Actionable recovery guidance for users
    - Performance-optimized mapping (<50ms)
    - Thread-safe concurrent operation
    """

    def __init__(self):
        """Initialize the error mapper with default mappings."""
        self._error_mappings = self._build_error_mappings()
        self._lock = threading.RLock()  # For thread safety

        logger.info(f"UserFriendlyErrorMapper initialized with {len(self._error_mappings)} mappings")

    def _build_error_mappings(self) -> Dict[ErrorType, Dict[str, Any]]:
        """Build the mapping from ErrorType to user-friendly messages."""
        return {
            # Rate Limiting Errors
            ErrorType.RATE_LIMIT_EXCEEDED: {
                'category': ErrorCategory.RATE_LIMITING,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "You've hit the rate limit for requests. Please wait a moment before trying again.",
                'actionable_advice': [
                    "Wait a few seconds before submitting your request again",
                    "Reduce the frequency of your requests",
                    "If this continues, try refreshing the page"
                ]
            },

            # Authentication Errors
            ErrorType.AUTHENTICATION_FAILED: {
                'category': ErrorCategory.AUTHENTICATION,
                'severity': ErrorSeverity.HIGH,
                'user_message': "Your authentication has expired. Please sign in again to continue.",
                'actionable_advice': [
                    "Click the sign in button to log in again",
                    "Check that you're using the correct credentials",
                    "Clear your browser cache if the problem persists"
                ]
            },
            ErrorType.AUTHORIZATION_FAILED: {
                'category': ErrorCategory.AUTHENTICATION,
                'severity': ErrorSeverity.HIGH,
                'user_message': "You don't have permission to access this feature.",
                'actionable_advice': [
                    "Contact your administrator to request access",
                    "Verify you're signed into the correct account",
                    "Check if your account subscription includes this feature"
                ]
            },
            ErrorType.TOKEN_EXPIRED: {
                'category': ErrorCategory.AUTHENTICATION,
                'severity': ErrorSeverity.HIGH,
                'user_message': "Your session has expired. Please sign in again.",
                'actionable_advice': [
                    "Click the sign in button to start a new session",
                    "Your work has been saved automatically",
                    "Consider enabling \"Stay signed in\" for longer sessions"
                ]
            },

            # Network Errors
            ErrorType.CONNECTION_LOST: {
                'category': ErrorCategory.NETWORK,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "Your connection was interrupted. We're trying to reconnect automatically.",
                'actionable_advice': [
                    "Check your internet connection",
                    "Refresh the page if the connection isn't restored",
                    "Try moving closer to your WiFi router if using wireless"
                ]
            },
            ErrorType.CONNECTION_TIMEOUT: {
                'category': ErrorCategory.NETWORK,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "The connection is taking longer than expected.",
                'actionable_advice': [
                    "Check your internet connection speed",
                    "Try refreshing the page",
                    "Contact support if you continue experiencing slow connections"
                ]
            },
            ErrorType.CONNECTION_REFUSED: {
                'category': ErrorCategory.NETWORK,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "Unable to connect to our services. This may be temporary.",
                'actionable_advice': [
                    "Wait a few moments and try again",
                    "Check if you can access other websites",
                    "Try using a different network if available"
                ]
            },
            ErrorType.NETWORK_ERROR: {
                'category': ErrorCategory.NETWORK,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "There's a problem with your network connection.",
                'actionable_advice': [
                    "Check your internet connection",
                    "Try refreshing the page",
                    "Contact your internet service provider if problems persist"
                ]
            },

            # Resource Exhaustion Errors
            ErrorType.RESOURCE_EXHAUSTED: {
                'category': ErrorCategory.RESOURCE_EXHAUSTION,
                'severity': ErrorSeverity.HIGH,
                'user_message': "Our system is currently at capacity. Please try again later.",
                'actionable_advice': [
                    "Wait 1-2 minutes and try again later",
                    "Try simplifying your request if possible",
                    "Contact support if you continue to experience issues"
                ]
            },
            ErrorType.MEMORY_LIMIT_EXCEEDED: {
                'category': ErrorCategory.RESOURCE_EXHAUSTION,
                'severity': ErrorSeverity.HIGH,
                'user_message': "Your request requires more processing power than currently available.",
                'actionable_advice': [
                    "Try breaking your request into smaller parts",
                    "Wait a few minutes and try again",
                    "Consider upgrading your plan for higher limits"
                ]
            },

            # WebSocket Errors
            ErrorType.MESSAGE_DELIVERY_FAILED: {
                'category': ErrorCategory.WEBSOCKET,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "There was a problem delivering your message. We're working to restore communication.",
                'actionable_advice': [
                    "Your message will be delivered once connection is restored",
                    "Try refreshing the page if the issue persists",
                    "Check your internet connection"
                ]
            },
            ErrorType.MESSAGE_SERIALIZATION_FAILED: {
                'category': ErrorCategory.WEBSOCKET,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "There was a problem processing your message format.",
                'actionable_advice': [
                    "Try sending your message again",
                    "If using special characters, try simpler text",
                    "Refresh the page if the problem continues"
                ]
            },
            ErrorType.MESSAGE_TOO_LARGE: {
                'category': ErrorCategory.WEBSOCKET,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "Your message is too long. Please try breaking it into smaller parts.",
                'actionable_advice': [
                    "Split your message into multiple shorter messages",
                    "Remove any large attachments or files",
                    "Try summarizing your request more concisely"
                ]
            },
            ErrorType.MESSAGE_INVALID_FORMAT: {
                'category': ErrorCategory.WEBSOCKET,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "Your message couldn't be processed due to formatting issues.",
                'actionable_advice': [
                    "Try retyping your message",
                    "Avoid special characters or unusual formatting",
                    "Copy and paste plain text instead of formatted content"
                ]
            },
            ErrorType.PROTOCOL_ERROR: {
                'category': ErrorCategory.WEBSOCKET,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "There's a communication problem with our service.",
                'actionable_advice': [
                    "Refresh the page to reset the connection",
                    "Try using a different browser if available",
                    "Clear your browser cache and cookies"
                ]
            },

            # Agent Execution Errors
            ErrorType.SERVICE_UNAVAILABLE: {
                'category': ErrorCategory.AGENT_EXECUTION,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "Our AI processing service is temporarily unavailable.",
                'actionable_advice': [
                    "Wait a few moments and try again",
                    "Check our status page for any known issues",
                    "Contact support if the problem persists"
                ]
            },
            ErrorType.TIMEOUT: {
                'category': ErrorCategory.AGENT_EXECUTION,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "Your request is taking longer than expected to process.",
                'actionable_advice': [
                    "Try simplifying your request",
                    "Wait a moment and submit your request again",
                    "Break complex requests into smaller parts"
                ]
            },
            ErrorType.DATABASE_ERROR: {
                'category': ErrorCategory.AGENT_EXECUTION,
                'severity': ErrorSeverity.HIGH,
                'user_message': "There's a temporary issue with our data services.",
                'actionable_advice': [
                    "Please try your request again in a few minutes",
                    "Your previous work has been automatically saved",
                    "Contact support if you continue to experience problems"
                ]
            },

            # Generic/Fallback Errors
            ErrorType.UNKNOWN_ERROR: {
                'category': ErrorCategory.GENERAL,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "Something unexpected happened. Our team has been notified and we're working on a fix.",
                'actionable_advice': [
                    "Try refreshing the page",
                    "Wait a few minutes and try again",
                    "Contact support with details about what you were doing"
                ]
            },
            ErrorType.VERSION_MISMATCH: {
                'category': ErrorCategory.GENERAL,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "Your browser version may be out of date. Please refresh the page.",
                'actionable_advice': [
                    "Refresh the page to get the latest version",
                    "Update your browser if possible",
                    "Clear your browser cache"
                ]
            },
            ErrorType.UNSUPPORTED_OPERATION: {
                'category': ErrorCategory.GENERAL,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': "This operation isn't supported with your current configuration.",
                'actionable_advice': [
                    "Try a different approach to accomplish your goal",
                    "Check if your account has the necessary permissions",
                    "Contact support for alternative solutions"
                ]
            }
        }

    def map_error(self, error_context: Dict[str, Any]) -> UserFriendlyErrorMessage:
        """Map a technical error to a user-friendly message.

        Args:
            error_context: Dictionary containing error information including:
                - error_type: ErrorType enum value
                - error_message: Original technical error message
                - timestamp: When the error occurred
                - Additional context data (user_id, endpoint, etc.)

        Returns:
            UserFriendlyErrorMessage with user-friendly content
        """
        start_time = time.time()

        try:
            with self._lock:  # Thread safety
                error_type = error_context.get('error_type')
                timestamp = error_context.get('timestamp', datetime.now(timezone.utc))

                # Get the mapping for this error type
                mapping = self._error_mappings.get(error_type)

                if not mapping:
                    # Fallback to unknown error mapping
                    mapping = self._error_mappings[ErrorType.UNKNOWN_ERROR]
                    logger.warning(f"No mapping found for error type: {error_type}, using fallback")

                # Create user-friendly error message
                user_friendly_message = UserFriendlyErrorMessage(
                    user_message=mapping['user_message'],
                    category=mapping['category'],
                    severity=mapping['severity'],
                    actionable_advice=mapping['actionable_advice'].copy(),  # Copy to avoid shared references
                    timestamp=timestamp,
                    technical_reference_id=str(uuid4())[:8]  # Short reference ID for support
                )

                # Optionally enhance advice based on context
                self._enhance_advice_with_context(user_friendly_message, error_context)

                # Log mapping performance
                mapping_time = (time.time() - start_time) * 1000
                if mapping_time > 50:  # Log if exceeding performance threshold
                    logger.warning(f"Error mapping took {mapping_time:.2f}ms, exceeding 50ms threshold")

                logger.debug(f"Mapped {error_type} to user-friendly message in {mapping_time:.2f}ms")

                return user_friendly_message

        except Exception as e:
            # Fallback error handling - never fail to return a message
            logger.error(f"Error mapping failed: {e}")
            return UserFriendlyErrorMessage(
                user_message="An unexpected error occurred. Please try again or contact support.",
                category=ErrorCategory.GENERAL,
                severity=ErrorSeverity.MEDIUM,
                actionable_advice=[
                    "Try refreshing the page",
                    "Contact support if the problem persists",
                    "Include error reference when contacting support"
                ],
                timestamp=datetime.now(timezone.utc),
                technical_reference_id=str(uuid4())[:8]
            )

    def _enhance_advice_with_context(
        self,
        user_message: UserFriendlyErrorMessage,
        error_context: Dict[str, Any]
    ) -> None:
        """Enhance actionable advice based on additional context.

        Args:
            user_message: The user-friendly message to enhance
            error_context: Additional context that might inform better advice
        """
        retry_count = error_context.get('retry_count', 0)

        # If user has already retried multiple times, suggest different actions
        if retry_count >= 3:
            enhanced_advice = [
                "You've tried this several times - please wait 5 minutes before trying again",
                "Contact support for assistance with persistent issues",
                "Check our status page for any ongoing issues"
            ]
            user_message.actionable_advice = enhanced_advice

        # Enhance based on specific context
        endpoint = error_context.get('endpoint', '')
        if 'agents' in endpoint and user_message.category == ErrorCategory.AGENT_EXECUTION:
            user_message.actionable_advice.append("Try using a simpler prompt or request")

        # Remove any sensitive information that might have leaked into context
        # (This is defensive - context should already be sanitized)
        user_id = error_context.get('user_id', '')
        if user_id:
            # Don't include user IDs in advice
            pass

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get statistics about error mappings (useful for monitoring)."""
        with self._lock:
            return {
                'total_mappings': len(self._error_mappings),
                'categories_covered': len(set(mapping['category'] for mapping in self._error_mappings.values())),
                'severity_distribution': {
                    severity: sum(1 for mapping in self._error_mappings.values()
                                if mapping['severity'] == severity)
                    for severity in ErrorSeverity
                }
            }