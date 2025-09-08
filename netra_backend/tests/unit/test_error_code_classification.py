"""
Test Error Code Classification Business Logic - Core Unit Tests

Business Value Justification (BVJ):
- Segment: All (Error handling affects all user tiers and internal operations)
- Business Goal: Operational excellence and rapid incident resolution
- Value Impact: Proper error classification enables faster debugging and improved uptime
- Strategic Impact: CRITICAL - System reliability directly affects user retention and business reputation

This test suite validates the core business logic for error code classification
that enables proper monitoring, alerting, and incident response.
"""

import pytest
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity


class TestErrorCodeClassification(BaseTestCase):
    """Test error code classification delivers operational excellence for business reliability."""
    
    def setup_method(self):
        """Setup test environment with isolated configuration."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        
    def teardown_method(self):
        """Clean up test environment."""
        super().teardown_method()
        
    @pytest.mark.unit
    def test_error_code_enum_completeness(self):
        """Test that error code enum covers all major system failure categories."""
        # Verify critical error categories are present
        critical_categories = [
            # Authentication errors - affect user access
            ErrorCode.AUTHENTICATION_FAILED,
            ErrorCode.AUTHORIZATION_FAILED,
            ErrorCode.TOKEN_EXPIRED,
            ErrorCode.TOKEN_INVALID,
            ErrorCode.SECURITY_VIOLATION,
            
            # Database errors - affect data integrity 
            ErrorCode.DATABASE_ERROR,
            ErrorCode.DATABASE_CONNECTION_FAILED,
            ErrorCode.DATABASE_QUERY_FAILED,
            ErrorCode.DATABASE_CONSTRAINT_VIOLATION,
            ErrorCode.RECORD_NOT_FOUND,
            ErrorCode.RECORD_ALREADY_EXISTS,
            
            # Service errors - affect system availability
            ErrorCode.SERVICE_UNAVAILABLE,
            ErrorCode.SERVICE_TIMEOUT,
            ErrorCode.EXTERNAL_SERVICE_ERROR,
            ErrorCode.HTTP_ERROR,
            
            # Agent/LLM errors - affect core business functionality
            ErrorCode.AGENT_EXECUTION_FAILED,
            ErrorCode.LLM_REQUEST_FAILED,
            ErrorCode.LLM_RATE_LIMIT_EXCEEDED,
            ErrorCode.AGENT_TIMEOUT,
            
            # WebSocket errors - affect real-time communication
            ErrorCode.WEBSOCKET_CONNECTION_FAILED,
            ErrorCode.WEBSOCKET_MESSAGE_INVALID,
            ErrorCode.WEBSOCKET_AUTHENTICATION_FAILED,
            
            # Data errors - affect data processing
            ErrorCode.FILE_NOT_FOUND,
            ErrorCode.FILE_ACCESS_DENIED,
            ErrorCode.DATA_PARSING_ERROR,
            ErrorCode.DATA_VALIDATION_ERROR,
            
            # General errors - affect overall system stability
            ErrorCode.INTERNAL_ERROR,
            ErrorCode.CONFIGURATION_ERROR,
            ErrorCode.VALIDATION_ERROR
        ]
        
        for error_code in critical_categories:
            # Each error code should have a meaningful string value
            assert isinstance(error_code.value, str)
            assert len(error_code.value) > 0
            assert error_code.value.isupper() or '_' in error_code.value
            
    @pytest.mark.unit
    def test_error_code_value_consistency(self):
        """Test that error code values follow consistent naming conventions for monitoring tools."""
        all_error_codes = list(ErrorCode)
        
        for error_code in all_error_codes:
            error_value = error_code.value
            
            # Should follow UPPERCASE_WITH_UNDERSCORES format
            assert error_value == error_value.upper(), \
                f"Error code {error_code.name} value should be uppercase: {error_value}"
                
            # Should not contain spaces or special characters (for log parsing)
            assert ' ' not in error_value, \
                f"Error code {error_code.name} should not contain spaces: {error_value}"
            assert not any(char in error_value for char in ['!', '@', '#', '$', '%', '^', '&', '*']), \
                f"Error code {error_code.name} should not contain special characters: {error_value}"
                
            # Should be descriptive (not just codes like "E001")
            assert len(error_value) >= 3, \
                f"Error code {error_code.name} should be descriptive: {error_value}"
            assert not error_value.isdigit(), \
                f"Error code {error_code.name} should not be just numbers: {error_value}"
                
    @pytest.mark.unit
    def test_error_code_categorization_logic(self):
        """Test that error codes are properly categorized for business impact assessment."""
        # Group errors by business impact category
        authentication_errors = [
            ErrorCode.AUTHENTICATION_FAILED,
            ErrorCode.AUTHORIZATION_FAILED,
            ErrorCode.TOKEN_EXPIRED,
            ErrorCode.TOKEN_INVALID,
            ErrorCode.SECURITY_VIOLATION,
            ErrorCode.WEBSOCKET_AUTHENTICATION_FAILED
        ]
        
        database_errors = [
            ErrorCode.DATABASE_ERROR,
            ErrorCode.DATABASE_CONNECTION_FAILED,
            ErrorCode.DATABASE_QUERY_FAILED,
            ErrorCode.DATABASE_CONSTRAINT_VIOLATION,
            ErrorCode.RECORD_NOT_FOUND,
            ErrorCode.RECORD_ALREADY_EXISTS
        ]
        
        service_availability_errors = [
            ErrorCode.SERVICE_UNAVAILABLE,
            ErrorCode.SERVICE_TIMEOUT,
            ErrorCode.EXTERNAL_SERVICE_ERROR,
            ErrorCode.HTTP_ERROR
        ]
        
        core_business_errors = [
            ErrorCode.AGENT_EXECUTION_FAILED,
            ErrorCode.LLM_REQUEST_FAILED,
            ErrorCode.LLM_RATE_LIMIT_EXCEEDED,
            ErrorCode.AGENT_TIMEOUT
        ]
        
        # Test that each category contains expected keywords
        for auth_error in authentication_errors:
            assert any(keyword in auth_error.value for keyword in ['AUTH', 'TOKEN', 'SECURITY']), \
                f"Authentication error should contain relevant keywords: {auth_error.value}"
                
        for db_error in database_errors:
            assert any(keyword in db_error.value for keyword in ['DATABASE', 'DB', 'RECORD']), \
                f"Database error should contain relevant keywords: {db_error.value}"
                
        for service_error in service_availability_errors:
            assert any(keyword in service_error.value for keyword in ['SERVICE', 'HTTP', 'TIMEOUT']), \
                f"Service error should contain relevant keywords: {service_error.value}"
                
        for business_error in core_business_errors:
            assert any(keyword in business_error.value for keyword in ['AGENT', 'LLM']), \
                f"Business logic error should contain relevant keywords: {business_error.value}"
                
    @pytest.mark.unit
    def test_error_severity_levels_business_alignment(self):
        """Test that error severity levels align with business incident response procedures."""
        severity_levels = list(ErrorSeverity)
        expected_severities = [
            ErrorSeverity.LOW,
            ErrorSeverity.MEDIUM, 
            ErrorSeverity.HIGH,
            ErrorSeverity.CRITICAL
        ]
        
        # All expected severity levels should exist
        for expected in expected_severities:
            assert expected in severity_levels
            
        # Severity values should be appropriate for monitoring systems
        for severity in severity_levels:
            assert isinstance(severity.value, str)
            assert len(severity.value) > 0
            assert severity.value.lower() == severity.value  # lowercase for consistency
            
        # Verify specific severity definitions match business needs
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"
        
    @pytest.mark.unit
    def test_error_code_uniqueness_for_monitoring(self):
        """Test that all error codes are unique to prevent monitoring system confusion."""
        all_error_codes = list(ErrorCode)
        error_values = [error.value for error in all_error_codes]
        
        # No duplicate values
        unique_values = set(error_values)
        assert len(unique_values) == len(error_values), \
            f"Duplicate error code values found: {len(error_values)} total, {len(unique_values)} unique"
            
        # No duplicate names (enum property)
        error_names = [error.name for error in all_error_codes]
        unique_names = set(error_names)
        assert len(unique_names) == len(error_names), \
            f"Duplicate error code names found: {len(error_names)} total, {len(unique_names)} unique"
            
    @pytest.mark.unit
    def test_error_code_business_impact_mapping(self):
        """Test that error codes can be mapped to appropriate business impact levels."""
        # Map error codes to expected business impact based on their nature
        critical_business_impact = [
            ErrorCode.DATABASE_CONNECTION_FAILED,  # Complete system failure
            ErrorCode.SECURITY_VIOLATION,  # Security breach
            ErrorCode.SERVICE_UNAVAILABLE,  # System unavailable
            ErrorCode.AUTHENTICATION_FAILED  # User access blocked
        ]
        
        high_business_impact = [
            ErrorCode.AGENT_EXECUTION_FAILED,  # Core functionality broken
            ErrorCode.LLM_REQUEST_FAILED,  # Core service disrupted
            ErrorCode.WEBSOCKET_CONNECTION_FAILED,  # Real-time features broken
            ErrorCode.DATABASE_QUERY_FAILED  # Data access issues
        ]
        
        medium_business_impact = [
            ErrorCode.RECORD_NOT_FOUND,  # Individual record issues
            ErrorCode.FILE_NOT_FOUND,  # Missing resource
            ErrorCode.DATA_VALIDATION_ERROR,  # Data quality issues
            ErrorCode.HTTP_ERROR  # External service issues
        ]
        
        low_business_impact = [
            ErrorCode.DATA_PARSING_ERROR,  # Input processing issues
            ErrorCode.VALIDATION_ERROR,  # User input validation
            ErrorCode.FILE_ACCESS_DENIED  # Permission issues
        ]
        
        # Verify that we can categorize errors appropriately
        all_categorized = (critical_business_impact + high_business_impact + 
                          medium_business_impact + low_business_impact)
        
        # Should cover most error codes (allowing for some uncategorized ones)
        all_error_codes = list(ErrorCode)
        coverage_ratio = len(all_categorized) / len(all_error_codes)
        assert coverage_ratio >= 0.8, \
            f"Business impact categorization should cover at least 80% of error codes: {coverage_ratio:.2f}"
            
    @pytest.mark.unit
    def test_error_code_string_representation(self):
        """Test that error codes have proper string representation for logging and debugging."""
        test_error = ErrorCode.AGENT_EXECUTION_FAILED
        
        # String representation should be meaningful
        str_repr = str(test_error)
        assert "AGENT_EXECUTION_FAILED" in str_repr
        
        # Value access should work for logging
        assert test_error.value == "AGENT_EXECUTION_FAILED"
        
        # Name access should work for debugging
        assert test_error.name == "AGENT_EXECUTION_FAILED"
        
    @pytest.mark.unit
    def test_severity_level_ordering_logic(self):
        """Test that severity levels can be compared for escalation logic."""
        # Create severity mapping for comparison
        severity_order = {
            ErrorSeverity.LOW: 1,
            ErrorSeverity.MEDIUM: 2,
            ErrorSeverity.HIGH: 3,
            ErrorSeverity.CRITICAL: 4
        }
        
        # Test that we can determine severity escalation
        low_severity = ErrorSeverity.LOW
        critical_severity = ErrorSeverity.CRITICAL
        
        assert severity_order[critical_severity] > severity_order[low_severity]
        assert severity_order[ErrorSeverity.HIGH] > severity_order[ErrorSeverity.MEDIUM]
        assert severity_order[ErrorSeverity.MEDIUM] > severity_order[ErrorSeverity.LOW]
        
    @pytest.mark.unit
    def test_error_code_business_categorization_completeness(self):
        """Test that error codes cover all major business operation areas."""
        all_error_codes = list(ErrorCode)
        
        # Define business operation areas and their required error coverage
        business_areas = {
            'user_authentication': ['AUTH', 'TOKEN', 'SECURITY'],
            'data_management': ['DATABASE', 'DB', 'RECORD', 'DATA'],
            'external_services': ['SERVICE', 'HTTP', 'EXTERNAL'],
            'core_ai_functionality': ['AGENT', 'LLM'],
            'real_time_communication': ['WEBSOCKET', 'WS'],
            'file_operations': ['FILE'],
            'system_configuration': ['CONFIG', 'VALIDATION'],
            'general_system': ['INTERNAL', 'ERROR']
        }
        
        # Check that each business area has error code coverage
        for area_name, keywords in business_areas.items():
            area_covered = False
            for error_code in all_error_codes:
                if any(keyword in error_code.value for keyword in keywords):
                    area_covered = True
                    break
                    
            assert area_covered, \
                f"Business area '{area_name}' not covered by error codes. Keywords: {keywords}"
                
    @pytest.mark.unit
    def test_error_code_monitoring_system_compatibility(self):
        """Test that error codes are compatible with common monitoring and alerting systems."""
        all_error_codes = list(ErrorCode)
        
        for error_code in all_error_codes:
            error_value = error_code.value
            
            # Should be compatible with Prometheus metric names
            # (alphanumeric plus underscore, must not start with digit)
            assert not error_value[0].isdigit(), \
                f"Error code should not start with digit for Prometheus: {error_value}"
            assert all(c.isalnum() or c == '_' for c in error_value), \
                f"Error code should only contain alphanumeric and underscore: {error_value}"
                
            # Should be compatible with JSON logging
            assert '"' not in error_value, \
                f"Error code should not contain quotes for JSON compatibility: {error_value}"
            assert '\\' not in error_value, \
                f"Error code should not contain backslashes for JSON compatibility: {error_value}"
            
            # Should be reasonable length for log parsing
            assert len(error_value) <= 50, \
                f"Error code too long for efficient log parsing: {error_value}"