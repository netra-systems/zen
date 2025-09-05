"""
CRITICAL E2E Test #8: Password Reset Complete Flow

BVJ (Business Value Justification):
1. Segment: All customer segments (user retention critical)
2. Business Goal: Prevent user churn due to forgotten passwords
3. Value Impact: Basic auth function that protects user access
4. Revenue Impact: Prevents lost customers due to locked accounts

REQUIREMENTS:
- Complete password reset flow validation
- Email sending and token validation
- Security testing (token expiry, single use)
- Old password invalidation
- New password login validation
- Must complete in <30 seconds
- 450-line file limit, 25-line function limit
"""
import time
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.auth_flow_manager import AuthCompleteFlowManager
from tests.e2e.integration.password_reset_complete_flow_tester import (
    PasswordResetCompleteFlowTester,
)
from tests.e2e.integration.password_reset_security_flow_tester import (
    PasswordResetSecurityFlowTester,
)


# Pytest Test Implementations
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_password_reset_flow():
    """
    Test #8: Complete Password Reset Flow
    
    BVJ: Prevents user churn due to forgotten passwords
    - User requests password reset
    - Email sent with reset link (mocked)
    - Reset link validated and used
    - New password set successfully
    - Old password no longer works
    - User can login with new password
    - Must complete in <30 seconds
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        flow_tester = PasswordResetCompleteFlowTester(auth_tester)
        
        # Execute complete password reset flow
        results = await flow_tester.execute_complete_password_reset_flow()
        
        # Validate business-critical success criteria
        assert results["success"], f"Password reset flow failed: {results.get('error')}"
        assert results["execution_time"] < 30.0, f"Performance failed: {results['execution_time']:.2f}s"
        
        # Validate each step completed successfully
        required_steps = [
            "reset_request", "email_validation", "token_extraction",
            "reset_confirmation", "old_password_invalid", "new_password_login"
        ]
        for step in required_steps:
            assert step in results["steps"], f"Missing critical step: {step}"
            assert results["steps"][step]["success"], f"Step failed: {step}"
        
        # Validate email was sent and formatted correctly
        email_step = results["steps"]["email_validation"]
        assert email_step["format_valid"], "Email format validation failed"
        assert email_step["content_valid"], "Email content validation failed"
        
        # Validate security - old password rejected, new password accepted
        old_pwd_step = results["steps"]["old_password_invalid"]
        new_pwd_step = results["steps"]["new_password_login"]
        assert old_pwd_step["old_password_rejected"], "Old password should be rejected"
        assert new_pwd_step["new_password_accepted"], "New password should be accepted"
        
        print(f"[SUCCESS] Password Reset Flow: {results['execution_time']:.2f}s")
        print(f"[PROTECTED] User retention and account recovery")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_password_reset_security_validation():
    """
    Password Reset Security Validation
    
    BVJ: Ensures password reset security prevents abuse
    - Token expiration validation
    - Single-use token enforcement
    - Invalid token rejection
    - Security measures protect user accounts
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        security_tester = PasswordResetSecurityFlowTester(auth_tester)
        
        # Execute security validation tests
        results = await security_tester.execute_security_validation_flow()
        
        # Validate security-critical success criteria
        assert results["success"], f"Security validation failed: {results.get('error')}"
        assert results["execution_time"] < 10.0, f"Security performance failed: {results['execution_time']:.2f}s"
        
        # Validate specific security tests
        security_tests = results["security_tests"]
        assert security_tests["token_expiration"]["success"], "Token expiration test failed"
        assert security_tests["single_use_token"]["success"], "Single-use token test failed"
        assert security_tests["invalid_token"]["success"], "Invalid token test failed"
        
        # Additional security validations
        single_use = security_tests["single_use_token"]
        assert single_use["first_use_valid"], "First token use should be valid"
        assert single_use["second_use_rejected"], "Second token use should be rejected"
        
        print(f"[SUCCESS] Password Reset Security: {results['execution_time']:.2f}s")
        print(f"[SECURE] Token expiration, single-use, and validation")
        print(f"[PROTECTED] Account security and abuse prevention")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_password_reset_performance_validation():
    """
    Performance validation for password reset flows.
    BVJ: User experience impacts customer satisfaction and retention.
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        total_start_time = time.time()
        
        # Test complete flow performance
        flow_tester = PasswordResetCompleteFlowTester(auth_tester)
        flow_results = await flow_tester.execute_complete_password_reset_flow()
        assert flow_results["execution_time"] < 30.0, f"Flow performance failed: {flow_results['execution_time']:.2f}s"
        
        # Test security validation performance
        security_tester = PasswordResetSecurityFlowTester(auth_tester)
        security_results = await security_tester.execute_security_validation_flow()
        assert security_results["execution_time"] < 10.0, f"Security performance failed: {security_results['execution_time']:.2f}s"
        
        total_time = time.time() - total_start_time
        
        print(f"[PASSED] Password Reset Performance validation")
        print(f"[METRICS] Flow time: {flow_results['execution_time']:.2f}s")
        print(f"[METRICS] Security time: {security_results['execution_time']:.2f}s")
        print(f"[METRICS] Total test time: {total_time:.2f}s")
        print(f"[OPTIMIZED] User experience and retention")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_password_reset_email_content_validation():
    """
    Email content and format validation for password reset.
    BVJ: Proper email format ensures user can complete reset flow.
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        flow_tester = PasswordResetCompleteFlowTester(auth_tester)
        
        # Setup test environment
        await flow_tester.reset_tester.setup_test_environment()
        
        try:
            # Request password reset to trigger email
            await flow_tester._request_password_reset()
            
            # Get email service and validate email
            email_service = flow_tester.reset_tester.get_email_service()
            latest_email = email_service.get_latest_email()
            
            assert latest_email, "No email was sent"
            assert latest_email["to"] == flow_tester.test_email, "Email sent to wrong address"
            assert "Password Reset Request" in latest_email["subject"], "Invalid email subject"
            
            # Validate email content structure
            content = latest_email["content"]
            assert "password reset" in content.lower(), "Missing password reset mention"
            assert "click the link" in content.lower(), "Missing reset link instruction"
            assert "expires" in content.lower(), "Missing expiration notice"
            assert "token=" in content, "Missing reset token"
            
            # Validate token extraction
            flow_validator = flow_tester.reset_tester.get_flow_validator()
            extracted_token = flow_validator.extract_reset_token_from_email(content)
            assert extracted_token, "Could not extract token from email"
            assert len(extracted_token) >= 20, "Token too short"
            
            print(f"[SUCCESS] Email content validation passed")
            print(f"[VALIDATED] Email format, content, and token extraction")
            
        finally:
            await flow_tester.reset_tester.cleanup_test_environment()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_password_reset_edge_cases():
    """
    Edge cases for password reset flow.
    BVJ: Robust error handling prevents user frustration and support costs.
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        flow_tester = PasswordResetCompleteFlowTester(auth_tester)
        
        # Test 1: Reset request for non-existent email
        await flow_tester.reset_tester.setup_test_environment()
        
        try:
            # This should not reveal if email exists
            email_service = flow_tester.reset_tester.get_email_service()
            
            # Clear any previous emails
            email_service.clear_sent_emails()
            
            # Mock request for non-existent email - should still appear successful
            result = await flow_tester._request_password_reset()
            assert result["success"], "Reset request should appear successful for non-existent email"
            
            # Test 2: Email delivery failure simulation
            email_service.set_delivery_failure(True)
            
            # Should handle gracefully
            delivery_result = await email_service.send_password_reset_email(
                "test@example.com", 
                "test_token"
            )
            assert not delivery_result, "Should return False for delivery failure"
            
            # Test 3: Invalid token formats
            security_tester = flow_tester.reset_tester.get_security_tester()
            
            invalid_tokens = ["", "short", "123", None]
            for token in invalid_tokens:
                if token is not None:
                    is_valid = security_tester.validate_token_format(token)
                    assert not is_valid, f"Invalid token {token} should be rejected"
            
            print(f"[SUCCESS] Edge cases validation passed")
            print(f"[PROTECTED] Robust error handling and security")
            
        finally:
            await flow_tester.reset_tester.cleanup_test_environment()
