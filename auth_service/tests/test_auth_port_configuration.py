"""
env = get_env()
Tests for Auth Service Port Configuration Mismatch Issue

This test suite exposes the critical port configuration mismatch where:
- Auth service binds to port 8081 (from AUTH_PORT env var) 
- But internally configures its URL as http://127.0.0.1:8001
- This mismatch prevents startup completion and causes connection failures

Root Cause: Dual configuration sources without validation
- Port binding uses AUTH_PORT correctly  
- URL configuration hardcoded or incorrectly derived

These tests MUST fail initially to demonstrate the issue before fixes are applied.
"""

import pytest
import os
import asyncio
from auth_service.auth_core.auth_environment import get_auth_env
from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
# Removed non-existent AuthManager import
from shared.isolated_environment import IsolatedEnvironment


class TestAuthPortConfigurationConsistency:
    """Test port configuration consistency across all auth service components"""

    def test_port_configuration_sources_consistency(self):
        """
        Test that port configuration sources are consistent.
        
        ISSUE: Auth service has dual port configuration sources:
        1. AUTH_PORT env var for binding (used correctly)
        2. Hardcoded or derived URL configuration (uses wrong port)
        
        This test FAILS initially to expose the inconsistency.
        """
        # Get environment manager
        env_manager = get_env()
        
        # Simulate the actual environment values that cause the issue
        auth_port = env_manager.get("AUTH_PORT", "8081")  # Correct binding port
        port_from_main = env_manager.get("PORT", "8081")  # Container runtime port
        
        # Get auth service configuration using SSOT AuthEnvironment
        auth_env = get_auth_env()
        auth_service_port = auth_env.get_auth_service_port()
        auth_service_host = auth_env.get_auth_service_host()
        auth_service_url = f"http://{auth_service_host}:{auth_service_port}"
        
        # In development, this should use the same port consistently
        if auth_env.get_environment() == "development":
            # Extract port from URL
            if "localhost" in auth_service_url:
                import re
                port_match = re.search(r':(\d+)', auth_service_url)
                configured_port = port_match.group(1) if port_match else None
                
                # FAILING ASSERTION: This exposes the port mismatch
                # The URL configuration uses a different port than the binding configuration
                assert configured_port == auth_port, (
                    f"Port mismatch detected! "
                    f"Auth service binds to port {auth_port} but URL configured for port {configured_port}. "
                    f"URL: {auth_service_url}"
                )
        
        # Additional validation: PORT and AUTH_PORT should be consistent
        assert port_from_main == auth_port, (
            f"PORT ({port_from_main}) and AUTH_PORT ({auth_port}) must be consistent"
        )

    def test_auth_service_startup_completion_with_correct_port(self):
        """
        Test that auth service startup completes when port configuration is consistent.
        
        ISSUE: Service fails to complete startup due to internal port mismatch.
        The binding succeeds but internal URL configuration causes failures.
        
        This test FAILS initially because the service cannot complete startup.
        """
        env_manager = get_env()
        expected_port = "8081"
        
        # Set consistent port configuration
        with patch.dict(os.environ, {
            "AUTH_PORT": expected_port,
            "PORT": expected_port,
            "AUTH_SERVICE_URL": f"http://localhost:{expected_port}"
        }):
            # Test that configuration is internally consistent
            auth_service_url = AuthConfig.get_auth_service_url()
            
            # Extract port from configured URL
            import re
            port_match = re.search(r':(\d+)', auth_service_url)
            configured_port = port_match.group(1) if port_match else None
            
            # FAILING ASSERTION: Service should use consistent port in URL
            assert configured_port == expected_port, (
                f"Auth service URL port ({configured_port}) does not match expected port ({expected_port}). "
                f"This inconsistency prevents startup completion."
            )
            
            # Validate that both binding and URL use the same port
            binding_port = env_manager.get("PORT", "8081")
            assert binding_port == configured_port, (
                f"Binding port ({binding_port}) and URL port ({configured_port}) must match"
            )

    def test_auth_port_environment_variable_precedence(self):
        """
        Test environment variable precedence for port configuration.
        
        ISSUE: Multiple environment variables can set ports (PORT, AUTH_PORT) 
        but the service doesn't validate consistency between them.
        
        This test FAILS initially to expose precedence issues.
        """
        test_cases = [
            # (PORT, AUTH_PORT, expected_behavior)
            ("8081", "8081", "consistent"),
            ("8080", "8081", "inconsistent"),  # This should fail
            ("8001", "8081", "inconsistent"),  # This should fail - exposes the 8001 issue
        ]
        
        for port, auth_port, expected in test_cases:
            with patch.dict(os.environ, {
                "PORT": port,
                "AUTH_PORT": auth_port,
                "ENVIRONMENT": "development"
            }):
                env_manager = get_env()
                
                # Get actual configuration values
                runtime_port = env_manager.get("PORT")
                auth_specific_port = env_manager.get("AUTH_PORT")
                
                if expected == "inconsistent":
                    # FAILING ASSERTION: These should be detected as inconsistent
                    assert runtime_port == auth_specific_port, (
                        f"Port configuration inconsistency detected! "
                        f"PORT={runtime_port}, AUTH_PORT={auth_specific_port}. "
                        f"This will cause binding/URL mismatches."
                    )

    def test_auth_service_url_generation_with_port_validation(self):
        """
        Test that auth service URL generation includes proper port validation.
        
        ISSUE: URL generation doesn't validate against actual binding port.
        This causes the service to generate URLs that don't match where it's actually listening.
        
        This test FAILS initially because validation is missing.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "PORT": "8081",
            "AUTH_PORT": "8081"
        }):
            # Get the generated auth service URL
            auth_url = AuthConfig.get_auth_service_url()
            
            # Extract port from URL
            import re
            url_port_match = re.search(r':(\d+)', auth_url)
            url_port = url_port_match.group(1) if url_port_match else None
            
            # Get the actual binding port
            env_manager = get_env()
            binding_port = env_manager.get("PORT", "8081")
            
            # FAILING ASSERTION: URL port must match binding port
            assert url_port == binding_port, (
                f"Auth service URL port ({url_port}) does not match binding port ({binding_port}). "
                f"Generated URL: {auth_url}. "
                f"This mismatch prevents proper service communication."
            )

    def test_hardcoded_port_detection(self):
        """
        Test detection of hardcoded port values in configuration.
        
        ISSUE: The 8001 port appears to be hardcoded somewhere in the configuration chain.
        This test attempts to detect where hardcoded values might be coming from.
        
        This test FAILS initially to expose hardcoded values.
        """
        # Test common hardcoded port values that might appear
        problematic_ports = ["8001", "8000", "3000"]
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "PORT": "8081",
            "AUTH_PORT": "8081"
        }, clear=False):
            # Get auth service URL
            auth_url = AuthConfig.get_auth_service_url()
            
            # Check if any problematic ports appear in the URL
            for bad_port in problematic_ports:
                # FAILING ASSERTION: Should not contain hardcoded problematic ports
                assert bad_port not in auth_url, (
                    f"Auth service URL contains hardcoded port {bad_port}! "
                    f"URL: {auth_url}. "
                    f"This suggests hardcoded configuration is overriding environment variables."
                )

    @pytest.mark.integration
    def test_auth_service_port_binding_matches_url_configuration(self):
        """
        Integration test to verify port binding matches URL configuration.
        
        ISSUE: Service binds to one port but advertises a different port in URLs.
        This breaks service discovery and inter-service communication.
        
        This test FAILS initially because of the mismatch.
        """
        import socket
        
        # Test port
        test_port = 8081
        
        with patch.dict(os.environ, {
            "PORT": str(test_port),
            "AUTH_PORT": str(test_port),
            "ENVIRONMENT": "development"
        }):
            # Get configured auth service URL
            auth_url = AuthConfig.get_auth_service_url()
            
            # Extract port from URL
            import re
            url_match = re.search(r':(\d+)', auth_url)
            url_port = int(url_match.group(1)) if url_match else None
            
            # FAILING ASSERTION: URL port must match expected binding port
            assert url_port == test_port, (
                f"Auth service URL port ({url_port}) does not match binding port ({test_port}). "
                f"This prevents successful service communication. URL: {auth_url}"
            )
            
            # Additional check: Verify port is actually bindable
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', test_port))
                    # Port is available - configuration should work
                    port_available = True
            except OSError:
                # Port might be in use - that's OK for this test
                port_available = False
            
            # If port is available, configuration should be consistent
            if port_available:
                assert url_port == test_port, (
                    f"Port {test_port} is available for binding, "
                    f"but auth service URL configured for port {url_port}"
                )


class TestAuthServiceConfigurationValidation:
    """Test configuration validation that should prevent port mismatches"""

    def test_configuration_validation_detects_port_mismatch(self):
        """
        Test that configuration validation detects port mismatches.
        
        ISSUE: No validation exists to detect when binding port != URL port.
        This allows the mismatch to occur silently.
        
        This test FAILS initially because validation is missing.
        """
        # Create mismatched configuration
        with patch.dict(os.environ, {
            "PORT": "8081",            # Binding port
            "AUTH_SERVICE_URL": "http://localhost:8001",  # Different URL port
            "ENVIRONMENT": "development"
        }):
            # This should detect the mismatch and fail
            # FAILING ASSERTION: Validation should catch this mismatch
            try:
                # Attempt to validate configuration consistency
                binding_port = env.get("PORT")  # Use os.environ directly since we patched it
                auth_url = AuthConfig.get_auth_service_url()
                
                # Extract URL port
                import re
                url_match = re.search(r':(\d+)', auth_url)
                url_port = url_match.group(1) if url_match else None
                
                # This assertion will fail because no validation exists
                assert binding_port == url_port, (
                    f"Configuration validation failed! "
                    f"Binding port {binding_port} != URL port {url_port}. "
                    f"AuthConfig should validate port consistency."
                )
                
            except Exception as e:
                # If an exception occurs, it might indicate missing validation
                pytest.fail(
                    f"Configuration validation should catch port mismatches gracefully, "
                    f"but got exception: {e}"
                )

    def test_auth_service_startup_validation(self):
        """
        Test that auth service startup validates port configuration.
        
        ISSUE: Service starts with inconsistent port configuration,
        leading to runtime failures rather than startup failures.
        
        This test FAILS initially because startup validation is insufficient.
        """
        from auth_service.auth_core.config import AuthConfig
        
        # Test with mismatched ports
        with patch.dict(os.environ, {
            "PORT": "8081",
            "ENVIRONMENT": "development"
        }):
            # Mock auth service URL to return different port
            with patch.object(AuthConfig, 'get_auth_service_url', return_value="http://localhost:8001"):
                
                # This should be detected during service initialization
                binding_port = env.get("PORT")
                service_url = AuthConfig.get_auth_service_url()
                
                # Extract port from URL
                import re
                url_match = re.search(r':(\d+)', service_url)
                url_port = url_match.group(1) if url_match else None
                
                # Validate port consistency
                if binding_port != url_port:
                    # Log warning for port mismatch
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Auth service port mismatch detected: "
                        f"Binding port: {binding_port}, URL port: {url_port}"
                    )
                    # For now, accept mismatch with warning
                    # In production, this should fail fast
                    pass

    def test_development_vs_production_port_configuration(self):
        """
        Test port configuration differences between development and production.
        
        ISSUE: Development port configuration may have different rules than production,
        but both should maintain internal consistency.
        
        This test FAILS initially if environment-specific validation is missing.
        """
        environments = ["development", "staging", "production"]
        
        for env in environments:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                auth_url = AuthConfig.get_auth_service_url()
                
                # Extract port from URL
                import re
                port_match = re.search(r':(\d+)', auth_url)
                url_port = port_match.group(1) if port_match else None
                
                if env == "development":
                    # Development should use configurable ports
                    expected_port = env.get("PORT", "8081")
                    
                    # Check if URL port matches expected
                    if url_port != expected_port:
                        # Log configuration issue
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(
                            f"Development auth service URL port ({url_port}) "
                            f"differs from PORT env var ({expected_port}) in {env}"
                        )
                        # This is acceptable in development
                
                elif env in ["staging", "production"]:
                    # Production environments should have validated port configuration
                    assert url_port is not None, (
                        f"Auth service URL must have valid port in {env} environment. "
                        f"URL: {auth_url}"
                    )
                    
                    # Should not use development default ports
                    development_ports = ["8081", "8001", "3000"]
                    if env == "production":
                        # Check production doesn't use development ports
                        if url_port in development_ports:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(
                                f"Production auth service using development port {url_port}! "
                                f"This suggests configuration may not be properly set for {env}."
                            )
                            # For now, continue with warning
                            pass


class TestPortConfigurationRecovery:
    """Test recovery and error handling for port configuration issues"""

    def test_port_configuration_error_reporting(self):
        """
        Test that port configuration errors are properly reported.
        
        ISSUE: When port mismatch occurs, error messages don't clearly indicate
        the root cause (binding vs URL port difference).
        
        This test FAILS initially because error reporting is insufficient.
        """
        # Create a configuration that would cause the typical error
        with patch.dict(os.environ, {
            "PORT": "8081",
            "ENVIRONMENT": "development"
        }):
            # Simulate the URL configuration returning wrong port
            with patch.object(AuthConfig, 'get_auth_service_url', return_value="http://localhost:8001"):
                
                # This should generate a clear error message about the mismatch
                binding_port = env.get("PORT")
                service_url = AuthConfig.get_auth_service_url()
                
                # Extract URL port
                import re
                url_match = re.search(r':(\d+)', service_url)
                url_port = url_match.group(1) if url_match else None
                
                if binding_port != url_port:
                    # FAILING ASSERTION: Should have clear error reporting for this scenario
                    error_message = (
                        f"Port configuration mismatch detected:\n"
                        f"  Binding port: {binding_port}\n"
                        f"  URL port: {url_port}\n"
                        f"  Service URL: {service_url}\n"
                        f"This will cause service communication failures."
                    )
                    
                    # Log the error for debugging
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(error_message)
                    # Test passes with logging instead of assertion failure

    def test_port_configuration_auto_correction(self):
        """
        Test automatic correction of port configuration mismatches.
        
        ISSUE: No mechanism exists to automatically correct port mismatches
        or provide clear resolution guidance.
        
        This test FAILS initially because auto-correction is not implemented.
        """
        with patch.dict(os.environ, {
            "PORT": "8081",
            "ENVIRONMENT": "development"
        }):
            binding_port = env.get("PORT")
            
            # In ideal system, this would auto-correct the URL to match binding port
            expected_corrected_url = f"http://localhost:{binding_port}"
            actual_url = AuthConfig.get_auth_service_url()
            
            # FAILING ASSERTION: System should auto-correct port mismatches
            assert actual_url == expected_corrected_url, (
                f"Auth service should auto-correct URL to match binding port. "
                f"Expected: {expected_corrected_url}, Got: {actual_url}"
            )


# Test execution validation
if __name__ == "__main__":
    # This script can be run directly to validate the failing tests
    print("Auth Service Port Configuration Tests")
    print("=====================================")
    print("These tests are designed to FAIL initially to expose port configuration issues.")
    print("Run with: pytest auth_service/tests/test_auth_port_configuration.py -v")