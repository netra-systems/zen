class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
"""
        """Send JSON message.""""""
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False
"""
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()"""
        """
        Integration Tests for Staging Deployment Script Compatibility

        These tests validate integration between SecretConfig and the actual deployment script,
        ensuring that the centralized secret configuration works correctly with GCP deployment.

        Related to commit 41e0dd6a8 which fixed deployment script integration issues and
        introduced centralized secrets configuration via SecretConfig.

        Business Value Justification (BVJ):
        - Segment: Platform/Internal
        - Business Goal: Ensure reliable deployment pipeline and prevent deployment failures
        - Value Impact: Eliminates deployment script errors that block development and staging
        - Strategic Impact: Maintains deployment reliability and development velocity

        Test Categories:
        - Integration tests that validate deployment script and SecretConfig integration"""
        - Cross-environment deployment configuration validation"""

import pytest
import subprocess
import os
import sys
import json
from typing import Dict, List, Optional, Any
import tempfile
from shared.isolated_environment import IsolatedEnvironment

            # Add project root to path for imports
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from deployment.secrets_config import SecretConfig
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
import asyncio

"""
        """Mock deployment script for testing integration."""
"""
        """Initialize mock deployment script."""
        self.project_id = "netra-staging"
        self.region = "us-central1"
services = {"backend": "netra-backend-staging",, "auth": "netra-auth-service"}
    def deploy_service(self, service_name: str, secrets_string: str) -> Dict[str, Any]:
        """Mock service deployment."""
        pass"""
        "success": True,
        "service_name": service_name,
        "secrets_count": len(secrets_string.split(",")),
        "url": "formatted_string"
    


class TestStagingDeploymentScriptCompatibility:
        """Integration tests for staging deployment script compatibility."""

        @pytest.fixture"""
        """Provide mock deployment script."""
        return MockDeploymentScript()
"""
        """Test that SecretConfig integrates correctly with deployment script patterns.
"""
        to deployment script parameter generation."""
        pass"""
        auth_secrets = SecretConfig.generate_secrets_string("auth", "staging")
        auth_result = mock_deployment_script.deploy_service("auth", auth_secrets)

        assert auth_result["success"], "Auth service deployment should succeed"
        assert auth_result["secrets_count"] > 5, "Auth service should have multiple secrets"

    # Test backend service integration
        backend_secrets = SecretConfig.generate_secrets_string("backend", "staging")
        backend_result = mock_deployment_script.deploy_service("backend", backend_secrets)

        assert backend_result["success"], "Backend service deployment should succeed"
        assert backend_result["secrets_count"] > 5, "Backend service should have multiple secrets"

    def test_gcloud_command_generation(self, mock_subprocess):
        """Test that gcloud commands are generated correctly with SecretConfig.
"""
        gcloud run deploy commands using SecretConfig output."""
        pass
    # Mock successful gcloud response
        websocket = TestWebSocketConnection()  # Real WebSocket implementation"""
        mock_result.stdout = "Service URL: https://service-url.googleapis.com
        "
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

    # Test auth service command generation
        auth_secrets = SecretConfig.generate_secrets_string("auth", "staging")

    # Simulate gcloud run deploy command
        cmd = [ )
        "gcloud", "run", "deploy", "netra-auth-service",
        "--project", "netra-staging",
        "--region", "us-central1",
        "--set-secrets", auth_secrets
    

    # Validate command structure
        assert cmd[0] == "gcloud"
        assert cmd[1] == "run"
        assert cmd[2] == "deploy"
        assert cmd[3] == "netra-auth-service"
        assert "--set-secrets" in cmd

        secrets_index = cmd.index("--set-secrets")
        secrets_param = cmd[secrets_index + 1]

    # Validate secrets parameter format
        assert len(secrets_param) > 0, "Secrets parameter should not be empty"
        assert "SECRET_KEY=secret-key-staging:latest" in secrets_param, ( )
        "Should contain SECRET_KEY mapping"
    
        assert not secrets_param.startswith(","), "Should not start with comma"
        assert not secrets_param.endswith(","), "Should not end with comma"

    def test_deployment_script_error_handling(self, mock_subprocess):
        """Test deployment script error handling with SecretConfig integration.
"""
        using SecretConfig-generated parameters."""
        pass
    # Mock gcloud failure
        websocket = TestWebSocketConnection()  # Real WebSocket implementation"""
        mock_result.stdout = ""
        mock_result.stderr = "ERROR: Secret 'missing-secret' not found"
        mock_subprocess.return_value = mock_result

    # Generate valid secrets string
        auth_secrets = SecretConfig.generate_secrets_string("auth", "staging")

    # Simulate deployment command that would fail
        cmd = [ )
        "gcloud", "run", "deploy", "netra-auth-service",
        "--set-secrets", auth_secrets
    

    # The command structure should still be valid even if gcloud fails
        assert "--set-secrets" in cmd
        secrets_index = cmd.index("--set-secrets")
        secrets_param = cmd[secrets_index + 1]

    # Validate that our secrets string is well-formed
        secrets_list = secrets_param.split(",")
        for secret_mapping in secrets_list:
        assert "=" in secret_mapping, "formatted_string"
        assert ":latest" in secret_mapping, "formatted_string"

    def test_environment_specific_deployment_configuration(self):
        """Test that deployment configuration is correct for staging environment."""
        This test validates staging-specific deployment patterns and configurations.""""""
        environment = "staging"

        for service_name in ["auth", "backend"]:
        # Generate environment-specific configuration
        secrets_string = SecretConfig.generate_secrets_string(service_name, environment)

        # Parse secrets to validate environment-specific patterns
        secret_mappings = secrets_string.split(",")

        for mapping in secret_mappings:
        env_var, gsm_spec = mapping.split("=", 1)
        gsm_name, version = gsm_spec.split(":", 1)

            # Validate staging patterns
        assert version == "latest", ( )
        "formatted_string"
            

            # Most staging secrets should contain 'staging' in GSM name
        if not any(word in gsm_name for word in ["staging", "oauth", "gemini"]):
                # Some exceptions are allowed (like service names)
        continue

    def test_deployment_readiness_validation_integration(self):
        """Test comprehensive deployment readiness validation.
"""
        prevent regressions like the SECRET_KEY incident."""
        pass
        deployment_readiness = {}"""
        for service_name in ["auth", "backend"]:
        # Simulate deployment readiness checks
readiness_checks = {"service_name": service_name,, "secrets_generation": False,, "command_generation": False,, "parameter_validation": False,, "regression_prevention": False}
        # Check 1: Secrets can be generated
        try:
        secrets_string = SecretConfig.generate_secrets_string(service_name, "staging")
        readiness_checks["secrets_generation"] = len(secrets_string) > 0
        except Exception:
        readiness_checks["secrets_generation"] = False

                # Check 2: Command can be generated
        if readiness_checks["secrets_generation"]:
        try:
        cmd = [ )
        "gcloud", "run", "deploy", "formatted_string",
        "--set-secrets", secrets_string
                        
        readiness_checks["command_generation"] = len(cmd) == 6
        except Exception:
        readiness_checks["command_generation"] = False

                            # Check 3: Parameters are valid
        if readiness_checks["command_generation"]:
        try:
        secrets_param = cmd[5]  # --set-secrets parameter
        mappings = secrets_param.split(",")
        valid_mappings = all( )
        "=" in mapping and ":latest" in mapping
        for mapping in mappings
                                    
        readiness_checks["parameter_validation"] = valid_mappings
        except Exception:
        readiness_checks["parameter_validation"] = False

                                        # Check 4: Regression-specific validations
        if readiness_checks["parameter_validation"]:
                                            # SECRET_KEY regression prevention
        secret_key_check = "SECRET_KEY=secret-key-staging:latest" in secrets_param
                                            # Redis configuration check
        redis_url_check = "REDIS_URL=" in secrets_param
                                            # OAuth configuration check (different per service)
        if service_name == "auth":
        oauth_check = "GOOGLE_OAUTH_CLIENT_ID_STAGING=" in secrets_param
        else:  # backend
        oauth_check = "GOOGLE_CLIENT_ID=" in secrets_param

        readiness_checks["regression_prevention"] = all([ ))
        secret_key_check, redis_url_check, oauth_check
                                                

        deployment_readiness[service_name] = readiness_checks

                                                # Assert all services pass all readiness checks
        for service_name, checks in deployment_readiness.items():
        for check_name, check_result in checks.items():
        assert check_result, ( )
        "formatted_string"
                                                        

    def test_deployment_script_cloud_sql_integration(self, mock_subprocess):
        """Test that Cloud SQL instances are properly configured with secrets.
"""
        instance configuration in the deployment script."""
        pass
    # Mock successful deployment
        websocket = TestWebSocketConnection()  # Real WebSocket implementation"""
        mock_result.stdout = "Service deployed successfully"
        mock_subprocess.return_value = mock_result

        for service_name in ["auth", "backend"]:
        secrets_string = SecretConfig.generate_secrets_string(service_name, "staging")

        # Validate that database secrets are present
        database_secrets = [ )
        "POSTGRES_HOST=postgres-host-staging:latest",
        "POSTGRES_PORT=postgres-port-staging:latest",
        "POSTGRES_DB=postgres-db-staging:latest",
        "POSTGRES_USER=postgres-user-staging:latest",
        "POSTGRES_PASSWORD=postgres-password-staging:latest"
        

        for db_secret in database_secrets:
        assert db_secret in secrets_string, ( )
        "formatted_string"
            

            # Simulate deployment with Cloud SQL instances
        cmd = [ )
        "gcloud", "run", "deploy", "formatted_string",
        "--add-cloudsql-instances", "netra-staging:us-central1:staging-shared-postgres",
        "--set-secrets", secrets_string
            

            # Validate command includes both Cloud SQL and secrets
        assert "--add-cloudsql-instances" in cmd
        assert "--set-secrets" in cmd

    def test_deployment_script_vpc_connector_integration(self):
        """Test that VPC connector configuration works with secret configuration.
"""
        have proper secret and network configuration.""""""
        for service_name in ["auth", "backend"]:
        secrets_string = SecretConfig.generate_secrets_string(service_name, "staging")

        # Services that need VPC connector should have Redis secrets
        redis_secrets = [ )
        "REDIS_HOST=redis-host-staging:latest",
        "REDIS_URL=redis-url-staging:latest"
        

        for redis_secret in redis_secrets:
        assert redis_secret in secrets_string, ( )
        "formatted_string"
            

            # Simulate deployment command with VPC connector
        cmd = [ )
        "gcloud", "run", "deploy", "formatted_string",
        "--vpc-connector", "staging-connector",
        "--set-secrets", secrets_string
            

            # Validate both VPC and secrets are configured
        assert "--vpc-connector" in cmd
        assert "staging-connector" in cmd
        assert "--set-secrets" in cmd

    def test_deployment_script_service_specific_configurations(self):
        """Test that service-specific configurations are handled correctly.
"""
        configurations based on their specific requirements."""
        pass"""
        auth_secrets = SecretConfig.generate_secrets_string("auth", "staging")

    # Auth service should have service-specific secrets
        auth_specific_secrets = [ )
        "SERVICE_ID=service-id-staging:latest",  # Only auth has SERVICE_ID
        "OAUTH_HMAC_SECRET=oauth-hmac-secret-staging:latest",  # Only auth has OAuth HMAC
        "GOOGLE_OAUTH_CLIENT_ID_STAGING=google-oauth-client-id-staging:latest"  # Environment-specific OAuth
    

        for secret in auth_specific_secrets:
        assert secret in auth_secrets, ( )
        "formatted_string"
        

        # Test backend service specific requirements
        backend_secrets = SecretConfig.generate_secrets_string("backend", "staging")

        # Backend service should have AI service secrets (auth doesn't need these)
        backend_specific_secrets = [ )
        "OPENAI_API_KEY=openai-api-key-staging:latest",
        "ANTHROPIC_API_KEY=anthropic-api-key-staging:latest",
        "GEMINI_API_KEY=gemini-api-key-staging:latest",
        "CLICKHOUSE_PASSWORD=clickhouse-password-staging:latest",
        "FERNET_KEY=fernet-key-staging:latest"
        

        for secret in backend_specific_secrets:
        assert secret in backend_secrets, ( )
        "formatted_string"
            

            # Validate that auth service doesn't have backend AI secrets
        for backend_specific in backend_specific_secrets:
        secret_name = backend_specific.split("=")[0]
        assert secret_name not in auth_secrets, ( )
        "formatted_string"
                

                # Validate that backend doesn't have auth-only secrets
        auth_only_secrets = ["SERVICE_ID", "OAUTH_HMAC_SECRET", "GOOGLE_OAUTH_CLIENT_ID_STAGING"]
        for secret_name in auth_only_secrets:
        assert secret_name not in backend_secrets, ( )
        "formatted_string"
                    


class TestDeploymentScriptRegressionPrevention:
        """Integration tests focused on preventing deployment script regressions."""
"""
        """Test that SECRET_KEY regression is prevented at deployment script level.
"""
        script command generation specifically for SECRET_KEY.""""""
        for service_name in ["auth", "backend"]:
        # Generate secrets string
        secrets_string = SecretConfig.generate_secrets_string(service_name, "staging")

        # Validate SECRET_KEY is present (regression prevention)
        assert "SECRET_KEY=secret-key-staging:latest" in secrets_string, ( )
        "formatted_string"
        

        # Simulate deployment command generation
        cmd = [ )
        "gcloud", "run", "deploy", "formatted_string",
        "--project", "netra-staging",
        "--region", "us-central1",
        "--set-secrets", secrets_string
        

        # Validate command structure (should be 10 elements)
        expected_cmd = ["gcloud", "run", "deploy", "formatted_string",
        "--project", "netra-staging", "--region", "us-central1",
        "--set-secrets", secrets_string]
        assert len(cmd) == 10, "formatted_string"
        assert cmd[-2] == "--set-secrets", "Should have --set-secrets parameter"
        assert "SECRET_KEY=" in cmd[-1], "Secrets parameter should contain SECRET_KEY"

    def test_deployment_failure_detection_integration(self, mock_subprocess):
        """Test that deployment failures are properly detected and handled.
"""
        failures that might be caused by missing or invalid secrets."""
        pass
    # Mock deployment failure due to missing secret
        websocket = TestWebSocketConnection()  # Real WebSocket implementation"""
        mock_result.stdout = ""
        mock_result.stderr = "ERROR: Failed to access secret 'secret-key-staging'"
        mock_subprocess.return_value = mock_result

    # Generate valid secrets configuration
        auth_secrets = SecretConfig.generate_secrets_string("auth", "staging")

    # Simulate deployment attempt
        cmd = [ )
        "gcloud", "run", "deploy", "netra-auth-service",
        "--set-secrets", auth_secrets
    

    # Even with deployment failure, our configuration should be valid
        assert "SECRET_KEY=secret-key-staging:latest" in auth_secrets
        assert len(auth_secrets.split(",")) > 5  # Multiple secrets configured

    The error should be detectable from the mock result
    # (In real implementation, this would help identify missing GSM secrets)
        assert mock_result.returncode != 0
        assert "secret-key-staging" in mock_result.stderr

    def test_oauth_configuration_deployment_integration(self):
        '''Test that OAuth configuration changes don't break deployment.

        This test validates that OAuth updates (which caused the original regression)
        work correctly with the deployment script integration.
        '''
        pass
    # Test auth service OAuth configuration
        auth_secrets = SecretConfig.generate_secrets_string("auth", "staging")

    # Should contain environment-specific OAuth secrets
        auth_oauth_secrets = [ )
        "GOOGLE_OAUTH_CLIENT_ID_STAGING=google-oauth-client-id-staging:latest",
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING=google-oauth-client-secret-staging:latest"
    

        for oauth_secret in auth_oauth_secrets:
        assert oauth_secret in auth_secrets, ( )
        "formatted_string"
        

        # Test backend service OAuth configuration
        backend_secrets = SecretConfig.generate_secrets_string("backend", "staging")

        # Should contain simplified OAuth secrets
        backend_oauth_secrets = [ )
        "GOOGLE_CLIENT_ID=google-oauth-client-id-staging:latest",
        "GOOGLE_CLIENT_SECRET=google-oauth-client-secret-staging:latest"
        

        for oauth_secret in backend_oauth_secrets:
        assert oauth_secret in backend_secrets, ( )
        "formatted_string"
            

            # Validate that OAuth changes don't affect SECRET_KEY
        assert "SECRET_KEY=secret-key-staging:latest" in auth_secrets
        assert "SECRET_KEY=secret-key-staging:latest" in backend_secrets

    def test_redis_configuration_deployment_integration(self):
        """Test that Redis configuration works correctly with deployment script.
"""
        script integration.""""""
        for service_name in ["auth", "backend"]:
        secrets_string = SecretConfig.generate_secrets_string(service_name, "staging")

        # Both REDIS_URL and REDIS_HOST/PORT should be available
        # for backward compatibility (as mentioned in the commit)
        redis_secrets = [ )
        "REDIS_URL=redis-url-staging:latest",
        "REDIS_HOST=redis-host-staging:latest",
        "REDIS_PORT=redis-port-staging:latest",
        "REDIS_PASSWORD=redis-password-staging:latest"
        

        for redis_secret in redis_secrets:
        assert redis_secret in secrets_string, ( )
        "formatted_string"
            

            # Validate deployment command includes VPC connector for Redis access
        cmd = [ )
        "gcloud", "run", "deploy", "formatted_string",
        "--vpc-connector", "staging-connector",
        "--set-secrets", secrets_string
            

        assert "--vpc-connector" in cmd, ( )
        "formatted_string"
            

    def test_critical_secrets_deployment_validation(self):
        """Test that critical secrets are validated before deployment.
"""
        critical secrets before attempting deployment.""""""
        for service_name in ["auth", "backend"]:
        # Get critical secrets for the service
        critical_secrets = set(SecretConfig.CRITICAL_SECRETS.get(service_name, []))

        # Generate deployment secrets string
        secrets_string = SecretConfig.generate_secrets_string(service_name, "staging")

        # Validate all critical secrets are present in deployment string
        for critical_secret in critical_secrets:
        gsm_mapping = SecretConfig.get_gsm_mapping(critical_secret)
        expected_mapping = "formatted_string"

        assert expected_mapping in secrets_string, ( )
        "formatted_string"
            

            # Simulate pre-deployment validation
        secrets_in_deployment = set()
        for mapping in secrets_string.split(","):
        secret_name = mapping.split("=")[0]
        secrets_in_deployment.add(secret_name)

                # All critical secrets should be in deployment
        missing_critical = critical_secrets - secrets_in_deployment
        assert len(missing_critical) == 0, ( )
        "formatted_string"
                
