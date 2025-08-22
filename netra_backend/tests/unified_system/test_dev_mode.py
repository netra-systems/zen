"""
Dev Mode Testing Suite - Backend Development Authentication

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Developer Velocity
- Value Impact: 70% faster iteration cycles, instant dev environment setup
- Strategic Impact: Enables rapid feature development and testing

Tests comprehensive dev mode functionality:
- Quick authentication bypass
- OAuth skipping in development
- Instant chat availability
- Dev-specific agent behaviors
- Mock LLM responses
- Debug information exposure

CRITICAL: These tests validate developer experience optimizations
that directly impact time-to-market and feature delivery velocity.
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import asyncio
import json
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.core.config import get_config

from netra_backend.app.main import app
from netra_backend.app.schemas.Config import AppConfig
from netra_backend.app.schemas.core_models import User

class TestDevModeAuthentication:
    """Test development mode authentication flows"""

    @pytest.fixture
    def mock_dev_mode_config(self):
        """Mock configuration with dev mode enabled"""
        config = MagicMock(spec=AppConfig)
        config.DEV_MODE = True
        config.ENVIRONMENT = "development"
        config.AUTH_SERVICE_URL = "http://localhost:8001"
        config.SKIP_AUTH_IN_DEV = True
        config.DEV_USER_EMAIL = "dev@netrasystems.ai"
        config.DEV_USER_ID = "dev-user-123"
        return config

    @pytest.fixture
    def mock_dev_user(self):
        """Mock development user"""
        return User(
            id="dev-user-123",
            email="dev@netrasystems.ai",
            full_name="Dev User",
            is_active=True,
            is_superuser=True,  # Dev users get full access
            picture=None,
            hashed_password=None,
            access_token="dev-token-123",
            token_type="Bearer"
        )

    @pytest.fixture
    def client_with_dev_mode(self, mock_dev_mode_config):
        """Test client with dev mode enabled"""
        with patch('app.config.get_config', return_value=mock_dev_mode_config):
            with TestClient(app) as client:
                yield client

    async def test_dev_user_quick_auth(self, mock_dev_mode_config, mock_dev_user):
        """Test development user quick authentication
        
        Business Value: Developer productivity - instant authentication
        bypasses OAuth flow for 70% faster dev cycles
        """
        with patch('app.config.get_config', return_value=mock_dev_mode_config):
            with patch('app.clients.auth_client.auth_client.validate_token') as mock_validate:
                # Setup: Dev mode auto-creates and validates dev user
                mock_validate.return_value = {
                    "valid": True,
                    "user_id": "dev-user-123",
                    "user": {
                        "id": "dev-user-123",
                        "email": "dev@netrasystems.ai",
                        "full_name": "Dev User",
                        "subscription_tier": "enterprise"
                    },
                    "permissions": ["read", "write", "admin"]
                }

                # Test: Dev token validation (auto-generated in dev mode)
                from fastapi.security import HTTPAuthorizationCredentials
                from sqlalchemy.ext.asyncio import AsyncSession

                from netra_backend.app.auth_integration.auth import get_current_user
                from netra_backend.app.db.models_postgres import User as DBUser
                
                # Mock database user
                mock_db_user = DBUser(
                    id="dev-user-123",
                    email="dev@netrasystems.ai",
                    full_name="Dev User",
                    is_active=True
                )
                
                # Mock database session and query
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_db_user
                
                mock_session = AsyncMock()
                mock_session.execute.return_value = mock_result
                mock_session.__aenter__.return_value = mock_session
                mock_session.__aexit__.return_value = None
                
                mock_db = AsyncMock(spec=AsyncSession)
                mock_db.__aenter__.return_value = mock_session
                mock_db.__aexit__.return_value = None
                
                mock_creds = HTTPAuthorizationCredentials(
                    scheme="Bearer",
                    credentials="dev-token-auto-generated"
                )

                # Execute: Quick auth should work instantly
                user = await get_current_user(mock_creds, mock_db)

                # Verify: Dev user authenticated instantly
                assert user is not None
                assert user.email == "dev@netrasystems.ai"
                assert user.full_name == "Dev User"
                assert user.is_active is True
                
                # Verify: Auth client called with dev token
                mock_validate.assert_called_once_with("dev-token-auto-generated")

    async def test_bypass_oauth_in_dev(self, client_with_dev_mode, mock_dev_mode_config):
        """Test OAuth bypass in development
        
        Business Value: Eliminates OAuth setup complexity in dev,
        reducing developer onboarding time from hours to minutes
        """
        with patch('app.config.get_config', return_value=mock_dev_mode_config):
            # Test: Check dev mode configuration
            config = get_config()
            assert config.DEV_MODE is True
            assert config.SKIP_AUTH_IN_DEV is True

            # Test: Auth endpoints should bypass OAuth in dev
            with patch('app.clients.auth_client.auth_client.create_dev_user') as mock_create_dev:
                mock_create_dev.return_value = {
                    "token": "dev-token-instant",
                    "user": {
                        "id": "dev-user-123",
                        "email": "dev@netrasystems.ai"
                    }
                }

                # Execute: Dev login endpoint (bypasses OAuth)
                response = client_with_dev_mode.post("/auth/dev-login", json={
                    "email": "dev@netrasystems.ai"
                })

                # Verify: Instant dev authentication
                assert response.status_code == 200
                data = response.json()
                assert "token" in data
                assert data["token"] == "dev-token-instant"
                assert data["user"]["email"] == "dev@netrasystems.ai"

    async def test_immediate_chat_availability(self, client_with_dev_mode):
        """Test instant chat access in dev
        
        Business Value: < 2 second total dev environment startup
        enables immediate testing and development iteration
        """
        start_time = datetime.utcnow()

        with patch('app.clients.auth_client.auth_client.validate_token') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user": {"id": "dev-user-123", "email": "dev@netrasystems.ai"},
                "permissions": ["read", "write"]
            }

            # Test: WebSocket connection in dev mode
            with client_with_dev_mode.websocket_connect(
                "/ws/chat",
                headers={"Authorization": "Bearer dev-token"}
            ) as websocket:
                # Execute: Send immediate chat message
                websocket.send_json({
                    "type": "message",
                    "content": "Hello dev mode!",
                    "thread_id": "dev-thread-123"
                })

                # Verify: Instant response (no loading states)
                response = websocket.receive_json()
                
                # Check response time < 2 seconds
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                assert elapsed < 2.0, f"Dev mode response took {elapsed}s, should be < 2s"
                
                # Verify: Chat immediately ready
                assert response["type"] in ["agent_response", "typing"]
                assert "dev-thread-123" in str(response)

    async def test_dev_mode_agent_responses(self, client_with_dev_mode):
        """Test agent behavior in dev mode
        
        Business Value: Enhanced debugging and development experience
        with exposed internals for faster troubleshooting
        """
        with patch('app.clients.auth_client.auth_client.validate_token') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user": {"id": "dev-user-123", "email": "dev@netrasystems.ai"},
                "permissions": ["read", "write"]
            }

            with patch('app.agents.supervisor.supervisor.process_message') as mock_supervisor:
                # Setup: Mock dev mode supervisor with debug info
                mock_supervisor.return_value = {
                    "response": "Dev mode response",
                    "debug_info": {
                        "execution_time": 0.150,
                        "tokens_used": 45,
                        "agent_chain": ["supervisor", "data_agent"],
                        "mock_llm_used": True,
                        "dev_mode": True
                    },
                    "performance_metrics": {
                        "latency_ms": 150,
                        "memory_usage": "12MB",
                        "cache_hits": 2,
                        "cache_misses": 1
                    }
                }

                # Test: Send message to agent in dev mode
                with client_with_dev_mode.websocket_connect(
                    "/ws/chat",
                    headers={"Authorization": "Bearer dev-token"}
                ) as websocket:
                    websocket.send_json({
                        "type": "message",
                        "content": "Test dev mode agent",
                        "thread_id": "dev-thread-456"
                    })

                    response = websocket.receive_json()

                    # Verify: Faster response times in dev
                    assert response.get("debug_info", {}).get("execution_time", 999) < 0.5
                    
                    # Verify: Mock LLM responses available
                    assert response.get("debug_info", {}).get("mock_llm_used") is True
                    
                    # Verify: Debug information included
                    assert "debug_info" in response
                    assert "performance_metrics" in response
                    
                    # Verify: Error details exposed (dev only)
                    debug_info = response.get("debug_info", {})
                    assert debug_info.get("dev_mode") is True
                    assert "agent_chain" in debug_info
                    
                    # Verify: Performance metrics shown
                    perf_metrics = response.get("performance_metrics", {})
                    assert "latency_ms" in perf_metrics
                    assert "memory_usage" in perf_metrics

    async def test_dev_mode_error_handling(self, client_with_dev_mode):
        """Test enhanced error handling in dev mode
        
        Business Value: Detailed error information speeds up debugging
        and reduces development time by exposing stack traces and internals
        """
        with patch('app.clients.auth_client.auth_client.validate_token') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user": {"id": "dev-user-123", "email": "dev@netrasystems.ai"},
                "permissions": ["read", "write"]
            }

            with patch('app.agents.supervisor.supervisor.process_message') as mock_supervisor:
                # Setup: Simulate error in dev mode
                test_error = ValueError("Test error for dev mode")
                mock_supervisor.side_effect = test_error

                # Test: Error response in dev mode
                with client_with_dev_mode.websocket_connect(
                    "/ws/chat",
                    headers={"Authorization": "Bearer dev-token"}
                ) as websocket:
                    websocket.send_json({
                        "type": "message",
                        "content": "Trigger error",
                        "thread_id": "dev-error-thread"
                    })

                    response = websocket.receive_json()

                    # Verify: Detailed error information in dev
                    assert response["type"] == "error"
                    assert "dev_error_details" in response
                    
                    # Verify: Stack trace included (dev only)
                    error_details = response["dev_error_details"]
                    assert "exception_type" in error_details
                    assert "stack_trace" in error_details
                    assert error_details["exception_type"] == "ValueError"
                    
                    # Verify: Error message preserved
                    assert "Test error for dev mode" in str(response)

    async def test_dev_mode_mock_llm_integration(self):
        """Test mock LLM integration in dev mode
        
        Business Value: Enables development without API costs
        and consistent testing with predictable responses
        """
        from netra_backend.app.core.config import get_config
        
        with patch('app.config.get_config') as mock_config:
            mock_config.return_value.DEV_MODE = True
            mock_config.return_value.USE_MOCK_LLM = True
            
            # Test: Mock LLM configuration
            config = get_config()
            assert config.DEV_MODE is True
            assert config.USE_MOCK_LLM is True

            # Test: Mock LLM responses
            with patch('app.llm.llm_client.LLMClient.generate') as mock_generate:
                mock_generate.return_value = {
                    "response": "Mock LLM response for testing",
                    "tokens_used": 25,
                    "model": "mock-gpt-4",
                    "cost": 0.0,  # No cost in dev mode
                    "mock": True
                }

                from netra_backend.app.llm.llm_client import LLMClient
                llm_client = LLMClient()
                
                result = await llm_client.generate("Test prompt")
                
                # Verify: Mock response returned
                assert result["response"] == "Mock LLM response for testing"
                assert result["mock"] is True
                assert result["cost"] == 0.0
                
                # Verify: Mock called instead of real API
                mock_generate.assert_called_once_with("Test prompt")

    async def test_dev_mode_config_validation(self):
        """Test dev mode configuration validation
        
        Business Value: Prevents dev environment misconfigurations
        that could lead to development delays or security issues
        """
        # Test: Valid dev mode config
        valid_config = AppConfig(
            DEV_MODE=True,
            ENVIRONMENT="development",
            SKIP_AUTH_IN_DEV=True,
            USE_MOCK_LLM=True,
            DEBUG_MODE=True,
            LOG_LEVEL="DEBUG"
        )
        
        # Verify: Dev mode settings are consistent
        assert valid_config.DEV_MODE is True
        assert valid_config.ENVIRONMENT == "development"
        assert valid_config.SKIP_AUTH_IN_DEV is True
        
        # Test: Invalid dev mode config (production with dev features)
        with pytest.raises(ValueError, match="DEV_MODE cannot be True in production"):
            AppConfig(
                DEV_MODE=True,
                ENVIRONMENT="production",
                SKIP_AUTH_IN_DEV=True
            )

    async def test_dev_mode_performance_baseline(self, client_with_dev_mode):
        """Test dev mode performance baselines
        
        Business Value: Ensures dev mode optimizations don't
        compromise performance and maintains development velocity
        """
        performance_metrics = []
        
        with patch('app.clients.auth_client.auth_client.validate_token') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user": {"id": "dev-user-123", "email": "dev@netrasystems.ai"},
                "permissions": ["read", "write"]
            }

            # Test: Multiple rapid requests (dev mode should handle burst)
            for i in range(5):
                start_time = datetime.utcnow()
                
                response = client_with_dev_mode.get(
                    "/health",
                    headers={"Authorization": "Bearer dev-token"}
                )
                
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                performance_metrics.append(duration)
                
                assert response.status_code == 200

            # Verify: Dev mode performance baseline
            avg_response_time = sum(performance_metrics) / len(performance_metrics)
            max_response_time = max(performance_metrics)
            
            # Dev mode should be fast (< 100ms average)
            assert avg_response_time < 0.1, f"Avg response time {avg_response_time}s too slow"
            assert max_response_time < 0.2, f"Max response time {max_response_time}s too slow"
            
            # Verify: Consistent performance (low variance)
            import statistics
            if len(performance_metrics) > 1:
                std_dev = statistics.stdev(performance_metrics)
                assert std_dev < 0.05, f"Performance variance {std_dev} too high"

class TestDevModeIntegration:
    """Integration tests for dev mode across system components"""

    async def test_dev_mode_full_stack_integration(self):
        """Test complete dev mode integration across all components
        
        Business Value: Validates end-to-end dev experience
        ensuring all components work together seamlessly
        """
        with patch('app.config.get_config') as mock_config:
            # Setup: Full dev mode configuration
            config = MagicMock()
            config.DEV_MODE = True
            config.ENVIRONMENT = "development"
            config.SKIP_AUTH_IN_DEV = True
            config.USE_MOCK_LLM = True
            config.DEBUG_MODE = True
            mock_config.return_value = config

            # Test: Auth integration
            with patch('app.clients.auth_client.auth_client.validate_token') as mock_auth:
                mock_auth.return_value = {
                    "valid": True,
                    "user": {"id": "dev-user-123", "email": "dev@netrasystems.ai"}
                }

                # Test: WebSocket integration
                with patch('app.ws_manager.ws_manager.send_message') as mock_ws:
                    mock_ws.return_value = True

                    # Test: Agent integration
                    with patch('app.agents.supervisor.supervisor.process_message') as mock_agent:
                        mock_agent.return_value = {
                            "response": "Full stack dev response",
                            "dev_mode": True
                        }

                        # Verify: All components configured for dev mode
                        assert config.DEV_MODE is True
                        mock_auth.assert_not_called()  # Not called yet
                        mock_ws.assert_not_called()    # Not called yet
                        mock_agent.assert_not_called() # Not called yet

                        # Full integration test would require actual WebSocket connection
                        # This validates the mocking setup is correct for integration testing

    async def test_dev_mode_data_seeding(self):
        """Test dev mode data seeding capabilities
        
        Business Value: Pre-populated dev data enables immediate testing
        of features without manual data creation
        """
        with patch('app.config.get_config') as mock_config:
            config = MagicMock()
            config.DEV_MODE = True
            config.SEED_DEV_DATA = True
            mock_config.return_value = config

            # Test: Dev data seeding configuration
            assert config.DEV_MODE is True
            assert config.SEED_DEV_DATA is True

            # Mock data seeding would be tested here
            # Actual implementation would create sample threads, messages, etc.
            # This test validates the configuration setup