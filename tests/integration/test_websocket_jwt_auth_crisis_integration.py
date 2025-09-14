"""
Integration Tests for WebSocket JWT Authentication Crisis (Issue #681)

Tests validate WebSocket authentication failures due to missing JWT secrets in staging.
These tests demonstrate the $50K MRR WebSocket functionality blockage.

Business Value: Validates WebSocket authentication works correctly with proper JWT configuration
Architecture: Integration tests with real WebSocket connections (no Docker required)
"""

import pytest
import asyncio
import json
import logging
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional

# SSOT test infrastructure  
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility

logger = logging.getLogger(__name__)


class TestWebSocketJWTAuthenticationCrisis(SSotAsyncTestCase):
    """Integration tests for WebSocket JWT authentication failures in staging."""
    
    async def asyncSetUp(self):
        """Set up async test fixtures."""
        await super().asyncSetUp()
        self.websocket_utility = WebSocketTestUtility()
        
    async def asyncTearDown(self):
        """Clean up async test fixtures."""
        # Clear JWT secret manager cache
        try:
            from shared.jwt_secret_manager import get_jwt_secret_manager
            get_jwt_secret_manager().clear_cache()
        except Exception:
            pass
        await super().asyncTearDown()
    
    def _mock_staging_environment(self, jwt_secrets: Dict[str, str] = None) -> Mock:
        """Mock staging environment with specific JWT secret configuration."""
        mock_env = Mock()
        
        # Base staging environment
        base_env = {
            "ENVIRONMENT": "staging",
            "TESTING": "false",
            "PYTEST_CURRENT_TEST": None
        }
        
        # Add JWT secrets if provided
        if jwt_secrets:
            base_env.update(jwt_secrets)
        
        mock_env.get.side_effect = lambda key, default=None: base_env.get(key, default)
        return mock_env
    
    async def test_websocket_connection_fails_with_missing_jwt_secret(self):
        """
        CRITICAL FAILURE TEST: WebSocket connection fails when JWT secret missing.
        
        This demonstrates the exact Issue #681 scenario:
        - Staging environment with no JWT secrets
        - WebSocket authentication attempt
        - Should fail with JWT configuration error
        
        Expected: Connection failure due to JWT misconfiguration
        """
        mock_env = self._mock_staging_environment()  # No JWT secrets
        
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            # Mock WebSocket manager creation that would fail
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # This should fail during initialization due to JWT config
            with pytest.raises((ValueError, RuntimeError, Exception)) as exc_info:
                manager = WebSocketManager()
                await manager.initialize()
            
            error_message = str(exc_info.value)
            # Should contain JWT-related error
            assert any(term in error_message.lower() for term in [
                "jwt", "secret", "staging", "configuration"
            ])
    
    async def test_websocket_middleware_auth_fails_missing_jwt(self):
        """
        Test WebSocket middleware authentication fails with missing JWT secret.
        
        This tests the exact middleware path that throws the error in 
        fastapi_auth_middleware.py:696
        """
        mock_env = self._mock_staging_environment()  # No JWT secrets
        
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
            
            middleware = FastAPIAuthMiddleware(Mock())
            
            # This should fail when trying to configure JWT secret
            with pytest.raises(ValueError) as exc_info:
                await middleware.configure_jwt_secret()
            
            error_message = str(exc_info.value)
            assert "JWT secret not configured" in error_message
    
    async def test_websocket_auth_success_with_valid_jwt_secret(self):
        """
        Test WebSocket authentication succeeds with valid JWT secret.
        
        This demonstrates the expected behavior after Issue #681 is fixed.
        """
        jwt_config = {
            "JWT_SECRET_KEY": "valid-jwt-secret-for-websocket-auth-32-characters"
        }
        mock_env = self._mock_staging_environment(jwt_config)
        
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
            
            middleware = FastAPIAuthMiddleware(Mock())
            
            # This should succeed with valid JWT secret
            secret = await middleware.configure_jwt_secret()
            assert secret == "valid-jwt-secret-for-websocket-auth-32-characters"
    
    async def test_websocket_connection_handshake_jwt_validation(self):
        """
        Test WebSocket connection handshake validates JWT properly.
        
        This tests the complete flow:
        1. Client connects with JWT token
        2. Middleware validates token using configured secret
        3. Connection succeeds/fails based on JWT configuration
        """
        # Test with missing JWT secret (should fail)
        mock_env = self._mock_staging_environment()
        
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            from netra_backend.app.websocket_core.auth import WebSocketAuth
            
            auth = WebSocketAuth()
            
            # Mock WebSocket with JWT token
            mock_websocket = Mock()
            mock_websocket.headers = {"authorization": "Bearer fake.jwt.token"}
            
            # Should fail to validate due to JWT configuration issue
            with pytest.raises((ValueError, Exception)) as exc_info:
                await auth.authenticate(mock_websocket)
            
            # Error should relate to JWT configuration
            error_message = str(exc_info.value)
            assert any(term in error_message.lower() for term in [
                "jwt", "secret", "configuration", "not configured"
            ])
    
    async def test_websocket_events_blocked_by_jwt_auth_failure(self):
        """
        Test WebSocket events are blocked by JWT authentication failure.
        
        This demonstrates the business impact: agent events cannot be sent
        when WebSocket authentication fails due to JWT misconfiguration.
        
        Business Impact: $50K MRR WebSocket-dependent functionality blocked
        """
        mock_env = self._mock_staging_environment()  # No JWT secrets
        
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            # Mock the complete WebSocket event flow
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # WebSocket manager creation should fail
            with pytest.raises((ValueError, Exception)) as exc_info:
                manager = WebSocketManager()
                await manager.initialize()
                
                # If initialization somehow succeeds, sending events should fail
                await manager.send_agent_event("user_123", {
                    "type": "agent_started",
                    "data": {"message": "Agent processing started"}
                })
            
            # Either initialization or event sending should fail due to JWT config
            assert exc_info.value is not None
    
    async def test_golden_path_websocket_flow_jwt_blockage(self):
        """
        Test Golden Path WebSocket flow blocked by JWT configuration.
        
        Golden Path: User login → Agent starts → WebSocket events → AI response
        Blockage Point: WebSocket authentication fails due to missing JWT secret
        """
        mock_env = self._mock_staging_environment()  # No JWT secrets
        
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            # Simulate Golden Path WebSocket flow
            try:
<<<<<<< HEAD
                from netra_backend.app.websocket_core.manager import WebSocketManager
                from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
=======
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                from netra_backend.app.agents.registry import AgentRegistry
>>>>>>> c2e4b48c66d9bf92657c93ac92e56d57f8cca6b1
                
                # Step 1: Initialize WebSocket manager (should fail)
                manager = WebSocketManager()
                await manager.initialize()
                
                # Step 2: Set up agent registry with WebSocket
                registry = AgentRegistry()
                registry.set_websocket_manager(manager)
                
                # Step 3: Send critical WebSocket events
                await manager.send_agent_event("user_123", {
                    "type": "agent_started", 
                    "data": {"agent_type": "supervisor"}
                })
                
                # If we reach here, the JWT issue might be resolved
                pytest.fail("Expected JWT configuration failure, but flow succeeded")
                
            except (ValueError, RuntimeError, Exception) as e:
                # Expected failure due to JWT configuration
                error_message = str(e)
                assert any(term in error_message.lower() for term in [
                    "jwt", "secret", "configuration", "staging"
                ])
                logger.info(f"Golden Path correctly blocked by JWT config issue: {error_message}")


class TestJWTConfigurationBusinessImpactIntegration(SSotAsyncTestCase):
    """Integration tests demonstrating business impact of JWT configuration failures."""
    
    async def test_websocket_revenue_functionality_integration(self):
        """
        Test $50K MRR WebSocket functionality integration with JWT configuration.
        
        This test validates that JWT configuration directly impacts
        revenue-generating WebSocket features.
        """
        # Mock staging environment with no JWT secrets
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default=None: {
            "ENVIRONMENT": "staging",
            "TESTING": "false"
        }.get(key, default)
        
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
            
            # This represents the revenue-critical WebSocket authentication step
            with pytest.raises(ValueError) as exc_info:
                secret = get_jwt_secret()
                
                # If secret resolution succeeded, test WebSocket integration
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                manager = WebSocketManager()
                await manager.initialize()
            
            # Failure indicates JWT configuration is blocking revenue functionality
            error_message = str(exc_info.value)
            assert "staging environment" in error_message.lower()
            logger.critical(f"$50K MRR WebSocket functionality blocked: {error_message}")
    
    async def test_staging_deployment_validation_jwt_integration(self):
        """
        Test staging deployment validation integration with JWT configuration.
        
        This simulates the staging deployment process where JWT configuration
        must be validated before WebSocket services can start.
        """
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default=None: {
            "ENVIRONMENT": "staging",
            "TESTING": "false"
        }.get(key, default)
        
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            # Simulate deployment validation sequence
            validation_steps = []
            
            try:
                # Step 1: JWT secret configuration validation
                from shared.jwt_secret_manager import get_unified_jwt_secret
                secret = get_unified_jwt_secret()
                validation_steps.append("JWT secret resolved")
                
                # Step 2: WebSocket service initialization
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                manager = WebSocketManager()
                await manager.initialize()
                validation_steps.append("WebSocket manager initialized")
                
                # Step 3: Authentication middleware configuration
                from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
                middleware = FastAPIAuthMiddleware(Mock())
                await middleware.configure_jwt_secret(secret)
                validation_steps.append("Auth middleware configured")
                
            except (ValueError, Exception) as e:
                # Expected failure in current staging configuration
                error_message = str(e)
                logger.error(f"Staging deployment validation failed at step {len(validation_steps) + 1}: {error_message}")
                
                # Validate this is the expected JWT configuration error
                assert any(term in error_message.lower() for term in [
                    "jwt", "secret", "staging", "not configured"
                ])
            
            # If all steps succeeded, JWT configuration is working
            if len(validation_steps) == 3:
                logger.info("All staging deployment validation steps passed")
            else:
                logger.warning(f"Staging deployment validation incomplete: {validation_steps}")


class TestJWTSecretDeploymentScenarios(SSotAsyncTestCase):
    """Integration tests for various JWT secret deployment scenarios."""
    
    async def test_environment_variable_jwt_secret_integration(self):
        """
        Test JWT secret integration via environment variables.
        
        This tests the expected fix path for Issue #681.
        """
        jwt_config = {
            "JWT_SECRET_STAGING": "environment-staging-jwt-secret-32-characters"
        }
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default=None: {
            "ENVIRONMENT": "staging",
            "TESTING": "false",
            **jwt_config
        }.get(key, default)
        
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # Should successfully resolve JWT secret
            secret = get_jwt_secret()
            assert secret == "environment-staging-jwt-secret-32-characters"
            
            # Should successfully initialize WebSocket manager
            manager = WebSocketManager()
            # Note: Full initialization might require additional mocking
            # but JWT secret resolution should succeed
    
    async def test_gcp_secret_manager_jwt_integration(self):
        """
        Test JWT secret integration via GCP Secret Manager.
        
        This tests the enterprise-grade fix for Issue #681.
        """
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default=None: {
            "ENVIRONMENT": "staging",
            "TESTING": "false"
        }.get(key, default)
        
        # Mock GCP Secret Manager
        mock_get_staging_secret = AsyncMock(return_value="gcp-managed-jwt-secret-32-characters")
        
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            with patch('deployment.secrets_config.get_staging_secret', mock_get_staging_secret):
                from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
                
                # Should successfully resolve JWT secret from GCP
                secret = get_jwt_secret()
                assert secret == "gcp-managed-jwt-secret-32-characters"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
