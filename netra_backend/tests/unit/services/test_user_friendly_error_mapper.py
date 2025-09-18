"""
Test UserFriendlyErrorMapper Service

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Improve user experience and reduce support burden
- Value Impact: Users receive actionable error messages instead of technical jargon
- Strategic Impact: Professional error handling improves platform credibility and user satisfaction

This test module validates the UserFriendlyErrorMapper service which converts
technical error messages into user-friendly, actionable error messages.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from netra_backend.app.services.user_friendly_error_mapper import (
    UserFriendlyErrorMapper,
    ErrorCategory,
    UserFriendlyErrorMessage,
    ErrorSeverity
)
from netra_backend.app.websocket_core.error_recovery_handler import ErrorType
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestUserFriendlyErrorMapper(SSotBaseTestCase):
    """Test UserFriendlyErrorMapper service for converting technical errors to user-friendly messages."""

    def setup_method(self, method=None):
        """Set up test fixtures."""
        super().setup_method(method)
        self.mapper = UserFriendlyErrorMapper()

    def test_mapper_initialization(self):
        """Test that mapper initializes correctly with default mappings."""
        # This should FAIL until UserFriendlyErrorMapper is implemented
        mapper = UserFriendlyErrorMapper()

        # Should have default mappings for all 6 core error categories
        assert hasattr(mapper, '_error_mappings')
        assert len(mapper._error_mappings) > 0

        # Should have mappings for all ErrorType enums
        assert ErrorType.RATE_LIMIT_EXCEEDED in mapper._error_mappings
        assert ErrorType.AUTHENTICATION_FAILED in mapper._error_mappings
        assert ErrorType.CONNECTION_LOST in mapper._error_mappings
        assert ErrorType.RESOURCE_EXHAUSTED in mapper._error_mappings
        assert ErrorType.MESSAGE_DELIVERY_FAILED in mapper._error_mappings
        assert ErrorType.UNKNOWN_ERROR in mapper._error_mappings

    def test_rate_limiting_error_mapping(self):
        """Test rate limiting errors map to user-friendly messages."""
        # This should FAIL until implementation exists
        error_context = {
            'error_type': ErrorType.RATE_LIMIT_EXCEEDED,
            'error_message': 'Rate limit exceeded: 100 requests per minute',
            'timestamp': datetime.now(timezone.utc)
        }

        result = self.mapper.map_error(error_context)

        # Should return UserFriendlyErrorMessage object
        assert isinstance(result, UserFriendlyErrorMessage)
        assert result.category == ErrorCategory.RATE_LIMITING
        assert result.severity == ErrorSeverity.MEDIUM

        # Message should be user-friendly, not technical
        assert "rate limit" in result.user_message.lower()
        assert "try again" in result.user_message.lower() or "wait" in result.user_message.lower()
        assert "requests per minute" not in result.user_message  # Technical detail should be filtered

        # Should include actionable advice
        assert result.actionable_advice is not None
        assert len(result.actionable_advice) > 0
        assert any("wait" in advice.lower() for advice in result.actionable_advice)

    def test_authentication_error_mapping(self):
        """Test authentication errors map to user-friendly messages."""
        # This should FAIL until implementation exists
        error_context = {
            'error_type': ErrorType.AUTHENTICATION_FAILED,
            'error_message': 'JWT token validation failed: signature invalid',
            'timestamp': datetime.now(timezone.utc)
        }

        result = self.mapper.map_error(error_context)

        assert isinstance(result, UserFriendlyErrorMessage)
        assert result.category == ErrorCategory.AUTHENTICATION
        assert result.severity == ErrorSeverity.HIGH

        # Should hide technical JWT details
        assert "JWT" not in result.user_message
        assert "signature" not in result.user_message
        assert "authentication" in result.user_message.lower() or "sign in" in result.user_message.lower()

        # Should provide actionable steps
        assert result.actionable_advice is not None
        assert any("sign in" in advice.lower() or "login" in advice.lower() for advice in result.actionable_advice)

    def test_network_error_mapping(self):
        """Test network errors map to user-friendly messages."""
        # This should FAIL until implementation exists
        error_context = {
            'error_type': ErrorType.CONNECTION_LOST,
            'error_message': 'WebSocket connection lost: errno 104, Connection reset by peer',
            'timestamp': datetime.now(timezone.utc)
        }

        result = self.mapper.map_error(error_context)

        assert isinstance(result, UserFriendlyErrorMessage)
        assert result.category == ErrorCategory.NETWORK
        assert result.severity == ErrorSeverity.MEDIUM

        # Should hide technical network details
        assert "errno" not in result.user_message
        assert "peer" not in result.user_message
        assert "connection" in result.user_message.lower() or "network" in result.user_message.lower()

        # Should suggest network-related actions
        assert result.actionable_advice is not None
        assert any("connection" in advice.lower() or "refresh" in advice.lower() for advice in result.actionable_advice)

    def test_resource_exhaustion_error_mapping(self):
        """Test resource exhaustion errors map to user-friendly messages."""
        # This should FAIL until implementation exists
        error_context = {
            'error_type': ErrorType.RESOURCE_EXHAUSTED,
            'error_message': 'Memory limit exceeded: allocated 2GB, limit 1.5GB',
            'timestamp': datetime.now(timezone.utc)
        }

        result = self.mapper.map_error(error_context)

        assert isinstance(result, UserFriendlyErrorMessage)
        assert result.category == ErrorCategory.RESOURCE_EXHAUSTION
        assert result.severity == ErrorSeverity.HIGH

        # Should hide technical memory details
        assert "GB" not in result.user_message
        assert "allocated" not in result.user_message
        assert "system" in result.user_message.lower() or "capacity" in result.user_message.lower()

        # Should suggest resource-related actions
        assert result.actionable_advice is not None
        assert any("try again" in advice.lower() or "later" in advice.lower() for advice in result.actionable_advice)

    def test_websocket_error_mapping(self):
        """Test WebSocket-specific errors map to user-friendly messages."""
        # This should FAIL until implementation exists
        error_context = {
            'error_type': ErrorType.MESSAGE_DELIVERY_FAILED,
            'error_message': 'WebSocket message delivery failed: connection state CLOSED (1006)',
            'timestamp': datetime.now(timezone.utc)
        }

        result = self.mapper.map_error(error_context)

        assert isinstance(result, UserFriendlyErrorMessage)
        assert result.category == ErrorCategory.WEBSOCKET
        assert result.severity == ErrorSeverity.MEDIUM

        # Should hide technical WebSocket details
        assert "1006" not in result.user_message
        assert "CLOSED" not in result.user_message
        assert "message" in result.user_message.lower() or "communication" in result.user_message.lower()

        # Should suggest communication-related actions
        assert result.actionable_advice is not None
        assert any("refresh" in advice.lower() or "reconnect" in advice.lower() for advice in result.actionable_advice)

    def test_agent_execution_error_mapping(self):
        """Test agent execution errors map to user-friendly messages."""
        # This should FAIL until implementation exists
        error_context = {
            'error_type': ErrorType.SERVICE_UNAVAILABLE,
            'error_message': 'Agent execution failed: LLM service timeout after 30s',
            'timestamp': datetime.now(timezone.utc)
        }

        result = self.mapper.map_error(error_context)

        assert isinstance(result, UserFriendlyErrorMessage)
        assert result.category == ErrorCategory.AGENT_EXECUTION
        assert result.severity == ErrorSeverity.MEDIUM

        # Should hide technical execution details
        assert "LLM" not in result.user_message
        assert "30s" not in result.user_message
        assert "timeout" not in result.user_message
        assert "processing" in result.user_message.lower() or "agent" in result.user_message.lower()

        # Should suggest retry-related actions
        assert result.actionable_advice is not None
        assert any("try again" in advice.lower() or "retry" in advice.lower() for advice in result.actionable_advice)

    def test_unknown_error_fallback(self):
        """Test unknown errors get appropriate fallback messages."""
        # This should FAIL until implementation exists
        error_context = {
            'error_type': ErrorType.UNKNOWN_ERROR,
            'error_message': 'Unexpected error in internal module xyz.core.processor.advanced',
            'timestamp': datetime.now(timezone.utc)
        }

        result = self.mapper.map_error(error_context)

        assert isinstance(result, UserFriendlyErrorMessage)
        assert result.category == ErrorCategory.GENERAL
        assert result.severity == ErrorSeverity.MEDIUM

        # Should provide generic but helpful message
        assert "internal module" not in result.user_message
        assert "xyz.core.processor" not in result.user_message
        assert "unexpected" in result.user_message.lower() or "error" in result.user_message.lower()

        # Should provide general troubleshooting advice
        assert result.actionable_advice is not None
        assert any("support" in advice.lower() or "contact" in advice.lower() for advice in result.actionable_advice)

    def test_error_message_structure(self):
        """Test that error messages have required structure and fields."""
        # This should FAIL until UserFriendlyErrorMessage class exists
        error_context = {
            'error_type': ErrorType.RATE_LIMIT_EXCEEDED,
            'error_message': 'Rate limit exceeded',
            'timestamp': datetime.now(timezone.utc)
        }

        result = self.mapper.map_error(error_context)

        # Check all required fields exist
        assert hasattr(result, 'user_message')
        assert hasattr(result, 'category')
        assert hasattr(result, 'severity')
        assert hasattr(result, 'actionable_advice')
        assert hasattr(result, 'timestamp')
        assert hasattr(result, 'technical_reference_id')

        # Check field types
        assert isinstance(result.user_message, str)
        assert isinstance(result.category, ErrorCategory)
        assert isinstance(result.severity, ErrorSeverity)
        assert isinstance(result.actionable_advice, list)
        assert isinstance(result.timestamp, datetime)
        assert isinstance(result.technical_reference_id, str)

        # Check content constraints
        assert len(result.user_message) > 10  # Meaningful message
        assert len(result.user_message) < 200  # Not too verbose
        assert len(result.actionable_advice) > 0  # Has advice
        assert all(len(advice) > 5 for advice in result.actionable_advice)  # Meaningful advice

    def test_error_category_enum_completeness(self):
        """Test that ErrorCategory enum covers all 6 core categories."""
        # This should FAIL until ErrorCategory enum is implemented
        expected_categories = {
            'RATE_LIMITING',
            'AUTHENTICATION',
            'NETWORK',
            'RESOURCE_EXHAUSTION',
            'WEBSOCKET',
            'AGENT_EXECUTION',
            'GENERAL'  # Fallback category
        }

        actual_categories = {category.name for category in ErrorCategory}

        assert expected_categories.issubset(actual_categories), \
            f"Missing categories: {expected_categories - actual_categories}"

    def test_error_severity_enum_completeness(self):
        """Test that ErrorSeverity enum has appropriate levels."""
        # This should FAIL until ErrorSeverity enum is implemented
        expected_severities = {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}
        actual_severities = {severity.name for severity in ErrorSeverity}

        assert expected_severities.issubset(actual_severities), \
            f"Missing severities: {expected_severities - actual_severities}"

    def test_context_data_handling(self):
        """Test mapper handles additional context data appropriately."""
        # This should FAIL until implementation exists
        error_context = {
            'error_type': ErrorType.RATE_LIMIT_EXCEEDED,
            'error_message': 'Rate limit exceeded',
            'timestamp': datetime.now(timezone.utc),
            'user_id': 'user_123',
            'endpoint': '/api/agents/execute',
            'retry_count': 3
        }

        result = self.mapper.map_error(error_context)

        # Should not expose sensitive context in user message
        assert 'user_123' not in result.user_message
        assert '/api/agents/execute' not in result.user_message

        # But should use context for better advice
        assert result.actionable_advice is not None
        # Could potentially reference retry information in advice

    def test_performance_requirements(self):
        """Test that error mapping is fast enough for real-time use."""
        # This should FAIL until implementation exists
        import time

        error_context = {
            'error_type': ErrorType.AUTHENTICATION_FAILED,
            'error_message': 'Auth failed',
            'timestamp': datetime.now(timezone.utc)
        }

        # Should complete mapping in under 50ms
        start_time = time.time()
        result = self.mapper.map_error(error_context)
        end_time = time.time()

        mapping_time = (end_time - start_time) * 1000  # Convert to ms
        assert mapping_time < 50, f"Error mapping took {mapping_time}ms, should be under 50ms"

        # Should still produce valid result
        assert isinstance(result, UserFriendlyErrorMessage)

    def test_concurrent_mapping_safety(self):
        """Test that mapper is thread-safe for concurrent use."""
        # This should FAIL until implementation exists
        import threading
        import time

        results = []
        errors = []

        def map_error_concurrent(error_type):
            try:
                error_context = {
                    'error_type': error_type,
                    'error_message': f'Test error {error_type}',
                    'timestamp': datetime.now(timezone.utc)
                }
                result = self.mapper.map_error(error_context)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads mapping different errors
        threads = []
        error_types = [
            ErrorType.RATE_LIMIT_EXCEEDED,
            ErrorType.AUTHENTICATION_FAILED,
            ErrorType.CONNECTION_LOST,
            ErrorType.RESOURCE_EXHAUSTED,
            ErrorType.MESSAGE_DELIVERY_FAILED
        ]

        for error_type in error_types:
            thread = threading.Thread(target=map_error_concurrent, args=(error_type,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should not have any errors
        assert len(errors) == 0, f"Concurrent mapping had errors: {errors}"
        assert len(results) == len(error_types), "Not all mappings completed"

        # All results should be valid
        for result in results:
            assert isinstance(result, UserFriendlyErrorMessage)
            assert len(result.user_message) > 0