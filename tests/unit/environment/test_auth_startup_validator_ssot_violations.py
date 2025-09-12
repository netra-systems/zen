"""
Unit Tests: Auth Startup Validator SSOT Violations - Issue #596

Purpose: Detect and reproduce os.environ fallback violations in AuthStartupValidator
Expected: These tests should FAIL initially to prove violations exist

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform)
- Business Goal: Stability - Protect $500K+ ARR Golden Path functionality
- Value Impact: Ensures users can login → get AI responses (90% of platform value) 
- Strategic Impact: SSOT compliance prevents authentication vulnerabilities
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from netra_backend.app.core.auth_startup_validator import (
    AuthStartupValidator,
    AuthComponent
)
from shared.jwt_secret_manager import get_jwt_secret_manager
from shared.isolated_environment import get_env
from test_framework.base_unit_test import BaseUnitTest


class TestAuthStartupValidatorSSOTViolations(BaseUnitTest):
    """Test SSOT violations in AuthStartupValidator that block Golden Path."""
    
    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        # Clear any cached state
        get_jwt_secret_manager().clear_cache()
    
    def teardown_method(self):
        """Teardown for each test."""
        super().teardown_method()
        # Clear cached state
        get_jwt_secret_manager().clear_cache()
        # Ensure isolation is disabled
        env = get_env()
        if hasattr(env, 'disable_isolation'):
            env.disable_isolation()

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    async def test_FAILING_env_var_resolution_uses_direct_os_environ(self):
        """
        TEST EXPECTATION: FAIL - Proves direct os.environ usage in auth startup validator
        
        This test demonstrates the SSOT violation in auth_startup_validator.py lines 507-516
        where _get_env_with_fallback() uses direct os.environ access instead of 
        IsolatedEnvironment SSOT pattern.
        
        CRITICAL: This violation blocks Golden Path authentication flow
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Set JWT_SECRET_KEY only in os.environ, NOT in IsolatedEnvironment
            test_jwt_key = "test-jwt-secret-direct-access-violation"
            
            with patch.dict(os.environ, {'JWT_SECRET_KEY': test_jwt_key}):
                # Ensure NOT in isolated environment (proper SSOT behavior)
                env.delete('JWT_SECRET_KEY')
                assert env.get('JWT_SECRET_KEY') is None
                
                # But should be in os.environ (the violation source)
                assert os.environ.get('JWT_SECRET_KEY') == test_jwt_key
                
                # Create validator - this should NOT find JWT_SECRET_KEY if SSOT compliant
                # But if it does, it proves direct os.environ access (SSOT violation)
                validator = AuthStartupValidator()
                
                # Call the private method that has SSOT violation (lines 507-516)
                fallback_value = validator._get_env_with_fallback('JWT_SECRET_KEY')
                
                # THIS ASSERTION SHOULD FAIL - proving SSOT violation exists
                assert fallback_value is None, (
                    f"🚨 SSOT VIOLATION DETECTED: AuthStartupValidator._get_env_with_fallback() "
                    f"found JWT_SECRET_KEY='{fallback_value}' via direct os.environ fallback "
                    f"instead of using IsolatedEnvironment SSOT pattern. "
                    f"This violation is in auth_startup_validator.py lines 507-516 and "
                    f"BLOCKS Golden Path authentication flow ($500K+ ARR impact)."
                )
                
        except Exception as e:
            # If we get an exception, it might indicate the violation is worse than expected
            pytest.fail(
                f"UNEXPECTED ERROR in SSOT violation test: {str(e)}. "
                f"This may indicate deeper SSOT compliance issues in AuthStartupValidator."
            )
        finally:
            env.disable_isolation()
            
    @pytest.mark.unit
    @pytest.mark.ssot_violation
    async def test_FAILING_jwt_validation_bypass_via_fallback(self):
        """
        TEST EXPECTATION: FAIL - Proves JWT validation can be bypassed via os.environ
        
        This test shows how the os.environ fallback creates authentication
        vulnerabilities by bypassing proper environment isolation. This is the
        core mechanism blocking Golden Path user login.
        
        BUSINESS IMPACT: Users cannot login → get AI responses
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Scenario: JWT secret exists in os.environ but not isolated env
            # This creates inconsistent JWT validation behavior
            bypassed_jwt_key = "bypassed-secret-key-via-fallback"
            
            with patch.dict(os.environ, {'JWT_SECRET_KEY': bypassed_jwt_key}):
                # Ensure NOT in isolated environment (proper SSOT state)
                env.delete('JWT_SECRET_KEY')  
                assert env.get('JWT_SECRET_KEY') is None
                
                # Run full validation (this tests the complete violation impact)
                validator = AuthStartupValidator()
                success, results = await validator.validate_all()
                
                # Find JWT validation result
                jwt_result = next((r for r in results 
                                 if r.component == AuthComponent.JWT_CONFIG), None)
                
                if jwt_result is None:
                    pytest.fail(
                        "TEST SETUP ERROR: JWT_CONFIG component not found in validation results. "
                        "Cannot verify SSOT violation impact."
                    )
                
                # THIS SHOULD FAIL - JWT validation should NOT succeed 
                # when secret only exists in os.environ fallback
                assert not jwt_result.valid, (
                    f"🚨 CRITICAL SSOT VIOLATION: JWT validation succeeded using "
                    f"os.environ fallback (key='{bypassed_jwt_key}'), bypassing "
                    f"IsolatedEnvironment isolation. This proves the SSOT violation "
                    f"in auth_startup_validator.py lines 507-516 creates authentication "
                    f"vulnerabilities that BLOCK Golden Path user login flow. "
                    f"Validation result: {jwt_result.error if hasattr(jwt_result, 'error') else 'No error details'}"
                )
                
        except Exception as e:
            # Expected exception - this might be how the violation manifests
            print(f"⚠️  Exception during JWT validation test (may indicate violation): {str(e)}")
            # Re-raise to show the test failure
            raise
        finally:
            env.disable_isolation()

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    async def test_FAILING_service_id_fallback_violation(self):
        """
        TEST EXPECTATION: FAIL - Proves SERVICE_ID resolution uses os.environ fallback
        
        This test demonstrates another SSOT violation where SERVICE_ID resolution
        bypasses IsolatedEnvironment, potentially causing service identification issues.
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Set SERVICE_ID only in os.environ
            test_service_id = "test-service-fallback-violation"
            
            with patch.dict(os.environ, {'SERVICE_ID': test_service_id}):
                # Ensure NOT in isolated environment
                env.delete('SERVICE_ID')
                assert env.get('SERVICE_ID') is None
                
                # Test the fallback mechanism
                validator = AuthStartupValidator()
                service_id_value = validator._get_env_with_fallback('SERVICE_ID')
                
                # THIS SHOULD FAIL - proving SERVICE_ID fallback violation
                assert service_id_value is None, (
                    f"🚨 SSOT VIOLATION: SERVICE_ID resolved to '{service_id_value}' "
                    f"via os.environ fallback instead of IsolatedEnvironment. "
                    f"This proves the violation affects multiple environment variables, "
                    f"not just JWT_SECRET_KEY."
                )
                
        finally:
            env.disable_isolation()

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_FAILING_environment_debug_info_shows_violation(self):
        """
        TEST EXPECTATION: FAIL - Environment debug info reveals os.environ usage
        
        This test examines the debug information to prove that the auth startup
        validator is using both IsolatedEnvironment AND direct os.environ access.
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Create scenario with different values in each environment source
            test_var = "TEST_DEBUG_VAR"
            os_value = "os-environ-value"
            isolated_value = "isolated-env-value"
            
            with patch.dict(os.environ, {test_var: os_value}):
                env.set(test_var, isolated_value, 'test')
                
                # Get debug information from validator
                validator = AuthStartupValidator()
                debug_info = validator._get_env_resolution_debug(test_var)
                
                # Debug info should reveal the dual access pattern
                has_isolated = debug_info.get('isolated_env', False)
                has_os_environ = debug_info.get('os_environ', False)
                
                # THIS SHOULD FAIL - proving the validator checks BOTH sources
                assert not (has_isolated and has_os_environ), (
                    f"🚨 SSOT VIOLATION CONFIRMED: Environment debug shows validator "
                    f"accesses BOTH IsolatedEnvironment ({has_isolated}) AND "
                    f"os.environ ({has_os_environ}) for variable '{test_var}'. "
                    f"SSOT pattern requires ONLY IsolatedEnvironment access. "
                    f"Full debug info: {debug_info}"
                )
                
        finally:
            env.disable_isolation()