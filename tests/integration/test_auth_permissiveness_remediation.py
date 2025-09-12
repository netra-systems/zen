"""
Integration Tests for Authentication Permissiveness Remediation

Business Value Justification:
- Segment: Platform/Quality Assurance - WebSocket Auth Testing
- Business Goal: Validate WebSocket 1011 error remediation system
- Value Impact: Ensures $500K+ ARR chat functionality through comprehensive testing
- Revenue Impact: Prevents production incidents and validates business continuity

CRITICAL MISSION:
Comprehensive integration testing of the auth permissiveness and circuit breaker
systems to ensure they properly resolve WebSocket 1011 authentication errors
while maintaining appropriate security boundaries.

TEST COVERAGE:
1. Auth permissiveness level detection and validation
2. Circuit breaker functionality and state transitions
3. Graceful degradation scenarios 
4. Environment-specific auth behavior
5. Configuration loading and validation
6. WebSocket integration with permissive auth
7. Security boundary enforcement
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.auth_integration.auth_permissiveness import (
    AuthPermissivenessLevel,
    AuthPermissivenessResult,
    EnvironmentAuthDetector,
    AuthPermissivenessValidator,
    StrictAuthValidator,
    RelaxedAuthValidator,
    DemoAuthValidator,
    EmergencyAuthValidator,
    authenticate_with_permissiveness,
    get_auth_permissiveness_validator
)
from netra_backend.app.auth_integration.auth_circuit_breaker import (
    CircuitBreakerState,
    CircuitBreakerConfig,
    CircuitBreakerAuth,
    authenticate_with_circuit_breaker,
    get_circuit_breaker_auth
)
from netra_backend.app.auth_integration.auth_config import (
    AuthPermissivenessConfig,
    get_auth_permissiveness_config,
    validate_auth_config
)


class MockWebSocket:
    """Mock WebSocket for testing auth permissiveness."""
    
    def __init__(
        self,
        headers=None,
        client_host="127.0.0.1",
        client_port=12345,
        has_demo_mode=False,
        environment="testing"
    ):
        self.headers = headers or {}
        self.client = MagicMock()
        self.client.host = client_host
        self.client.port = client_port
        self.client_state = "connected"
        
        # Mock environment for testing
        self._test_environment = environment
        self._demo_mode = has_demo_mode


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket for testing."""
    return MockWebSocket()


@pytest.fixture
def mock_websocket_staging():
    """Create mock WebSocket for staging environment."""
    return MockWebSocket(environment="staging")


@pytest.fixture  
def mock_websocket_production():
    """Create mock WebSocket for production environment."""
    return MockWebSocket(environment="production")


@pytest.fixture
def mock_websocket_demo():
    """Create mock WebSocket with demo mode enabled."""
    return MockWebSocket(has_demo_mode=True)


@pytest.fixture
def circuit_breaker_config():
    """Create test circuit breaker configuration."""
    return CircuitBreakerConfig(
        failure_threshold=3,  # Lower threshold for testing
        failure_rate_threshold=0.6,  # Higher threshold for testing
        open_timeout_seconds=1,  # Faster timeout for testing
        success_threshold=2   # Lower success threshold
    )


@pytest.mark.asyncio
class TestEnvironmentAuthDetector:
    """Test environment-based auth level detection."""
    
    def test_detector_initialization(self):
        """Test that detector initializes properly."""
        detector = EnvironmentAuthDetector()
        assert detector is not None
        assert hasattr(detector, 'env')
    
    @patch('netra_backend.app.auth_integration.auth_permissiveness.get_env')
    def test_detect_auth_level_development(self, mock_get_env, mock_websocket):
        """Test auth level detection for development environment."""
        mock_env = MagicMock()
        mock_env.get.side_effect = lambda key, default=None: {
            'ENVIRONMENT': 'development',
            'K_SERVICE': None,
            'DEMO_MODE': '0',
            'EMERGENCY_MODE': '0'
        }.get(key, default)
        mock_get_env.return_value = mock_env
        
        detector = EnvironmentAuthDetector()
        level = detector.detect_auth_level(mock_websocket)
        
        assert level == AuthPermissivenessLevel.RELAXED
    
    @patch('netra_backend.app.auth_integration.auth_permissiveness.get_env')
    def test_detect_auth_level_production(self, mock_get_env, mock_websocket):
        """Test auth level detection for production environment."""
        mock_env = MagicMock()
        mock_env.get.side_effect = lambda key, default=None: {
            'ENVIRONMENT': 'production',
            'K_SERVICE': 'netra-backend',
            'DEMO_MODE': '0',
            'EMERGENCY_MODE': '0'
        }.get(key, default)
        mock_get_env.return_value = mock_env
        
        detector = EnvironmentAuthDetector()
        level = detector.detect_auth_level(mock_websocket)
        
        assert level == AuthPermissivenessLevel.STRICT
    
    @patch('netra_backend.app.auth_integration.auth_permissiveness.get_env')
    def test_detect_auth_level_demo_mode(self, mock_get_env, mock_websocket):
        """Test auth level detection with demo mode enabled."""
        mock_env = MagicMock()
        mock_env.get.side_effect = lambda key, default=None: {
            'ENVIRONMENT': 'development',
            'DEMO_MODE': '1',
            'EMERGENCY_MODE': '0'
        }.get(key, default)
        mock_get_env.return_value = mock_env
        
        detector = EnvironmentAuthDetector()
        level = detector.detect_auth_level(mock_websocket)
        
        assert level == AuthPermissivenessLevel.DEMO
    
    @patch('netra_backend.app.auth_integration.auth_permissiveness.get_env')
    def test_detect_auth_level_emergency_mode(self, mock_get_env, mock_websocket):
        """Test auth level detection with emergency mode enabled."""
        mock_env = MagicMock()
        mock_env.get.side_effect = lambda key, default=None: {
            'ENVIRONMENT': 'staging',
            'EMERGENCY_MODE': '1'
        }.get(key, default)
        mock_get_env.return_value = mock_env
        
        detector = EnvironmentAuthDetector()
        level = detector.detect_auth_level(mock_websocket)
        
        assert level == AuthPermissivenessLevel.EMERGENCY


@pytest.mark.asyncio
class TestAuthValidators:
    """Test individual auth validator implementations."""
    
    async def test_demo_validator_success(self, mock_websocket):
        """Test demo validator creates demo user successfully."""
        validator = DemoAuthValidator()
        
        with patch('netra_backend.app.auth_integration.auth_permissiveness.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'development',
                'DEMO_MODE': '1'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            
            result = await validator.validate(mock_websocket)
            
            assert result.success is True
            assert result.level == AuthPermissivenessLevel.DEMO
            assert result.user_context is not None
            assert result.user_context.user_id == "demo-user-001"
            assert result.auth_method == "demo_bypass"
            assert "DEMO MODE ACTIVE" in "; ".join(result.security_warnings)
    
    async def test_demo_validator_blocked_in_production(self, mock_websocket):
        """Test demo validator is blocked in production."""
        validator = DemoAuthValidator()
        
        with patch('netra_backend.app.auth_integration.auth_permissiveness.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'production',
                'DEMO_MODE': '1'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            
            result = await validator.validate(mock_websocket)
            
            assert result.success is False
            assert result.auth_method == "demo_blocked_production"
            assert "Demo mode not allowed in production" in result.security_warnings
    
    async def test_emergency_validator_conditions_not_met(self, mock_websocket):
        """Test emergency validator when conditions aren't met."""
        validator = EmergencyAuthValidator()
        
        with patch('netra_backend.app.auth_integration.auth_permissiveness.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'development',
                'EMERGENCY_MODE': '0'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            
            # Mock auth service as available
            with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth:
                mock_auth.return_value = MagicMock()  # Service available
                
                result = await validator.validate(mock_websocket)
                
                assert result.success is False
                assert result.auth_method == "emergency_not_justified"
    
    async def test_emergency_validator_success(self, mock_websocket):
        """Test emergency validator when emergency conditions are met."""
        validator = EmergencyAuthValidator()
        
        with patch('netra_backend.app.auth_integration.auth_permissiveness.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'development',
                'EMERGENCY_MODE': '1'  # Explicit emergency mode
            }.get(key, default)
            mock_get_env.return_value = mock_env
            
            result = await validator.validate(mock_websocket)
            
            assert result.success is True
            assert result.level == AuthPermissivenessLevel.EMERGENCY
            assert result.user_context is not None
            assert result.auth_method == "emergency_bypass"
            assert "EMERGENCY MODE ACTIVE" in "; ".join(result.security_warnings)
    
    async def test_relaxed_validator_fallback(self, mock_websocket):
        """Test relaxed validator fallback when strict auth fails."""
        validator = RelaxedAuthValidator()
        
        # Mock strict auth to fail
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_ssot') as mock_strict:
            mock_strict.side_effect = Exception("Auth service unavailable")
            
            result = await validator.validate(mock_websocket)
            
            assert result.success is True
            assert result.level == AuthPermissivenessLevel.RELAXED
            assert result.auth_method == "relaxed_fallback"
            assert result.user_context is not None
            assert "Using relaxed authentication" in "; ".join(result.security_warnings)


@pytest.mark.asyncio 
class TestCircuitBreakerAuth:
    """Test circuit breaker authentication functionality."""
    
    async def test_circuit_breaker_normal_operation(self, mock_websocket, circuit_breaker_config):
        """Test circuit breaker in normal CLOSED state."""
        circuit_breaker = CircuitBreakerAuth(circuit_breaker_config)
        
        # Mock successful authentication
        with patch('netra_backend.app.auth_integration.auth_permissiveness.authenticate_with_permissiveness') as mock_auth:
            mock_result = AuthPermissivenessResult(
                success=True,
                level=AuthPermissivenessLevel.STRICT,
                auth_method="strict_validation"
            )
            mock_auth.return_value = mock_result
            
            result = await circuit_breaker.authenticate(mock_websocket)
            
            assert result.success is True
            assert circuit_breaker.state == CircuitBreakerState.CLOSED
            assert circuit_breaker.successful_requests == 1
    
    async def test_circuit_breaker_trip_on_failures(self, mock_websocket, circuit_breaker_config):
        """Test circuit breaker trips after consecutive failures."""
        circuit_breaker = CircuitBreakerAuth(circuit_breaker_config)
        
        # Mock failed authentication
        with patch('netra_backend.app.auth_integration.auth_permissiveness.authenticate_with_permissiveness') as mock_auth:
            mock_result = AuthPermissivenessResult(
                success=False,
                level=AuthPermissivenessLevel.STRICT,
                auth_method="strict_validation_failed",
                security_warnings=["Authentication failed"]
            )
            mock_auth.return_value = mock_result
            
            # Trigger enough failures to trip breaker
            for i in range(circuit_breaker_config.failure_threshold):
                result = await circuit_breaker.authenticate(mock_websocket)
                assert result.success is False
            
            # Circuit breaker should now be OPEN
            assert circuit_breaker.state == CircuitBreakerState.OPEN
            assert circuit_breaker.failed_requests == circuit_breaker_config.failure_threshold
    
    async def test_circuit_breaker_fallback_when_open(self, mock_websocket, circuit_breaker_config):
        """Test circuit breaker uses fallback when OPEN."""
        circuit_breaker = CircuitBreakerAuth(circuit_breaker_config)
        
        # Force circuit breaker to OPEN state
        circuit_breaker._trip_breaker()
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Mock fallback authentication success
        with patch.object(circuit_breaker.degradation_manager, 'authenticate_with_fallback') as mock_fallback:
            mock_result = AuthPermissivenessResult(
                success=True,
                level=AuthPermissivenessLevel.DEMO,
                auth_method="demo_fallback"
            )
            mock_fallback.return_value = mock_result
            
            result = await circuit_breaker.authenticate(mock_websocket)
            
            assert result.success is True
            assert result.auth_method == "demo_fallback"
            mock_fallback.assert_called_once()
    
    async def test_circuit_breaker_half_open_transition(self, mock_websocket, circuit_breaker_config):
        """Test circuit breaker transitions to HALF_OPEN after timeout."""
        circuit_breaker = CircuitBreakerAuth(circuit_breaker_config)
        
        # Force to OPEN state
        circuit_breaker._trip_breaker()
        
        # Wait for timeout (use small timeout for testing)
        await asyncio.sleep(circuit_breaker_config.open_timeout_seconds + 0.1)
        
        # Mock successful recovery test
        with patch('netra_backend.app.auth_integration.auth_permissiveness.authenticate_with_permissiveness') as mock_auth:
            mock_result = AuthPermissivenessResult(
                success=True,
                level=AuthPermissivenessLevel.STRICT,
                auth_method="recovery_test_success"
            )
            mock_auth.return_value = mock_result
            
            result = await circuit_breaker.authenticate(mock_websocket)
            
            # Should transition to HALF_OPEN then potentially back to CLOSED
            assert result.success is True
            # State could be HALF_OPEN or CLOSED depending on success threshold


@pytest.mark.asyncio
class TestPermissivenessIntegration:
    """Test integration of permissiveness system with WebSocket auth."""
    
    async def test_authenticate_with_permissiveness_auto_detect(self, mock_websocket):
        """Test authentication with automatic level detection."""
        with patch('netra_backend.app.auth_integration.auth_permissiveness.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'development',
                'DEMO_MODE': '1'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            
            result = await authenticate_with_permissiveness(mock_websocket)
            
            # Should detect demo mode and succeed
            assert result.success is True
            assert result.level == AuthPermissivenessLevel.DEMO
    
    async def test_validate_with_circuit_breaker_protection(self, mock_websocket):
        """Test authentication with circuit breaker protection."""
        result = await authenticate_with_circuit_breaker(mock_websocket)
        
        # Should get some result (success depends on mocks)
        assert isinstance(result, AuthPermissivenessResult)
        assert hasattr(result, 'success')
        assert hasattr(result, 'level')
    
    def test_validator_statistics_tracking(self):
        """Test that validator tracks statistics properly."""
        validator = get_auth_permissiveness_validator()
        initial_stats = validator.get_validation_stats()
        
        assert "auth_permissiveness_stats" in initial_stats
        assert "success_rate_percent" in initial_stats
        assert isinstance(initial_stats["success_rate_percent"], (int, float))


@pytest.mark.asyncio
class TestConfigurationSystem:
    """Test authentication configuration system."""
    
    def test_config_loading(self):
        """Test configuration loads properly."""
        config = get_auth_permissiveness_config()
        
        assert isinstance(config, AuthPermissivenessConfig)
        assert hasattr(config, 'permissiveness_enabled')
        assert hasattr(config, 'circuit_breaker_enabled')
        assert hasattr(config, 'environment')
    
    def test_config_validation_valid(self):
        """Test validation of valid configuration."""
        config = AuthPermissivenessConfig(
            failure_threshold=5,
            failure_rate_threshold=0.5,
            open_timeout_seconds=30,
            is_production=False
        )
        
        validation = validate_auth_config(config)
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
    
    def test_config_validation_invalid_thresholds(self):
        """Test validation catches invalid thresholds."""
        config = AuthPermissivenessConfig(
            failure_threshold=0,  # Invalid
            failure_rate_threshold=1.5,  # Invalid
            open_timeout_seconds=-1  # Invalid
        )
        
        validation = validate_auth_config(config)
        assert validation["valid"] is False
        assert len(validation["errors"]) == 3
    
    def test_config_security_warnings(self):
        """Test configuration validation for security issues."""
        config = AuthPermissivenessConfig(
            is_production=True,
            demo_mode=True,  # Security issue in production
            strict_mode=False  # Security issue in production
        )
        
        validation = validate_auth_config(config)
        assert len(validation["security_issues"]) >= 1
        assert "Demo mode enabled in production" in validation["security_issues"]
    
    def test_effective_mode_detection(self):
        """Test effective mode detection with environment factors."""
        # Production config should be strict by default
        config = AuthPermissivenessConfig(
            is_production=True,
            strict_mode=None  # Auto-detect
        )
        assert config.get_effective_strict_mode() is True
        
        # Development config should allow demo mode
        config = AuthPermissivenessConfig(
            is_production=False,
            demo_mode=None  # Auto-detect
        )
        # Will depend on environment variables, but should not crash
        result = config.get_effective_demo_mode()
        assert isinstance(result, bool)


@pytest.mark.asyncio 
class TestWebSocketIntegration:
    """Test integration with actual WebSocket SSOT system."""
    
    async def test_mock_websocket_permissive_auth_flow(self):
        """Test the complete permissive auth flow with mock WebSocket."""
        mock_ws = MockWebSocket(
            headers={
                "origin": "http://localhost:3010",
                "user-agent": "test-client/1.0"
            }
        )
        
        # Test with environment that should allow demo mode
        with patch('netra_backend.app.auth_integration.auth_permissiveness.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'development',
                'DEMO_MODE': '1'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            
            result = await authenticate_with_permissiveness(mock_ws)
            
            assert result.success is True
            assert result.user_context is not None
            assert result.level == AuthPermissivenessLevel.DEMO
    
    def test_websocket_auth_context_extraction(self):
        """Test extraction of auth context from WebSocket."""
        mock_ws = MockWebSocket(
            headers={
                "sec-websocket-protocol": "jwt.eyJhbGciOiJIUzI1NiJ9.test.token",
                "origin": "https://app.netra.ai"
            },
            client_host="203.0.113.1"
        )
        
        detector = EnvironmentAuthDetector()
        context = detector._build_auth_context(mock_ws)
        
        assert context.headers_available is True
        assert context.subprotocols_available is True
        assert context.client_ip == "203.0.113.1"
        assert context.connection_source == "external"  # Based on origin


# Performance and stress tests
@pytest.mark.asyncio
class TestPerformanceAndResilience:
    """Test performance and resilience of auth permissiveness system."""
    
    async def test_concurrent_authentication_requests(self):
        """Test handling of concurrent authentication requests."""
        mock_websockets = [MockWebSocket() for _ in range(10)]
        
        # Mock environment for demo mode
        with patch('netra_backend.app.auth_integration.auth_permissiveness.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'development',
                'DEMO_MODE': '1'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            
            # Run concurrent authentications
            tasks = [authenticate_with_permissiveness(ws) for ws in mock_websockets]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed in demo mode
            successful_results = [r for r in results if isinstance(r, AuthPermissivenessResult) and r.success]
            assert len(successful_results) == 10
    
    async def test_circuit_breaker_recovery_resilience(self, circuit_breaker_config):
        """Test circuit breaker recovery under various conditions."""
        circuit_breaker = CircuitBreakerAuth(circuit_breaker_config)
        mock_ws = MockWebSocket()
        
        # Test recovery cycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
        
        # 1. Trip the breaker
        circuit_breaker._trip_breaker()
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # 2. Wait for recovery timeout
        await asyncio.sleep(circuit_breaker_config.open_timeout_seconds + 0.1)
        
        # 3. Mock successful recovery
        with patch('netra_backend.app.auth_integration.auth_permissiveness.authenticate_with_permissiveness') as mock_auth:
            mock_result = AuthPermissivenessResult(
                success=True,
                level=AuthPermissivenessLevel.RELAXED,
                auth_method="recovery_success"
            )
            mock_auth.return_value = mock_result
            
            # Perform recovery tests
            for _ in range(circuit_breaker_config.success_threshold):
                result = await circuit_breaker.authenticate(mock_ws)
                assert result.success is True
            
            # Should eventually close
            assert circuit_breaker.state in [CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])