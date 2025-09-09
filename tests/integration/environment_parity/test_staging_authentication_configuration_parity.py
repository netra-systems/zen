"""
Environment Parity Test: Staging Authentication Configuration

Tests to validate authentication configuration gaps between environments
that are blocking the Golden Path. Focuses on SERVICE_ID missing from 
staging docker-compose and hardcoded system user authentication failures.

CRITICAL: These tests MUST FAIL initially to demonstrate the authentication issues.
"""
import os
import pytest
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from shared.isolated_environment import IsolatedEnvironment

# Configure logging for authentication diagnostics
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestStagingAuthenticationConfigurationParity:
    """
    Environment parity tests for staging authentication configuration.
    
    These tests validate that authentication configuration is properly
    aligned across environments. Initial runs SHOULD FAIL to demonstrate
    the current authentication configuration gaps.
    """
    
    @pytest.fixture(scope="class")
    def isolated_env(self):
        """Isolated environment for testing configuration consistency."""
        return IsolatedEnvironment()

    def test_service_id_present_in_staging_docker_compose(self, isolated_env):
        """
        Test that SERVICE_ID is present in staging docker-compose configuration.
        
        EXPECTED TO FAIL: This test should fail initially because SERVICE_ID
        is missing from the staging docker-compose.yml file.
        """
        logger.info("Testing SERVICE_ID presence in staging docker-compose")
        
        # Check if staging docker-compose file exists
        project_root = Path.cwd()
        staging_compose_file = project_root / "docker-compose.staging.yml"
        
        assert staging_compose_file.exists(), f"Staging docker-compose file not found: {staging_compose_file}"
        
        # Read the staging compose file
        compose_content = staging_compose_file.read_text()
        logger.debug(f"Staging compose content length: {len(compose_content)} characters")
        
        # Check for SERVICE_ID in backend service environment
        assert "SERVICE_ID" in compose_content, (
            "SERVICE_ID is missing from staging docker-compose.yml. "
            "This configuration gap causes authentication failures in staging environment."
        )
        
        # Verify SERVICE_ID is set for backend service specifically
        lines = compose_content.split('\n')
        in_backend_service = False
        in_environment_section = False
        service_id_found = False
        
        for line in lines:
            if 'backend:' in line:
                in_backend_service = True
            elif in_backend_service and 'environment:' in line:
                in_environment_section = True
            elif in_backend_service and in_environment_section:
                if 'SERVICE_ID' in line:
                    service_id_found = True
                    break
                # Reset if we hit another service or section
                if line.strip() and not line.startswith(' ') and not line.startswith('-'):
                    break
        
        assert service_id_found, (
            "SERVICE_ID not found in backend service environment section of staging docker-compose.yml. "
            "This is the root cause of system user authentication failures."
        )

    def test_hardcoded_system_user_in_dependencies(self):
        """
        Test that dependencies.py does not use hardcoded 'system' user_id.
        
        EXPECTED TO FAIL: This test should fail because dependencies.py
        uses hardcoded "system" user_id which causes 403 authentication errors.
        """
        logger.info("Testing for hardcoded system user in dependencies.py")
        
        # Find all dependencies.py files
        project_root = Path.cwd()
        dependencies_files = []
        
        for deps_file in project_root.rglob("dependencies.py"):
            if not any(skip in str(deps_file) for skip in ['.git', '__pycache__', 'node_modules']):
                dependencies_files.append(deps_file)
        
        assert dependencies_files, "No dependencies.py files found in project"
        
        hardcoded_system_user_found = False
        problematic_files = []
        
        for deps_file in dependencies_files:
            content = deps_file.read_text()
            
            # Check for hardcoded "system" user_id patterns
            if 'user_id="system"' in content or "user_id='system'" in content:
                hardcoded_system_user_found = True
                problematic_files.append(str(deps_file))
                logger.error(f"Found hardcoded 'system' user_id in: {deps_file}")
        
        assert not hardcoded_system_user_found, (
            f"Hardcoded 'system' user_id found in dependencies files: {problematic_files}. "
            "This causes 403 authentication errors because 'system' is not a valid authenticated user_id. "
            "System operations should use proper service authentication or dynamic user context."
        )

    def test_system_user_authentication_with_real_services(self, auth_helper, docker_helper, service_validator):
        """
        Test system user authentication with real services running.
        
        EXPECTED TO FAIL: This test should fail because system operations
        cannot authenticate properly due to configuration gaps.
        """
        start_time = time.time()
        logger.info("Testing system user authentication with real services")
        
        # Ensure services are running
        services_ready = docker_helper.ensure_services_running(['backend', 'auth', 'redis', 'postgres'])
        assert services_ready, "Failed to start required services for authentication testing"
        
        # Validate service connectivity
        backend_healthy = service_validator.validate_service_health('backend')
        auth_healthy = service_validator.validate_service_health('auth')
        
        logger.debug(f"Backend health: {backend_healthy}, Auth health: {auth_healthy}")
        
        # Attempt system user authentication
        try:
            # Try to create an authenticated context for system operations
            system_context = auth_helper.create_authenticated_context(
                user_id=UserID("system"),
                request_id=RequestID("test-system-auth-001")
            )
            
            # If we get here, system auth is working (test should pass)
            assert system_context is not None, "System authentication should work for internal operations"
            
        except Exception as e:
            # Expected failure - system user authentication fails
            logger.error(f"System user authentication failed as expected: {e}")
            pytest.fail(
                f"System user authentication failed: {e}. "
                "This demonstrates the authentication configuration gap that's blocking the Golden Path. "
                "System operations require proper service authentication configuration."
            )
        
        execution_time = time.time() - start_time
        logger.info(f"System authentication test completed in {execution_time:.2f} seconds")

    def test_service_to_service_authentication_configuration(self, isolated_env, docker_helper):
        """
        Test service-to-service authentication configuration.
        
        EXPECTED TO FAIL: This test validates that services can authenticate
        with each other for internal operations.
        """
        logger.info("Testing service-to-service authentication configuration")
        
        # Check for service authentication environment variables
        required_service_auth_vars = [
            'SERVICE_ID',
            'SERVICE_SECRET',
            'JWT_SECRET_KEY'
        ]
        
        missing_vars = []
        for var in required_service_auth_vars:
            try:
                value = isolated_env.get_env_var(var)
                if not value:
                    missing_vars.append(var)
            except Exception as e:
                missing_vars.append(var)
                logger.error(f"Failed to get {var}: {e}")
        
        assert not missing_vars, (
            f"Missing service authentication environment variables: {missing_vars}. "
            "These are required for proper service-to-service authentication. "
            "Without these, internal operations fail with 403 errors."
        )

    def test_staging_authentication_performance_baseline(self, auth_helper):
        """
        Establish performance baseline for authentication operations in staging.
        
        This test measures current authentication performance to establish
        a baseline for comparison after fixes are applied.
        """
        logger.info("Establishing authentication performance baseline")
        
        # Measure multiple authentication attempts
        auth_times = []
        
        for i in range(5):
            start_time = time.time()
            
            try:
                # Attempt authentication operation
                test_user_id = UserID(f"test-user-{i}")
                request_id = RequestID(f"perf-baseline-{i}")
                
                context = auth_helper.create_authenticated_context(
                    user_id=test_user_id,
                    request_id=request_id
                )
                
                auth_time = time.time() - start_time
                auth_times.append(auth_time)
                logger.debug(f"Auth attempt {i+1} took {auth_time:.3f} seconds")
                
            except Exception as e:
                auth_time = time.time() - start_time
                auth_times.append(auth_time)  # Include failed attempts in timing
                logger.error(f"Auth attempt {i+1} failed in {auth_time:.3f} seconds: {e}")
        
        # Calculate baseline metrics
        avg_auth_time = sum(auth_times) / len(auth_times)
        max_auth_time = max(auth_times)
        min_auth_time = min(auth_times)
        
        logger.info(f"Authentication performance baseline:")
        logger.info(f"  Average: {avg_auth_time:.3f} seconds")
        logger.info(f"  Min: {min_auth_time:.3f} seconds")
        logger.info(f"  Max: {max_auth_time:.3f} seconds")
        
        # Store baseline for comparison (this test documents current state)
        baseline_data = {
            'average_auth_time': avg_auth_time,
            'max_auth_time': max_auth_time,
            'min_auth_time': min_auth_time,
            'total_attempts': len(auth_times),
            'timestamp': time.time()
        }
        
        # For now, just log the baseline - future tests can compare against this
        logger.info(f"Authentication baseline established: {baseline_data}")
        
        # This test always passes - it's just establishing a baseline
        assert True, f"Authentication performance baseline established: {baseline_data}"

    def test_docker_compose_environment_variable_consistency(self):
        """
        Test consistency of environment variables across docker-compose files.
        
        This validates that critical authentication variables are consistently
        defined across different environment configurations.
        """
        logger.info("Testing docker-compose environment variable consistency")
        
        project_root = Path.cwd()
        compose_files = [
            'docker-compose.yml',
            'docker-compose.staging.yml', 
            'docker-compose.alpine.yml',
            'docker-compose.alpine-test.yml'
        ]
        
        critical_auth_vars = ['SERVICE_ID', 'SERVICE_SECRET', 'JWT_SECRET_KEY']
        
        compose_configs = {}
        for compose_file in compose_files:
            file_path = project_root / compose_file
            if file_path.exists():
                content = file_path.read_text()
                compose_configs[compose_file] = content
                logger.debug(f"Loaded {compose_file}: {len(content)} characters")
        
        # Check each critical variable across compose files
        missing_vars_by_file = {}
        
        for compose_file, content in compose_configs.items():
            missing_vars = []
            for var in critical_auth_vars:
                if var not in content:
                    missing_vars.append(var)
            
            if missing_vars:
                missing_vars_by_file[compose_file] = missing_vars
        
        assert not missing_vars_by_file, (
            f"Critical authentication variables missing from compose files: {missing_vars_by_file}. "
            "Environment variable consistency is required for proper authentication across environments."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])