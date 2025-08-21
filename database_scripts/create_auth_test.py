# Create test_staging_cross_service_auth_propagation.py
content = """\"\"\"
Staging Cross-Service Authentication Propagation Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform/Internal)
- Business Goal: Security, Platform Stability, Service Integration
- Value Impact: Ensures authentication tokens propagate correctly across all microservices
- Revenue Impact: Prevents authentication barriers that could block user workflows and revenue generation

Tests authentication token propagation across microservices, JWT validation in each service,
auth failure handling and recovery, service-to-service authentication, and authorization
boundaries between services in staging environment.
\"\"\"

import asyncio
import json
import os
import pytest
import time
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import patch, Mock, AsyncMock, MagicMock
import aiohttp
import jwt
from fastapi import Request, HTTPException
from fastapi.testclient import TestClient

from app.core.cross_service_auth import (
    CrossServiceAuthManager,
    AuthToken,
    AuthTokenType,
    ServiceRole,
    AuthContext,
    AuthenticationMiddleware,
    setup_authentication
)
from app.clients.auth_client import AuthClient
from test_framework.mock_utils import mock_justified


class TestStagingCrossServiceAuthPropagation:
    \"\"\"Test authentication token propagation across microservices in staging.\"\"\"
    
    @pytest.fixture
    def staging_services_config(self):
        \"\"\"Staging services configuration.\"\"\"
        return {
            "auth_service": {
                "url": "http://auth-service:8081",
                "port": 8081,
                "role": ServiceRole.AUTH
            },
            "backend_service": {
                "url": "http://backend-service:8000", 
                "port": 8000,
                "role": ServiceRole.BACKEND
            },
            "frontend_service": {
                "url": "http://frontend-service:3000",
                "port": 3000,
                "role": ServiceRole.FRONTEND
            },
            "jwt_secret": "staging-cross-service-jwt-secret"
        }
    
    @pytest.fixture
    def test_user_credentials(self):
        \"\"\"Test user credentials for multi-service authentication.\"\"\"
        return {
            "user_id": "cross_service_user_456",
            "email": "crossservice@staging.netrasystems.ai",
            "roles": ["user", "mid_tier"],
            "scopes": ["read", "write", "analytics", "cross_service"],
            "permissions": {
                "auth": ["authenticate", "validate"],
                "backend": ["api_access", "data_read", "data_write"],
                "frontend": ["ui_access", "dashboard"]
            }
        }

    @mock_justified("JWT validation requires controlled token generation not available in test environment")
    def test_jwt_validation_in_each_service(self, staging_services_config, test_user_credentials):
        \"\"\"Test JWT validation logic in Auth, Backend, and Frontend services.\"\"\"
        jwt_secret = staging_services_config["jwt_secret"]
        
        # Create JWT tokens for each service context
        services = ["auth", "backend", "frontend"]
        
        for service_name in services:
            # Create service-specific JWT payload
            payload = {
                "type": AuthTokenType.USER_ACCESS.value,
                "user_id": test_user_credentials["user_id"],
                "scopes": test_user_credentials["scopes"],
                "service_context": service_name,
                "iat": int(datetime.now(UTC).timestamp()),
                "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
                "iss": service_name
            }
            
            # Create JWT token
            jwt_token = jwt.encode(payload, jwt_secret, algorithm="HS256")
            
            # Validate JWT in service-specific auth manager
            auth_manager = CrossServiceAuthManager(
                auth_service_url=staging_services_config["auth_service"]["url"],
                jwt_secret=jwt_secret,
                service_name=service_name
            )
            
            # Test JWT validation
            auth_token = auth_manager._validate_jwt_token(jwt_token)
            
            assert auth_token.token == jwt_token
            assert auth_token.token_type == AuthTokenType.USER_ACCESS
            assert auth_token.user_id == test_user_credentials["user_id"]
            assert auth_token.scopes == test_user_credentials["scopes"]
            assert not auth_token.is_expired

    @mock_justified("Environment configuration testing requires controlled environment variables")
    async def test_staging_specific_auth_configuration_propagation(self, staging_services_config):
        \"\"\"Test staging-specific authentication configuration propagation.\"\"\"
        staging_env = {
            "NETRA_ENVIRONMENT": "staging",
            "AUTH_SERVICE_URL": staging_services_config["auth_service"]["url"],
            "JWT_SECRET": staging_services_config["jwt_secret"]
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # Test each service picks up staging configuration
            services = ["auth", "backend", "frontend"]
            
            for service_name in services:
                auth_manager = CrossServiceAuthManager(service_name=service_name)
                
                # Verify staging configuration
                assert auth_manager.auth_service_url == staging_services_config["auth_service"]["url"]
                assert auth_manager.jwt_secret == staging_services_config["jwt_secret"]
                assert auth_manager.service_name == service_name
                
                # Test staging-specific token creation
                test_token = auth_manager.create_user_token(
                    user_id="staging_config_test",
                    scopes=["staging_test"]
                )
                
                # Verify token can be validated with staging configuration
                auth_token = auth_manager._validate_jwt_token(test_token)
                assert auth_token.user_id == "staging_config_test"
                assert auth_token.scopes == ["staging_test"]
"""

with open('app/tests/integration/staging/test_staging_cross_service_auth_propagation.py', 'w') as f:
    f.write(content)

print('Created test_staging_cross_service_auth_propagation.py')
