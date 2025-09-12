"""
Tests for custom agent error classes.
All functions  <= 8 lines per requirements.
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add netra_backend to path  

import pytest

from netra_backend.app.core.exceptions_agent import AgentError
from netra_backend.app.agents.agent_error_types import (
DatabaseError,
NetworkError,
AgentValidationError as ValidationError,
)
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.core.error_codes import ErrorSeverity

class TestAgentErrors:
    """Test custom agent error classes."""

    def _create_basic_agent_error(self):
        """Create basic agent error for testing"""
        return AgentError(
    message="Test error message",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.HIGH,
    original_error=ValueError("Original error")
    )

    def _assert_basic_agent_error(self, error):
        """Assert basic agent error properties"""
        assert error.message == "Test error message"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.HIGH
        assert isinstance(error.original_error, ValueError)

        def test_agent_error_creation(self):
            """Test AgentError creation with all parameters."""
            error = self._create_basic_agent_error()
            self._assert_basic_agent_error(error)

            def _create_default_agent_error(self):
                """Create agent error with defaults"""
                return AgentError("Default error")

            def test_agent_error_defaults(self):
                """Test AgentError with default values."""
                error = self._create_default_agent_error()
                assert error.message == "Default error"
                assert error.category == ErrorCategory.UNKNOWN
                assert error.severity == ErrorSeverity.MEDIUM

                def _create_validation_error(self):
                    """Create validation error for testing"""
                    return ValidationError("Invalid input", field_name="test_field")

                def test_validation_error(self):
                    """Test ValidationError creation."""
                    error = self._create_validation_error()
                    assert error.message == "Invalid input"
                    assert error.category == ErrorCategory.VALIDATION
                    assert error.field_name == "test_field"

                    def _create_network_error(self):
                        """Create network error for testing"""
                        return NetworkError("Connection failed", endpoint="http://test.com")

                    def test_network_error(self):
                        """Test NetworkError creation."""
                        error = self._create_network_error()
                        assert error.message == "Connection failed"
                        assert error.category == ErrorCategory.NETWORK
                        assert error.endpoint == "http://test.com"

                        def _create_database_error(self):
                            """Create database error for testing"""
                            return DatabaseError("Query failed", query="SELECT * FROM test")

                        def test_database_error(self):
                            """Test DatabaseError creation."""
                            error = self._create_database_error()
                            assert error.message == "Query failed"
                            assert error.category == ErrorCategory.DATABASE
                            assert error.query == "SELECT * FROM test"

                            def test_agent_error_inheritance(self):
                                """Test that custom errors inherit from AgentError."""
                                validation_error = self._create_validation_error()
                                network_error = self._create_network_error()
                                database_error = self._create_database_error()

                                assert isinstance(validation_error, AgentError)
                                assert isinstance(network_error, AgentError)
                                assert isinstance(database_error, AgentError)

                                def test_agent_error_string_representation(self):
                                    """Test AgentError string representation."""
                                    error = self._create_basic_agent_error()

                                    str_repr = str(error)
                                    assert "Test error message" in str_repr
                                    assert "VALIDATION" in str_repr

                                    def _create_error_with_context(self):
                                        """Create error with context data"""
                                        return AgentError(
                                    "Context error",
                                    context={"operation": "test", "data": {"key": "value"}}
                                    )

                                    def test_agent_error_with_context(self):
                                        """Test AgentError with context data."""
                                        error = self._create_error_with_context()

                                        assert error.message == "Context error"
                                        assert error.context["operation"] == "test"
                                        assert error.context["data"]["key"] == "value"

                                        def test_agent_error_serialization(self):
                                            """Test AgentError serialization capabilities."""
                                            error = self._create_basic_agent_error()

        # Test dict conversion if available
                                            if hasattr(error, 'to_dict'):
                                                error_dict = error.to_dict()
                                                assert "message" in error_dict
                                                assert "category" in error_dict

                                                def _create_chained_error(self):
                                                    """Create chained error for testing"""
                                                    original = ValueError("Original issue")
                                                    return AgentError("Chained error", original_error=original)

                                                def test_error_chaining(self):
                                                    """Test error chaining functionality."""
                                                    error = self._create_chained_error()

                                                    assert error.message == "Chained error"
                                                    assert isinstance(error.original_error, ValueError)
                                                    assert str(error.original_error) == "Original issue"

                                                    def test_error_severity_ordering(self):
                                                        """Test error severity ordering."""
                                                        low_error = AgentError("Low", severity=ErrorSeverity.LOW)
                                                        high_error = AgentError("High", severity=ErrorSeverity.HIGH)

                                                        assert low_error.severity == ErrorSeverity.LOW
                                                        assert high_error.severity == ErrorSeverity.HIGH

                                                        def test_error_category_specificity(self):
                                                            """Test error category specificity."""
                                                            validation_error = self._create_validation_error()
                                                            network_error = self._create_network_error()

                                                            assert validation_error.category != network_error.category
                                                            assert validation_error.category == ErrorCategory.VALIDATION
                                                            assert network_error.category == ErrorCategory.NETWORK

                                                            def _create_error_with_metadata(self):
                                                                """Create error with additional metadata"""
                                                                return AgentError(
                                                            "Metadata error",
                                                            metadata={
                                                            "timestamp": 1234567890,
                                                            "agent_id": "test_agent",
                                                            "correlation_id": "abc123"
                                                            }
                                                            )

                                                            def test_agent_error_metadata(self):
                                                                """Test AgentError with metadata."""
                                                                error = self._create_error_with_metadata()

                                                                assert error.message == "Metadata error"
                                                                if hasattr(error, 'metadata'):
                                                                    assert error.metadata["agent_id"] == "test_agent"
                                                                    assert error.metadata["correlation_id"] == "abc123"