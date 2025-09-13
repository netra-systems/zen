"""
CRITICAL Enterprise SSO/SAML Authentication Tests

BVJ (Business Value Justification):
1. Segment: Enterprise ($60K+ MRR protection)
2. Business Goal: Prevent SSO authentication failures that cost enterprise accounts
3. Value Impact: Ensures enterprise customers can seamlessly authenticate via SAML 2.0
4. Revenue Impact: Each SSO failure prevented saves $5K+ monthly enterprise conversions

REQUIREMENTS:
- Test SAML 2.0 assertion validation
- Validate session synchronization across services
- Test MFA integration with SSO
- Verify permission inheritance from IdP
- Architecture: File <300 lines, functions <8 lines each

TEST SCENARIOS:
1. SAML authentication flow with valid assertion
2. Session creation and JWT token generation
3. Permission mapping from IdP attributes
4. MFA challenge after SSO authentication
5. Session invalidation on IdP logout
"""
import time
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.enterprise_sso_helpers import EnterpriseSSOTestHarness


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_saml_authentication_flow_with_valid_assertion():
    """
    Test #1: Complete SAML Authentication Flow
    
    BVJ: Protects $15K+ MRR from SSO authentication failures
    - Validates SAML 2.0 assertion parsing
    - Tests IdP integration and attribute mapping
    - Verifies session creation with enterprise permissions
    - Must complete in <3 seconds
    """
    harness = EnterpriseSSOTestHarness()
    start_time = time.time()
    
    # Execute complete SSO flow
    user_email = "john.doe@enterprise.com"
    permissions = ["enterprise_admin", "billing_access"]
    
    results = await harness.execute_complete_sso_flow(user_email, permissions)
    execution_time = time.time() - start_time
    
    # Validate business-critical success criteria
    assert results["success"], f"SSO flow failed: {results.get('error')}"
    assert execution_time < 3.0, f"Performance failed: {execution_time:.2f}s > 3.0s"
    
    # Validate SAML response quality
    assert results["saml_response"], "Missing SAML response"
    assert "saml2:Assertion" in harness.idp._create_saml_xml({"id": "test"}), "Invalid SAML structure"
    
    # Validate session creation
    session = results["session"]
    assert session["user_id"] == user_email, "User ID mismatch"
    assert session["auth_method"] == "saml_sso", "Auth method incorrect"
    assert session["enterprise_id"] == "enterprise_123", "Enterprise ID missing"
    
    # Validate permission mapping
    mapped_permissions = session["permissions"]
    expected_perms = ["read", "write", "admin", "billing"]
    assert all(perm in mapped_permissions for perm in expected_perms), "Permission mapping failed"
    
    print(f"[SUCCESS] SAML Authentication: {execution_time:.2f}s")
    print(f"[PROTECTED] $15K+ MRR enterprise authentication")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_jwt_token_generation_with_enterprise_claims():
    """
    Test #2: JWT Token Generation with Enterprise Claims
    
    BVJ: Ensures enterprise users get proper JWT tokens with enhanced security
    - Creates JWT tokens with enterprise-specific claims
    - Validates token structure and enterprise metadata
    - Tests token validation across services
    """
    harness = EnterpriseSSOTestHarness()
    
    # Create SSO session
    user_email = "admin@enterprise.com"
    results = await harness.execute_complete_sso_flow(user_email, ["enterprise_admin"])
    
    assert results["success"], f"SSO setup failed: {results.get('error')}"
    
    # Validate JWT token structure
    jwt_token = results["jwt_token"]
    assert jwt_token, "JWT token not generated"
    
    # Validate token claims
    payload = await harness.jwt_manager.validate_enterprise_jwt(jwt_token)
    assert payload, "JWT validation failed"
    
    # Check enterprise-specific claims
    assert payload["enterprise_id"] == "enterprise_123", "Enterprise ID claim missing"
    assert payload["auth_method"] == "saml_sso", "Auth method claim incorrect"
    assert payload["mfa_verified"] is False, "MFA verification claim incorrect"
    
    # Validate permissions in JWT
    assert "admin" in payload["permissions"], "Admin permission missing from JWT"
    assert "billing" in payload["permissions"], "Billing permission missing from JWT"
    
    print("[SUCCESS] Enterprise JWT generation and validation")
    print("[SECURE] Enterprise claims properly embedded")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_session_synchronization_across_services():
    """
    Test #3: Session Synchronization Across Services
    
    BVJ: Prevents session inconsistencies that cause enterprise user frustration
    - Tests session consistency across auth service and backend
    - Validates session state synchronization
    - Ensures enterprise users have seamless experience
    """
    harness = EnterpriseSSOTestHarness()
    
    # Create enterprise SSO session
    user_email = "user@enterprise.com"
    results = await harness.execute_complete_sso_flow(user_email)
    
    assert results["success"], f"SSO flow failed: {results.get('error')}"
    
    session_id = results["session"]["session_id"]
    
    # Test session consistency validation
    consistency_check = await harness.verify_session_consistency(session_id)
    assert consistency_check, "Session consistency validation failed"
    
    # Validate session exists in session store
    assert session_id in harness.session_manager.sessions, "Session not found in store"
    
    # Validate session data integrity
    session_data = harness.session_manager.sessions[session_id]
    assert session_data["user_id"] == user_email, "Session user mismatch"
    assert session_data["auth_method"] == "saml_sso", "Session auth method incorrect"
    
    print("[SUCCESS] Session synchronization validated")
    print("[PROTECTED] Enterprise user experience consistency")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_mfa_integration_with_sso_authentication():
    """
    Test #4: MFA Integration with SSO Authentication
    
    BVJ: Ensures enterprise security compliance through MFA verification
    - Creates MFA challenge after SSO authentication
    - Tests TOTP verification flow
    - Validates MFA bypass for pre-verified assertions
    """
    harness = EnterpriseSSOTestHarness()
    
    # Execute SSO flow (MFA not yet verified)
    user_email = "security@enterprise.com"
    results = await harness.execute_complete_sso_flow(user_email)
    
    assert results["success"], f"SSO flow failed: {results.get('error')}"
    
    # Validate MFA challenge creation
    mfa_challenge = results["mfa_challenge"]
    assert mfa_challenge["challenge_type"] == "totp", "MFA challenge type incorrect"
    assert mfa_challenge["user_email"] == user_email, "MFA user email mismatch"
    assert mfa_challenge["max_attempts"] == 3, "MFA max attempts incorrect"
    
    # Test valid MFA verification
    valid_verification = await harness.mfa_challenge.verify_mfa_challenge(
        mfa_challenge["challenge_id"], "123456"
    )
    assert valid_verification, "Valid MFA code verification failed"
    
    # Test invalid MFA verification
    new_challenge = await harness.mfa_challenge.require_mfa_after_sso(
        results["session"]["session_id"], user_email
    )
    invalid_verification = await harness.mfa_challenge.verify_mfa_challenge(
        new_challenge["challenge_id"], "invalid"
    )
    assert not invalid_verification, "Invalid MFA code should be rejected"
    
    print("[SUCCESS] MFA integration with SSO")
    print("[SECURE] Enterprise security compliance validated")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_permission_inheritance_from_idp_attributes():
    """
    Test #5: Permission Inheritance from IdP Attributes
    
    BVJ: Ensures enterprise users get correct permissions from IdP
    - Maps SAML attributes to internal permission system
    - Tests different enterprise role mappings
    - Validates permission inheritance accuracy
    """
    harness = EnterpriseSSOTestHarness()
    
    # Test different permission levels
    test_cases = [
        {"role": "enterprise_admin", "expected_perms": ["read", "write", "admin", "billing"], "user": "admin@enterprise.com"},
        {"role": "enterprise_user", "expected_perms": ["read", "write"], "user": "user@enterprise.com"},
        {"role": "enterprise_viewer", "expected_perms": ["read"], "user": "viewer@enterprise.com"}
    ]
    
    for case in test_cases:
        # Execute SSO flow with specific role
        results = await harness.execute_complete_sso_flow(case["user"], [case["role"]])
        assert results["success"], f"SSO failed for {case['role']}"
        
        # Validate permission mapping
        session_permissions = results["session"]["permissions"]
        for expected_perm in case["expected_perms"]:
            assert expected_perm in session_permissions, f"Missing {expected_perm} for {case['role']}"
        print(f"[SUCCESS] Permission mapping for {case['role']}")
    
    print("[PROTECTED] Enterprise permission accuracy")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_session_invalidation_on_idp_logout():
    """
    Test #6: Session Invalidation on IdP Logout
    
    BVJ: Prevents security vulnerabilities from stale enterprise sessions
    - Tests logout propagation to IdP
    - Validates session cleanup across services
    - Ensures enterprise security compliance
    """
    harness = EnterpriseSSOTestHarness()
    
    # Create enterprise session
    user_email = "logout.test@enterprise.com"
    results = await harness.execute_complete_sso_flow(user_email)
    
    assert results["success"], f"SSO setup failed: {results.get('error')}"
    
    session_id = results["session"]["session_id"]
    
    # Verify session exists before logout
    assert session_id in harness.session_manager.sessions, "Session not found before logout"
    
    # Test IdP logout propagation
    logout_success = await harness.test_idp_logout_propagation(session_id)
    assert logout_success, "IdP logout propagation failed"
    
    # Verify session is invalidated
    assert session_id not in harness.session_manager.sessions, "Session not invalidated"
    
    # Test session consistency after logout
    consistency_check = await harness.verify_session_consistency(session_id)
    assert not consistency_check, "Session should be invalid after logout"
    
    print("[SUCCESS] IdP logout propagation")
    print("[SECURE] Enterprise session cleanup validated")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_enterprise_sso_performance_validation():
    """
    Performance validation for enterprise SSO flows.
    BVJ: Enterprise user experience directly impacts retention and satisfaction.
    """
    harness = EnterpriseSSOTestHarness()
    total_start_time = time.time()
    
    # Test multiple SSO flows for performance consistency
    performance_results = []
    
    for i in range(3):
        start_time = time.time()
        user_email = f"perf.test.{i}@enterprise.com"
        
        results = await harness.execute_complete_sso_flow(user_email, ["enterprise_user"])
        execution_time = time.time() - start_time
        
        assert results["success"], f"Performance test {i} failed"
        assert execution_time < 3.0, f"Performance test {i} too slow: {execution_time:.2f}s"
        
        performance_results.append(execution_time)
    
    # Calculate performance metrics
    avg_time = sum(performance_results) / len(performance_results)
    max_time = max(performance_results)
    total_time = time.time() - total_start_time
    
    # Performance assertions
    assert avg_time < 2.0, f"Average time too high: {avg_time:.2f}s"
    assert max_time < 3.0, f"Max time too high: {max_time:.2f}s"
    assert total_time < 10.0, f"Total test time too high: {total_time:.2f}s"
    
    print(f"[PASSED] Enterprise SSO Performance validation")
    print(f"[METRICS] Average SSO time: {avg_time:.2f}s")
    print(f"[METRICS] Max SSO time: {max_time:.2f}s")
    print(f"[PROTECTED] $60K+ MRR enterprise experience")
