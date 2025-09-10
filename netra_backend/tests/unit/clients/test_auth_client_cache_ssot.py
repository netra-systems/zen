"""
Test Auth Client Cache SSOT Compliance

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: System Reliability & Code Quality
- Value Impact: Ensure AuthCircuitBreakerManager properly delegates to UnifiedCircuitBreaker
- Strategic Impact: Critical for Golden Path - auth circuit breaker must work consistently

This unit test validates proper delegation patterns for SSOT compliance:
1. Mock-based validation of delegation calls to UnifiedCircuitBreaker
2. Config mapping verification between AuthCircuitBreakerManager and UnifiedCircuitBreaker
3. State management delegation testing
4. Error handling consistency validation

PURPOSE: Validate the INTERNAL delegation mechanics after SSOT migration is complete.
"""

import pytest
import asyncio
from typing import Any, Dict
from unittest.mock import patch, MagicMock, AsyncMock, call

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.clients.auth_client_cache import AuthCircuitBreakerManager
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerState
)


class TestAuthClientCacheSSOT(SSotBaseTestCase):
    """Unit tests for AuthCircuitBreakerManager SSOT delegation compliance."""

    @pytest.mark.unit
    @pytest.mark.ssot_delegation
    @patch('netra_backend.app.clients.auth_client_cache.UnifiedCircuitBreaker')
    def test_auth_circuit_breaker_manager_creates_unified_breakers(self, mock_unified_cb_class):
        """
        Test that AuthCircuitBreakerManager creates UnifiedCircuitBreaker instances.
        
        This validates the core delegation pattern - AuthCircuitBreakerManager should
        create and delegate to UnifiedCircuitBreaker instances, not implement its own logic.
        """
        # Setup mock
        mock_breaker_instance = MagicMock(spec=UnifiedCircuitBreaker)
        mock_unified_cb_class.return_value = mock_breaker_instance
        
        # Create AuthCircuitBreakerManager
        auth_cb_manager = AuthCircuitBreakerManager()
        
        # Get a circuit breaker
        breaker = auth_cb_manager.get_breaker("test_auth_service")
        
        # Verify UnifiedCircuitBreaker was instantiated
        mock_unified_cb_class.assert_called_once()
        
        # Verify the call was made with UnifiedCircuitConfig
        call_args = mock_unified_cb_class.call_args
        assert len(call_args[0]) == 1, "Should pass exactly one argument (config)"
        
        config_arg = call_args[0][0]
        assert isinstance(config_arg, UnifiedCircuitConfig), (
            f"Should pass UnifiedCircuitConfig, got {type(config_arg)}"
        )
        
        # Verify config parameters are appropriate for auth operations
        assert config_arg.name == "test_auth_service"
        assert config_arg.failure_threshold > 0
        assert config_arg.success_threshold > 0
        assert config_arg.recovery_timeout > 0
        assert config_arg.timeout_seconds > 0
        
        # Verify returned breaker is the mock instance
        assert breaker is mock_breaker_instance
        
        # Success: AuthCircuitBreakerManager properly delegates to UnifiedCircuitBreaker
        print(f"✅ DELEGATION CREATION VERIFIED: AuthCircuitBreakerManager delegates to UnifiedCircuitBreaker "
              f"with failure_threshold={config_arg.failure_threshold}, recovery_timeout={config_arg.recovery_timeout}")

    @pytest.mark.unit
    @pytest.mark.ssot_delegation
    @patch('netra_backend.app.clients.auth_client_cache.UnifiedCircuitBreaker')
    def test_auth_circuit_breaker_manager_caches_breakers(self, mock_unified_cb_class):
        """
        Test that AuthCircuitBreakerManager properly caches breaker instances.
        
        Multiple calls with the same name should return the same UnifiedCircuitBreaker instance.
        """
        # Setup mock
        mock_breaker_instance = MagicMock(spec=UnifiedCircuitBreaker)
        mock_unified_cb_class.return_value = mock_breaker_instance
        
        auth_cb_manager = AuthCircuitBreakerManager()
        
        # Get the same breaker multiple times
        breaker1 = auth_cb_manager.get_breaker("cached_auth_service")
        breaker2 = auth_cb_manager.get_breaker("cached_auth_service")
        breaker3 = auth_cb_manager.get_breaker("cached_auth_service")
        
        # Should only create UnifiedCircuitBreaker once
        assert mock_unified_cb_class.call_count == 1, (
            f"Should create UnifiedCircuitBreaker only once, got {mock_unified_cb_class.call_count} calls"
        )
        
        # All returned breakers should be the same instance
        assert breaker1 is breaker2 is breaker3 is mock_breaker_instance
        
        # Different names should create different breakers
        breaker4 = auth_cb_manager.get_breaker("different_auth_service")
        assert mock_unified_cb_class.call_count == 2, "Should create second breaker for different name"
        assert breaker4 is mock_breaker_instance  # Mock returns same instance, but would be different in real scenario
        
        # Success: AuthCircuitBreakerManager properly caches breaker instances
        print(f"✅ CACHING VERIFIED: AuthCircuitBreakerManager properly caches breaker instances")

    @pytest.mark.unit
    @pytest.mark.ssot_delegation
    @pytest.mark.asyncio
    async def test_auth_circuit_breaker_reset_all_delegation(self):
        """
        Test that reset_all() properly delegates to all cached UnifiedCircuitBreaker instances.
        """
        auth_cb_manager = AuthCircuitBreakerManager()
        
        # Create multiple mock breakers
        mock_breaker1 = MagicMock(spec=UnifiedCircuitBreaker)
        mock_breaker1.state = UnifiedCircuitBreakerState.OPEN
        mock_breaker1.failure_count = 5
        mock_breaker1.success_count = 0
        
        mock_breaker2 = MagicMock(spec=UnifiedCircuitBreaker)
        mock_breaker2.state = UnifiedCircuitBreakerState.HALF_OPEN
        mock_breaker2.failure_count = 3
        mock_breaker2.success_count = 1
        
        # Add to manager's cache directly (simulating get_breaker calls)
        auth_cb_manager._breakers = {
            "auth_service_1": mock_breaker1,
            "auth_service_2": mock_breaker2
        }
        
        # Call reset_all
        await auth_cb_manager.reset_all()
        
        # Verify all breakers were reset to CLOSED state
        assert mock_breaker1.state == UnifiedCircuitBreakerState.CLOSED
        assert mock_breaker1.failure_count == 0
        assert mock_breaker1.success_count == 0
        
        assert mock_breaker2.state == UnifiedCircuitBreakerState.CLOSED
        assert mock_breaker2.failure_count == 0
        assert mock_breaker2.success_count == 0
        
        # Success: reset_all() properly resets all UnifiedCircuitBreaker instances
        print(f"✅ RESET_ALL DELEGATION VERIFIED: All UnifiedCircuitBreaker instances reset to CLOSED state")

    @pytest.mark.unit
    @pytest.mark.ssot_delegation
    @pytest.mark.asyncio
    @patch('netra_backend.app.clients.auth_client_cache.UnifiedCircuitBreaker')
    async def test_call_with_breaker_delegation(self, mock_unified_cb_class):
        """
        Test that call_with_breaker properly delegates to UnifiedCircuitBreaker.call().
        """
        # Setup mock
        mock_breaker_instance = AsyncMock(spec=UnifiedCircuitBreaker)
        mock_breaker_instance.call = AsyncMock(return_value={"result": "success"})
        mock_unified_cb_class.return_value = mock_breaker_instance
        
        auth_cb_manager = AuthCircuitBreakerManager()
        
        # Define test function
        async def test_auth_function(token: str, user_id: str):
            return {"valid": True, "token": token, "user_id": user_id}
        
        # Call through call_with_breaker
        result = await auth_cb_manager.call_with_breaker(
            test_auth_function,
            "test_token_123",
            user_id="user_456"
        )
        
        # Verify UnifiedCircuitBreaker was created
        mock_unified_cb_class.assert_called_once()
        
        # Verify the breaker's call method was invoked with correct arguments
        mock_breaker_instance.call.assert_called_once_with(
            test_auth_function,
            "test_token_123",
            user_id="user_456"
        )
        
        # Verify result is passed through
        assert result == {"result": "success"}
        
        # Verify breaker is cached with function name
        expected_breaker_name = f"{test_auth_function.__name__}_breaker"
        assert expected_breaker_name in auth_cb_manager._breakers
        assert auth_cb_manager._breakers[expected_breaker_name] is mock_breaker_instance
        
        self.log_test_success(
            "auth_circuit_breaker_call_with_breaker_delegation",
            f"call_with_breaker properly delegates to UnifiedCircuitBreaker.call() with breaker name: {expected_breaker_name}"
        )

    @pytest.mark.unit
    @pytest.mark.ssot_delegation
    def test_auth_circuit_breaker_config_mapping(self):
        """
        Test that AuthCircuitBreakerManager maps its configuration appropriately to UnifiedCircuitConfig.
        
        This validates that auth-specific requirements are properly translated to UnifiedCircuitConfig.
        """
        with patch('netra_backend.app.clients.auth_client_cache.UnifiedCircuitBreaker') as mock_unified_cb_class:
            mock_breaker = MagicMock(spec=UnifiedCircuitBreaker)
            mock_unified_cb_class.return_value = mock_breaker
            
            auth_cb_manager = AuthCircuitBreakerManager()
            breaker = auth_cb_manager.get_breaker("auth_config_test")
            
            # Get the config that was passed to UnifiedCircuitBreaker
            call_args = mock_unified_cb_class.call_args
            config = call_args[0][0]
            
            # Validate auth-specific configuration requirements
            # Auth operations should be more tolerant than general operations
            assert config.failure_threshold >= 3, (
                f"Auth failure threshold should be >= 3 for reliability, got {config.failure_threshold}"
            )
            
            # Auth operations should recover faster for user experience
            assert config.recovery_timeout <= 30, (
                f"Auth recovery timeout should be <= 30s for UX, got {config.recovery_timeout}"
            )
            
            # Auth operations should have reasonable timeouts
            assert 1.0 <= config.timeout_seconds <= 10.0, (
                f"Auth timeout should be 1-10 seconds, got {config.timeout_seconds}"
            )
            
            # Success threshold should be reasonable for auth
            assert 1 <= config.success_threshold <= 3, (
                f"Auth success threshold should be 1-3, got {config.success_threshold}"
            )
            
            # Validate config name matches requested name
            assert config.name == "auth_config_test"
            
            self.log_test_success(
                "auth_circuit_breaker_config_mapping",
                f"AuthCircuitBreakerManager properly maps config with "
                f"failure_threshold={config.failure_threshold}, "
                f"recovery_timeout={config.recovery_timeout}, "
                f"timeout_seconds={config.timeout_seconds}"
            )

    @pytest.mark.unit
    @pytest.mark.ssot_delegation
    @pytest.mark.asyncio
    async def test_auth_circuit_breaker_error_handling_delegation(self):
        """
        Test that AuthCircuitBreakerManager properly delegates error handling to UnifiedCircuitBreaker.
        """
        with patch('netra_backend.app.clients.auth_client_cache.UnifiedCircuitBreaker') as mock_unified_cb_class:
            # Setup mock that raises an exception
            mock_breaker = AsyncMock(spec=UnifiedCircuitBreaker)
            mock_breaker.call = AsyncMock(side_effect=Exception("Circuit breaker open"))
            mock_unified_cb_class.return_value = mock_breaker
            
            auth_cb_manager = AuthCircuitBreakerManager()
            
            async def failing_auth_function():
                raise Exception("Auth service down")
            
            # Verify exception propagates through delegation
            with pytest.raises(Exception, match="Circuit breaker open"):
                await auth_cb_manager.call_with_breaker(failing_auth_function)
            
            # Verify the call was attempted on the breaker
            mock_breaker.call.assert_called_once_with(failing_auth_function)
            
            self.log_test_success(
                "auth_circuit_breaker_error_handling_delegation",
                "AuthCircuitBreakerManager properly delegates error handling to UnifiedCircuitBreaker"
            )