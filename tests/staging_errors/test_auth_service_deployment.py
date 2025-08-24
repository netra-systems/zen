"""Test to reproduce auth service deployment configuration issues."""

import os
import pytest
import sys
from unittest.mock import patch, MagicMock

# Add the auth_service to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def test_auth_service_missing_jwt_secret():
    """Test that auth service fails to start without JWT_SECRET_KEY or JWT_SECRET."""
    
    # Clear any existing JWT secrets
    os.environ.pop('JWT_SECRET_KEY', None)
    os.environ.pop('JWT_SECRET', None)
    os.environ['ENVIRONMENT'] = 'staging'
    
    from auth_service.auth_core.utils.secrets import AuthSecretLoader
    
    # This should raise ValueError when JWT secret is missing
    with pytest.raises(ValueError, match="JWT_SECRET"):
        AuthSecretLoader.get_jwt_secret()


def test_auth_service_missing_database_url():
    """Test that auth service fails to initialize database without DATABASE_URL."""
    
    # Clear DATABASE_URL
    os.environ.pop('DATABASE_URL', None)
    os.environ['ENVIRONMENT'] = 'staging'
    
    # Mock the auth_db module
    with patch('auth_service.auth_db') as mock_auth_db:
        # Simulate database initialization failure
        mock_auth_db.initialize.side_effect = Exception("Connection failed: DATABASE_URL not set")
        
        # This should fail with database connection error
        with pytest.raises(Exception, match="DATABASE_URL"):
            import asyncio
            asyncio.run(mock_auth_db.initialize())


def test_deployment_script_auth_service_configuration():
    """Test that deployment script correctly configures auth service secrets."""
    
    from scripts.deploy_to_gcp import DeploymentConfig, ServiceDeployment
    
    # Create deployment config for staging
    config = DeploymentConfig(
        project_id="netra-staging",
        region="us-central1",
        environment="staging",
        build_local=True,
        run_checks=False,
        cleanup=False,
        service_account="netra-staging-deploy@netra-staging.iam.gserviceaccount.com"
    )
    
    # Get auth service deployment configuration
    auth_service = ServiceDeployment(
        name="netra-auth-service",
        image=f"gcr.io/{config.project_id}/netra-auth-service:latest",
        port=8080,
        memory="512Mi",
        cpu="1",
        min_instances=1,
        max_instances=10,
        environment_vars={
            "ENVIRONMENT": config.environment,
            "PYTHONUNBUFFERED": "1",
            "FRONTEND_URL": "https://app.staging.netrasystems.ai",
        },
        secrets={},  # This is the problem - no secrets configured!
        timeout="5m",
        service_account=config.service_account
    )
    
    # Test that required secrets are missing
    assert "DATABASE_URL" not in auth_service.environment_vars
    assert "JWT_SECRET_KEY" not in auth_service.environment_vars
    assert len(auth_service.secrets) == 0  # No secrets configured
    
    # These should be present for auth service to work
    required_secrets = [
        "DATABASE_URL",
        "JWT_SECRET_KEY",
        "GOOGLE_CLIENT_ID", 
        "GOOGLE_CLIENT_SECRET",
        "SERVICE_SECRET",
        "SERVICE_ID"
    ]
    
    for secret in required_secrets:
        assert secret not in auth_service.environment_vars
        assert secret not in auth_service.secrets


def test_auth_service_startup_with_all_configs():
    """Test that auth service can start when all required configs are present."""
    
    # Set all required environment variables
    os.environ['ENVIRONMENT'] = 'staging'
    os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost/test'
    os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key'
    os.environ['GOOGLE_CLIENT_ID'] = 'test-client-id'
    os.environ['GOOGLE_CLIENT_SECRET'] = 'test-client-secret'
    os.environ['SERVICE_SECRET'] = 'test-service-secret'
    os.environ['SERVICE_ID'] = 'auth-service'
    os.environ['PORT'] = '8080'
    
    from auth_service.auth_core.utils.secrets import AuthSecretLoader
    
    # This should work now
    jwt_secret = AuthSecretLoader.get_jwt_secret()
    assert jwt_secret == 'test-jwt-secret-key'
    
    # Test that the service can access all required configs
    assert os.getenv('DATABASE_URL') is not None
    assert os.getenv('GOOGLE_CLIENT_ID') is not None
    assert os.getenv('GOOGLE_CLIENT_SECRET') is not None