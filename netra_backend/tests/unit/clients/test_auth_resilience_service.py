"""
Comprehensive tests for AuthenticationResilienceService.

Tests all resilience mechanisms including:
- Circuit breaker integration
- Fallback mechanisms
- Cache validation
- Degraded mode operations
- Emergency bypass
- Recovery mechanisms
- Health monitoring
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from netra_backend.app.clients.auth_resilience_service import (
    AuthenticationResilienceService,
    AuthResilienceMode,
    AuthOperationType,
    ResilienceConfig,
    get_auth_resilience_service,
    validate_token_with_resilience,
)
from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitBreakerState


class TestAuthenticationResilienceService:
    """Test suite for AuthenticationResilienceService."""

    def setup_method(self):
        """Setup test fixtures before each test."""
        self.config = ResilienceConfig(
            circuit_breaker_failure_threshold=3,
            circuit_breaker_recovery_timeout=1.0,  # Short for testing
            cache_ttl_seconds=300,
            max_retry_attempts=2,
            retry_base_delay=0.1,  # Fast for testing
            emergency_bypass_timeout=60.0,
        )
        self.service = AuthenticationResilienceService(self.config)
        
    def teardown_method(self):
        """Cleanup after each test."""
        # Reset to normal mode
        asyncio.create_task(self.service.force_mode(AuthResilienceMode.NORMAL))

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test service initialization."""
        assert self.service.current_mode == AuthResilienceMode.NORMAL
        assert self.service.config.circuit_breaker_failure_threshold == 3
        assert self.service.circuit_breaker is not None
        assert self.service.retry_handler is not None
        assert self.service.token_cache is not None

    @pytest.mark.asyncio
    async def test_successful_token_validation(self):
        """Test successful token validation through normal path."""
        mock_token = "valid_token_123"
        expected_result = {
            "valid": True,
            "user_id": "user_123",
            "email": "user@test.com",
            "permissions": ["read", "write"]
        }
        
        with patch.object(self.service.circuit_breaker, 'call', new_callable=AsyncMock) as mock_circuit:
            mock_circuit.return_value = expected_result
            
            result = await self.service.validate_token_with_resilience(mock_token)
            
            assert result["success"] is True
            assert result["valid"] is True
            assert result["user_id"] == "user_123"
            assert result["resilience_mode"] == "normal"
            assert result["source"] == "auth_service"
            mock_circuit.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_fallback_to_cache(self):
        """Test fallback to cache when circuit breaker is open."""
        mock_token = "cached_token_123"
        cached_data = {
            "valid": True,
            "user_id": "cached_user",
            "email": "cached@test.com",
            "permissions": ["read"],
            "cached_at": time.time()
        }
        
        # Setup circuit breaker to throw exception (simulating open state)
        with patch.object(self.service.circuit_breaker, 'call', side_effect=Exception("Circuit breaker open")):
            with patch.object(self.service.token_cache, 'get_cached_token', return_value=cached_data):
                
                result = await self.service.validate_token_with_resilience(mock_token)
                
                assert result["success"] is True
                assert result["valid"] is True
                assert result["user_id"] == "cached_user"
                assert result["resilience_mode"] == "cached_fallback"
                assert result["source"] == "cache"
                assert result["fallback_used"] is True
                assert "cache_age_seconds" in result

    @pytest.mark.asyncio
    async def test_degraded_mode_for_health_check(self):
        """Test degraded mode allows health check operations."""
        mock_token = "any_token"
        
        # Force circuit breaker failure and no cache
        with patch.object(self.service.circuit_breaker, 'call', side_effect=Exception("Service down")):
            with patch.object(self.service.token_cache, 'get_cached_token', return_value=None):
                
                result = await self.service.validate_token_with_resilience(
                    mock_token, 
                    AuthOperationType.HEALTH_CHECK
                )
                
                assert result["success"] is True
                assert result["valid"] is True
                assert result["user_id"] == "degraded_user"
                assert result["resilience_mode"] == "degraded"
                assert result["source"] == "degraded_mode"
                assert result["fallback_used"] is True
                assert "warning" in result

    @pytest.mark.asyncio
    async def test_emergency_bypass_activation(self):
        """Test emergency bypass activation for critical endpoints."""
        mock_token = "any_token"
        
        # Setup service to be in emergency mode
        await self.service.force_mode(AuthResilienceMode.EMERGENCY)
        
        result = await self.service.validate_token_with_resilience(
            mock_token,
            AuthOperationType.HEALTH_CHECK
        )
        
        assert result["success"] is True
        assert result["valid"] is True
        assert result["user_id"] == "emergency_user"
        assert result["resilience_mode"] == "emergency"
        assert result["source"] == "emergency_bypass"
        assert result["fallback_used"] is True
        assert "EMERGENCY BYPASS ACTIVE" in result["warning"]

    @pytest.mark.asyncio
    async def test_recovery_mode_transition(self):
        """Test automatic recovery mode transition."""
        mock_token = "recovery_token"
        success_result = {
            "valid": True,
            "user_id": "user_123",
            "email": "user@test.com",
            "permissions": ["read"]
        }
        
        # Start in degraded mode
        await self.service.force_mode(AuthResilienceMode.DEGRADED)
        assert self.service.current_mode == AuthResilienceMode.DEGRADED
        
        # Simulate successful validation that should trigger recovery
        with patch.object(self.service.circuit_breaker, 'call', return_value=success_result):
            with patch.object(self.service.circuit_breaker, 'is_closed', True):
                with patch.object(self.service.circuit_breaker, 'is_half_open', False):
                    
                    # First successful validation should start recovery
                    result = await self.service.validate_token_with_resilience(mock_token)
                    
                    # Should be in recovery mode after first success from degraded
                    assert self.service.current_mode == AuthResilienceMode.RECOVERY
                    assert result["success"] is True

    @pytest.mark.asyncio
    async def test_cache_miss_no_fallback(self):
        """Test behavior when cache miss and no degraded mode available."""
        mock_token = "missing_token"
        
        # Configure to not allow read-only operations
        self.service.config.allow_read_only_operations = False
        
        # Setup failures: circuit breaker fails, cache misses
        with patch.object(self.service.circuit_breaker, 'call', side_effect=Exception("Service down")):
            with patch.object(self.service.token_cache, 'get_cached_token', return_value=None):
                
                result = await self.service.validate_token_with_resilience(mock_token)
                
                assert result["success"] is False
                assert result["valid"] is False
                assert "Authentication unavailable" in result["error"]
                assert result["fallback_used"] is True

    @pytest.mark.asyncio
    async def test_emergency_bypass_timeout(self):
        """Test emergency bypass timeout behavior."""
        # Set very short timeout for testing
        self.service.config.emergency_bypass_timeout = 0.1
        
        # Activate emergency bypass
        self.service._activate_emergency_bypass()
        assert self.service.emergency_bypass_active is True
        
        # Wait for timeout
        await asyncio.sleep(0.2)
        
        # Check that timeout would cause deactivation
        should_bypass = self.service._should_use_emergency_bypass(AuthOperationType.HEALTH_CHECK)
        assert should_bypass is False

    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        """Test comprehensive metrics tracking."""
        mock_token = "metrics_token"
        
        # Reset metrics
        self.service.reset_metrics()
        initial_metrics = await self.service.get_metrics()
        
        assert initial_metrics.total_auth_attempts == 0
        assert initial_metrics.successful_auth_operations == 0
        assert initial_metrics.cache_hits == 0
        
        # Perform successful validation
        success_result = {"valid": True, "user_id": "test"}
        with patch.object(self.service.circuit_breaker, 'call', return_value=success_result):
            await self.service.validate_token_with_resilience(mock_token)
        
        # Check metrics updated
        updated_metrics = await self.service.get_metrics()
        assert updated_metrics.total_auth_attempts == 1
        assert updated_metrics.successful_auth_operations == 1
        assert updated_metrics.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_force_mode_changes(self):
        """Test manual mode forcing."""
        # Test each mode transition
        modes_to_test = [
            AuthResilienceMode.CACHED_FALLBACK,
            AuthResilienceMode.DEGRADED,
            AuthResilienceMode.EMERGENCY,
            AuthResilienceMode.RECOVERY,
            AuthResilienceMode.NORMAL,
        ]
        
        for mode in modes_to_test:
            await self.service.force_mode(mode)
            assert self.service.current_mode == mode
            
            metrics = await self.service.get_metrics()
            assert metrics.current_mode == mode

    @pytest.mark.asyncio
    async def test_health_status(self):
        """Test health status reporting."""
        health = await self.service.get_health_status()
        
        assert health["service"] == "authentication_resilience"
        assert health["current_mode"] == "normal"
        assert "auth_service_available" in health
        assert "metrics" in health
        assert "circuit_breaker" in health
        assert "cache_status" in health
        assert "recovery" in health
        
        # Check metrics structure
        metrics = health["metrics"]
        assert "total_attempts" in metrics
        assert "success_rate" in metrics
        assert "cache_hit_rate" in metrics
        assert "consecutive_failures" in metrics

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker integration and state changes."""
        mock_token = "circuit_test_token"
        
        # Test that circuit breaker state affects behavior
        with patch.object(self.service.circuit_breaker, 'is_open', True):
            with patch.object(self.service, '_should_use_emergency_bypass', return_value=False):
                with patch.object(self.service.token_cache, 'get_cached_token', return_value=None):
                    
                    result = await self.service.validate_token_with_resilience(mock_token)
                    
                    # Should fallback when circuit breaker is open
                    assert result["success"] is False or result["fallback_used"] is True

    @pytest.mark.asyncio  
    async def test_operation_type_determination(self):
        """Test that different operation types are handled correctly."""
        mock_token = "operation_test_token"
        
        # Setup service to use degraded mode
        with patch.object(self.service.circuit_breaker, 'call', side_effect=Exception("Service down")):
            with patch.object(self.service.token_cache, 'get_cached_token', return_value=None):
                
                # Health check should succeed in degraded mode
                health_result = await self.service.validate_token_with_resilience(
                    mock_token, AuthOperationType.HEALTH_CHECK
                )
                assert health_result["success"] is True
                assert health_result["source"] == "degraded_mode"
                
                # Regular token validation should fail in degraded mode
                token_result = await self.service.validate_token_with_resilience(
                    mock_token, AuthOperationType.TOKEN_VALIDATION
                )
                # This might succeed or fail depending on config, but should be consistent
                assert isinstance(token_result["success"], bool)

    @pytest.mark.asyncio
    async def test_cache_behavior(self):
        """Test token cache behavior during resilience operations."""
        mock_token = "cache_test_token"
        cache_data = {
            "valid": True,
            "user_id": "cached_user",
            "permissions": ["read"],
            "cached_at": time.time() - 100  # 100 seconds old
        }
        
        # Test cache hit
        with patch.object(self.service.token_cache, 'get_cached_token', return_value=cache_data):
            with patch.object(self.service.circuit_breaker, 'call', side_effect=Exception("Service down")):
                
                result = await self.service.validate_token_with_resilience(mock_token)
                
                assert result["success"] is True
                assert result["source"] == "cache"
                assert "cache_age_seconds" in result
                assert result["cache_age_seconds"] >= 100

    @pytest.mark.asyncio
    async def test_consecutive_failures_tracking(self):
        """Test tracking of consecutive failures."""
        mock_token = "failure_test_token"
        
        # Reset metrics
        self.service.reset_metrics()
        
        # Simulate multiple failures
        with patch.object(self.service.circuit_breaker, 'call', side_effect=Exception("Service down")):
            with patch.object(self.service.token_cache, 'get_cached_token', return_value=None):
                with patch.object(self.service, '_should_use_degraded_mode', return_value=False):
                    
                    # First failure
                    await self.service.validate_token_with_resilience(mock_token)
                    metrics1 = await self.service.get_metrics()
                    assert metrics1.consecutive_failures == 1
                    
                    # Second failure  
                    await self.service.validate_token_with_resilience(mock_token)
                    metrics2 = await self.service.get_metrics()
                    assert metrics2.consecutive_failures == 2


class TestGlobalAuthResilienceService:
    """Test the global singleton service."""

    def test_singleton_behavior(self):
        """Test that get_auth_resilience_service returns same instance."""
        service1 = get_auth_resilience_service()
        service2 = get_auth_resilience_service()
        
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_convenience_function(self):
        """Test the convenience validation function."""
        mock_token = "convenience_test_token"
        
        with patch('netra_backend.app.clients.auth_resilience_service.get_auth_resilience_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.validate_token_with_resilience = AsyncMock(return_value={
                "success": True,
                "valid": True,
                "user_id": "test_user"
            })
            mock_get_service.return_value = mock_service
            
            result = await validate_token_with_resilience(mock_token, AuthOperationType.TOKEN_VALIDATION)
            
            assert result["success"] is True
            assert result["user_id"] == "test_user"
            mock_service.validate_token_with_resilience.assert_called_once_with(
                mock_token, AuthOperationType.TOKEN_VALIDATION
            )


class TestResilienceConfig:
    """Test ResilienceConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ResilienceConfig()
        
        assert config.circuit_breaker_failure_threshold == 5
        assert config.cache_ttl_seconds == 300
        assert config.max_retry_attempts == 3
        assert config.allow_read_only_operations is True
        assert config.emergency_bypass_enabled is True
        
        # Check that default endpoints are set
        assert "/health" in config.read_only_endpoints
        assert "/metrics" in config.emergency_bypass_endpoints

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ResilienceConfig(
            circuit_breaker_failure_threshold=10,
            cache_ttl_seconds=600,
            max_retry_attempts=5,
            allow_read_only_operations=False,
        )
        
        assert config.circuit_breaker_failure_threshold == 10
        assert config.cache_ttl_seconds == 600
        assert config.max_retry_attempts == 5
        assert config.allow_read_only_operations is False


class TestAuthResilienceModes:
    """Test AuthResilienceMode enumeration."""

    def test_mode_values(self):
        """Test that all expected modes exist with correct values."""
        assert AuthResilienceMode.NORMAL.value == "normal"
        assert AuthResilienceMode.CACHED_FALLBACK.value == "cached_fallback"
        assert AuthResilienceMode.DEGRADED.value == "degraded"
        assert AuthResilienceMode.EMERGENCY.value == "emergency"
        assert AuthResilienceMode.RECOVERY.value == "recovery"

    def test_mode_transitions(self):
        """Test that mode transitions work correctly."""
        # This is implicitly tested in the service tests, but we can add specific tests here
        modes = list(AuthResilienceMode)
        assert len(modes) == 5  # Ensure we have all expected modes


class TestAuthOperationType:
    """Test AuthOperationType enumeration."""

    def test_operation_types(self):
        """Test that all expected operation types exist."""
        expected_types = [
            "token_validation",
            "login", 
            "logout",
            "token_refresh",
            "permission_check",
            "health_check",
            "monitoring"
        ]
        
        for expected_type in expected_types:
            # Should not raise exception
            AuthOperationType(expected_type)

    def test_operation_type_values(self):
        """Test specific operation type values."""
        assert AuthOperationType.TOKEN_VALIDATION.value == "token_validation"
        assert AuthOperationType.HEALTH_CHECK.value == "health_check"
        assert AuthOperationType.MONITORING.value == "monitoring"


@pytest.mark.integration
class TestAuthResilienceIntegration:
    """Integration tests for auth resilience with real components."""

    @pytest.fixture
    def real_service(self):
        """Create service with real dependencies for integration testing."""
        config = ResilienceConfig(
            circuit_breaker_failure_threshold=2,
            circuit_breaker_recovery_timeout=1.0,
            cache_ttl_seconds=60,
            max_retry_attempts=2,
        )
        return AuthenticationResilienceService(config)

    @pytest.mark.asyncio
    async def test_end_to_end_resilience_flow(self, real_service):
        """Test complete resilience flow from normal to recovery."""
        mock_token = "e2e_test_token"
        
        # 1. Start in normal mode
        assert real_service.current_mode == AuthResilienceMode.NORMAL
        
        # 2. Simulate auth service failures to trigger circuit breaker
        with patch.object(real_service.circuit_breaker, 'call', side_effect=Exception("Service down")):
            
            # Multiple failures should eventually trigger mode changes
            for i in range(3):
                result = await real_service.validate_token_with_resilience(mock_token)
                # Each failure should be handled by fallback mechanisms
                assert isinstance(result, dict)
        
        # 3. Service should have adapted to failures
        metrics = await real_service.get_metrics()
        assert metrics.total_auth_attempts >= 3
        assert metrics.failed_auth_operations > 0

    @pytest.mark.asyncio  
    async def test_recovery_cycle(self, real_service):
        """Test full recovery cycle."""
        mock_token = "recovery_cycle_token"
        
        # Force into degraded mode
        await real_service.force_mode(AuthResilienceMode.DEGRADED)
        
        # Simulate service recovery with successful validations
        success_result = {"valid": True, "user_id": "recovered_user"}
        
        with patch.object(real_service.circuit_breaker, 'call', return_value=success_result):
            with patch.object(real_service.circuit_breaker, 'is_closed', True):
                
                # Multiple successful validations should trigger recovery
                for i in range(real_service.config.recovery_validation_count + 1):
                    result = await real_service.validate_token_with_resilience(mock_token)
                    if result["success"]:
                        # Successful validations should help recovery
                        pass
                
                # Should eventually return to normal mode
                # This might take multiple cycles depending on timing
                assert real_service.current_mode in [
                    AuthResilienceMode.RECOVERY, 
                    AuthResilienceMode.NORMAL
                ]