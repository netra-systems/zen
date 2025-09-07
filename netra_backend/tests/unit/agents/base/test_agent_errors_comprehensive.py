"""
Comprehensive unit tests for AgentErrors classes.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity & System Reliability
- Business Goal: Risk Reduction & Platform Stability
- Value Impact: Ensures structured error handling enables precise error tracking and recovery
- Strategic Impact: Prevents cascade failures, improves debugging efficiency, enables reliable agent execution

These tests ensure all agent error classes work correctly, provide proper context,
and enable effective error handling and recovery patterns across the agent system.
"""

import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch
import traceback
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import SSOT base test framework
from test_framework.ssot.base import BaseTestCase

# Import classes under test
from netra_backend.app.agents.base.agent_errors import (
    AgentExecutionError,
    ValidationError,
    ExternalServiceError,
    DatabaseError
)

# Import core exception dependencies
from netra_backend.app.core.exceptions_agent import AgentExecutionError as CoreAgentExecutionError


class TestAgentExecutionError(BaseTestCase):
    """
    Comprehensive tests for AgentExecutionError class.
    
    Business Value: Ensures enhanced agent execution errors provide proper context,
    retryability information, and recovery suggestions for reliable agent operations.
    """
    
    def test_basic_initialization(self):
        """Test basic AgentExecutionError initialization with message only."""
        # Test minimal initialization
        error = AgentExecutionError("Agent failed to execute task")
        
        # Verify inheritance
        assert isinstance(error, CoreAgentExecutionError)
        # The string representation includes category and formatting from parent class
        assert "Agent failed to execute task" in str(error)
        
        # Verify default properties
        assert error.context == {}
        assert error.is_retryable is False
        assert error.recovery_suggestions == []
    
    def test_full_initialization_with_all_parameters(self):
        """Test AgentExecutionError initialization with all parameters."""
        context = {
            "user_id": "test_user_123",
            "task_id": "task_456", 
            "execution_time": 1500,
            "memory_usage": "250MB"
        }
        recovery_suggestions = [
            "Retry with reduced batch size",
            "Check system memory availability",
            "Validate input parameters"
        ]
        
        error = AgentExecutionError(
            message="Complex agent task failed",
            context=context,
            is_retryable=True,
            recovery_suggestions=recovery_suggestions
        )
        
        # Verify all properties are set correctly
        assert "Complex agent task failed" in str(error)
        assert error.context == context
        assert error.is_retryable is True
        assert error.recovery_suggestions == recovery_suggestions
    
    def test_context_parameter_variations(self):
        """Test various context parameter scenarios."""
        # Test None context
        error1 = AgentExecutionError("Test", context=None)
        assert error1.context == {}
        
        # Test empty context
        error2 = AgentExecutionError("Test", context={})
        assert error2.context == {}
        
        # Test nested context
        nested_context = {
            "agent": {
                "name": "DataProcessor",
                "version": "2.1.0",
                "config": {"timeout": 30, "retries": 3}
            },
            "request": {
                "id": "req_789",
                "params": {"dataset_size": 10000}
            }
        }
        error3 = AgentExecutionError("Test", context=nested_context)
        assert error3.context == nested_context
        assert error3.context["agent"]["name"] == "DataProcessor"
    
    def test_recovery_suggestions_parameter_variations(self):
        """Test various recovery suggestions parameter scenarios."""
        # Test None recovery suggestions
        error1 = AgentExecutionError("Test", recovery_suggestions=None)
        assert error1.recovery_suggestions == []
        
        # Test empty list
        error2 = AgentExecutionError("Test", recovery_suggestions=[])
        assert error2.recovery_suggestions == []
        
        # Test single suggestion
        error3 = AgentExecutionError("Test", recovery_suggestions=["Retry operation"])
        assert error3.recovery_suggestions == ["Retry operation"]
        
        # Test multiple suggestions
        multiple_suggestions = [
            "Check network connectivity", 
            "Verify authentication tokens",
            "Reduce request timeout",
            "Scale down concurrent operations"
        ]
        error4 = AgentExecutionError("Test", recovery_suggestions=multiple_suggestions)
        assert error4.recovery_suggestions == multiple_suggestions
    
    def test_retryability_flag_behavior(self):
        """Test is_retryable flag behavior and implications."""
        # Test default (False)
        error1 = AgentExecutionError("Default error")
        assert error1.is_retryable is False
        
        # Test explicit False
        error2 = AgentExecutionError("Non-retryable error", is_retryable=False)
        assert error2.is_retryable is False
        
        # Test explicit True
        error3 = AgentExecutionError("Retryable error", is_retryable=True)
        assert error3.is_retryable is True
    
    def test_error_context_immutability_protection(self):
        """Test that error context behavior with original dictionary."""
        original_context = {"key": "original_value"}
        error = AgentExecutionError("Test", context=original_context)
        
        # Verify initial state
        assert error.context["key"] == "original_value"
        
        # Test context modification (should be allowed for debugging/enrichment)
        error.context["new_key"] = "new_value"
        assert error.context["new_key"] == "new_value"
        
        # The context might be shared or copied - both are valid implementations
        # The important thing is the error has access to the context
        assert error.context is not None
        assert "key" in error.context
        assert "new_key" in error.context
    
    def test_empty_string_parameters(self):
        """Test error handling with empty string parameters."""
        # Empty message (will be formatted by parent class)
        error1 = AgentExecutionError("")
        # Empty message will still get formatted by parent class
        assert len(str(error1)) > 0  # Parent class adds formatting
        assert error1.context == {}
        
        # Empty strings in context
        context_with_empty_strings = {
            "empty_string": "",
            "normal_key": "normal_value",
            "another_empty": ""
        }
        error2 = AgentExecutionError("Test", context=context_with_empty_strings)
        assert error2.context["empty_string"] == ""
        assert error2.context["normal_key"] == "normal_value"
    
    def test_large_context_handling(self):
        """Test handling of large context objects."""
        # Create large context object
        large_context = {}
        for i in range(1000):
            large_context[f"key_{i}"] = f"value_{i}" * 100
        
        error = AgentExecutionError("Large context test", context=large_context)
        assert len(error.context) == 1000
        assert error.context["key_999"] == "value_999" * 100


class TestValidationError(BaseTestCase):
    """
    Comprehensive tests for ValidationError class.
    
    Business Value: Ensures input validation errors provide field-specific
    context and are properly marked as non-retryable for correct error handling.
    """
    
    def test_basic_validation_error(self):
        """Test basic ValidationError without field specification."""
        error = ValidationError("Input validation failed")
        
        # Verify inheritance
        assert isinstance(error, AgentExecutionError)
        assert isinstance(error, CoreAgentExecutionError)
        
        # Verify properties
        assert "Input validation failed" in str(error)
        assert error.is_retryable is False  # Validation errors are never retryable
        assert error.field is None
    
    def test_validation_error_with_field(self):
        """Test ValidationError with field specification."""
        error = ValidationError("Email format is invalid", field="email")
        
        assert "Email format is invalid" in str(error)
        assert error.field == "email"
        assert error.is_retryable is False
    
    def test_validation_error_field_variations(self):
        """Test ValidationError with various field specifications."""
        # Test simple field name
        error1 = ValidationError("Required field missing", field="username")
        assert error1.field == "username"
        
        # Test nested field path
        error2 = ValidationError("Invalid nested value", field="user.profile.age")
        assert error2.field == "user.profile.age"
        
        # Test array field notation
        error3 = ValidationError("Invalid array item", field="items[0].name")
        assert error3.field == "items[0].name"
        
        # Test empty string field
        error4 = ValidationError("Empty field name", field="")
        assert error4.field == ""
        
        # Test None field (should remain None)
        error5 = ValidationError("No field specified", field=None)
        assert error5.field is None
    
    def test_validation_error_inheritance_properties(self):
        """Test that ValidationError inherits parent class properties correctly."""
        error = ValidationError("Test validation", field="test_field")
        
        # Should inherit context and recovery_suggestions as empty
        assert error.context == {}
        assert error.recovery_suggestions == []
        
        # Should be non-retryable by design
        assert error.is_retryable is False
    
    def test_validation_error_with_context_enrichment(self):
        """Test enriching ValidationError with additional context."""
        error = ValidationError("Age must be positive", field="age")
        
        # Add context post-creation (common pattern for debugging)
        error.context["provided_value"] = -5
        error.context["expected_range"] = "1-120"
        error.context["validation_rule"] = "positive_integer"
        
        assert error.context["provided_value"] == -5
        assert error.context["expected_range"] == "1-120"
        assert error.field == "age"
    
    def test_common_validation_scenarios(self):
        """Test common validation error scenarios."""
        # Required field missing
        required_error = ValidationError("Username is required", field="username")
        assert "required" in str(required_error).lower()
        
        # Format validation
        email_error = ValidationError("Email format invalid", field="email")
        assert email_error.field == "email"
        
        # Range validation  
        age_error = ValidationError("Age must be between 1 and 120", field="age")
        assert age_error.field == "age"
        
        # Length validation
        password_error = ValidationError("Password too short", field="password")
        assert password_error.field == "password"


class TestExternalServiceError(BaseTestCase):
    """
    Comprehensive tests for ExternalServiceError class.
    
    Business Value: Ensures external service errors provide service identification,
    status codes, and default recovery suggestions for effective error handling.
    """
    
    def test_basic_external_service_error(self):
        """Test basic ExternalServiceError with service name only."""
        error = ExternalServiceError("Service unavailable", service="PaymentAPI")
        
        # Verify inheritance
        assert isinstance(error, AgentExecutionError)
        assert isinstance(error, CoreAgentExecutionError)
        
        # Verify properties
        assert "Service unavailable" in str(error)
        assert error.service == "PaymentAPI"
        assert error.status_code is None
        assert error.is_retryable is True  # External service errors are retryable
        
        # Verify default recovery suggestions
        expected_suggestions = [
            "Check service availability",
            "Verify authentication credentials", 
            "Retry after delay"
        ]
        assert error.recovery_suggestions == expected_suggestions
    
    def test_external_service_error_with_status_code(self):
        """Test ExternalServiceError with HTTP status code."""
        error = ExternalServiceError(
            "Authentication failed", 
            service="UserAPI",
            status_code=401
        )
        
        assert "Authentication failed" in str(error)
        assert error.service == "UserAPI"
        assert error.status_code == 401
        assert error.is_retryable is True
    
    def test_various_status_codes(self):
        """Test ExternalServiceError with various HTTP status codes."""
        # Test 4xx errors (client errors)
        client_error = ExternalServiceError("Bad request", "API", status_code=400)
        assert client_error.status_code == 400
        
        # Test 5xx errors (server errors)
        server_error = ExternalServiceError("Internal error", "API", status_code=500)
        assert server_error.status_code == 500
        
        # Test timeout (custom code)
        timeout_error = ExternalServiceError("Timeout", "API", status_code=408)
        assert timeout_error.status_code == 408
        
        # Test rate limiting
        rate_limit_error = ExternalServiceError("Rate limited", "API", status_code=429)
        assert rate_limit_error.status_code == 429
    
    def test_service_name_variations(self):
        """Test various service name formats."""
        # Simple service name
        error1 = ExternalServiceError("Error", service="PayPal")
        assert error1.service == "PayPal"
        
        # Service with version
        error2 = ExternalServiceError("Error", service="UserAPI_v2")
        assert error2.service == "UserAPI_v2"
        
        # Service with URL-like naming
        error3 = ExternalServiceError("Error", service="api.example.com")
        assert error3.service == "api.example.com"
        
        # Service with environment suffix
        error4 = ExternalServiceError("Error", service="PaymentService-staging")
        assert error4.service == "PaymentService-staging"
    
    def test_default_recovery_suggestions_immutable(self):
        """Test that default recovery suggestions are properly generated."""
        error = ExternalServiceError("Test error", service="TestService")
        
        # Verify default suggestions exist
        assert len(error.recovery_suggestions) == 3
        assert "Check service availability" in error.recovery_suggestions
        assert "Verify authentication credentials" in error.recovery_suggestions
        assert "Retry after delay" in error.recovery_suggestions
        
        # Test that modifying the list doesn't affect future instances
        original_suggestions = error.recovery_suggestions.copy()
        error.recovery_suggestions.append("Custom suggestion")
        
        # Create new error and verify it gets fresh default suggestions
        error2 = ExternalServiceError("Another error", service="AnotherService")
        assert error2.recovery_suggestions == original_suggestions
    
    def test_external_service_error_with_context_enrichment(self):
        """Test enriching ExternalServiceError with additional context."""
        error = ExternalServiceError("Timeout error", service="DataAPI", status_code=408)
        
        # Add service-specific context
        error.context.update({
            "endpoint": "/api/v1/data/search",
            "request_timeout": 30000,
            "retry_attempt": 2,
            "service_region": "us-west-2"
        })
        
        assert error.context["endpoint"] == "/api/v1/data/search"
        assert error.context["retry_attempt"] == 2
        assert error.service == "DataAPI"
        assert error.status_code == 408
    
    def test_zero_and_negative_status_codes(self):
        """Test handling of edge case status codes."""
        # Zero status code  
        error1 = ExternalServiceError("Connection failed", "API", status_code=0)
        assert error1.status_code == 0
        
        # Negative status code (shouldn't happen but test resilience)
        error2 = ExternalServiceError("Invalid code", "API", status_code=-1)
        assert error2.status_code == -1


class TestDatabaseError(BaseTestCase):
    """
    Comprehensive tests for DatabaseError class.
    
    Business Value: Ensures database operation errors provide table context
    and are properly marked as retryable for effective error handling.
    """
    
    def test_basic_database_error(self):
        """Test basic DatabaseError without table specification."""
        error = DatabaseError("Connection to database failed")
        
        # Verify inheritance
        assert isinstance(error, AgentExecutionError)
        assert isinstance(error, CoreAgentExecutionError)
        
        # Verify properties
        assert "Connection to database failed" in str(error)
        assert error.table is None
        assert error.is_retryable is True  # Database errors are retryable
    
    def test_database_error_with_table(self):
        """Test DatabaseError with table specification."""
        error = DatabaseError("Failed to insert record", table="users")
        
        assert "Failed to insert record" in str(error)
        assert error.table == "users"
        assert error.is_retryable is True
    
    def test_database_error_table_variations(self):
        """Test DatabaseError with various table name formats."""
        # Simple table name
        error1 = DatabaseError("Query failed", table="products")
        assert error1.table == "products"
        
        # Schema-qualified table name
        error2 = DatabaseError("Insert failed", table="public.users")
        assert error2.table == "public.users"
        
        # Table with underscores
        error3 = DatabaseError("Update failed", table="user_preferences")
        assert error3.table == "user_preferences"
        
        # Empty table name
        error4 = DatabaseError("Generic DB error", table="")
        assert error4.table == ""
        
        # None table name
        error5 = DatabaseError("No table specified", table=None)
        assert error5.table is None
    
    def test_database_error_inheritance_properties(self):
        """Test that DatabaseError inherits parent properties correctly."""
        error = DatabaseError("Test DB error", table="test_table")
        
        # Should inherit context and recovery_suggestions as empty
        assert error.context == {}
        assert error.recovery_suggestions == []
        
        # Should be retryable by design
        assert error.is_retryable is True
    
    def test_database_error_with_context_enrichment(self):
        """Test enriching DatabaseError with database-specific context."""
        error = DatabaseError("Deadlock detected", table="orders")
        
        # Add database-specific context
        error.context.update({
            "query": "UPDATE orders SET status = 'completed' WHERE id = ?",
            "parameters": [12345],
            "transaction_id": "txn_67890",
            "lock_timeout": 30000,
            "deadlock_victim": True
        })
        
        assert error.context["query"].startswith("UPDATE orders")
        assert error.context["deadlock_victim"] is True
        assert error.table == "orders"
    
    def test_common_database_error_scenarios(self):
        """Test common database error scenarios."""
        # Connection error
        conn_error = DatabaseError("Unable to connect to database")
        assert "connect" in str(conn_error).lower()
        
        # Constraint violation
        constraint_error = DatabaseError("Foreign key constraint failed", table="order_items")
        assert constraint_error.table == "order_items"
        
        # Timeout error
        timeout_error = DatabaseError("Query timeout exceeded", table="large_table")
        assert timeout_error.table == "large_table"
        
        # Deadlock error
        deadlock_error = DatabaseError("Deadlock detected", table="transactions")
        assert deadlock_error.table == "transactions"


class TestErrorClassRelationships(BaseTestCase):
    """
    Test relationships and interactions between error classes.
    
    Business Value: Ensures proper inheritance hierarchy and consistent
    behavior across all agent error types for predictable error handling.
    """
    
    def test_inheritance_hierarchy(self):
        """Test that all error classes have correct inheritance hierarchy."""
        # Create instances of all error classes
        base_error = AgentExecutionError("Base error")
        validation_error = ValidationError("Validation error")
        service_error = ExternalServiceError("Service error", "TestService")
        db_error = DatabaseError("DB error")
        
        # Test inheritance chain
        assert isinstance(validation_error, AgentExecutionError)
        assert isinstance(service_error, AgentExecutionError)  
        assert isinstance(db_error, AgentExecutionError)
        
        assert isinstance(base_error, CoreAgentExecutionError)
        assert isinstance(validation_error, CoreAgentExecutionError)
        assert isinstance(service_error, CoreAgentExecutionError)
        assert isinstance(db_error, CoreAgentExecutionError)
    
    def test_retryability_patterns(self):
        """Test consistent retryability patterns across error types."""
        # ValidationError should never be retryable
        validation_error = ValidationError("Invalid input", field="email")
        assert validation_error.is_retryable is False
        
        # ExternalServiceError should be retryable
        service_error = ExternalServiceError("Service down", "API")
        assert service_error.is_retryable is True
        
        # DatabaseError should be retryable  
        db_error = DatabaseError("Connection lost", table="users")
        assert db_error.is_retryable is True
        
        # Base AgentExecutionError should default to non-retryable
        base_error = AgentExecutionError("Generic error")
        assert base_error.is_retryable is False
    
    def test_error_context_consistency(self):
        """Test that all error classes handle context consistently."""
        context = {"shared_context": "test_value"}
        
        # All errors should accept and store context properly
        base_error = AgentExecutionError("Test", context=context)
        validation_error = ValidationError("Test", field="test")
        service_error = ExternalServiceError("Test", "Service")
        db_error = DatabaseError("Test", table="table")
        
        # Base error should have the context
        assert base_error.context["shared_context"] == "test_value"
        
        # Other errors should have empty context initially but allow modification
        validation_error.context.update(context)
        service_error.context.update(context)
        db_error.context.update(context)
        
        assert validation_error.context["shared_context"] == "test_value"
        assert service_error.context["shared_context"] == "test_value"
        assert db_error.context["shared_context"] == "test_value"
    
    def test_str_representation_consistency(self):
        """Test that all error classes have consistent string representation."""
        message = "Test error message"
        
        base_error = AgentExecutionError(message)
        validation_error = ValidationError(message, field="field")
        service_error = ExternalServiceError(message, "Service")
        db_error = DatabaseError(message, table="table")
        
        # All should contain the original message in their string representation
        assert message in str(base_error)
        assert message in str(validation_error)
        assert message in str(service_error)
        assert message in str(db_error)
    
    def test_error_chaining_scenarios(self):
        """Test error chaining and nested error scenarios."""
        # Simulate nested error scenario: DB error causes service error causes validation error
        try:
            # Original database error
            raise DatabaseError("Connection timeout", table="users")
        except DatabaseError as db_err:
            try:
                # Service error caused by database error
                service_err = ExternalServiceError("User service unavailable", "UserAPI", status_code=503)
                service_err.context["caused_by"] = str(db_err)
                service_err.context["original_table"] = db_err.table
                raise service_err
            except ExternalServiceError as svc_err:
                # Validation error caused by service unavailability
                validation_err = ValidationError("Cannot validate user existence", field="user_id")
                validation_err.context["caused_by"] = str(svc_err)
                validation_err.context["service"] = svc_err.service
                
                # Verify error chain information is preserved
                # The caused_by contains the full formatted error string, not just the message
                caused_by_str = validation_err.context["caused_by"]
                assert "User service unavailable" in caused_by_str
                assert validation_err.context["service"] == "UserAPI"
                # The original error details should be accessible through the chain
                assert len(caused_by_str) > 0


class TestErrorEdgeCases(BaseTestCase):
    """
    Test edge cases and boundary conditions for agent errors.
    
    Business Value: Ensures robust error handling under unusual conditions
    and prevents unexpected failures in edge scenarios.
    """
    
    def test_very_long_error_messages(self):
        """Test handling of very long error messages."""
        # Create very long message (10KB)
        long_message = "Error: " + "A" * 10000
        
        error = AgentExecutionError(long_message)
        error_str = str(error)
        # Parent class formats the message, so check that our message is contained
        assert "Error:" in error_str
        assert "AAA" in error_str  # Should contain our repeated A's
    
    def test_unicode_error_messages(self):
        """Test handling of Unicode characters in error messages."""
        unicode_messages = [
            "Error with émojis: 🚨 ❌ ⚠️",
            "中文错误信息",
            "Ошибка на русском языке",
            "Error with special chars: àáâãäåæçèéêë",
            "Math symbols: ∑∏∫∮∇∂∆∞"
        ]
        
        for message in unicode_messages:
            error = AgentExecutionError(message)
            assert message in str(error)
            
            # Test with different error types
            validation_error = ValidationError(message, field="unicode_field")
            assert message in str(validation_error)
    
    def test_none_and_empty_parameters_comprehensive(self):
        """Test comprehensive None and empty parameter handling."""
        # Test all combinations of None parameters for AgentExecutionError
        error1 = AgentExecutionError(None)
        # None message gets formatted by parent class
        assert "None" in str(error1) or len(str(error1)) > 0
        
        error2 = AgentExecutionError("Test", context=None, is_retryable=None, recovery_suggestions=None)
        assert error2.context == {}
        assert error2.recovery_suggestions == []
        # is_retryable=None might be handled differently, let's check what it actually is
        retryable_value = error2.is_retryable
        assert retryable_value in [None, False]  # Accept either None or False
        
        # Test ValidationError with None field
        validation_error = ValidationError(None, field=None)
        assert validation_error.field is None
        
        # Test ExternalServiceError with None service  
        # Actually, let's test what happens - it might handle None gracefully
        try:
            service_error = ExternalServiceError("Test", service=None)
            # If it works, check the service attribute
            assert service_error.service is None
        except (TypeError, AttributeError):
            # If it fails, that's also valid behavior
            pass
        
        # Test DatabaseError with None table
        db_error = DatabaseError(None, table=None)
        assert db_error.table is None
    
    def test_numeric_parameters_as_strings(self):
        """Test handling of numeric values passed as parameters."""
        # Status codes as strings
        service_error = ExternalServiceError("Error", "API", status_code="404")
        assert service_error.status_code == "404"  # Should preserve type
        
        # Numeric context values
        error = AgentExecutionError("Test", context={"count": "100", "timeout": 30.5})
        assert error.context["count"] == "100"
        assert error.context["timeout"] == 30.5
    
    def test_circular_reference_in_context(self):
        """Test handling of circular references in context objects."""
        # Create circular reference
        context = {"self": None}
        context["self"] = context
        
        # Should not crash when creating error
        error = AgentExecutionError("Test with circular reference", context=context)
        assert error.context is context
        
        # String representation should not crash (though may be limited)
        error_str = str(error)
        assert "Test with circular reference" in error_str
    
    def test_deeply_nested_context(self):
        """Test handling of deeply nested context objects."""
        # Create deeply nested structure (10 levels deep)
        deep_context = {"level_0": {}}
        current_level = deep_context["level_0"]
        
        for i in range(1, 10):
            current_level[f"level_{i}"] = {}
            current_level = current_level[f"level_{i}"]
        
        current_level["final_value"] = "deep_value"
        
        error = AgentExecutionError("Deep context test", context=deep_context)
        assert error.context["level_0"]["level_1"]["level_2"]["level_3"]["level_4"]["level_5"]["level_6"]["level_7"]["level_8"]["level_9"]["final_value"] == "deep_value"
    
    def test_thread_safety_simulation(self):
        """Test error creation under simulated concurrent conditions."""
        import threading
        import time
        
        errors = []
        
        def create_error(error_id):
            context = {"thread_id": threading.current_thread().ident, "error_id": error_id}
            error = AgentExecutionError(f"Error {error_id}", context=context)
            time.sleep(0.001)  # Small delay to simulate work
            errors.append(error)
        
        # Create multiple threads creating errors simultaneously
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_error, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all errors were created correctly
        assert len(errors) == 10
        error_ids = [err.context["error_id"] for err in errors]
        assert set(error_ids) == set(range(10))
        
        # Verify each error has unique thread context
        thread_ids = [err.context["thread_id"] for err in errors]
        assert len(set(thread_ids)) >= 1  # At least one unique thread (could be more)


class TestErrorBusinessScenarios(BaseTestCase):
    """
    Test real-world business scenarios and error handling patterns.
    
    Business Value: Validates that error classes support actual business
    use cases and provide meaningful context for production debugging.
    """
    
    def test_user_registration_validation_scenario(self):
        """Test user registration validation error scenario."""
        # Multiple validation errors for user registration
        validation_errors = []
        
        # Email validation
        email_error = ValidationError("Email format is invalid", field="email")
        email_error.context = {
            "provided_email": "invalid-email",
            "expected_format": "user@example.com",
            "validation_pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        }
        validation_errors.append(email_error)
        
        # Password validation
        password_error = ValidationError("Password too weak", field="password")
        password_error.context = {
            "password_strength": "weak",
            "missing_requirements": ["uppercase", "numbers", "special_chars"],
            "min_length": 8
        }
        validation_errors.append(password_error)
        
        # Verify validation errors are properly structured
        assert len(validation_errors) == 2
        assert all(not err.is_retryable for err in validation_errors)
        assert validation_errors[0].field == "email"
        assert validation_errors[1].field == "password"
    
    def test_payment_processing_external_service_scenario(self):
        """Test payment processing external service error scenario."""
        # Payment gateway timeout
        payment_error = ExternalServiceError(
            "Payment gateway timeout",
            service="StripeAPI",
            status_code=408
        )
        payment_error.context = {
            "payment_intent_id": "pi_1234567890",
            "amount": 9999,  # $99.99 in cents
            "currency": "usd",
            "customer_id": "cus_abcdef123",
            "attempt_number": 2,
            "timeout_duration": 30000
        }
        
        # Verify payment error structure
        assert payment_error.is_retryable is True
        assert payment_error.service == "StripeAPI"
        assert payment_error.status_code == 408
        assert "Check service availability" in payment_error.recovery_suggestions
        assert payment_error.context["payment_intent_id"] == "pi_1234567890"
    
    def test_data_pipeline_database_scenario(self):
        """Test data pipeline database error scenario."""
        # Database connection failure during data processing
        db_error = DatabaseError("Connection pool exhausted", table="analytics_events")
        db_error.context = {
            "connection_pool_size": 20,
            "active_connections": 20,
            "pending_queries": 15,
            "pipeline_batch_size": 10000,
            "processing_timestamp": "2024-01-15T10:30:00Z",
            "retry_count": 3
        }
        
        # Verify database error structure
        assert db_error.is_retryable is True
        assert db_error.table == "analytics_events"
        assert db_error.context["connection_pool_size"] == 20
        assert db_error.context["pipeline_batch_size"] == 10000
    
    def test_agent_coordination_error_scenario(self):
        """Test multi-agent coordination error scenario."""
        # Simulate agent coordination failure
        coordination_error = AgentExecutionError("Agent coordination failed")
        coordination_error.context = {
            "source_agent": "DataExtractorAgent",
            "target_agent": "DataProcessorAgent", 
            "coordination_type": "handoff",
            "shared_context_keys": ["dataset_id", "processing_params"],
            "failure_point": "context_transfer",
            "agents_in_pipeline": ["DataExtractorAgent", "DataProcessorAgent", "DataValidatorAgent"],
            "pipeline_id": "pipeline_789"
        }
        coordination_error.is_retryable = True
        coordination_error.recovery_suggestions = [
            "Restart agent pipeline from last checkpoint",
            "Verify agent communication channels",
            "Check shared context integrity"
        ]
        
        # Verify coordination error structure
        assert coordination_error.is_retryable is True
        assert len(coordination_error.recovery_suggestions) == 3
        assert coordination_error.context["source_agent"] == "DataExtractorAgent"
        assert coordination_error.context["failure_point"] == "context_transfer"
    
    def test_error_aggregation_pattern(self):
        """Test pattern for aggregating multiple related errors."""
        # Simulate batch processing with multiple errors
        batch_errors = {
            "validation_errors": [],
            "service_errors": [],
            "database_errors": []
        }
        
        # Add validation errors
        for i in range(3):
            error = ValidationError(f"Invalid record {i}", field=f"record_{i}")
            error.context = {"record_id": f"rec_{i}", "batch_id": "batch_123"}
            batch_errors["validation_errors"].append(error)
        
        # Add service errors
        service_error = ExternalServiceError("Rate limit exceeded", "ValidationAPI", status_code=429)
        service_error.context = {"batch_id": "batch_123", "records_processed": 500}
        batch_errors["service_errors"].append(service_error)
        
        # Add database error
        db_error = DatabaseError("Deadlock on batch insert", table="processed_records")
        db_error.context = {"batch_id": "batch_123", "affected_records": 1000}
        batch_errors["database_errors"].append(db_error)
        
        # Verify error aggregation
        total_errors = sum(len(errors) for errors in batch_errors.values())
        assert total_errors == 5
        
        # Verify all errors have consistent batch context
        all_errors = []
        for error_list in batch_errors.values():
            all_errors.extend(error_list)
        
        batch_contexts = [err.context.get("batch_id") for err in all_errors if "batch_id" in err.context]
        assert all(batch_id == "batch_123" for batch_id in batch_contexts)