# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''Test SECRET_KEY validation issues found in staging.
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: These tests reproduce the SECRET_KEY configuration problems where the key
    # REMOVED_SYNTAX_ERROR: is too short (less than 32 characters) causing security warnings and
    # REMOVED_SYNTAX_ERROR: potential startup failures.

    # REMOVED_SYNTAX_ERROR: Based on staging audit findings:
        # REMOVED_SYNTAX_ERROR: - "[CRITICAL] Staging startup check failed: check_configuration - SECRET_KEY must be at least 32 characters"
        # REMOVED_SYNTAX_ERROR: - SECRET_KEY configuration is too short (less than 32 characters)
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import os
        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: from typing import Dict, Optional
        # REMOVED_SYNTAX_ERROR: from test_framework.environment_markers import staging_only, env_requires
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient


# REMOVED_SYNTAX_ERROR: class TestSecretKeyValidation:
    # REMOVED_SYNTAX_ERROR: """Test SECRET_KEY validation and configuration issues in staging."""
    # REMOVED_SYNTAX_ERROR: pass

    # REMOVED_SYNTAX_ERROR: @staging_only
    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_secret_key_too_short_validation_failure(self):
    # REMOVED_SYNTAX_ERROR: '''Test that SECRET_KEY fails validation when shorter than 32 characters.

    # REMOVED_SYNTAX_ERROR: This test SHOULD FAIL, demonstrating the exact SECRET_KEY length issue
    # REMOVED_SYNTAX_ERROR: found in staging where the key is too short for security requirements.

    # REMOVED_SYNTAX_ERROR: Expected failure: SECRET_KEY validation error for keys < 32 characters
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Simulate the short SECRET_KEY found in staging
    # REMOVED_SYNTAX_ERROR: short_secret_keys = [ )
    # REMOVED_SYNTAX_ERROR: "short",                    # 5 characters - way too short
    # REMOVED_SYNTAX_ERROR: "still_too_short_key",     # 20 characters - still too short
    # REMOVED_SYNTAX_ERROR: "this_is_exactly_31_chars_long!",  # 31 characters - 1 short of requirement
    

    # REMOVED_SYNTAX_ERROR: validation_failures = []

    # REMOVED_SYNTAX_ERROR: for short_key in short_secret_keys:
        # Test SECRET_KEY validation logic
        # REMOVED_SYNTAX_ERROR: key_length = len(short_key)
        # REMOVED_SYNTAX_ERROR: min_required_length = 32

        # This is the validation that should FAIL in staging
        # REMOVED_SYNTAX_ERROR: if key_length < min_required_length:
            # REMOVED_SYNTAX_ERROR: validation_failures.append({ ))
            # REMOVED_SYNTAX_ERROR: "secret_key": short_key[:10] + "...",  # Truncate for security
            # REMOVED_SYNTAX_ERROR: "length": key_length,
            # REMOVED_SYNTAX_ERROR: "required_minimum": min_required_length,
            # REMOVED_SYNTAX_ERROR: "failure_reason": "formatted_string"
            

            # This test SHOULD FAIL - expecting validation failures for short keys
            # REMOVED_SYNTAX_ERROR: assert len(validation_failures) == len(short_secret_keys), ( )
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            # REMOVED_SYNTAX_ERROR: f"If some short keys are accepted, the validation logic is broken."
            

            # Verify specific length requirements from staging audit
            # REMOVED_SYNTAX_ERROR: keys_31_chars = [item for item in []] == 31]
            # REMOVED_SYNTAX_ERROR: assert len(keys_31_chars) >= 1, ( )
            # REMOVED_SYNTAX_ERROR: f"Expected at least 1 key with exactly 31 characters to fail "
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            # REMOVED_SYNTAX_ERROR: f"This tests the exact boundary condition from staging."
            

            # REMOVED_SYNTAX_ERROR: @staging_only
            # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_staging_secret_key_environment_variable_too_short(self):
    # REMOVED_SYNTAX_ERROR: '''Test that staging SECRET_KEY environment variable is too short.

    # REMOVED_SYNTAX_ERROR: This test should FAIL, showing that the actual staging SECRET_KEY
    # REMOVED_SYNTAX_ERROR: environment variable does not meet the 32-character minimum requirement.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Get the actual SECRET_KEY from staging environment
    # REMOVED_SYNTAX_ERROR: staging_secret_key = get_env().get("SECRET_KEY", "")

    # Check if SECRET_KEY exists
    # REMOVED_SYNTAX_ERROR: assert staging_secret_key, ( )
    # REMOVED_SYNTAX_ERROR: "SECRET_KEY environment variable is not set in staging. "
    # REMOVED_SYNTAX_ERROR: "This explains why backend startup fails with configuration errors."
    

    # Test the actual length requirement that's failing in staging
    # REMOVED_SYNTAX_ERROR: actual_length = len(staging_secret_key)
    # REMOVED_SYNTAX_ERROR: required_minimum = 32

    # This assertion SHOULD FAIL in broken staging
    # REMOVED_SYNTAX_ERROR: assert actual_length >= required_minimum, ( )
    # REMOVED_SYNTAX_ERROR: "formatted_string"
    # REMOVED_SYNTAX_ERROR: "formatted_string"
    # REMOVED_SYNTAX_ERROR: "formatted_string"
    # REMOVED_SYNTAX_ERROR: f"This is the ROOT CAUSE of the staging startup configuration failure."
    

    # REMOVED_SYNTAX_ERROR: @staging_only
    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_secret_key_consistency_across_services(self):
    # REMOVED_SYNTAX_ERROR: '''Test SECRET_KEY consistency between backend and auth services.

    # REMOVED_SYNTAX_ERROR: This test should FAIL if services have different SECRET_KEYs or
    # REMOVED_SYNTAX_ERROR: if one/both have keys that are too short.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Check SECRET_KEY in different service contexts
    # REMOVED_SYNTAX_ERROR: service_secret_keys = {}

    # Backend service SECRET_KEY
    # REMOVED_SYNTAX_ERROR: backend_secret = get_env().get("SECRET_KEY", "")
    # REMOVED_SYNTAX_ERROR: service_secret_keys["backend"] = { )
    # REMOVED_SYNTAX_ERROR: "key": backend_secret,
    # REMOVED_SYNTAX_ERROR: "length": len(backend_secret),
    # REMOVED_SYNTAX_ERROR: "valid": len(backend_secret) >= 32
    

    # Auth service might use different variable names
    # REMOVED_SYNTAX_ERROR: auth_secret_vars = ["SECRET_KEY", "JWT_SECRET", "AUTH_SECRET_KEY"]
    # REMOVED_SYNTAX_ERROR: auth_secret = None

    # REMOVED_SYNTAX_ERROR: for var in auth_secret_vars:
        # REMOVED_SYNTAX_ERROR: if get_env().get(var):
            # REMOVED_SYNTAX_ERROR: auth_secret = get_env().get(var, "")
            # REMOVED_SYNTAX_ERROR: break

            # REMOVED_SYNTAX_ERROR: if auth_secret:
                # REMOVED_SYNTAX_ERROR: service_secret_keys["auth"] = { )
                # REMOVED_SYNTAX_ERROR: "key": auth_secret,
                # REMOVED_SYNTAX_ERROR: "length": len(auth_secret),
                # REMOVED_SYNTAX_ERROR: "valid": len(auth_secret) >= 32
                

                # Check for consistency and validity issues
                # REMOVED_SYNTAX_ERROR: consistency_failures = []

                # Test 1: Check if any service has invalid (too short) SECRET_KEY
                # REMOVED_SYNTAX_ERROR: for service, config in service_secret_keys.items():
                    # REMOVED_SYNTAX_ERROR: if not config["valid"]:
                        # REMOVED_SYNTAX_ERROR: consistency_failures.append({ ))
                        # REMOVED_SYNTAX_ERROR: "service": service,
                        # REMOVED_SYNTAX_ERROR: "issue": "SECRET_KEY too short",
                        # REMOVED_SYNTAX_ERROR: "length": config["length"],
                        # REMOVED_SYNTAX_ERROR: "required": 32
                        

                        # Test 2: Check if services have different SECRET_KEYs (security risk)
                        # REMOVED_SYNTAX_ERROR: if len(service_secret_keys) > 1:
                            # REMOVED_SYNTAX_ERROR: keys_list = [config["key"] for config in service_secret_keys.values()]
                            # REMOVED_SYNTAX_ERROR: if len(set(keys_list)) > 1:
                                # REMOVED_SYNTAX_ERROR: consistency_failures.append({ ))
                                # REMOVED_SYNTAX_ERROR: "issue": "Services have different SECRET_KEYs",
                                # REMOVED_SYNTAX_ERROR: "services": list(service_secret_keys.keys()),
                                # REMOVED_SYNTAX_ERROR: "security_risk": "JWT/session validation will fail across services"
                                

                                # This test SHOULD FAIL - expecting SECRET_KEY issues in staging
                                # REMOVED_SYNTAX_ERROR: assert len(consistency_failures) > 0, ( )
                                # REMOVED_SYNTAX_ERROR: f"Expected SECRET_KEY configuration issues between services, "
                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                # REMOVED_SYNTAX_ERROR: f"This suggests the SECRET_KEY staging issues have been resolved."
                                

                                # Verify we found the specific "too short" issue from audit
                                # REMOVED_SYNTAX_ERROR: short_key_failures = [ )
                                # REMOVED_SYNTAX_ERROR: f for f in consistency_failures
                                # REMOVED_SYNTAX_ERROR: if "too short" in f.get("issue", "")
                                

                                # REMOVED_SYNTAX_ERROR: assert len(short_key_failures) >= 1, ( )
                                # REMOVED_SYNTAX_ERROR: f"Expected at least 1 service with 'SECRET_KEY too short' issue "
                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                

                                # REMOVED_SYNTAX_ERROR: @staging_only
                                # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_secret_key_entropy_insufficient_for_production(self):
    # REMOVED_SYNTAX_ERROR: '''Test that SECRET_KEY has insufficient entropy for production security.

    # REMOVED_SYNTAX_ERROR: This test should FAIL, showing that even if the key meets length
    # REMOVED_SYNTAX_ERROR: requirements, it may not have sufficient randomness/entropy.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: secret_key = get_env().get("SECRET_KEY", "")

    # Basic entropy checks that should fail on weak keys
    # REMOVED_SYNTAX_ERROR: entropy_issues = []

    # Check 1: Minimum length (from audit)
    # REMOVED_SYNTAX_ERROR: if len(secret_key) < 32:
        # REMOVED_SYNTAX_ERROR: entropy_issues.append({ ))
        # REMOVED_SYNTAX_ERROR: "issue": "Length too short",
        # REMOVED_SYNTAX_ERROR: "actual": len(secret_key),
        # REMOVED_SYNTAX_ERROR: "required": 32
        

        # Check 2: Pattern detection (weak keys)
        # REMOVED_SYNTAX_ERROR: if secret_key:
            # Check for obviously weak patterns
            # REMOVED_SYNTAX_ERROR: if secret_key.lower() in ["development", "test", "staging", "default"]:
                # REMOVED_SYNTAX_ERROR: entropy_issues.append({ ))
                # REMOVED_SYNTAX_ERROR: "issue": "Uses predictable development key",
                # REMOVED_SYNTAX_ERROR: "pattern": secret_key[:10] + "..."
                

                # Check for repeated characters (low entropy)
                # REMOVED_SYNTAX_ERROR: if len(set(secret_key)) < len(secret_key) * 0.5:  # Less than 50% unique chars
                # REMOVED_SYNTAX_ERROR: entropy_issues.append({ ))
                # REMOVED_SYNTAX_ERROR: "issue": "Low character diversity",
                # REMOVED_SYNTAX_ERROR: "unique_chars": len(set(secret_key)),
                # REMOVED_SYNTAX_ERROR: "total_chars": len(secret_key)
                

                # Check for sequential patterns
                # REMOVED_SYNTAX_ERROR: sequential_patterns = ["123", "abc", "qwe", "aaa", "000"]
                # REMOVED_SYNTAX_ERROR: for pattern in sequential_patterns:
                    # REMOVED_SYNTAX_ERROR: if pattern in secret_key.lower():
                        # REMOVED_SYNTAX_ERROR: entropy_issues.append({ ))
                        # REMOVED_SYNTAX_ERROR: "issue": "formatted_string",
                        # REMOVED_SYNTAX_ERROR: "security_risk": "Predictable key generation"
                        

                        # This test SHOULD FAIL - expecting entropy/security issues
                        # REMOVED_SYNTAX_ERROR: assert len(entropy_issues) > 0, ( )
                        # REMOVED_SYNTAX_ERROR: f"Expected SECRET_KEY to have entropy or security issues "
                        # REMOVED_SYNTAX_ERROR: f"(explaining staging configuration warnings), but the key appears "
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        # REMOVED_SYNTAX_ERROR: f"If the key is actually secure, the staging audit findings may be outdated."
                        

                        # Verify we found the specific length issue from staging audit
                        # REMOVED_SYNTAX_ERROR: length_issues = [item for item in []]

                        # REMOVED_SYNTAX_ERROR: assert len(length_issues) >= 1, ( )
                        # REMOVED_SYNTAX_ERROR: f"Expected SECRET_KEY length issue (from staging audit), "
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        # REMOVED_SYNTAX_ERROR: f"The length requirement is the primary issue found in staging."
                        

                        # REMOVED_SYNTAX_ERROR: @staging_only
                        # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_missing_secret_key_environment_variable(self):
    # REMOVED_SYNTAX_ERROR: '''Test behavior when SECRET_KEY environment variable is completely missing.

    # REMOVED_SYNTAX_ERROR: This test should FAIL, demonstrating what happens when SECRET_KEY
    # REMOVED_SYNTAX_ERROR: is not set at all in the staging environment.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Temporarily remove SECRET_KEY to test missing key scenario
    # REMOVED_SYNTAX_ERROR: original_secret = get_env().get("SECRET_KEY")

    # REMOVED_SYNTAX_ERROR: try:
        # Remove SECRET_KEY environment variable
        # REMOVED_SYNTAX_ERROR: import os
        # REMOVED_SYNTAX_ERROR: if get_env().get("SECRET_KEY") is not None:
            # REMOVED_SYNTAX_ERROR: if "SECRET_KEY" in os.environ:
                # REMOVED_SYNTAX_ERROR: del os.environ["SECRET_KEY"]

                # Test what happens with missing SECRET_KEY
                # REMOVED_SYNTAX_ERROR: missing_key_issues = []

                # Check 1: Environment variable exists
                # REMOVED_SYNTAX_ERROR: secret_key = get_env().get("SECRET_KEY")
                # REMOVED_SYNTAX_ERROR: if not secret_key:
                    # REMOVED_SYNTAX_ERROR: missing_key_issues.append({ ))
                    # REMOVED_SYNTAX_ERROR: "issue": "SECRET_KEY environment variable not set",
                    # REMOVED_SYNTAX_ERROR: "impact": "Backend startup will fail"
                    

                    # Check 2: Default fallback behavior
                    # REMOVED_SYNTAX_ERROR: fallback_key = get_env().get("SECRET_KEY", "default_insecure_key")
                    # REMOVED_SYNTAX_ERROR: if fallback_key == "default_insecure_key":
                        # REMOVED_SYNTAX_ERROR: missing_key_issues.append({ ))
                        # REMOVED_SYNTAX_ERROR: "issue": "Using insecure default fallback key",
                        # REMOVED_SYNTAX_ERROR: "security_risk": "All sessions/tokens vulnerable"
                        

                        # Check 3: Service startup simulation
                        # REMOVED_SYNTAX_ERROR: if not secret_key and not fallback_key:
                            # REMOVED_SYNTAX_ERROR: missing_key_issues.append({ ))
                            # REMOVED_SYNTAX_ERROR: "issue": "No SECRET_KEY available for service startup",
                            # REMOVED_SYNTAX_ERROR: "expected_behavior": "Configuration validation failure"
                            

                            # This test SHOULD FAIL - expecting missing key issues
                            # REMOVED_SYNTAX_ERROR: assert len(missing_key_issues) > 0, ( )
                            # REMOVED_SYNTAX_ERROR: f"Expected missing SECRET_KEY to cause configuration issues, "
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            # REMOVED_SYNTAX_ERROR: f"environment setup is working correctly."
                            

                            # REMOVED_SYNTAX_ERROR: finally:
                                # Restore original SECRET_KEY
                                # REMOVED_SYNTAX_ERROR: if original_secret is not None:
                                    # REMOVED_SYNTAX_ERROR: get_env().set("SECRET_KEY", original_secret)

                                    # REMOVED_SYNTAX_ERROR: @staging_only
                                    # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_secret_key_staging_vs_production_security_requirements(self):
    # REMOVED_SYNTAX_ERROR: '''Test SECRET_KEY meets different security levels for staging vs production.

    # REMOVED_SYNTAX_ERROR: This test should FAIL, showing that staging SECRET_KEY doesn"t meet
    # REMOVED_SYNTAX_ERROR: the production security requirements that startup validation checks for.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: secret_key = get_env().get("SECRET_KEY", "")

    # Security requirement levels from staging audit
    # REMOVED_SYNTAX_ERROR: security_requirements = { )
    # REMOVED_SYNTAX_ERROR: "development": {"min_length": 16, "entropy": "low"},
    # REMOVED_SYNTAX_ERROR: "staging": {"min_length": 32, "entropy": "medium"},
    # REMOVED_SYNTAX_ERROR: "production": {"min_length": 64, "entropy": "high"}
    

    # REMOVED_SYNTAX_ERROR: current_environment = "staging"  # We"re testing staging
    # REMOVED_SYNTAX_ERROR: requirements = security_requirements[current_environment]

    # REMOVED_SYNTAX_ERROR: security_failures = []

    # Test staging-specific requirements
    # REMOVED_SYNTAX_ERROR: if len(secret_key) < requirements["min_length"]:
        # REMOVED_SYNTAX_ERROR: security_failures.append({ ))
        # REMOVED_SYNTAX_ERROR: "requirement": "formatted_string",
        # REMOVED_SYNTAX_ERROR: "actual": len(secret_key),
        # REMOVED_SYNTAX_ERROR: "status": "FAILED"
        

        # Test if key would meet production requirements (it shouldn't)
        # REMOVED_SYNTAX_ERROR: prod_requirements = security_requirements["production"]
        # REMOVED_SYNTAX_ERROR: if len(secret_key) < prod_requirements["min_length"]:
            # REMOVED_SYNTAX_ERROR: security_failures.append({ ))
            # REMOVED_SYNTAX_ERROR: "requirement": "formatted_string",
            # REMOVED_SYNTAX_ERROR: "actual": len(secret_key),
            # REMOVED_SYNTAX_ERROR: "status": "NOT PRODUCTION READY",
            # REMOVED_SYNTAX_ERROR: "impact": "Cannot promote to production without key rotation"
            

            # This test SHOULD FAIL - expecting staging key to not meet requirements
            # REMOVED_SYNTAX_ERROR: assert len(security_failures) >= 1, ( )
            # REMOVED_SYNTAX_ERROR: f"Expected SECRET_KEY to fail security requirements for staging "
            # REMOVED_SYNTAX_ERROR: f"(matching audit findings), but key meets all requirements: "
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            # REMOVED_SYNTAX_ERROR: f"This suggests the SECRET_KEY issue has been resolved."
            

            # Verify we found the specific staging length failure
            # REMOVED_SYNTAX_ERROR: staging_length_failures = [ )
            # REMOVED_SYNTAX_ERROR: f for f in security_failures
            # REMOVED_SYNTAX_ERROR: if "Staging minimum length" in f.get("requirement", "")
            

            # REMOVED_SYNTAX_ERROR: assert len(staging_length_failures) >= 1, ( )
            # REMOVED_SYNTAX_ERROR: f"Expected SECRET_KEY to fail staging length requirement "
            # REMOVED_SYNTAX_ERROR: f"(32 characters from audit), but got other security failures: "
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            # REMOVED_SYNTAX_ERROR: f"primary issue identified in the audit logs."
            