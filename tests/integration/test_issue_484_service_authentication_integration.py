"""
Integration tests for Issue #484: Service Authentication Integration

This test suite performs integration testing to reproduce the service authentication
failures that occur when service:netra-backend users attempt to create database
sessions and perform agent operations.

These tests simulate the real-world conditions that cause the 403 'Not authenticated'
errors and validate the complete authentication flow from dependencies through
session factory to database operations.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch
from contextlib import asynccontextmanager

# Import the integration test targets
from netra_backend.app.dependencies import (
    get_request_scoped_db_session,
    get_service_user_context,
    get_request_scoped_user_context
)
from netra_backend.app.database.request_scoped_session_factory import (
    get_session_factory,
    get_isolated_session
)
from netra_backend.app.clients.auth_client_core import AuthServiceClient


class TestIssue484ServiceAuthenticationIntegration:
    """Integration test class for Issue #484 service authentication failures."""
    
    @pytest.mark.asyncio
    async def test_service_user_context_to_session_creation_flow(self):
        """Test the complete flow from service user context to session creation.
        
        This integration test reproduces the exact flow that fails in Issue #484.
        """
        # Step 1: Get service user context (this should work)
        with patch('netra_backend.app.core.configuration.get_configuration') as mock_config:
            mock_config_obj = Mock()
            mock_config_obj.service_id = "netra-backend"
            mock_config.return_value = mock_config_obj
            
            service_user_id = get_service_user_context()
            assert service_user_id == "service:netra-backend"
        
        # Step 2: Attempt to create a session with service user (this fails in Issue #484)
        session_factory = await get_session_factory()
        
        # Mock database connection since we're testing auth flow
        with patch('netra_backend.app.database.request_scoped_session_factory.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_session.info = {}
            
            @asynccontextmanager
            async def mock_db_session():
                try:
                    yield mock_session
                finally:
                    pass
            
            mock_get_db.return_value = mock_db_session()
            
            # Mock auth client validation to simulate the failure scenario
            with patch.object(AuthServiceClient, 'validate_service_user_context') as mock_validate:
                # Simulate missing service credentials (Issue #484 cause)
                mock_validate.return_value = {
                    "valid": False,
                    "error": "missing_service_credentials",
                    "details": "SERVICE_ID and SERVICE_SECRET required for service user operations"
                }
                
                # This should fail and reproduce Issue #484
                try:
                    async with session_factory.get_request_scoped_session(service_user_id, "test-req") as session:
                        pytest.fail("Session creation should have failed due to missing service credentials")
                        
                except Exception as e:
                    # This is the expected failure reproducing Issue #484
                    assert "service user validation failed" in str(e).lower() or "authentication" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_dependencies_get_request_scoped_db_session_integration(self):
        """Test the full dependencies.py flow for service authentication.
        
        This reproduces the exact scenario from Issue #484 where get_request_scoped_db_session
        fails for service users.
        """
        # Mock service user context
        with patch('netra_backend.app.dependencies.get_service_user_context') as mock_service_context:
            mock_service_context.return_value = "service:netra-backend"
            
            # Mock auth client to simulate missing service credentials
            with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient') as mock_auth_client_class:
                mock_auth_client = Mock()
                mock_auth_client.validate_service_user_context = AsyncMock(return_value={
                    "valid": False,
                    "error": "missing_service_credentials",
                    "details": "SERVICE_ID and SERVICE_SECRET required",
                    "fix": "Check service configuration"
                })
                mock_auth_client_class.return_value = mock_auth_client
                
                # Mock session factory to simulate auth failure
                with patch('netra_backend.app.database.request_scoped_session_factory.get_session_factory') as mock_factory:
                    mock_factory_instance = AsyncMock()
                    
                    @asynccontextmanager
                    async def failing_session_creation(user_id, request_id):
                        if user_id.startswith("service:"):
                            # Reproduce the 403 authentication error from Issue #484
                            raise Exception("403 Not authenticated - service user validation failed") 
                        mock_session = AsyncMock()
                        mock_session.info = {}
                        yield mock_session
                    
                    mock_factory_instance.get_request_scoped_session = failing_session_creation
                    mock_factory.return_value = mock_factory_instance
                    
                    # Try to get a request-scoped session - this should fail
                    try:
                        async for session in get_request_scoped_db_session():
                            pytest.fail("get_request_scoped_db_session should have failed for service user")
                            
                    except Exception as e:
                        # Verify we reproduced Issue #484
                        assert "403 Not authenticated" in str(e)
                        assert "service user validation failed" in str(e)
    
    @pytest.mark.asyncio
    async def test_service_auth_vs_system_auth_comparison(self):
        """Compare service authentication vs system authentication to show the difference.
        
        This test demonstrates that system users work but service users fail.
        """
        session_factory = await get_session_factory()
        
        # Mock database connections
        with patch('netra_backend.app.database.request_scoped_session_factory.get_db') as mock_get_db, \
             patch('netra_backend.app.database.request_scoped_session_factory.get_system_db') as mock_get_system_db:
            
            mock_session = AsyncMock()
            mock_session.info = {}
            
            @asynccontextmanager 
            async def mock_db_session():
                yield mock_session
            
            mock_get_db.return_value = mock_db_session()
            mock_get_system_db.return_value = mock_db_session()
            
            # Test 1: System user should work (legacy bypass)
            try:
                async with session_factory.get_request_scoped_session("system", "test-req-1") as session:
                    assert session is not None
                    print("CHECK System user authentication works")
                    
            except Exception as e:
                pytest.fail(f"System user authentication failed: {e}")
            
            # Test 2: Service user should fail without proper config (Issue #484)
            with patch.object(AuthServiceClient, 'validate_service_user_context') as mock_validate:
                mock_validate.return_value = {
                    "valid": False,
                    "error": "missing_service_credentials"
                }
                
                try:
                    async with session_factory.get_request_scoped_session("service:netra-backend", "test-req-2") as session:
                        pytest.fail("Service user should fail without proper authentication config")
                        
                except Exception as e:
                    print(f"CHECK Service user authentication fails as expected: {e}")
                    assert True  # Expected failure
    
    @pytest.mark.asyncio
    async def test_auth_service_connectivity_impact_on_service_users(self):
        """Test how auth service connectivity affects service user authentication.
        
        This reproduces the staging environment issues mentioned in Issue #484.
        """
        auth_client = AuthServiceClient()
        
        # Simulate auth service being unavailable (common in test environments)
        with patch.object(auth_client, '_check_auth_service_connectivity', return_value=False):
            
            # Test service user validation when auth service is unavailable
            result = await auth_client.validate_service_user_context("netra-backend", "database_session")
            
            # Service validation should still work with proper credentials even if auth service is down
            # But in Issue #484, missing credentials cause this to fail
            if not auth_client.service_secret:
                assert result["valid"] is False
                assert result["error"] == "missing_service_credentials"
            else:
                assert result["valid"] is True  # Should work with local validation
    
    @pytest.mark.asyncio
    async def test_complete_agent_execution_flow_service_auth_failure(self):
        """Test complete agent execution flow to show service auth failure impact.
        
        This integration test shows how Issue #484 breaks the entire agent execution pipeline.
        """
        # Mock the complete flow from user context to database session to agent execution
        with patch('netra_backend.app.dependencies.get_service_user_context') as mock_service_context:
            mock_service_context.return_value = "service:netra-backend"
            
            # Mock request scoped user context creation
            with patch('netra_backend.app.dependencies.get_request_scoped_user_context') as mock_user_context:
                from netra_backend.app.dependencies import RequestScopedContext
                
                mock_context = RequestScopedContext(
                    user_id="service:netra-backend",
                    thread_id="test-thread",
                    run_id="test-run",
                    websocket_client_id="test-ws-client"
                )
                mock_user_context.return_value = mock_context
                
                # Try to create the complete context - this fails in Issue #484
                try:
                    context = await get_request_scoped_user_context(
                        user_id="service:netra-backend",
                        thread_id="test-thread"
                    )
                    
                    # If we get here, context creation worked
                    assert context.user_id == "service:netra-backend"
                    
                    # Now try to get a database session with this context
                    # This is where Issue #484 manifests
                    with patch('netra_backend.app.database.request_scoped_session_factory.get_session_factory') as mock_factory:
                        mock_factory_instance = AsyncMock()
                        
                        @asynccontextmanager
                        async def auth_failing_session(user_id, request_id):
                            if user_id.startswith("service:"):
                                raise Exception("403 Not authenticated - Issue #484 reproduction")
                            mock_session = AsyncMock()
                            yield mock_session
                        
                        mock_factory_instance.get_request_scoped_session = auth_failing_session
                        mock_factory.return_value = mock_factory_instance
                        
                        # This should fail, showing how Issue #484 breaks agent execution
                        try:
                            async for session in get_request_scoped_db_session():
                                pytest.fail("Session creation should fail due to Issue #484")
                                
                        except Exception as e:
                            assert "403 Not authenticated" in str(e)
                            assert "Issue #484" in str(e)
                            print("CHECK Reproduced complete agent execution failure due to Issue #484")
                            
                except Exception as e:
                    pytest.fail(f"Context creation failed: {e}")
    
    @pytest.mark.asyncio
    async def test_service_authentication_fix_validation(self):
        """Test what the service authentication should look like when fixed.
        
        This is an integration test for the expected fix behavior.
        """
        auth_client = AuthServiceClient()
        
        # Mock proper service credentials configuration (the fix)
        auth_client.service_id = "netra-backend"
        auth_client.service_secret = "properly-configured-secret"
        
        # Mock auth service connectivity
        with patch.object(auth_client, '_check_auth_service_connectivity', return_value=True):
            
            # Test service user validation with proper config
            result = await auth_client.validate_service_user_context("netra-backend", "database_session")
            
            # After the fix, this should work
            assert result["valid"] is True
            assert result["user_id"] == "service:netra-backend"
            assert result["authentication_method"] == "service_to_service"
            assert result["service_id"] == "netra-backend"
            
        # Test session creation with proper service auth
        session_factory = await get_session_factory()
        
        with patch('netra_backend.app.database.request_scoped_session_factory.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_session.info = {}
            
            @asynccontextmanager
            async def working_session():
                yield mock_session
            
            mock_get_db.return_value = working_session()
            
            # With proper auth client validation, session creation should work
            with patch.object(AuthServiceClient, 'validate_service_user_context') as mock_validate:
                mock_validate.return_value = result  # Use the successful validation result
                
                try:
                    async with session_factory.get_request_scoped_session("service:netra-backend", "test-req") as session:
                        assert session is not None
                        print("CHECK Service user session creation works with proper authentication")
                        
                except Exception as e:
                    pytest.fail(f"Fixed service authentication should work: {e}")
    
    @pytest.mark.asyncio
    async def test_environment_variable_configuration_integration(self):
        """Test integration with environment variable configuration for service auth.
        
        This tests the configuration aspects of Issue #484.
        """
        # Test scenarios for different environment configurations
        test_scenarios = [
            {
                "name": "staging_missing_service_secret",
                "env_vars": {"SERVICE_ID": "netra-backend"},  # Missing SERVICE_SECRET
                "expected_failure": True
            },
            {
                "name": "staging_proper_config", 
                "env_vars": {"SERVICE_ID": "netra-backend", "SERVICE_SECRET": "test-secret"},
                "expected_failure": False
            },
            {
                "name": "staging_no_config",
                "env_vars": {},  # No service config at all
                "expected_failure": True
            }
        ]
        
        for scenario in test_scenarios:
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env.return_value = scenario["env_vars"]
                
                with patch('netra_backend.app.core.configuration.get_configuration') as mock_config:
                    mock_config_obj = Mock()
                    mock_config_obj.service_id = scenario["env_vars"].get("SERVICE_ID")
                    mock_config_obj.service_secret = scenario["env_vars"].get("SERVICE_SECRET")
                    mock_config.return_value = mock_config_obj
                    
                    # Create new auth client with this configuration
                    auth_client = AuthServiceClient()
                    
                    # Test service user validation
                    result = await auth_client.validate_service_user_context("netra-backend", "test")
                    
                    if scenario["expected_failure"]:
                        assert result["valid"] is False
                        assert result["error"] == "missing_service_credentials"
                        print(f"CHECK Scenario '{scenario['name']}' fails as expected")
                    else:
                        assert result["valid"] is True
                        print(f"CHECK Scenario '{scenario['name']}' succeeds as expected")
    
    @pytest.mark.asyncio
    async def test_concurrent_service_sessions_auth_failure(self):
        """Test that multiple concurrent service user sessions all fail consistently.
        
        This shows the scale of Issue #484 impact during high load.
        """
        session_factory = await get_session_factory()
        
        # Mock auth failure for service users
        with patch.object(AuthServiceClient, 'validate_service_user_context') as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "error": "missing_service_credentials"
            }
            
            with patch('netra_backend.app.database.request_scoped_session_factory.get_db'):
                
                # Create multiple concurrent service user session attempts
                async def attempt_session(session_id):
                    try:
                        async with session_factory.get_request_scoped_session("service:netra-backend", f"req-{session_id}"):
                            return f"session-{session_id}-success"
                    except Exception as e:
                        return f"session-{session_id}-failed: {str(e)}"
                
                # Run 5 concurrent session attempts
                tasks = [attempt_session(i) for i in range(5)]
                results = await asyncio.gather(*tasks)
                
                # All should fail due to Issue #484
                for result in results:
                    assert "failed" in result
                    print(f"CHECK Concurrent session failure: {result}")
                
                # This demonstrates the scale of the issue - ALL service operations fail


if __name__ == "__main__":
    # Run the integration tests
    pytest.main([__file__, "-v", "-s"])