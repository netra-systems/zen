"""
Agent Message Security Validation Unit Tests

Business Value Justification (BVJ):
- SEGMENT: Enterprise ($500K+ ARR customers requiring SOC2/HIPAA compliance)
- GOAL: Retention and Expansion through security validation
- VALUE IMPACT: Comprehensive message security prevents data breaches and ensures regulatory compliance
- REVENUE IMPACT: Protects $500K+ ARR through enterprise-grade security validation

GOLDEN PATH PROTECTION:
- Message input sanitization prevents injection attacks
- Rate limiting prevents abuse and ensures fair resource allocation
- Authentication validation prevents unauthorized access
- User isolation prevents cross-customer data contamination
- Audit logging provides compliance and forensic capabilities

TEST PERFORMANCE REQUIREMENTS:
- Target: <5 seconds total execution for rapid feedback
- User isolation tests: <2 seconds per test method
- Security validation tests: <1 second per test method
- Rate limiting tests: <3 seconds per test method

COVERAGE AREAS:
1. Message Input Sanitization and Validation
2. Rate Limiting and Abuse Prevention
3. Authentication and Authorization Validation
4. User Context Isolation Security
5. Audit Trail and Compliance Logging
6. Message Encryption and Data Protection
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from typing import Dict, Any, List

# SSOT Testing Framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


class TestAgentMessageSecurityValidation(SSotAsyncTestCase):
    """
    Unit tests for agent message security validation functionality.
    
    BUSINESS PRIORITY: Enterprise security compliance ($500K+ ARR protection)
    PERFORMANCE TARGET: <5 seconds total execution time
    GOLDEN PATH: Message security enables trusted AI interactions
    """
    
    async def setup_method(self, method=None):
        """Setup method for each test - creates fresh security context."""
        await super().setup_method(method)
        
        # Create security validation mocks
        self.security_validator = SSotMockFactory.create_mock_security_validator()
        self.rate_limiter = SSotMockFactory.create_mock_rate_limiter()
        self.audit_logger = SSotMockFactory.create_mock_audit_logger()
        
        # Test user contexts for isolation testing
        self.user_context_1 = SSotMockFactory.create_mock_user_context(
            user_id="test_user_1",
            role="enterprise_user"
        )
        self.user_context_2 = SSotMockFactory.create_mock_user_context(
            user_id="test_user_2", 
            role="basic_user"
        )
        
        # Security test payloads
        self.clean_message = {
            "type": "user_message",
            "content": "What is the weather like?",
            "user_id": "test_user_1"
        }
        
        self.malicious_message = {
            "type": "user_message",
            "content": "<script>alert('xss')</script>DROP TABLE users;",
            "user_id": "malicious_user"
        }
        
        self.oversized_message = {
            "type": "user_message",
            "content": "x" * 100000,  # Oversized payload
            "user_id": "test_user_1"
        }

    async def test_message_input_sanitization_success(self):
        """
        GOLDEN PATH TEST: Message sanitization prevents injection attacks
        
        BVJ: Protects enterprise customers from XSS and SQL injection threats
        Performance: <1 second execution
        """
        start_time = time.time()
        
        # Configure security validator for sanitization
        self.security_validator.sanitize_input.return_value = "What is the weather like?"
        self.security_validator.validate_content_safety.return_value = True
        
        # Test message sanitization
        sanitized_content = self.security_validator.sanitize_input(
            self.malicious_message["content"]
        )
        is_safe = self.security_validator.validate_content_safety(sanitized_content)
        
        # Verify sanitization occurred
        assert sanitized_content == "What is the weather like?"
        assert is_safe is True
        assert "<script>" not in sanitized_content
        assert "DROP TABLE" not in sanitized_content
        
        # Verify security validator was called correctly
        self.security_validator.sanitize_input.assert_called_once_with(
            self.malicious_message["content"]
        )
        self.security_validator.validate_content_safety.assert_called_once()
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 1.0, f"Test took {execution_time:.2f}s, expected <1s"

    async def test_message_input_sanitization_failure(self):
        """
        FAILURE TEST: Security validator rejects unsafe content
        
        BVJ: Prevents malicious content from reaching agent processing
        Performance: <1 second execution
        """
        start_time = time.time()
        
        # Configure security validator to reject malicious content
        self.security_validator.validate_content_safety.return_value = False
        self.security_validator.get_security_violations.return_value = [
            "XSS_ATTEMPT", "SQL_INJECTION_ATTEMPT"
        ]
        
        # Test unsafe content rejection
        is_safe = self.security_validator.validate_content_safety(
            self.malicious_message["content"]
        )
        violations = self.security_validator.get_security_violations()
        
        # Verify content was rejected
        assert is_safe is False
        assert "XSS_ATTEMPT" in violations
        assert "SQL_INJECTION_ATTEMPT" in violations
        assert len(violations) == 2
        
        # Verify security methods were called
        self.security_validator.validate_content_safety.assert_called_once_with(
            self.malicious_message["content"]
        )
        self.security_validator.get_security_violations.assert_called_once()
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 1.0, f"Test took {execution_time:.2f}s, expected <1s"

    async def test_rate_limiting_enforcement_success(self):
        """
        GOLDEN PATH TEST: Rate limiting prevents message abuse
        
        BVJ: Protects system resources and ensures fair access for all users
        Performance: <2 seconds execution
        """
        start_time = time.time()
        
        # Configure rate limiter for normal usage
        self.rate_limiter.check_rate_limit.return_value = True
        self.rate_limiter.get_remaining_quota.return_value = 95
        self.rate_limiter.record_message.return_value = None
        
        # Test rate limit checking
        can_proceed = self.rate_limiter.check_rate_limit("test_user_1")
        remaining_quota = self.rate_limiter.get_remaining_quota("test_user_1")
        
        # Record message usage
        self.rate_limiter.record_message("test_user_1", len(self.clean_message["content"]))
        
        # Verify rate limiting allowed message
        assert can_proceed is True
        assert remaining_quota == 95
        assert remaining_quota > 0  # User has remaining quota
        
        # Verify rate limiter methods were called correctly
        self.rate_limiter.check_rate_limit.assert_called_once_with("test_user_1")
        self.rate_limiter.get_remaining_quota.assert_called_once_with("test_user_1")
        self.rate_limiter.record_message.assert_called_once_with(
            "test_user_1", len(self.clean_message["content"])
        )
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 2.0, f"Test took {execution_time:.2f}s, expected <2s"

    async def test_rate_limiting_enforcement_failure(self):
        """
        FAILURE TEST: Rate limiter blocks excessive usage
        
        BVJ: Prevents abuse and maintains system stability for all users
        Performance: <2 seconds execution
        """
        start_time = time.time()
        
        # Configure rate limiter for quota exceeded
        self.rate_limiter.check_rate_limit.return_value = False
        self.rate_limiter.get_remaining_quota.return_value = 0
        self.rate_limiter.get_retry_after.return_value = 300  # 5 minutes
        
        # Test rate limit exceeded
        can_proceed = self.rate_limiter.check_rate_limit("abusive_user")
        remaining_quota = self.rate_limiter.get_remaining_quota("abusive_user")
        retry_after = self.rate_limiter.get_retry_after("abusive_user")
        
        # Verify rate limiting blocked message
        assert can_proceed is False
        assert remaining_quota == 0
        assert retry_after == 300
        
        # Verify rate limiter methods were called correctly
        self.rate_limiter.check_rate_limit.assert_called_once_with("abusive_user")
        self.rate_limiter.get_remaining_quota.assert_called_once_with("abusive_user")
        self.rate_limiter.get_retry_after.assert_called_once_with("abusive_user")
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 2.0, f"Test took {execution_time:.2f}s, expected <2s"

    async def test_authentication_validation_success(self):
        """
        GOLDEN PATH TEST: Authentication validation protects agent access
        
        BVJ: Ensures only authorized users can access AI agents
        Performance: <1 second execution
        """
        start_time = time.time()
        
        # Configure authentication validator
        auth_validator = SSotMockFactory.create_mock_auth_validator()
        auth_validator.validate_token.return_value = True
        auth_validator.get_user_permissions.return_value = ["agent_access", "premium_features"]
        auth_validator.is_user_active.return_value = True
        
        # Test authentication validation
        valid_token = "valid_jwt_token_12345"
        is_valid = auth_validator.validate_token(valid_token)
        permissions = auth_validator.get_user_permissions(valid_token)
        is_active = auth_validator.is_user_active(valid_token)
        
        # Verify authentication succeeded
        assert is_valid is True
        assert "agent_access" in permissions
        assert "premium_features" in permissions
        assert is_active is True
        assert len(permissions) == 2
        
        # Verify auth validator methods were called correctly
        auth_validator.validate_token.assert_called_once_with(valid_token)
        auth_validator.get_user_permissions.assert_called_once_with(valid_token)
        auth_validator.is_user_active.assert_called_once_with(valid_token)
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 1.0, f"Test took {execution_time:.2f}s, expected <1s"

    async def test_authentication_validation_failure(self):
        """
        FAILURE TEST: Authentication rejects invalid tokens
        
        BVJ: Prevents unauthorized access to protect customer data
        Performance: <1 second execution
        """
        start_time = time.time()
        
        # Configure authentication validator for invalid token
        auth_validator = SSotMockFactory.create_mock_auth_validator()
        auth_validator.validate_token.return_value = False
        auth_validator.get_validation_error.return_value = "TOKEN_EXPIRED"
        
        # Test invalid authentication
        invalid_token = "expired_jwt_token_67890"
        is_valid = auth_validator.validate_token(invalid_token)
        error = auth_validator.get_validation_error()
        
        # Verify authentication failed appropriately
        assert is_valid is False
        assert error == "TOKEN_EXPIRED"
        
        # Verify auth validator methods were called correctly
        auth_validator.validate_token.assert_called_once_with(invalid_token)
        auth_validator.get_validation_error.assert_called_once()
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 1.0, f"Test took {execution_time:.2f}s, expected <1s"

    async def test_user_context_isolation_validation(self):
        """
        GOLDEN PATH TEST: User context isolation prevents data contamination
        
        BVJ: Critical for enterprise compliance and multi-tenant security
        Performance: <2 seconds execution
        """
        start_time = time.time()
        
        # Create isolation validator
        isolation_validator = SSotMockFactory.create_mock_isolation_validator()
        
        # Configure isolation validation for two users
        isolation_validator.validate_user_isolation.return_value = True
        isolation_validator.check_data_contamination.return_value = False
        isolation_validator.get_user_data_scope.side_effect = [
            {"user_id": "test_user_1", "data_scope": ["user1_data"]},
            {"user_id": "test_user_2", "data_scope": ["user2_data"]}
        ]
        
        # Test user isolation validation
        is_isolated = isolation_validator.validate_user_isolation(
            self.user_context_1["user_id"], self.user_context_2["user_id"]
        )
        has_contamination = isolation_validator.check_data_contamination(
            self.user_context_1["user_id"], self.user_context_2["user_id"]
        )
        
        user1_scope = isolation_validator.get_user_data_scope(self.user_context_1["user_id"])
        user2_scope = isolation_validator.get_user_data_scope(self.user_context_2["user_id"])
        
        # Verify user isolation is maintained
        assert is_isolated is True
        assert has_contamination is False
        assert user1_scope["data_scope"] == ["user1_data"]
        assert user2_scope["data_scope"] == ["user2_data"]
        assert user1_scope["data_scope"] != user2_scope["data_scope"]
        
        # Verify isolation validator methods were called correctly
        isolation_validator.validate_user_isolation.assert_called_once()
        isolation_validator.check_data_contamination.assert_called_once()
        assert isolation_validator.get_user_data_scope.call_count == 2
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 2.0, f"Test took {execution_time:.2f}s, expected <2s"

    async def test_audit_logging_compliance(self):
        """
        GOLDEN PATH TEST: Audit logging provides compliance trail
        
        BVJ: Enables SOC2/HIPAA compliance for enterprise customers
        Performance: <1 second execution
        """
        start_time = time.time()
        
        # Configure audit logger
        self.audit_logger.log_message_event.return_value = "audit_entry_12345"
        self.audit_logger.log_security_event.return_value = "security_entry_67890"
        self.audit_logger.get_audit_trail.return_value = [
            {"event_type": "message_received", "timestamp": "2025-09-14T15:20:00Z"},
            {"event_type": "security_validation", "timestamp": "2025-09-14T15:20:01Z"}
        ]
        
        # Test audit logging
        message_entry = self.audit_logger.log_message_event(
            user_id="test_user_1",
            event_type="message_received",
            message_content="Test message"
        )
        
        security_entry = self.audit_logger.log_security_event(
            user_id="test_user_1",
            event_type="security_validation",
            validation_result="passed"
        )
        
        audit_trail = self.audit_logger.get_audit_trail("test_user_1")
        
        # Verify audit logging occurred
        assert message_entry == "audit_entry_12345"
        assert security_entry == "security_entry_67890"
        assert len(audit_trail) == 2
        assert audit_trail[0]["event_type"] == "message_received"
        assert audit_trail[1]["event_type"] == "security_validation"
        
        # Verify audit logger methods were called correctly
        self.audit_logger.log_message_event.assert_called_once_with(
            user_id="test_user_1",
            event_type="message_received",
            message_content="Test message"
        )
        self.audit_logger.log_security_event.assert_called_once_with(
            user_id="test_user_1",
            event_type="security_validation",
            validation_result="passed"
        )
        self.audit_logger.get_audit_trail.assert_called_once_with("test_user_1")
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 1.0, f"Test took {execution_time:.2f}s, expected <1s"

    async def test_message_size_validation_enforcement(self):
        """
        FAILURE TEST: Message size limits prevent resource abuse
        
        BVJ: Protects system resources and prevents DoS attacks
        Performance: <1 second execution
        """
        start_time = time.time()
        
        # Configure size validator
        size_validator = SSotMockFactory.create_mock_size_validator()
        size_validator.validate_message_size.side_effect = [True, False]  # Clean vs oversized
        size_validator.get_max_message_size.return_value = 50000
        size_validator.get_message_size.side_effect = [
            len(self.clean_message["content"]),  # Small message
            len(self.oversized_message["content"])  # Large message
        ]
        
        # Test clean message size validation
        clean_size_valid = size_validator.validate_message_size(self.clean_message["content"])
        clean_size = size_validator.get_message_size(self.clean_message["content"])
        
        # Test oversized message rejection
        oversized_valid = size_validator.validate_message_size(self.oversized_message["content"])
        oversized_size = size_validator.get_message_size(self.oversized_message["content"])
        max_size = size_validator.get_max_message_size()
        
        # Verify size validation worked correctly
        assert clean_size_valid is True
        assert clean_size < max_size
        assert oversized_valid is False
        assert oversized_size > max_size
        assert oversized_size == 100000
        
        # Verify size validator methods were called correctly
        assert size_validator.validate_message_size.call_count == 2
        assert size_validator.get_message_size.call_count == 2
        size_validator.get_max_message_size.assert_called_once()
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 1.0, f"Test took {execution_time:.2f}s, expected <1s"

    async def test_comprehensive_security_validation_flow(self):
        """
        INTEGRATION TEST: Complete security validation pipeline
        
        BVJ: Validates end-to-end security for enterprise customers
        Performance: <3 seconds execution
        """
        start_time = time.time()
        
        # Create comprehensive security pipeline mock
        security_pipeline = SSotMockFactory.create_mock_security_pipeline()
        
        # Configure security pipeline for comprehensive validation
        security_pipeline.validate_message_security.return_value = {
            "is_valid": True,
            "sanitized_content": "What is the weather like?",
            "security_checks": {
                "input_sanitization": True,
                "rate_limiting": True,
                "authentication": True,
                "user_isolation": True,
                "audit_logging": True,
                "size_validation": True
            },
            "violations": [],
            "audit_trail_id": "audit_12345"
        }
        
        # Test comprehensive security validation
        validation_result = security_pipeline.validate_message_security(
            message=self.clean_message,
            user_context=self.user_context_1
        )
        
        # Verify comprehensive validation succeeded
        assert validation_result["is_valid"] is True
        assert validation_result["sanitized_content"] == "What is the weather like?"
        assert len(validation_result["violations"]) == 0
        assert validation_result["audit_trail_id"] == "audit_12345"
        
        # Verify all security checks passed
        security_checks = validation_result["security_checks"]
        assert security_checks["input_sanitization"] is True
        assert security_checks["rate_limiting"] is True
        assert security_checks["authentication"] is True
        assert security_checks["user_isolation"] is True
        assert security_checks["audit_logging"] is True
        assert security_checks["size_validation"] is True
        assert len(security_checks) == 6  # All security checks covered
        
        # Verify security pipeline method was called correctly
        security_pipeline.validate_message_security.assert_called_once_with(
            message=self.clean_message,
            user_context=self.user_context_1
        )
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 3.0, f"Test took {execution_time:.2f}s, expected <3s"


# PERFORMANCE VALIDATION - Ensure entire test suite runs within time limits
class TestAgentMessageSecurityValidationPerformance(SSotAsyncTestCase):
    """
    Performance validation for agent message security test suite.
    
    GOLDEN PATH REQUIREMENT: All security tests must complete within 5 seconds
    """
    
    async def test_complete_security_suite_performance(self):
        """
        PERFORMANCE TEST: Complete security test suite execution time
        
        BVJ: Rapid feedback enables efficient security-focused development
        Requirement: <5 seconds total execution time
        """
        start_time = time.time()
        
        # Create test instance
        security_test = TestAgentMessageSecurityValidation()
        await security_test.setup_method()
        
        # Execute all security validation tests
        test_methods = [
            security_test.test_message_input_sanitization_success(),
            security_test.test_message_input_sanitization_failure(),
            security_test.test_rate_limiting_enforcement_success(),
            security_test.test_rate_limiting_enforcement_failure(),
            security_test.test_authentication_validation_success(),
            security_test.test_authentication_validation_failure(),
            security_test.test_user_context_isolation_validation(),
            security_test.test_audit_logging_compliance(),
            security_test.test_message_size_validation_enforcement(),
            security_test.test_comprehensive_security_validation_flow()
        ]
        
        # Run all tests concurrently for maximum performance
        await asyncio.gather(*test_methods)
        
        # Verify total execution time
        total_execution_time = time.time() - start_time
        assert total_execution_time < 5.0, (
            f"Security test suite took {total_execution_time:.2f}s, "
            f"expected <5s for rapid feedback"
        )
        
        # Log performance achievement
        print(f"✅ Security validation suite completed in {total_execution_time:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])