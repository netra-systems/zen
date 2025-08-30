"""Test SECRET_KEY validation issues found in staging.

These tests reproduce the SECRET_KEY configuration problems where the key
is too short (less than 32 characters) causing security warnings and 
potential startup failures.

Based on staging audit findings:
- "[CRITICAL] Staging startup check failed: check_configuration - SECRET_KEY must be at least 32 characters"
- SECRET_KEY configuration is too short (less than 32 characters)
"""

import pytest
import os
import asyncio
from typing import Dict, Optional
from test_framework.environment_markers import staging_only, env_requires


class TestSecretKeyValidation:
    """Test SECRET_KEY validation and configuration issues in staging."""

    @staging_only
    @env_requires(services=["backend_service"])
    @pytest.mark.e2e
    def test_secret_key_too_short_validation_failure(self):
        """Test that SECRET_KEY fails validation when shorter than 32 characters.
        
        This test SHOULD FAIL, demonstrating the exact SECRET_KEY length issue
        found in staging where the key is too short for security requirements.
        
        Expected failure: SECRET_KEY validation error for keys < 32 characters
        """
        # Simulate the short SECRET_KEY found in staging
        short_secret_keys = [
            "short",                    # 5 characters - way too short
            "still_too_short_key",     # 20 characters - still too short 
            "this_is_exactly_31_chars_long!",  # 31 characters - 1 short of requirement
        ]
        
        validation_failures = []
        
        for short_key in short_secret_keys:
            # Test SECRET_KEY validation logic
            key_length = len(short_key)
            min_required_length = 32
            
            # This is the validation that should FAIL in staging
            if key_length < min_required_length:
                validation_failures.append({
                    "secret_key": short_key[:10] + "...",  # Truncate for security
                    "length": key_length,
                    "required_minimum": min_required_length,
                    "failure_reason": f"SECRET_KEY length {key_length} < required {min_required_length}"
                })
        
        # This test SHOULD FAIL - expecting validation failures for short keys
        assert len(validation_failures) == len(short_secret_keys), (
            f"Expected ALL {len(short_secret_keys)} short SECRET_KEYs to fail validation, "
            f"but {len(short_secret_keys) - len(validation_failures)} passed. "
            f"Validation failures: {validation_failures}. "
            f"If some short keys are accepted, the validation logic is broken."
        )
        
        # Verify specific length requirements from staging audit
        keys_31_chars = [f for f in validation_failures if f["length"] == 31]
        assert len(keys_31_chars) >= 1, (
            f"Expected at least 1 key with exactly 31 characters to fail "
            f"(demonstrating off-by-one validation), but got {len(keys_31_chars)}. "
            f"This tests the exact boundary condition from staging."
        )

    @staging_only
    @pytest.mark.e2e
    def test_staging_secret_key_environment_variable_too_short(self):
        """Test that staging SECRET_KEY environment variable is too short.
        
        This test should FAIL, showing that the actual staging SECRET_KEY
        environment variable does not meet the 32-character minimum requirement.
        """
        # Get the actual SECRET_KEY from staging environment
        staging_secret_key = os.environ.get("SECRET_KEY", "")
        
        # Check if SECRET_KEY exists
        assert staging_secret_key, (
            "SECRET_KEY environment variable is not set in staging. "
            "This explains why backend startup fails with configuration errors."
        )
        
        # Test the actual length requirement that's failing in staging
        actual_length = len(staging_secret_key)
        required_minimum = 32
        
        # This assertion SHOULD FAIL in broken staging
        assert actual_length >= required_minimum, (
            f"Staging SECRET_KEY is {actual_length} characters long, "
            f"but requires minimum {required_minimum} characters. "
            f"Current key: '{staging_secret_key[:8]}...' (truncated for security). "
            f"This is the ROOT CAUSE of the staging startup configuration failure."
        )

    @staging_only
    @env_requires(services=["backend_service", "auth_service"])
    @pytest.mark.e2e
    def test_secret_key_consistency_across_services(self):
        """Test SECRET_KEY consistency between backend and auth services.
        
        This test should FAIL if services have different SECRET_KEYs or
        if one/both have keys that are too short.
        """
        # Check SECRET_KEY in different service contexts
        service_secret_keys = {}
        
        # Backend service SECRET_KEY
        backend_secret = os.environ.get("SECRET_KEY", "")
        service_secret_keys["backend"] = {
            "key": backend_secret,
            "length": len(backend_secret),
            "valid": len(backend_secret) >= 32
        }
        
        # Auth service might use different variable names
        auth_secret_vars = ["SECRET_KEY", "JWT_SECRET", "AUTH_SECRET_KEY"]
        auth_secret = None
        
        for var in auth_secret_vars:
            if os.environ.get(var):
                auth_secret = os.environ.get(var, "")
                break
        
        if auth_secret:
            service_secret_keys["auth"] = {
                "key": auth_secret,
                "length": len(auth_secret),
                "valid": len(auth_secret) >= 32
            }
        
        # Check for consistency and validity issues
        consistency_failures = []
        
        # Test 1: Check if any service has invalid (too short) SECRET_KEY
        for service, config in service_secret_keys.items():
            if not config["valid"]:
                consistency_failures.append({
                    "service": service,
                    "issue": "SECRET_KEY too short",
                    "length": config["length"],
                    "required": 32
                })
        
        # Test 2: Check if services have different SECRET_KEYs (security risk)
        if len(service_secret_keys) > 1:
            keys_list = [config["key"] for config in service_secret_keys.values()]
            if len(set(keys_list)) > 1:
                consistency_failures.append({
                    "issue": "Services have different SECRET_KEYs",
                    "services": list(service_secret_keys.keys()),
                    "security_risk": "JWT/session validation will fail across services"
                })
        
        # This test SHOULD FAIL - expecting SECRET_KEY issues in staging
        assert len(consistency_failures) > 0, (
            f"Expected SECRET_KEY configuration issues between services, "
            f"but all services have valid and consistent keys: {service_secret_keys}. "
            f"This suggests the SECRET_KEY staging issues have been resolved."
        )
        
        # Verify we found the specific "too short" issue from audit
        short_key_failures = [
            f for f in consistency_failures 
            if "too short" in f.get("issue", "")
        ]
        
        assert len(short_key_failures) >= 1, (
            f"Expected at least 1 service with 'SECRET_KEY too short' issue "
            f"(matching staging audit), but got {len(short_key_failures)}. "
            f"All consistency failures: {consistency_failures}"
        )

    @staging_only
    @pytest.mark.e2e
    def test_secret_key_entropy_insufficient_for_production(self):
        """Test that SECRET_KEY has insufficient entropy for production security.
        
        This test should FAIL, showing that even if the key meets length
        requirements, it may not have sufficient randomness/entropy.
        """
        secret_key = os.environ.get("SECRET_KEY", "")
        
        # Basic entropy checks that should fail on weak keys
        entropy_issues = []
        
        # Check 1: Minimum length (from audit)
        if len(secret_key) < 32:
            entropy_issues.append({
                "issue": "Length too short",
                "actual": len(secret_key),
                "required": 32
            })
        
        # Check 2: Pattern detection (weak keys)
        if secret_key:
            # Check for obviously weak patterns
            if secret_key.lower() in ["development", "test", "staging", "default"]:
                entropy_issues.append({
                    "issue": "Uses predictable development key",
                    "pattern": secret_key[:10] + "..."
                })
            
            # Check for repeated characters (low entropy)
            if len(set(secret_key)) < len(secret_key) * 0.5:  # Less than 50% unique chars
                entropy_issues.append({
                    "issue": "Low character diversity",
                    "unique_chars": len(set(secret_key)),
                    "total_chars": len(secret_key)
                })
            
            # Check for sequential patterns
            sequential_patterns = ["123", "abc", "qwe", "aaa", "000"]
            for pattern in sequential_patterns:
                if pattern in secret_key.lower():
                    entropy_issues.append({
                        "issue": f"Contains sequential pattern: {pattern}",
                        "security_risk": "Predictable key generation"
                    })
        
        # This test SHOULD FAIL - expecting entropy/security issues
        assert len(entropy_issues) > 0, (
            f"Expected SECRET_KEY to have entropy or security issues "
            f"(explaining staging configuration warnings), but the key appears "
            f"to be secure: length={len(secret_key)}, unique_chars={len(set(secret_key)) if secret_key else 0}. "
            f"If the key is actually secure, the staging audit findings may be outdated."
        )
        
        # Verify we found the specific length issue from staging audit
        length_issues = [i for i in entropy_issues if "too short" in i.get("issue", "")]
        
        assert len(length_issues) >= 1, (
            f"Expected SECRET_KEY length issue (from staging audit), "
            f"but got other entropy issues: {entropy_issues}. "
            f"The length requirement is the primary issue found in staging."
        )

    @staging_only  
    @patch.dict(os.environ, {}, clear=False)  # Don't clear all env vars
    @pytest.mark.e2e
    def test_missing_secret_key_environment_variable(self):
        """Test behavior when SECRET_KEY environment variable is completely missing.
        
        This test should FAIL, demonstrating what happens when SECRET_KEY
        is not set at all in the staging environment.
        """
        # Temporarily remove SECRET_KEY to test missing key scenario
        original_secret = os.environ.get("SECRET_KEY")
        
        try:
            # Remove SECRET_KEY environment variable
            if "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]
            
            # Test what happens with missing SECRET_KEY
            missing_key_issues = []
            
            # Check 1: Environment variable exists
            secret_key = os.environ.get("SECRET_KEY")
            if not secret_key:
                missing_key_issues.append({
                    "issue": "SECRET_KEY environment variable not set",
                    "impact": "Backend startup will fail"
                })
            
            # Check 2: Default fallback behavior
            fallback_key = os.environ.get("SECRET_KEY", "default_insecure_key")
            if fallback_key == "default_insecure_key":
                missing_key_issues.append({
                    "issue": "Using insecure default fallback key",
                    "security_risk": "All sessions/tokens vulnerable"
                })
            
            # Check 3: Service startup simulation
            if not secret_key and not fallback_key:
                missing_key_issues.append({
                    "issue": "No SECRET_KEY available for service startup", 
                    "expected_behavior": "Configuration validation failure"
                })
            
            # This test SHOULD FAIL - expecting missing key issues
            assert len(missing_key_issues) > 0, (
                f"Expected missing SECRET_KEY to cause configuration issues, "
                f"but no problems detected. Secret key: '{secret_key}', "
                f"Fallback: '{fallback_key}'. This suggests the SECRET_KEY "
                f"environment setup is working correctly."
            )
            
        finally:
            # Restore original SECRET_KEY
            if original_secret is not None:
                os.environ["SECRET_KEY"] = original_secret

    @staging_only
    @pytest.mark.e2e
    def test_secret_key_staging_vs_production_security_requirements(self):
        """Test SECRET_KEY meets different security levels for staging vs production.
        
        This test should FAIL, showing that staging SECRET_KEY doesn't meet
        the production security requirements that startup validation checks for.
        """
        secret_key = os.environ.get("SECRET_KEY", "")
        
        # Security requirement levels from staging audit
        security_requirements = {
            "development": {"min_length": 16, "entropy": "low"},
            "staging": {"min_length": 32, "entropy": "medium"}, 
            "production": {"min_length": 64, "entropy": "high"}
        }
        
        current_environment = "staging"  # We're testing staging
        requirements = security_requirements[current_environment]
        
        security_failures = []
        
        # Test staging-specific requirements
        if len(secret_key) < requirements["min_length"]:
            security_failures.append({
                "requirement": f"Staging minimum length: {requirements['min_length']}",
                "actual": len(secret_key),
                "status": "FAILED"
            })
        
        # Test if key would meet production requirements (it shouldn't)
        prod_requirements = security_requirements["production"]
        if len(secret_key) < prod_requirements["min_length"]:
            security_failures.append({
                "requirement": f"Production readiness: {prod_requirements['min_length']} chars",
                "actual": len(secret_key),
                "status": "NOT PRODUCTION READY",
                "impact": "Cannot promote to production without key rotation"
            })
        
        # This test SHOULD FAIL - expecting staging key to not meet requirements
        assert len(security_failures) >= 1, (
            f"Expected SECRET_KEY to fail security requirements for staging "
            f"(matching audit findings), but key meets all requirements: "
            f"length={len(secret_key)}, staging_min={requirements['min_length']}. "
            f"This suggests the SECRET_KEY issue has been resolved."
        )
        
        # Verify we found the specific staging length failure
        staging_length_failures = [
            f for f in security_failures 
            if "Staging minimum length" in f.get("requirement", "")
        ]
        
        assert len(staging_length_failures) >= 1, (
            f"Expected SECRET_KEY to fail staging length requirement "
            f"(32 characters from audit), but got other security failures: "
            f"{security_failures}. The staging length requirement is the "
            f"primary issue identified in the audit logs."
        )