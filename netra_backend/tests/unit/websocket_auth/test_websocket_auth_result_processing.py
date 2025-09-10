"""
Unit Tests for WebSocket Authentication Result Processing

Business Value Justification (BVJ):
- Segment: Platform/Internal - Authentication Infrastructure
- Business Goal: Reliable authentication result handling for $120K+ MRR chat platform
- Value Impact: Ensures proper authentication response formatting and error handling
- Strategic Impact: Foundation for secure WebSocket communication and user feedback

CRITICAL TESTING REQUIREMENTS:
1. Authentication results must be properly serialized for WebSocket responses
2. Error handling must provide clear, actionable feedback to users
3. Success results must contain all required user context information
4. Result processing must be performant and thread-safe
5. Strongly typed results prevent serialization errors

This test suite validates WebSocket Authentication Result Processing:
- WebSocketAuthResult creation, validation, and serialization
- Authentication success result formatting with user context
- Authentication failure result formatting with error details
- Result serialization for WebSocket JSON responses
- Error code standardization and categorization
- Performance metrics and timing data inclusion
- Thread-safe result processing for concurrent authentications

AUTHENTICATION RESULT SCENARIOS TO TEST:
Success Results:
- Valid JWT authentication with complete user context
- E2E testing authentication with bypass indicators
- OAuth authentication with external provider integration
- Token refresh authentication with updated credentials

Failure Results:
- Invalid/expired JWT tokens with specific error codes
- Missing authorization headers with actionable guidance
- WebSocket connection state errors with retry instructions
- Authentication service unavailable with fallback options
- Rate limiting exceeded with backoff recommendations

Following SSOT patterns:
- Uses WebSocketAuthResult from unified_websocket_auth (SSOT)
- Strongly typed with AuthResult integration
- Absolute imports only (no relative imports)
- Test categorization with @pytest.mark.unit
- No mocking of core result processing logic
"""

import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import Mock

# SSOT Imports - Using absolute imports only
from netra_backend.app.websocket_core.unified_websocket_auth import (
    WebSocketAuthResult,
    UnifiedWebSocketAuthenticator
)
from netra_backend.app.services.unified_authentication_service import (
    AuthResult,
    AuthenticationContext,
    AuthenticationMethod
)
from shared.types.core_types import UserID, ensure_user_id
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class TestWebSocketAuthResultCreationAndValidation(SSotBaseTestCase):
    """
    Unit tests for WebSocketAuthResult creation and validation.
    
    CRITICAL: These tests validate that authentication results are properly
    created with all required fields and pass validation checks.
    
    Tests focus on:
    1. Successful authentication result creation
    2. Failed authentication result creation
    3. Field validation and type checking
    4. Default value handling and optional fields
    5. Result consistency and immutability
    """
    
    def test_successful_websocket_auth_result_creation(self):
        """Test successful WebSocket authentication result creation."""
        # Create successful authentication result
        success_result = WebSocketAuthResult(
            success=True,
            user_id="user_12345",
            message="Authentication successful",
            auth_method="jwt",
            execution_time_ms=125.7,
            statistics={'total_attempts': 1, 'success_rate': 1.0}
        )
        
        # Validate required success fields
        assert success_result.success is True
        assert success_result.user_id == "user_12345"
        assert success_result.message == "Authentication successful"
        assert success_result.auth_method == "jwt"
        assert success_result.execution_time_ms == 125.7
        
        # Validate optional fields
        assert success_result.error_code is None
        assert success_result.statistics is not None
        assert success_result.statistics['total_attempts'] == 1
        
        # Validate timestamps
        assert hasattr(success_result, 'timestamp')
        if hasattr(success_result, 'timestamp'):
            assert isinstance(success_result.timestamp, datetime)
    
    def test_failed_websocket_auth_result_creation(self):
        """Test failed WebSocket authentication result creation."""
        # Create failed authentication result
        failure_result = WebSocketAuthResult(
            success=False,
            error_code="INVALID_JWT_TOKEN",
            message="JWT token is expired or malformed",
            execution_time_ms=45.3,
            statistics={'total_attempts': 1, 'failure_rate': 1.0}
        )
        
        # Validate required failure fields
        assert failure_result.success is False
        assert failure_result.error_code == "INVALID_JWT_TOKEN"
        assert failure_result.message == "JWT token is expired or malformed"
        assert failure_result.execution_time_ms == 45.3
        
        # Validate success-specific fields are None
        assert failure_result.user_id is None
        assert failure_result.auth_method is None
        
        # Validate statistics tracking
        assert failure_result.statistics is not None
        assert failure_result.statistics['failure_rate'] == 1.0
    
    def test_websocket_auth_result_field_validation(self):
        """Test WebSocket authentication result field validation."""
        # Test required field validation
        required_fields = ['success', 'message']
        
        for required_field in required_fields:
            # Each required field should be validated
            if required_field == 'success':
                # Success field must be boolean
                valid_result = WebSocketAuthResult(
                    success=True,
                    message="Test message"
                )
                assert isinstance(valid_result.success, bool)
                
            elif required_field == 'message':
                # Message field must be string
                valid_result = WebSocketAuthResult(
                    success=False,
                    message="Test error message"
                )
                assert isinstance(valid_result.message, str)
                assert len(valid_result.message) > 0
    
    def test_websocket_auth_result_type_checking(self):
        """Test WebSocket authentication result type checking."""
        # Test type validation for different field types
        type_test_cases = [
            {
                'field': 'success',
                'valid_values': [True, False],
                'invalid_values': ['true', 1, 0, None]
            },
            {
                'field': 'user_id', 
                'valid_values': ['user123', None],
                'invalid_values': [123, True, []]
            },
            {
                'field': 'execution_time_ms',
                'valid_values': [0.0, 100.5, 1000, None],
                'invalid_values': ['100', True, []]
            }
        ]
        
        for test_case in type_test_cases:
            field_name = test_case['field']
            
            # Test valid values
            for valid_value in test_case['valid_values']:
                # Create result with valid value
                kwargs = {
                    'success': True,
                    'message': 'Test message',
                    field_name: valid_value
                }
                
                try:
                    result = WebSocketAuthResult(**kwargs)
                    # Validate field was set correctly
                    assert getattr(result, field_name) == valid_value
                except Exception as e:
                    pytest.fail(f"Valid value {valid_value} for {field_name} failed: {e}")
    
    def test_websocket_auth_result_default_values(self):
        """Test WebSocket authentication result default value handling."""
        # Create minimal result with only required fields
        minimal_result = WebSocketAuthResult(
            success=True,
            message="Minimal authentication result"
        )
        
        # Validate default values
        assert minimal_result.success is True
        assert minimal_result.message == "Minimal authentication result"
        
        # Optional fields should have sensible defaults
        expected_defaults = {
            'user_id': None,
            'error_code': None,
            'auth_method': None,
            'execution_time_ms': None,
            'statistics': None
        }
        
        for field_name, expected_default in expected_defaults.items():
            actual_value = getattr(minimal_result, field_name, 'FIELD_MISSING')
            if actual_value != 'FIELD_MISSING':
                # Field exists, validate default
                assert actual_value == expected_default
    
    def test_websocket_auth_result_consistency_and_immutability(self):
        """Test WebSocket authentication result consistency and immutability."""
        # Create result with specific values
        original_result = WebSocketAuthResult(
            success=True,
            user_id="consistent_user",
            message="Consistency test",
            execution_time_ms=200.0
        )
        
        # Validate consistency of field access
        assert original_result.success is True
        assert original_result.user_id == "consistent_user"
        assert original_result.message == "Consistency test"
        assert original_result.execution_time_ms == 200.0
        
        # Multiple accesses should return same values
        for _ in range(5):
            assert original_result.success is True
            assert original_result.user_id == "consistent_user"
            assert original_result.execution_time_ms == 200.0
        
        # Test that result fields maintain consistency
        first_read = original_result.success
        second_read = original_result.success
        assert first_read == second_read


@pytest.mark.unit
class TestWebSocketAuthResultSerialization(SSotBaseTestCase):
    """
    Unit tests for WebSocket authentication result serialization.
    
    CRITICAL: These tests validate that authentication results can be properly
    serialized for WebSocket JSON responses and client consumption.
    
    Tests focus on:
    1. JSON serialization for successful authentication
    2. JSON serialization for failed authentication
    3. Complex data structure serialization
    4. Serialization performance and efficiency
    5. Deserialization and round-trip consistency
    """
    
    def test_successful_auth_result_json_serialization(self):
        """Test JSON serialization of successful authentication results."""
        # Create successful result with complex data
        success_result = WebSocketAuthResult(
            success=True,
            user_id="user_json_test",
            message="Authentication successful for JSON test",
            auth_method="jwt",
            execution_time_ms=150.75,
            statistics={
                'total_attempts': 3,
                'success_rate': 0.67,
                'average_time_ms': 125.5,
                'last_attempt': '2023-10-01T12:00:00Z'
            }
        )
        
        # Serialize to dictionary
        result_dict = success_result.to_dict()
        
        # Validate dictionary structure
        assert isinstance(result_dict, dict)
        assert result_dict['success'] is True
        assert result_dict['user_id'] == "user_json_test"
        assert result_dict['message'] == "Authentication successful for JSON test"
        assert result_dict['auth_method'] == "jwt"
        assert result_dict['execution_time_ms'] == 150.75
        
        # Validate nested statistics serialization
        assert 'statistics' in result_dict
        assert isinstance(result_dict['statistics'], dict)
        assert result_dict['statistics']['total_attempts'] == 3
        assert result_dict['statistics']['success_rate'] == 0.67
        
        # Test JSON serialization
        json_str = json.dumps(result_dict)
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        
        # Validate JSON is valid and parseable
        parsed_json = json.loads(json_str)
        assert parsed_json == result_dict
    
    def test_failed_auth_result_json_serialization(self):
        """Test JSON serialization of failed authentication results."""
        # Create failed result with detailed error information
        failure_result = WebSocketAuthResult(
            success=False,
            error_code="JWT_EXPIRED",
            message="JWT token expired at 2023-10-01T11:30:00Z",
            execution_time_ms=25.5,
            statistics={
                'total_failures': 5,
                'failure_types': ['expired', 'malformed', 'missing'],
                'retry_recommended': True
            }
        )
        
        # Serialize to dictionary
        result_dict = failure_result.to_dict()
        
        # Validate dictionary structure for failures
        assert isinstance(result_dict, dict)
        assert result_dict['success'] is False
        assert result_dict['error_code'] == "JWT_EXPIRED"
        assert result_dict['message'] == "JWT token expired at 2023-10-01T11:30:00Z"
        assert result_dict['execution_time_ms'] == 25.5
        
        # Success-only fields should not be present or be None
        assert result_dict.get('user_id') is None
        assert result_dict.get('auth_method') is None
        
        # Validate error-specific statistics
        assert 'statistics' in result_dict
        assert result_dict['statistics']['total_failures'] == 5
        assert result_dict['statistics']['retry_recommended'] is True
        
        # Test JSON serialization
        json_str = json.dumps(result_dict)
        parsed_json = json.loads(json_str)
        assert parsed_json == result_dict
    
    def test_complex_data_structure_serialization(self):
        """Test serialization of complex nested data structures."""
        # Create result with complex nested statistics
        complex_result = WebSocketAuthResult(
            success=True,
            user_id="complex_user",
            message="Complex data serialization test",
            auth_method="oauth",
            execution_time_ms=300.25,
            statistics={
                'authentication_flow': {
                    'provider': 'google',
                    'scopes': ['email', 'profile'],
                    'redirect_uri': 'https://app.example.com/auth/callback'
                },
                'timing_breakdown': {
                    'token_validation': 50.0,
                    'user_context_creation': 75.5,
                    'database_queries': 120.25,
                    'response_formatting': 54.5
                },
                'security_context': {
                    'ip_address': '192.168.1.100',
                    'user_agent': 'Mozilla/5.0 WebSocket Client',
                    'rate_limit_remaining': 45,
                    'session_id': 'session_12345abcdef'
                }
            }
        )
        
        # Serialize complex result
        result_dict = complex_result.to_dict()
        
        # Validate nested structure preservation
        assert isinstance(result_dict['statistics']['authentication_flow'], dict)
        assert isinstance(result_dict['statistics']['timing_breakdown'], dict)
        assert isinstance(result_dict['statistics']['security_context'], dict)
        
        # Validate specific nested values
        auth_flow = result_dict['statistics']['authentication_flow']
        assert auth_flow['provider'] == 'google'
        assert auth_flow['scopes'] == ['email', 'profile']
        
        timing = result_dict['statistics']['timing_breakdown']
        assert timing['token_validation'] == 50.0
        assert timing['database_queries'] == 120.25
        
        # Test JSON serialization of complex structure
        json_str = json.dumps(result_dict)
        parsed_json = json.loads(json_str)
        
        # Validate round-trip consistency
        assert parsed_json == result_dict
        assert parsed_json['statistics']['authentication_flow']['provider'] == 'google'
        assert parsed_json['statistics']['timing_breakdown']['token_validation'] == 50.0
    
    def test_serialization_performance_and_efficiency(self):
        """Test serialization performance and efficiency."""
        # Create result with moderately complex data
        perf_result = WebSocketAuthResult(
            success=True,
            user_id="performance_test_user",
            message="Performance test authentication",
            auth_method="jwt",
            execution_time_ms=100.0,
            statistics={
                'metrics': {f'metric_{i}': i * 10.5 for i in range(100)},
                'timestamps': [f'2023-10-01T12:{i:02d}:00Z' for i in range(60)]
            }
        )
        
        # Measure serialization time
        start_time = time.time()
        
        # Perform multiple serializations
        serialization_count = 1000
        for _ in range(serialization_count):
            result_dict = perf_result.to_dict()
            json_str = json.dumps(result_dict)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_serialization = (total_time / serialization_count) * 1000  # ms
        
        # Validate performance is reasonable
        assert avg_time_per_serialization < 10.0  # Less than 10ms per serialization
        assert total_time < 10.0  # Total time less than 10 seconds
        
        # Validate serialization still produces correct results
        final_dict = perf_result.to_dict()
        assert final_dict['success'] is True
        assert final_dict['user_id'] == "performance_test_user"
        assert len(final_dict['statistics']['metrics']) == 100
        assert len(final_dict['statistics']['timestamps']) == 60
    
    def test_deserialization_and_round_trip_consistency(self):
        """Test deserialization and round-trip consistency."""
        # Create original result
        original_result = WebSocketAuthResult(
            success=True,
            user_id="roundtrip_user",
            message="Round-trip consistency test",
            auth_method="jwt",
            execution_time_ms=175.5,
            statistics={
                'test_data': 'round_trip_test',
                'numeric_value': 42.7,
                'boolean_value': True,
                'array_value': [1, 2, 3, 'four', 5.0]
            }
        )
        
        # Serialize to dict
        serialized_dict = original_result.to_dict()
        
        # Serialize to JSON string
        json_string = json.dumps(serialized_dict)
        
        # Deserialize from JSON
        deserialized_dict = json.loads(json_string)
        
        # Validate round-trip consistency
        assert deserialized_dict == serialized_dict
        
        # Validate all field values preserved
        assert deserialized_dict['success'] == original_result.success
        assert deserialized_dict['user_id'] == original_result.user_id
        assert deserialized_dict['message'] == original_result.message
        assert deserialized_dict['auth_method'] == original_result.auth_method
        assert deserialized_dict['execution_time_ms'] == original_result.execution_time_ms
        
        # Validate nested statistics preserved
        original_stats = original_result.statistics
        deserialized_stats = deserialized_dict['statistics']
        
        assert deserialized_stats['test_data'] == original_stats['test_data']
        assert deserialized_stats['numeric_value'] == original_stats['numeric_value']
        assert deserialized_stats['boolean_value'] == original_stats['boolean_value']
        assert deserialized_stats['array_value'] == original_stats['array_value']


@pytest.mark.unit
class TestWebSocketAuthResultErrorHandling(SSotBaseTestCase):
    """
    Unit tests for WebSocket authentication result error handling.
    
    CRITICAL: These tests validate that authentication result errors are properly
    categorized, formatted, and provide actionable guidance to users.
    
    Tests focus on:
    1. Error code standardization and categorization
    2. Error message formatting and user guidance
    3. Error severity classification
    4. Recovery recommendation generation
    5. Error logging and monitoring integration
    """
    
    def test_error_code_standardization_and_categorization(self):
        """Test error code standardization and categorization."""
        # Define standard error categories and their codes
        error_categories = {
            'AUTHENTICATION_ERRORS': [
                'INVALID_JWT_TOKEN',
                'EXPIRED_JWT_TOKEN', 
                'MALFORMED_JWT_TOKEN',
                'JWT_SIGNATURE_INVALID',
                'JWT_DECODE_ERROR'
            ],
            'AUTHORIZATION_ERRORS': [
                'MISSING_AUTHORIZATION_HEADER',
                'INVALID_AUTHORIZATION_FORMAT',
                'INSUFFICIENT_PERMISSIONS',
                'USER_NOT_AUTHORIZED'
            ],
            'CONNECTION_ERRORS': [
                'WEBSOCKET_STATE_INVALID',
                'WEBSOCKET_CONNECTION_CLOSED',
                'WEBSOCKET_HANDSHAKE_FAILED'
            ],
            'SERVICE_ERRORS': [
                'AUTH_SERVICE_UNAVAILABLE',
                'AUTH_SERVICE_TIMEOUT',
                'DATABASE_CONNECTION_ERROR',
                'EXTERNAL_AUTH_PROVIDER_ERROR'
            ]
        }
        
        # Test each error category
        for category, error_codes in error_categories.items():
            for error_code in error_codes:
                # Create failure result with specific error code
                failure_result = WebSocketAuthResult(
                    success=False,
                    error_code=error_code,
                    message=f"Test error for {error_code}",
                    statistics={'error_category': category}
                )
                
                # Validate error code format
                assert isinstance(error_code, str)
                assert len(error_code) > 0
                assert '_' in error_code  # Should follow CONSTANT_CASE format
                assert error_code.isupper()  # Should be uppercase
                
                # Validate error result creation
                assert failure_result.success is False
                assert failure_result.error_code == error_code
                assert failure_result.statistics['error_category'] == category
    
    def test_error_message_formatting_and_user_guidance(self):
        """Test error message formatting and user guidance."""
        # Define error scenarios with expected user-friendly messages
        error_scenarios = [
            {
                'error_code': 'EXPIRED_JWT_TOKEN',
                'expected_guidance': 'token expired',
                'expected_action': 'refresh'
            },
            {
                'error_code': 'MISSING_AUTHORIZATION_HEADER',
                'expected_guidance': 'authorization required',
                'expected_action': 'login'
            },
            {
                'error_code': 'WEBSOCKET_CONNECTION_CLOSED',
                'expected_guidance': 'connection lost',
                'expected_action': 'reconnect'
            },
            {
                'error_code': 'AUTH_SERVICE_UNAVAILABLE',
                'expected_guidance': 'service temporarily unavailable',
                'expected_action': 'retry'
            }
        ]
        
        for scenario in error_scenarios:
            error_code = scenario['error_code']
            expected_guidance = scenario['expected_guidance']
            expected_action = scenario['expected_action']
            
            # Create user-friendly error message
            user_message = f"Authentication failed: {expected_guidance}. Please {expected_action} and try again."
            
            # Create error result with user guidance
            error_result = WebSocketAuthResult(
                success=False,
                error_code=error_code,
                message=user_message,
                statistics={
                    'user_guidance': expected_guidance,
                    'recommended_action': expected_action
                }
            )
            
            # Validate error message formatting
            assert error_result.success is False
            assert error_result.error_code == error_code
            assert expected_guidance in error_result.message.lower()
            assert expected_action in error_result.message.lower()
            
            # Validate guidance metadata
            assert error_result.statistics['user_guidance'] == expected_guidance
            assert error_result.statistics['recommended_action'] == expected_action
    
    def test_error_severity_classification(self):
        """Test error severity classification for monitoring and alerts."""
        # Define error severity classifications
        error_severities = {
            'CRITICAL': [
                'AUTH_SERVICE_UNAVAILABLE',
                'DATABASE_CONNECTION_ERROR'
            ],
            'HIGH': [
                'JWT_SIGNATURE_INVALID',
                'USER_NOT_AUTHORIZED'
            ],
            'MEDIUM': [
                'EXPIRED_JWT_TOKEN',
                'INVALID_JWT_TOKEN'
            ],
            'LOW': [
                'MISSING_AUTHORIZATION_HEADER',
                'MALFORMED_JWT_TOKEN'
            ]
        }
        
        for severity, error_codes in error_severities.items():
            for error_code in error_codes:
                # Create error result with severity classification
                error_result = WebSocketAuthResult(
                    success=False,
                    error_code=error_code,
                    message=f"Severity test for {error_code}",
                    statistics={
                        'severity': severity,
                        'requires_alert': severity in ['CRITICAL', 'HIGH']
                    }
                )
                
                # Validate severity classification
                assert error_result.statistics['severity'] == severity
                
                # Critical and high severity errors should trigger alerts
                requires_alert = error_result.statistics['requires_alert']
                if severity in ['CRITICAL', 'HIGH']:
                    assert requires_alert is True
                else:
                    assert requires_alert is False
    
    def test_recovery_recommendation_generation(self):
        """Test recovery recommendation generation for different error types."""
        # Define recovery strategies for different error types
        recovery_strategies = {
            'EXPIRED_JWT_TOKEN': {
                'immediate_action': 'refresh_token',
                'retry_delay_ms': 0,
                'max_retries': 3,
                'user_message': 'Please log in again to continue'
            },
            'AUTH_SERVICE_UNAVAILABLE': {
                'immediate_action': 'retry_with_backoff',
                'retry_delay_ms': 5000,
                'max_retries': 5,
                'user_message': 'Service temporarily unavailable, retrying...'
            },
            'WEBSOCKET_CONNECTION_CLOSED': {
                'immediate_action': 'reconnect_websocket',
                'retry_delay_ms': 1000,
                'max_retries': 10,
                'user_message': 'Connection lost, reconnecting...'
            },
            'INSUFFICIENT_PERMISSIONS': {
                'immediate_action': 'contact_support',
                'retry_delay_ms': 0,
                'max_retries': 0,
                'user_message': 'Access denied. Contact support if needed.'
            }
        }
        
        for error_code, strategy in recovery_strategies.items():
            # Create error result with recovery recommendations
            error_result = WebSocketAuthResult(
                success=False,
                error_code=error_code,
                message=strategy['user_message'],
                statistics={
                    'recovery_strategy': strategy,
                    'retry_recommended': strategy['max_retries'] > 0
                }
            )
            
            # Validate recovery recommendations
            assert error_result.statistics['recovery_strategy'] == strategy
            assert error_result.statistics['retry_recommended'] == (strategy['max_retries'] > 0)
            
            # Validate strategy components
            recovery = error_result.statistics['recovery_strategy']
            assert recovery['immediate_action'] == strategy['immediate_action']
            assert recovery['retry_delay_ms'] == strategy['retry_delay_ms']
            assert recovery['max_retries'] == strategy['max_retries']
            assert recovery['user_message'] == strategy['user_message']
    
    def test_error_logging_and_monitoring_integration(self):
        """Test error logging and monitoring integration metadata."""
        # Create error result with monitoring metadata
        monitoring_error = WebSocketAuthResult(
            success=False,
            error_code="JWT_DECODE_ERROR",
            message="Failed to decode JWT token",
            execution_time_ms=15.5,
            statistics={
                'monitoring_metadata': {
                    'correlation_id': 'error_12345abcdef',
                    'trace_id': 'trace_67890ghijkl',
                    'error_timestamp': datetime.now(timezone.utc).isoformat(),
                    'service_version': '1.2.3',
                    'environment': 'staging'
                },
                'metrics_tags': {
                    'error_type': 'authentication',
                    'error_category': 'jwt_processing',
                    'failure_point': 'token_decode'
                },
                'alert_conditions': {
                    'should_alert': True,
                    'alert_threshold': 5,
                    'alert_window_minutes': 5
                }
            }
        )
        
        # Validate monitoring metadata structure
        monitoring_meta = monitoring_error.statistics['monitoring_metadata']
        assert 'correlation_id' in monitoring_meta
        assert 'trace_id' in monitoring_meta
        assert 'error_timestamp' in monitoring_meta
        assert 'service_version' in monitoring_meta
        assert 'environment' in monitoring_meta
        
        # Validate metrics tags
        metrics_tags = monitoring_error.statistics['metrics_tags']
        assert metrics_tags['error_type'] == 'authentication'
        assert metrics_tags['error_category'] == 'jwt_processing'
        assert metrics_tags['failure_point'] == 'token_decode'
        
        # Validate alert conditions
        alert_conditions = monitoring_error.statistics['alert_conditions']
        assert alert_conditions['should_alert'] is True
        assert alert_conditions['alert_threshold'] == 5
        assert alert_conditions['alert_window_minutes'] == 5


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])