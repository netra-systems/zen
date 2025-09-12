"""
Docker Compose Configuration Validation for Issue #115

Business Value Justification (BVJ):
- Segment: Platform/Internal (System Stability)
- Business Goal: Validate docker-compose.staging.yml configuration fix for SERVICE_ID/SECRET
- Value Impact: Ensures proper service authentication configuration in staging environment
- Strategic Impact: Critical for confirming Issue #115 resolution and preventing regression

This test validates that the configuration fix was properly applied to docker-compose.staging.yml.
"""

import pytest
import yaml
from pathlib import Path


class TestDockerComposeConfigValidation:
    """Validate docker-compose.staging.yml configuration fix for Issue #115."""
    
    def test_staging_backend_has_service_id_configured(self):
        """Test that backend service has SERVICE_ID configured correctly.
        
        This test validates the first part of the Issue #115 fix.
        Should FAIL initially, then PASS after adding SERVICE_ID to docker-compose.staging.yml.
        """
        staging_compose_path = Path("/Users/anthony/Documents/GitHub/netra-apex/docker-compose.staging.yml")
        
        with open(staging_compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        backend_env = compose_config['services']['backend']['environment']
        
        # Validate SERVICE_ID is present and correct
        assert 'SERVICE_ID' in backend_env, (
            "SERVICE_ID must be added to docker-compose.staging.yml backend environment. "
            "This is required to fix Issue #115 - System User Authentication Failure. "
            "Add: SERVICE_ID: netra-backend"
        )
        
        assert backend_env['SERVICE_ID'] == 'netra-backend', (
            f"SERVICE_ID should be 'netra-backend' (hardcoded stable value), "
            f"got: '{backend_env['SERVICE_ID']}'. "
            f"This ensures consistent service identification across all environments."
        )
    
    def test_staging_backend_has_service_secret_configured(self):
        """Test that backend service has SERVICE_SECRET configured correctly.
        
        This test validates the second part of the Issue #115 fix.
        Should FAIL initially, then PASS after adding SERVICE_SECRET to docker-compose.staging.yml.
        """
        staging_compose_path = Path("/Users/anthony/Documents/GitHub/netra-apex/docker-compose.staging.yml")
        
        with open(staging_compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        backend_env = compose_config['services']['backend']['environment']
        
        # Validate SERVICE_SECRET is present
        assert 'SERVICE_SECRET' in backend_env, (
            "SERVICE_SECRET must be added to docker-compose.staging.yml backend environment. "
            "This is required to fix Issue #115 - System User Authentication Failure. "
            "Add: SERVICE_SECRET: <secure_secret_32_chars_minimum>"
        )
        
        service_secret = backend_env['SERVICE_SECRET']
        assert isinstance(service_secret, str) and len(service_secret) >= 32, (
            f"SERVICE_SECRET should be at least 32 characters for security, "
            f"got: {len(service_secret) if isinstance(service_secret, str) else 'non-string'}. "
            f"Use a secure secret like: staging_service_secret_secure_32_chars_minimum_2024"
        )
    
    def test_service_secret_different_from_jwt_secret(self):
        """Test that SERVICE_SECRET is different from JWT_SECRET_KEY for security isolation.
        
        This validates proper security isolation between service auth and JWT auth.
        """
        staging_compose_path = Path("/Users/anthony/Documents/GitHub/netra-apex/docker-compose.staging.yml")
        
        with open(staging_compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        backend_env = compose_config['services']['backend']['environment']
        
        # Both should be present for this test
        if 'SERVICE_SECRET' not in backend_env:
            pytest.skip("SERVICE_SECRET not configured yet - run after Issue #115 fix")
        
        service_secret = backend_env['SERVICE_SECRET']
        jwt_secret = backend_env.get('JWT_SECRET_KEY', '')
        
        assert service_secret != jwt_secret, (
            "SERVICE_SECRET should be different from JWT_SECRET_KEY for security isolation. "
            "Service authentication and JWT authentication should use separate secrets. "
            f"Both currently have the same value."
        )
    
    def test_auth_service_has_matching_service_secret(self):
        """Test that auth service has matching SERVICE_SECRET for cross-service authentication.
        
        This validates that both backend and auth services can authenticate with each other.
        """
        staging_compose_path = Path("/Users/anthony/Documents/GitHub/netra-apex/docker-compose.staging.yml")
        
        with open(staging_compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        backend_env = compose_config['services']['backend']['environment']
        auth_env = compose_config['services']['auth']['environment']
        
        # Skip if backend SERVICE_SECRET not configured yet
        if 'SERVICE_SECRET' not in backend_env:
            pytest.skip("Backend SERVICE_SECRET not configured yet - run after Issue #115 fix")
        
        backend_service_secret = backend_env['SERVICE_SECRET']
        auth_service_secret = auth_env.get('SERVICE_SECRET')
        
        # Auth service should also have SERVICE_SECRET for validation
        assert auth_service_secret is not None, (
            "Auth service should have SERVICE_SECRET configured to validate backend requests. "
            "Add SERVICE_SECRET to auth service environment with the same value as backend."
        )
        
        assert backend_service_secret == auth_service_secret, (
            f"Backend and auth services should have matching SERVICE_SECRET for cross-service auth. "
            f"Backend: '{backend_service_secret}', Auth: '{auth_service_secret}'"
        )
    
    def test_all_required_auth_variables_present(self):
        """Test that all required authentication variables are present for Issue #115 fix.
        
        This is a comprehensive validation of the complete authentication configuration.
        """
        staging_compose_path = Path("/Users/anthony/Documents/GitHub/netra-apex/docker-compose.staging.yml")
        
        with open(staging_compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        backend_env = compose_config['services']['backend']['environment']
        
        required_auth_vars = {
            'SERVICE_ID': 'netra-backend',
            'SERVICE_SECRET': lambda x: isinstance(x, str) and len(x) >= 32,
            'JWT_SECRET_KEY': lambda x: isinstance(x, str) and len(x) >= 32,
        }
        
        missing_vars = []
        invalid_vars = []
        
        for var_name, expected_value in required_auth_vars.items():
            if var_name not in backend_env:
                missing_vars.append(var_name)
                continue
            
            actual_value = backend_env[var_name]
            
            if callable(expected_value):
                # Validation function
                if not expected_value(actual_value):
                    invalid_vars.append(f"{var_name}: {actual_value}")
            else:
                # Exact value check
                if actual_value != expected_value:
                    invalid_vars.append(f"{var_name}: expected '{expected_value}', got '{actual_value}'")
        
        assert not missing_vars, (
            f"Missing required authentication variables in docker-compose.staging.yml backend environment: "
            f"{', '.join(missing_vars)}. These are required to fix Issue #115."
        )
        
        assert not invalid_vars, (
            f"Invalid authentication variables in docker-compose.staging.yml backend environment: "
            f"{', '.join(invalid_vars)}. Check configuration requirements."
        )


class TestServiceAuthConfigurationRegression:
    """Regression prevention tests for service authentication configuration."""
    
    def test_no_dynamic_service_id_generation(self):
        """Test that SERVICE_ID is not dynamically generated (prevents regression).
        
        Dynamic SERVICE_ID generation causes authentication failures.
        SERVICE_ID must always be the hardcoded value 'netra-backend'.
        """
        staging_compose_path = Path("/Users/anthony/Documents/GitHub/netra-apex/docker-compose.staging.yml")
        
        with open(staging_compose_path, 'r') as f:
            compose_content = f.read()
        
        # Check for problematic dynamic generation patterns
        dynamic_patterns = [
            '${', 'timestamp', 'date', 'time', 'uuid', 'random', 'env:', '${'
        ]
        
        service_id_line = None
        for line_num, line in enumerate(compose_content.split('\n'), 1):
            if 'SERVICE_ID' in line and ':' in line:
                service_id_line = (line_num, line.strip())
                break
        
        if service_id_line:
            line_num, line_content = service_id_line
            for pattern in dynamic_patterns:
                assert pattern not in line_content, (
                    f"SERVICE_ID configuration at line {line_num} contains dynamic pattern '{pattern}': {line_content}. "
                    f"SERVICE_ID must be hardcoded as 'netra-backend' to prevent authentication failures. "
                    f"Dynamic generation causes service identification mismatches."
                )
    
    def test_service_secret_not_empty_or_placeholder(self):
        """Test that SERVICE_SECRET is not empty or a placeholder value.
        
        Prevents configuration with dummy/placeholder values that cause auth failures.
        """
        staging_compose_path = Path("/Users/anthony/Documents/GitHub/netra-apex/docker-compose.staging.yml")
        
        with open(staging_compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        backend_env = compose_config['services']['backend']['environment']
        
        if 'SERVICE_SECRET' not in backend_env:
            pytest.skip("SERVICE_SECRET not configured yet - run after Issue #115 fix")
        
        service_secret = backend_env['SERVICE_SECRET']
        
        # Check for placeholder/dummy values
        invalid_values = [
            '', 'changeme', 'placeholder', 'todo', 'fixme', 'temp', 'test',
            'secret', 'password', 'key', 'replace', 'update'
        ]
        
        service_secret_lower = service_secret.lower()
        for invalid_value in invalid_values:
            assert invalid_value not in service_secret_lower, (
                f"SERVICE_SECRET appears to contain placeholder value '{invalid_value}': {service_secret}. "
                f"Use a proper secure secret for staging environment. "
                f"Example: staging_service_secret_secure_32_chars_minimum_2024"
            )
        
        # Should not be overly simple patterns
        assert not service_secret.isdigit(), (
            f"SERVICE_SECRET should not be only digits: {service_secret}. "
            f"Use a complex alphanumeric secret for security."
        )
        
        assert not service_secret.isalpha(), (
            f"SERVICE_SECRET should not be only letters: {service_secret}. "
            f"Use a complex alphanumeric secret for security."
        )


if __name__ == "__main__":
    print("[U+1F527] Running Docker Compose Configuration Validation for Issue #115")
    print("This validates the configuration fix in docker-compose.staging.yml")
    print("=" * 70)
    
    pytest.main([__file__, "-v", "--tb=short"])