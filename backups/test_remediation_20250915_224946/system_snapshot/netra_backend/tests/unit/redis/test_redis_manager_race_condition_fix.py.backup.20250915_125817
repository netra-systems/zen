"""
Unit Tests for Redis Manager Race Condition Fix

MISSION CRITICAL: Validates the 500ms grace period fix that prevents
GCP WebSocket readiness validation failures due to Redis race conditions.

ROOT CAUSE VALIDATION: These tests confirm that:
1. Redis readiness validation includes the 500ms stabilization delay in GCP environments
2. Background task race conditions are eliminated by the grace period
3. Non-GCP environments are not affected by the delay
4. The fix integrates properly with existing SSOT patterns

SSOT COMPLIANCE: Uses existing test patterns and Redis infrastructure.

Business Value:
- Segment: Platform/Internal  
- Business Goal: Platform Stability & Chat Value Delivery
- Value Impact: Eliminates Redis race condition preventing WebSocket connections
- Strategic Impact: Ensures reliable chat functionality in GCP Cloud Run
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any, Dict

from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    GCPReadinessState,
    create_gcp_websocket_validator
)


class TestRedisManagerRaceConditionFix:
    """Unit tests for the Redis race condition fix in GCP environments."""
    
    @pytest.fixture
    def mock_app_state_gcp(self):
        """Create mock app state for GCP environment testing."""
        app_state = Mock()
        
        # Mock successful service states
        app_state.db_session_factory = Mock()
        app_state.database_available = True
        app_state.auth_validation_complete = True
        app_state.key_manager = Mock()
        app_state.agent_supervisor = Mock()
        app_state.thread_service = Mock()
        app_state.agent_websocket_bridge = Mock()
        app_state.startup_complete = True
        app_state.startup_failed = False
        app_state.startup_phase = "complete"
        
        # Mock Redis manager with race condition scenario
        app_state.redis_manager = Mock()
        app_state.redis_manager.is_connected = Mock(return_value=True)
        
        return app_state
    
    @pytest.fixture
    def gcp_environment(self):
        """Mock GCP Cloud Run environment variables."""
        with patch.dict('os.environ', {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-backend'
        }):
            yield
    
    @pytest.fixture
    def non_gcp_environment(self):
        """Mock non-GCP development environment variables."""
        with patch.dict('os.environ', {
            'ENVIRONMENT': 'development'
        }, clear=True):
            yield
    
    def test_redis_readiness_includes_grace_period_in_gcp(self, mock_app_state_gcp, gcp_environment):
        """Test that Redis readiness validation includes 500ms grace period in GCP."""
        validator = create_gcp_websocket_validator(mock_app_state_gcp)
        
        # Verify GCP environment detection
        assert validator.is_gcp_environment is True
        assert validator.is_cloud_run is True
        
        # Mock time.sleep to verify it's called with correct delay
        with patch('time.sleep') as mock_sleep:
            # Test Redis readiness validation
            result = validator._validate_redis_readiness()
            
            # Should succeed
            assert result is True
            
            # Verify grace period was applied
            mock_sleep.assert_called_once_with(0.5)  # 500ms grace period
    
    def test_redis_readiness_no_grace_period_in_non_gcp(self, mock_app_state_gcp, non_gcp_environment):
        """Test that Redis readiness validation skips grace period in non-GCP environments."""
        validator = create_gcp_websocket_validator(mock_app_state_gcp)
        
        # Verify non-GCP environment detection
        assert validator.is_gcp_environment is False
        assert validator.is_cloud_run is False
        
        # Mock time.sleep to verify it's NOT called
        with patch('time.sleep') as mock_sleep:
            # Test Redis readiness validation
            result = validator._validate_redis_readiness()
            
            # Should succeed
            assert result is True
            
            # Verify grace period was NOT applied
            mock_sleep.assert_not_called()
    
    def test_redis_readiness_handles_manager_none(self, gcp_environment):
        """Test Redis readiness validation handles missing redis_manager gracefully."""
        app_state = Mock()
        app_state.redis_manager = None
        
        validator = create_gcp_websocket_validator(app_state)
        
        result = validator._validate_redis_readiness()
        
        # Should fail gracefully
        assert result is False
    
    def test_redis_readiness_handles_is_connected_false(self, mock_app_state_gcp, gcp_environment):
        """Test Redis readiness validation handles disconnected Redis manager."""
        # Mock Redis manager that reports disconnected
        mock_app_state_gcp.redis_manager.is_connected = Mock(return_value=False)
        
        validator = create_gcp_websocket_validator(mock_app_state_gcp)
        
        with patch('time.sleep') as mock_sleep:
            result = validator._validate_redis_readiness()
            
            # Should fail
            assert result is False
            
            # Grace period should still be applied (for connected check)
            mock_sleep.assert_called_once_with(0.5)
    
    def test_redis_readiness_handles_missing_is_connected_method(self, mock_app_state_gcp, gcp_environment):
        """Test Redis readiness validation handles Redis manager without is_connected method."""
        # Mock Redis manager without is_connected method
        redis_manager = Mock()
        delattr(redis_manager, 'is_connected')  # Remove method if it exists
        mock_app_state_gcp.redis_manager = redis_manager
        
        validator = create_gcp_websocket_validator(mock_app_state_gcp)
        
        result = validator._validate_redis_readiness()
        
        # Should succeed (fallback behavior)
        assert result is True
    
    def test_redis_readiness_handles_exception_gracefully(self, mock_app_state_gcp, gcp_environment):
        """Test Redis readiness validation handles exceptions gracefully."""
        # Mock Redis manager that raises exception
        mock_app_state_gcp.redis_manager.is_connected = Mock(side_effect=Exception("Redis connection error"))
        
        validator = create_gcp_websocket_validator(mock_app_state_gcp)
        
        result = validator._validate_redis_readiness()
        
        # Should fail gracefully
        assert result is False
    
    def test_grace_period_timing_accuracy(self, mock_app_state_gcp, gcp_environment):
        """Test that the grace period timing is accurate (500ms)."""
        validator = create_gcp_websocket_validator(mock_app_state_gcp)
        
        # Record timing around the validation call
        start_time = time.time()
        
        result = validator._validate_redis_readiness()
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Should succeed
        assert result is True
        
        # Should take at least 500ms due to grace period (allowing some tolerance)
        assert elapsed_time >= 0.45, f"Grace period too short: {elapsed_time}s"
        assert elapsed_time <= 0.6, f"Grace period too long: {elapsed_time}s"
    
    def test_redis_readiness_check_configuration(self, mock_app_state_gcp, gcp_environment):
        """Test that Redis readiness check is properly configured in validator."""
        validator = create_gcp_websocket_validator(mock_app_state_gcp)
        
        # Verify Redis check exists in readiness_checks
        assert 'redis' in validator.readiness_checks
        
        redis_check = validator.readiness_checks['redis']
        
        # Verify configuration is appropriate for GCP
        assert redis_check.name == 'redis'
        assert redis_check.timeout_seconds == 60.0  # Increased timeout for GCP
        assert redis_check.retry_count == 5
        assert redis_check.retry_delay == 1.5  # Longer delay for GCP
        assert redis_check.is_critical is True
        assert 'Redis connection and caching system' in redis_check.description
        
        # Verify validator function
        assert redis_check.validator == validator._validate_redis_readiness


class TestRedisRaceConditionIntegration:
    """Integration tests for Redis race condition fix with other components."""
    
    @pytest.fixture
    def mock_app_state_full(self):
        """Create comprehensive mock app state with all components."""
        app_state = Mock()
        
        # All required components
        app_state.db_session_factory = Mock()
        app_state.database_available = True
        app_state.redis_manager = Mock()
        app_state.redis_manager.is_connected = Mock(return_value=True)
        app_state.auth_validation_complete = True
        app_state.key_manager = Mock()
        app_state.agent_supervisor = Mock()
        app_state.thread_service = Mock()
        
        # WebSocket bridge with required methods
        app_state.agent_websocket_bridge = Mock()
        app_state.agent_websocket_bridge.notify_agent_started = Mock()
        app_state.agent_websocket_bridge.notify_agent_completed = Mock()
        app_state.agent_websocket_bridge.notify_tool_executing = Mock()
        
        # Startup completion flags
        app_state.startup_complete = True
        app_state.startup_failed = False
        app_state.startup_phase = "complete"
        
        return app_state
    
    @pytest.mark.asyncio
    async def test_full_gcp_validation_with_redis_grace_period(self, mock_app_state_full):
        """Test full GCP validation includes Redis grace period without affecting other checks."""
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'test'}):
            validator = create_gcp_websocket_validator(mock_app_state_full)
            
            with patch('time.sleep') as mock_sleep:
                # Run full GCP readiness validation
                result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=60.0)
                
                # Should succeed
                assert result.ready is True
                assert result.state == GCPReadinessState.WEBSOCKET_READY
                assert len(result.failed_services) == 0
                
                # Verify Redis grace period was applied once during Redis validation
                mock_sleep.assert_called_once_with(0.5)
    
    @pytest.mark.asyncio
    async def test_redis_failure_after_grace_period_fails_validation(self, mock_app_state_full):
        """Test that Redis failure after grace period still fails overall validation."""
        
        # Mock Redis manager that becomes disconnected after initial check
        mock_app_state_full.redis_manager.is_connected = Mock(return_value=False)
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'test'}):
            validator = create_gcp_websocket_validator(mock_app_state_full)
            
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=60.0)
            
            # Should fail due to Redis
            assert result.ready is False
            assert result.state == GCPReadinessState.FAILED
            assert 'redis' in result.failed_services
    
    @pytest.mark.asyncio
    async def test_non_gcp_environment_bypasses_redis_grace_period(self, mock_app_state_full):
        """Test that non-GCP environments complete validation faster by skipping grace period."""
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'development'}, clear=True):
            validator = create_gcp_websocket_validator(mock_app_state_full)
            
            start_time = time.time()
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=10.0)
            elapsed_time = time.time() - start_time
            
            # Should succeed quickly
            assert result.ready is True
            assert result.state == GCPReadinessState.WEBSOCKET_READY
            
            # Should complete much faster (no 500ms delay)
            assert elapsed_time < 0.1, f"Non-GCP validation took too long: {elapsed_time}s"
            
            # Should skip GCP validation entirely
            assert "Skipped GCP validation" in result.warnings[0]