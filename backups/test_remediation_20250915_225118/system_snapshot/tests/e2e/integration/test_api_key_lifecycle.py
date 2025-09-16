"""
Test #5: API Key Generation  ->  Usage  ->  Revocation Flow

BVJ (Business Value Justification):
1. Segment: Mid/Enterprise ($50K+ MRR customers)
2. Business Goal: Enable programmatic access for high-value customers
3. Value Impact: API key management directly enables integration workflows
4. Revenue Impact: Critical for Enterprise SLA compliance and customer retention

REQUIREMENTS:
- User generates API key securely
- Key stored with proper encryption/hashing
- API calls authenticate successfully with key
- Usage tracking per key in database
- Key revocation works immediately
- Revoked keys rejected across all endpoints
- Rate limiting per key enforced
- Different scopes/permissions validated
"""
import pytest
import time
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.auth_flow_manager import AuthCompleteFlowManager
from tests.e2e.api_key_lifecycle_helpers import (
    create_test_user_session,
    ApiKeyLifecycleManager,
    ApiKeyScopeValidator
)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_api_key_lifecycle():
    """
    Test #5: Complete API Key Lifecycle
    
    BVJ: Protects $50K+ MRR Enterprise integration workflows
    - Secure key generation with proper entropy
    - Real authentication using generated keys
    - Usage tracking for billing and monitoring
    - Immediate revocation security
    - Performance under 10 seconds
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        # Setup authenticated user session using JWT helper
        user_session = await create_test_user_session(auth_tester)
        
        # Initialize API key manager
        key_manager = ApiKeyLifecycleManager(manager)
        
        start_time = time.time()
        
        # Phase 1: Generate secure API key
        api_key_result = await key_manager.generate_secure_api_key(
            user_session, "test-integration-key", ["read_only", "write_access"]
        )
        
        # Phase 2: Test authentication with generated key
        auth_result = await key_manager.test_api_authentication(
            api_key_result["key"]
        )
        
        # Phase 3: Track usage
        usage_result = await key_manager.track_key_usage(
            api_key_result["key"], "/api/users/profile"
        )
        
        # Phase 4: Test rate limiting
        rate_limit_result = await key_manager.test_rate_limiting(
            api_key_result["key"]
        )
        
        # Phase 5: Revoke key and validate
        revocation_success = await key_manager.revoke_api_key(
            user_session, api_key_result["id"]
        )
        
        # Phase 6: Verify revoked key is rejected
        post_revocation_auth = await key_manager.test_api_authentication(
            api_key_result["key"]
        )
        
        execution_time = time.time() - start_time
        
        # Validate business-critical success criteria
        assert api_key_result["key"], "API key generation failed"
        assert auth_result["success"], "API key authentication failed"
        assert usage_result["request_count"] > 0, "Usage tracking failed"
        assert rate_limit_result["limit_enforced"], "Rate limiting not enforced"
        assert revocation_success, "API key revocation failed"
        assert not post_revocation_auth["success"], "Revoked key still working"
        assert execution_time < 10.0, f"Performance failed: {execution_time:.2f}s"
        
        print(f"[SUCCESS] API Key Lifecycle: {execution_time:.2f}s")
        print(f"[PROTECTED] $50K+ MRR Enterprise integrations")
        print(f"[SECURED] Key generation, usage, and revocation")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_api_key_scope_permissions():
    """
    Test API key scope and permission validation
    
    BVJ: Prevents security breaches that cost Enterprise trust
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        user_session = await create_test_user_session(auth_tester)
        key_manager = ApiKeyLifecycleManager(manager)
        scope_validator = ApiKeyScopeValidator(key_manager)
        
        # Create keys with different permission levels
        limited_key = await key_manager.generate_secure_api_key(
            user_session, "limited-key", ["read_only"]
        )
        
        admin_key = await key_manager.generate_secure_api_key(
            user_session, "admin-key", ["read_only", "write_access", "admin_access"]
        )
        
        # Validate scope restrictions
        limited_scope_results = await scope_validator.validate_scope_restrictions(
            limited_key["key"], ["read_only"]
        )
        
        admin_scope_results = await scope_validator.validate_scope_restrictions(
            admin_key["key"], ["read_only", "write_access", "admin_access"]
        )
        
        # Test permission enforcement
        permission_results = await scope_validator.test_permission_enforcement(
            limited_key["key"], admin_key["key"]
        )
        
        # Validate security boundaries
        assert limited_scope_results, "Limited scope validation failed"
        assert admin_scope_results, "Admin scope validation failed"
        assert permission_results["permission_enforcement"], "Permission enforcement failed"
        
        print("[SUCCESS] API Key Scope Validation")
        print("[SECURED] Permission boundaries enforced")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_api_key_security_validation():
    """
    Security-focused API key validation
    
    BVJ: Prevents security vulnerabilities that cost user trust
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        user_session = await create_test_user_session(auth_tester)
        key_manager = ApiKeyLifecycleManager(manager)
        
        # Test multiple key generation for entropy validation
        keys = []
        for i in range(3):
            key_result = await key_manager.generate_secure_api_key(
                user_session, f"security-test-{i}", ["read_only"]
            )
            keys.append(key_result["key"])
        
        # Validate key uniqueness (entropy check)
        assert len(set(keys)) == 3, "Generated keys not unique"
        
        # Validate key format security
        for key in keys:
            assert len(key) >= 40, "Key too short for security"
            assert not any(c in key for c in [' ', '\n', '\t']), "Key contains whitespace"
            
        # Test immediate revocation effect
        revocation_tests = []
        for i, key in enumerate(keys):
            # Use key successfully
            auth_before = await key_manager.test_api_authentication(key)
            
            # Find the key info with this key value
            key_info = None
            for created_key in key_manager.created_keys:
                if created_key["key"] == key:
                    key_info = created_key
                    break
            
            # Revoke key using the actual key ID
            if key_info:
                await key_manager.revoke_api_key(user_session, key_info["id"])
            
            # Test immediate rejection
            auth_after = await key_manager.test_api_authentication(key)
            
            revocation_tests.append({
                "before_revocation": auth_before["success"],
                "after_revocation": not auth_after["success"]
            })
        
        # Validate all security tests passed
        for test in revocation_tests:
            assert test["before_revocation"], "Key didn't work before revocation"
            assert test["after_revocation"], "Key still works after revocation"
        
        print("[SUCCESS] API Key Security Validation")
        print("[SECURED] Entropy, format, and immediate revocation")
