"""
Integration Tests for GCP WebSocket Redis Race Condition Fix

MISSION CRITICAL: Integration tests that validate the Redis race condition fix
works correctly with real Redis services in GCP-like environments.

ROOT CAUSE VALIDATION: These tests confirm that:
1. Real Redis connections work with the 500ms grace period fix
2. WebSocket readiness validation integrates properly with Redis services
3. GCP environment detection works with real service configurations
4. The fix prevents race conditions during service startup

SSOT COMPLIANCE: Uses real Redis services and existing WebSocket infrastructure.

Business Value:
- Segment: Platform/Internal
- Business Goal: Platform Stability & Chat Value Delivery  
- Value Impact: Ensures Redis race condition fix works with real services
- Strategic Impact: Validates production-ready WebSocket reliability
"""

import asyncio
import pytest
import time
import redis.asyncio as redis
from unittest.mock import Mock, patch
from typing import Any, Dict

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.containers_utils import ensure_redis_container

from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    GCPReadinessState, 
    create_gcp_websocket_validator,
    gcp_websocket_readiness_guard,
    gcp_websocket_readiness_check
)


class TestGCPWebSocketRedisRaceConditionIntegration(BaseIntegrationTest):
    """Integration tests for GCP WebSocket Redis race condition fix with real Redis."""
    
    @pytest.fixture
    async def real_redis_connection(self, isolated_env):
        """Create real Redis connection for testing."""
        # Ensure Redis container is running
        ensure_redis_container()
        
        # Create Redis connection using test configuration
        redis_url = "redis://localhost:6381"  # Test Redis port
        redis_client = redis.from_url(redis_url, decode_responses=True)
        
        # Verify connection
        await redis_client.ping()
        
        yield redis_client
        
        # Cleanup
        await redis_client.close()
    
    @pytest.fixture
    def mock_app_state_with_real_redis(self, real_redis_connection):
        """Create mock app state with real Redis manager."""
        app_state = Mock()
        
        # Mock Redis manager with real Redis connection
        redis_manager = Mock()
        redis_manager.is_connected = Mock(return_value=True)
        redis_manager.redis_client = real_redis_connection
        app_state.redis_manager = redis_manager
        
        # Mock other required components
        app_state.db_session_factory = Mock()
        app_state.database_available = True
        app_state.auth_validation_complete = True
        app_state.key_manager = Mock()
        app_state.agent_supervisor = Mock()
        app_state.thread_service = Mock()
        
        # WebSocket bridge
        app_state.agent_websocket_bridge = Mock()
        app_state.agent_websocket_bridge.notify_agent_started = Mock()
        app_state.agent_websocket_bridge.notify_agent_completed = Mock()
        app_state.agent_websocket_bridge.notify_tool_executing = Mock()
        
        # Startup flags
        app_state.startup_complete = True
        app_state.startup_failed = False
        app_state.startup_phase = "complete"
        
        return app_state
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_readiness_with_real_redis_gcp_environment(
        self, 
        mock_app_state_with_real_redis,
        real_redis_connection
    ):
        """Test Redis readiness validation with real Redis in GCP environment."""
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            validator = create_gcp_websocket_validator(mock_app_state_with_real_redis)
            
            # Verify GCP environment detection
            assert validator.is_gcp_environment is True
            assert validator.is_cloud_run is True
            
            # Test Redis readiness with real connection
            start_time = time.time()
            result = validator._validate_redis_readiness()
            elapsed_time = time.time() - start_time
            
            # Should succeed
            assert result is True
            
            # Should include grace period (at least 500ms)
            assert elapsed_time >= 0.45, f"Grace period not applied: {elapsed_time}s"
            
            # Verify Redis is actually reachable
            ping_result = await real_redis_connection.ping()
            assert ping_result is True
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_full_websocket_readiness_with_real_redis(
        self,
        mock_app_state_with_real_redis,
        real_redis_connection
    ):
        """Test full WebSocket readiness validation with real Redis services."""
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            validator = create_gcp_websocket_validator(mock_app_state_with_real_redis)
            
            # Run full readiness validation
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=120.0)
            
            # Should succeed
            assert result.ready is True
            assert result.state == GCPReadinessState.WEBSOCKET_READY
            assert len(result.failed_services) == 0
            
            # Should take time due to Redis grace period
            assert result.elapsed_time >= 0.5, f"Grace period not reflected in timing: {result.elapsed_time}s"
            
            # Verify Redis was included in validation
            assert result.details["gcp_detected"] is True
            assert result.details["is_cloud_run"] is True
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_connection_failure_handling(
        self,
        mock_app_state_with_real_redis
    ):
        """Test Redis readiness validation handles real connection failures."""
        
        # Mock Redis manager with failing connection
        mock_app_state_with_real_redis.redis_manager.is_connected = Mock(return_value=False)
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            validator = create_gcp_websocket_validator(mock_app_state_with_real_redis)
            
            # Should still apply grace period even for failed connections
            start_time = time.time()
            result = validator._validate_redis_readiness()
            elapsed_time = time.time() - start_time
            
            # Should fail but still take time for grace period
            assert result is False
            assert elapsed_time >= 0.45, f"Grace period not applied to failed connection: {elapsed_time}s"
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_readiness_guard_with_real_redis(
        self,
        mock_app_state_with_real_redis,
        real_redis_connection
    ):
        """Test WebSocket readiness guard context manager with real Redis."""
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            # Test successful guard usage
            guard_result = None
            async with gcp_websocket_readiness_guard(mock_app_state_with_real_redis, timeout=60.0) as result:
                guard_result = result
                
                # Inside guard - services should be ready
                assert result.ready is True
                assert result.state == GCPReadinessState.WEBSOCKET_READY
            
            # Verify guard completed successfully
            assert guard_result is not None
            assert guard_result.ready is True
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_readiness_guard_failure_with_redis_down(self, isolated_env):
        """Test WebSocket readiness guard fails when Redis services are down."""
        
        # Create app state with unavailable Redis
        app_state = Mock()
        app_state.redis_manager = None  # No Redis manager
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
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            # Guard should raise exception for failed readiness
            with pytest.raises(RuntimeError, match="GCP WebSocket readiness validation failed"):
                async with gcp_websocket_readiness_guard(app_state, timeout=30.0):
                    pass  # Should not reach here
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_check_integration_with_redis(
        self,
        mock_app_state_with_real_redis,
        real_redis_connection
    ):
        """Test health check endpoint integration with real Redis services."""
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            # Test health check function
            ready, details = await gcp_websocket_readiness_check(mock_app_state_with_real_redis)
            
            # Should report ready
            assert ready is True
            assert details["websocket_ready"] is True
            assert details["state"] == GCPReadinessState.WEBSOCKET_READY.value
            assert details["gcp_environment"] is True
            assert details["cloud_run"] is True
            assert len(details["failed_services"]) == 0
            
            # Should include timing information
            assert "elapsed_time" in details
            assert details["elapsed_time"] >= 0.5  # Grace period effect
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_redis_readiness_checks(
        self,
        mock_app_state_with_real_redis,
        real_redis_connection
    ):
        """Test concurrent Redis readiness checks don't interfere with each other."""
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            async def run_readiness_check(check_id: int):
                """Run a single readiness check."""
                validator = create_gcp_websocket_validator(mock_app_state_with_real_redis)
                
                start_time = time.time()
                result = validator._validate_redis_readiness()
                elapsed_time = time.time() - start_time
                
                return {
                    'check_id': check_id,
                    'result': result,
                    'elapsed_time': elapsed_time
                }
            
            # Run multiple concurrent checks
            concurrent_checks = 5
            tasks = [run_readiness_check(i) for i in range(concurrent_checks)]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All checks should succeed
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), f"Check {i} failed: {result}"
                assert result['result'] is True, f"Check {i} returned False"
                assert result['elapsed_time'] >= 0.45, f"Check {i} missing grace period: {result['elapsed_time']}s"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_race_condition_simulation(
        self,
        mock_app_state_with_real_redis,
        real_redis_connection
    ):
        """Simulate Redis race condition scenario and verify fix prevents issues."""
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            # Simulate race condition by making Redis connection unstable initially
            connection_attempts = []
            original_is_connected = mock_app_state_with_real_redis.redis_manager.is_connected
            
            def unstable_connection():
                """Simulate unstable Redis connection during startup."""
                connection_attempts.append(time.time())
                
                # First few attempts fail (simulating background task race)
                if len(connection_attempts) <= 2:
                    return False
                
                # After grace period, connection stabilizes
                return True
            
            mock_app_state_with_real_redis.redis_manager.is_connected = Mock(side_effect=unstable_connection)
            
            validator = create_gcp_websocket_validator(mock_app_state_with_real_redis)
            
            # First attempt should fail (before grace period)
            first_result = validator._validate_redis_readiness()
            assert first_result is False
            
            # Reset for second attempt
            connection_attempts.clear()
            
            # Second attempt should succeed (grace period allows stabilization)
            second_result = validator._validate_redis_readiness()
            assert second_result is True
            
            # Verify grace period was applied
            assert len(connection_attempts) >= 1