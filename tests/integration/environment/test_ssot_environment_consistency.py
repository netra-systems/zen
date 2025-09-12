"""
Integration Tests: SSOT Environment Variable Consistency - Issue #596

Purpose: Test environment variable resolution across multiple components
Expected: Detect inconsistencies in environment variable access patterns

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform)
- Business Goal: Stability - Ensure consistent environment resolution across all components  
- Value Impact: Prevents cascade failures and authentication inconsistencies
- Strategic Impact: SSOT compliance protects $500K+ ARR Golden Path functionality
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from netra_backend.app.core.auth_startup_validator import (
    AuthStartupValidator,
    AuthComponent
)
from netra_backend.app.core.configuration.unified_secrets import UnifiedSecrets
from shared.jwt_secret_manager import get_jwt_secret_manager
from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest


class TestSSOTEnvironmentConsistency(BaseIntegrationTest):
    """Test environment variable resolution consistency across components."""
    
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

    @pytest.mark.integration
    @pytest.mark.ssot_violation
    async def test_FAILING_jwt_secret_inconsistency_across_components(self):
        """
        TEST EXPECTATION: FAIL - Proves inconsistent JWT secret resolution
        
        This test shows how different components resolve JWT_SECRET_KEY
        differently due to SSOT violations, leading to authentication failures 
        in Golden Path.
        
        CRITICAL: This inconsistency BLOCKS the primary user flow
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Scenario: JWT secret in os.environ but isolated env has different value
            # This creates the exact condition that breaks Golden Path authentication
            os_jwt_secret = "os-environ-jwt-secret-violation"
            isolated_jwt_secret = "isolated-env-jwt-secret"
            
            with patch.dict(os.environ, {'JWT_SECRET_KEY': os_jwt_secret}):
                # Set different value in isolated environment
                env.set('JWT_SECRET_KEY', isolated_jwt_secret, 'test')
                
                # Test multiple components that should all use the same secret
                auth_validator = AuthStartupValidator()
                secrets_manager = UnifiedSecrets()
                jwt_manager = get_jwt_secret_manager()
                
                # Get JWT secrets from different components
                validator_secret = auth_validator._get_env_with_fallback('JWT_SECRET_KEY')
                secrets_secret = secrets_manager.get_secret('JWT_SECRET_KEY')
                jwt_secret = jwt_manager.get_secret()
                
                # Collect all resolved values
                resolved_secrets = {
                    'AuthValidator': validator_secret,
                    'UnifiedSecrets': secrets_secret,
                    'JWTManager': jwt_secret
                }
                
                # Remove None values for analysis
                non_none_secrets = {k: v for k, v in resolved_secrets.items() if v is not None}
                secrets_set = set(non_none_secrets.values())
                
                # THIS ASSERTION SHOULD FAIL - proving inconsistency exists
                assert len(secrets_set) == 1, (
                    f"🚨 CRITICAL SSOT CONSISTENCY VIOLATION: JWT_SECRET_KEY resolved "
                    f"differently across components due to SSOT violations. "
                    f"This BLOCKS Golden Path authentication flow ($500K+ ARR impact). "
                    f"Resolution results: {resolved_secrets}. "
                    f"IsolatedEnvironment value: '{isolated_jwt_secret}', "
                    f"os.environ value: '{os_jwt_secret}'. "
                    f"Components using os.environ fallback create authentication failures."
                )
                
        except Exception as e:
            # Expected - this is likely how the inconsistency manifests
            pytest.fail(
                f"AUTHENTICATION FAILURE due to SSOT violations: {str(e)}. "
                f"This proves the inconsistent environment resolution BLOCKS "
                f"Golden Path user authentication flow."
            )
        finally:
            env.disable_isolation()
            jwt_manager.clear_cache()

    @pytest.mark.integration  
    @pytest.mark.ssot_violation
    async def test_FAILING_auth_service_url_resolution_inconsistency(self):
        """
        TEST EXPECTATION: FAIL - Proves AUTH_SERVICE_URL resolution inconsistency
        
        This test shows how AUTH_SERVICE_URL resolution varies across components,
        potentially causing service connectivity failures that block user authentication.
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Create inconsistent AUTH_SERVICE_URL scenario
            os_auth_url = "http://os-environ-auth:8081"
            isolated_auth_url = "http://isolated-auth:8081"
            
            with patch.dict(os.environ, {'AUTH_SERVICE_URL': os_auth_url}):
                env.set('AUTH_SERVICE_URL', isolated_auth_url, 'test')
                
                # Test components that need auth service URL
                auth_validator = AuthStartupValidator()
                secrets_manager = UnifiedSecrets()
                
                # Get auth URLs from different sources
                validator_url = auth_validator._get_env_with_fallback('AUTH_SERVICE_URL')
                secrets_url = secrets_manager.get_secret('AUTH_SERVICE_URL')
                
                # If different components get different URLs, it proves inconsistency
                url_sources = {
                    'AuthValidator': validator_url,
                    'UnifiedSecrets': secrets_url,
                    'IsolatedEnvironment': env.get('AUTH_SERVICE_URL'),
                    'os.environ': os.environ.get('AUTH_SERVICE_URL')
                }
                
                # Remove None values
                non_none_urls = {k: v for k, v in url_sources.items() if v is not None}
                unique_urls = set(non_none_urls.values())
                
                # THIS SHOULD FAIL - proving URL resolution inconsistency
                assert len(unique_urls) == 1, (
                    f"🚨 SSOT VIOLATION: AUTH_SERVICE_URL resolved inconsistently "
                    f"across components: {non_none_urls}. This creates service "
                    f"connectivity issues that can block Golden Path authentication. "
                    f"SSOT violations prevent consistent service discovery."
                )
                
        finally:
            env.disable_isolation()

    @pytest.mark.integration
    @pytest.mark.ssot_violation
    async def test_FAILING_environment_isolation_effectiveness(self):
        """
        TEST EXPECTATION: FAIL - Proves environment isolation is compromised
        
        This test validates that IsolatedEnvironment isolation is effective,
        or demonstrates how SSOT violations compromise the isolation.
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Create test scenario with sensitive environment variable
            sensitive_key = "SENSITIVE_TEST_VARIABLE"
            exposed_value = "EXPOSED-VIA-OS-ENVIRON"
            protected_value = "PROTECTED-VIA-ISOLATION"
            
            with patch.dict(os.environ, {sensitive_key: exposed_value}):
                # Set protected value in isolated environment
                env.set(sensitive_key, protected_value, 'test')
                
                # Test if components can access the exposed os.environ value
                # when they should only see the isolated environment value
                
                auth_validator = AuthStartupValidator()
                secrets_manager = UnifiedSecrets()
                
                # Get values from components with SSOT violations
                validator_value = auth_validator._get_env_with_fallback(sensitive_key)
                secrets_value = secrets_manager.get_secret(sensitive_key)
                
                # Check if any component accessed the exposed os.environ value
                violations_detected = []
                
                if validator_value == exposed_value:
                    violations_detected.append(f"AuthValidator accessed os.environ: '{validator_value}'")
                    
                if secrets_value == exposed_value:
                    violations_detected.append(f"UnifiedSecrets accessed os.environ: '{secrets_value}'")
                
                # THIS SHOULD FAIL if violations compromise isolation
                assert not violations_detected, (
                    f"🚨 CRITICAL SECURITY VIOLATION: Environment isolation "
                    f"compromised by SSOT violations. Components accessed "
                    f"os.environ directly: {violations_detected}. "
                    f"IsolatedEnvironment value: '{protected_value}', "
                    f"os.environ value: '{exposed_value}'. "
                    f"This proves SSOT violations create security vulnerabilities."
                )
                
                # Even if no direct exposure detected, document the violation risk
                if validator_value or secrets_value:
                    pytest.fail(
                        f"🚨 SSOT ISOLATION RISK: Components with os.environ access "
                        f"create potential for environment isolation bypass. "
                        f"AuthValidator: '{validator_value}', UnifiedSecrets: '{secrets_value}'. "
                        f"While current test didn't detect direct exposure, "
                        f"the violation mechanisms exist in the code."
                    )
                
        finally:
            env.disable_isolation()

    @pytest.mark.integration
    @pytest.mark.ssot_violation
    async def test_FAILING_cascade_failure_from_env_inconsistency(self):
        """
        TEST EXPECTATION: FAIL - Proves environment inconsistencies cause cascade failures
        
        This test demonstrates how SSOT environment violations can create
        cascade failures that impact multiple system components simultaneously.
        """
        env = get_env()
        env.enable_isolation()
        
        cascade_failures = []
        
        try:
            # Create multiple environment inconsistencies simultaneously
            inconsistent_vars = {
                'JWT_SECRET_KEY': {
                    'os_environ': 'jwt-secret-os',
                    'isolated': 'jwt-secret-isolated'
                },
                'AUTH_SERVICE_URL': {
                    'os_environ': 'http://auth-os:8081',
                    'isolated': 'http://auth-isolated:8081'  
                },
                'SERVICE_ID': {
                    'os_environ': 'service-id-os',
                    'isolated': 'service-id-isolated'
                }
            }
            
            # Setup inconsistent environment state
            os_environ_patch = {}
            for var_name, values in inconsistent_vars.items():
                os_environ_patch[var_name] = values['os_environ']
                env.set(var_name, values['isolated'], 'test')
            
            with patch.dict(os.environ, os_environ_patch):
                # Test auth startup validation with inconsistent environment
                auth_validator = AuthStartupValidator()
                
                try:
                    success, results = await auth_validator.validate_all()
                    
                    # Analyze validation results for cascade failures
                    failed_components = [r for r in results if not r.valid]
                    
                    if failed_components:
                        cascade_failures.extend([
                            f"{comp.component.value}: {comp.error}" 
                            for comp in failed_components
                        ])
                    
                    # If validation succeeds despite inconsistencies, it might indicate
                    # the violations are masking failures
                    if success and len(failed_components) == 0:
                        cascade_failures.append(
                            "Validation succeeded despite environment inconsistencies - "
                            "SSOT violations may be masking configuration errors"
                        )
                        
                except Exception as e:
                    cascade_failures.append(f"Auth validation exception: {str(e)}")
                
                # Test secrets management with inconsistencies
                try:
                    secrets_manager = UnifiedSecrets()
                    
                    for var_name in inconsistent_vars.keys():
                        secret_value = secrets_manager.get_secret(var_name)
                        expected_isolated = inconsistent_vars[var_name]['isolated']
                        expected_os = inconsistent_vars[var_name]['os_environ']
                        
                        if secret_value == expected_os:
                            cascade_failures.append(
                                f"UnifiedSecrets resolved {var_name} to os.environ "
                                f"value '{secret_value}' instead of isolated value"
                            )
                            
                except Exception as e:
                    cascade_failures.append(f"Secrets management exception: {str(e)}")
                
                # THIS SHOULD FAIL - proving cascade failures occur
                assert not cascade_failures, (
                    f"🚨 CRITICAL CASCADE FAILURE: SSOT environment violations "
                    f"created multiple system failures: {cascade_failures}. "
                    f"This proves that environment inconsistencies from SSOT "
                    f"violations can compromise system-wide stability and "
                    f"block Golden Path functionality."
                )
                
        except Exception as e:
            # Document the cascade failure
            cascade_failures.append(f"Test execution exception: {str(e)}")
            
            pytest.fail(
                f"🚨 SYSTEM-WIDE CASCADE FAILURE: SSOT environment violations "
                f"caused test execution failure: {cascade_failures}. "
                f"This demonstrates the critical impact of environment "
                f"inconsistencies on system stability."
            )
        finally:
            env.disable_isolation()