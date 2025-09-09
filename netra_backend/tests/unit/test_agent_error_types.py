"""
Unit Tests for Agent Error Types

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure proper error handling and user feedback
- Value Impact: Error classification enables appropriate user messaging and system recovery
- Strategic Impact: Platform reliability and user experience depend on clear error handling

These tests validate the business logic of agent error classification without external dependencies.
Testing custom error types ensures proper error categorization, severity assignment, and context handling.
"""

import pytest
from typing import Optional

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.agent_error_types import (
    AgentValidationError,
    NetworkError,
    AgentDatabaseError,
    DatabaseError  # Backward compatibility alias
)
from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.schemas.shared_types import ErrorContext


class TestAgentErrorTypes(SSotBaseTestCase):
    """Test agent error type classification and behavior."""

    @pytest.mark.unit
    def test_agent_validation_error_creation(self):
        """Test AgentValidationError creation with proper attributes.
        
        BVJ: Validation errors must be properly classified for user feedback.
        """
        error_msg = "Invalid input parameter"
        field_name = "user_id"
        context = ErrorContext(operation="test_validation", trace_id="test-123", user_id="user-456")
        
        error = AgentValidationError(
            message=error_msg,
            field_name=field_name,
            context=context
        )
        
        # Verify error message and custom attributes
        assert error_msg in str(error)  # Error may include category prefix
        assert error.field_name == field_name
        assert error.context == context
        
        # Verify proper classification
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.VALIDATION
        
        # Record business metrics
        self.record_metric("validation_error_attributes_verified", True)
        self.record_metric("error_classification_correct", "validation")

    @pytest.mark.unit
    def test_agent_validation_error_optional_parameters(self):
        """Test AgentValidationError with optional parameters.
        
        BVJ: Error handling must be flexible for different validation scenarios.
        """
        error_msg = "Required field missing"
        
        # Create error with minimal parameters
        error = AgentValidationError(message=error_msg)
        
        assert str(error) == error_msg
        assert error.field_name is None
        assert error.context is None
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.VALIDATION

    @pytest.mark.unit
    def test_network_error_creation(self):
        """Test NetworkError creation with endpoint tracking.
        
        BVJ: Network errors must capture endpoint information for debugging and monitoring.
        """
        error_msg = "Connection timeout"
        endpoint = "https://api.external-service.com/v1/data"
        context = ErrorContext(operation="test_network", trace_id="net-456", user_id="user-789")
        
        error = NetworkError(
            message=error_msg,
            endpoint=endpoint,
            context=context
        )
        
        assert str(error) == error_msg
        assert error.endpoint == endpoint
        assert error.context == context
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.category == ErrorCategory.NETWORK
        
        # Record business metrics
        self.record_metric("network_error_endpoint_captured", True)
        self.record_metric("network_error_severity", "medium")

    @pytest.mark.unit
    def test_network_error_optional_parameters(self):
        """Test NetworkError with minimal parameters.
        
        BVJ: Network errors must work without endpoint specification for internal errors.
        """
        error_msg = "Internal network failure"
        
        error = NetworkError(message=error_msg)
        
        assert str(error) == error_msg
        assert error.endpoint is None
        assert error.context is None
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.category == ErrorCategory.NETWORK

    @pytest.mark.unit
    def test_agent_database_error_creation(self):
        """Test AgentDatabaseError creation with query tracking.
        
        BVJ: Database errors must capture query information for performance analysis.
        """
        error_msg = "Query execution failed"
        query = "SELECT * FROM user_sessions WHERE user_id = $1"
        context = ErrorContext(operation="test_database", trace_id="db-789", user_id="user-012")
        
        error = AgentDatabaseError(
            message=error_msg,
            query=query,
            context=context
        )
        
        assert str(error) == error_msg
        assert error.query == query
        assert error.context == context
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.DATABASE
        
        # Record business metrics
        self.record_metric("database_error_query_captured", True)
        self.record_metric("database_error_severity", "high")

    @pytest.mark.unit
    def test_agent_database_error_optional_parameters(self):
        """Test AgentDatabaseError with minimal parameters.
        
        BVJ: Database errors must work without query specification for connection issues.
        """
        error_msg = "Database connection lost"
        
        error = AgentDatabaseError(message=error_msg)
        
        assert str(error) == error_msg
        assert error.query is None
        assert error.context is None
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.DATABASE

    @pytest.mark.unit
    def test_database_error_backward_compatibility(self):
        """Test backward compatibility alias for DatabaseError.
        
        BVJ: Existing code must continue working during transition periods.
        """
        error_msg = "Legacy database error"
        
        # Use the alias
        error = DatabaseError(message=error_msg)
        
        # Verify it's actually AgentDatabaseError
        assert isinstance(error, AgentDatabaseError)
        assert str(error) == error_msg
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.DATABASE
        
        self.record_metric("backward_compatibility_verified", True)

    @pytest.mark.unit 
    def test_error_severity_classification(self):
        """Test that different error types have appropriate severity levels.
        
        BVJ: Proper severity classification enables appropriate alerting and response.
        """
        validation_error = AgentValidationError("test")
        network_error = NetworkError("test")
        database_error = AgentDatabaseError("test")
        
        # Verify severity assignments match business requirements
        assert validation_error.severity == ErrorSeverity.HIGH  # User input issues are high priority
        assert network_error.severity == ErrorSeverity.MEDIUM   # Network issues are medium priority  
        assert database_error.severity == ErrorSeverity.HIGH    # Data issues are high priority
        
        self.record_metric("severity_classification_verified", True)

    @pytest.mark.unit
    def test_error_category_classification(self):
        """Test that error types are properly categorized for monitoring.
        
        BVJ: Error categorization enables proper monitoring dashboards and alerting rules.
        """
        validation_error = AgentValidationError("test")
        network_error = NetworkError("test")  
        database_error = AgentDatabaseError("test")
        
        # Verify category assignments
        assert validation_error.category == ErrorCategory.VALIDATION
        assert network_error.category == ErrorCategory.NETWORK
        assert database_error.category == ErrorCategory.DATABASE
        
        self.record_metric("category_classification_verified", True)

    @pytest.mark.unit
    def test_error_context_propagation(self):
        """Test that error context is properly propagated for tracing.
        
        BVJ: Error context enables distributed tracing and user impact analysis.
        """
        trace_id = "trace-123-456"
        user_id = "user-789-012"
        context = ErrorContext(operation="test_error_creation", trace_id=trace_id, user_id=user_id)
        
        validation_error = AgentValidationError("test", context=context)
        network_error = NetworkError("test", context=context)
        database_error = AgentDatabaseError("test", context=context)
        
        # Verify context is preserved
        assert validation_error.context.trace_id == trace_id
        assert validation_error.context.user_id == user_id
        
        assert network_error.context.trace_id == trace_id
        assert network_error.context.user_id == user_id
        
        assert database_error.context.trace_id == trace_id
        assert database_error.context.user_id == user_id
        
        self.record_metric("error_context_propagated", True)

    @pytest.mark.unit
    def test_error_inheritance_hierarchy(self):
        """Test that all custom errors inherit from AgentError.
        
        BVJ: Proper inheritance enables consistent error handling across the platform.
        """
        from netra_backend.app.core.exceptions_agent import AgentError
        
        validation_error = AgentValidationError("test")
        network_error = NetworkError("test")
        database_error = AgentDatabaseError("test")
        
        # Verify inheritance chain
        assert isinstance(validation_error, AgentError)
        assert isinstance(network_error, AgentError)
        assert isinstance(database_error, AgentError)
        
        self.record_metric("error_inheritance_verified", True)

    def test_execution_timing_under_threshold(self):
        """Verify test execution performance meets requirements.
        
        BVJ: Fast unit tests enable rapid development cycles.
        """
        # Unit tests must execute under 100ms
        self.assert_execution_time_under(0.1)
        
        # Verify business metrics were recorded
        self.assert_metrics_recorded(
            "validation_error_attributes_verified",
            "network_error_endpoint_captured", 
            "database_error_query_captured",
            "backward_compatibility_verified",
            "severity_classification_verified",
            "category_classification_verified",
            "error_context_propagated",
            "error_inheritance_verified"
        )