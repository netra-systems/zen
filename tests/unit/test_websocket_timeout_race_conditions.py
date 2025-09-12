"""
Unit Tests for WebSocket Timeout Configuration and Race Condition Prevention

Business Value Justification (BVJ):
- Segment: Platform/Enterprise 
- Business Goal: Prevent WebSocket race conditions causing 1011 errors
- Value Impact: Protect $500K+ ARR by ensuring reliable WebSocket handshakes
- Strategic Impact: Critical for chat functionality (90% of platform value)

These tests are designed to INITIALLY FAIL to demonstrate the current race condition
issues in WebSocket handshake timeout configuration. After implementing fixes,
all tests should pass.

Issue #372: WebSocket handshake race condition causing 1011 errors in Cloud Run
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from netra_backend.app.core.timeout_configuration import (
    get_websocket_recv_timeout,
    get_agent_execution_timeout, 
    get_timeout_config,
    validate_timeout_hierarchy,
    TimeoutTier,
    TimeoutEnvironment,
    CloudNativeTimeoutManager,
    reset_timeout_manager
)
from netra_backend.app.websocket_core.utils import (
    validate_websocket_handshake_completion,
    is_websocket_connected_and_ready,
    safe_websocket_send,
    get_progressive_delay
)
from test_framework.base_integration_test import BaseIntegrationTest


@pytest.mark.unit
@pytest.mark.timeout_race_conditions
class TestWebSocketTimeoutRaceConditions(BaseIntegrationTest):
    """
    Test WebSocket timeout configuration to prevent race conditions.
    
    CRITICAL: These tests initially FAIL to demonstrate current issues.
    After race condition fixes, all tests should pass.
    """
    
    def setup_method(self, method):
        """Set up test environment and reset timeout manager."""
        super().setup_method(method)
        reset_timeout_manager()
    
    def teardown_method(self, method):
        """Clean up after each test."""
        reset_timeout_manager()
        super().teardown_method(method)
    
    def test_timeout_hierarchy_prevents_race_condition_staging(self):
        """
        Test that WebSocket timeout > Agent timeout in staging environment.
        
        EXPECTED TO FAIL INITIALLY: Current staging config has WebSocket timeout (3s) 
        < Agent timeout (15s), causing race conditions and 1011 errors.
        
        After fix: WebSocket timeout should be > Agent timeout (e.g., 35s > 30s)
        """
        # Set staging environment
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
            websocket_timeout = get_websocket_recv_timeout()
            agent_timeout = get_agent_execution_timeout()
            
            # CRITICAL: This assertion will FAIL initially
            # Current: websocket_timeout=3, agent_timeout=15 (WRONG)
            # Required: websocket_timeout=35, agent_timeout=30 (CORRECT)
            assert websocket_timeout > agent_timeout, (
                f"Race condition risk: WebSocket timeout ({websocket_timeout}s) must be > "
                f"Agent timeout ({agent_timeout}s) to prevent 1011 errors. "
                f"Current gap: {websocket_timeout - agent_timeout}s"
            )
            
            # Additional validation for proper gap
            timeout_gap = websocket_timeout - agent_timeout
            assert timeout_gap >= 5, (
                f"Insufficient timeout gap: {timeout_gap}s. Need at least 5s buffer "
                f"to handle Cloud Run network latency and prevent race conditions."
            )
    
    def test_timeout_hierarchy_prevents_race_condition_production(self):
        """
        Test timeout hierarchy in production environment.
        
        EXPECTED TO FAIL INITIALLY: Production may have similar timeout misalignment.
        """
        with patch.dict('os.environ', {'ENVIRONMENT': 'production'}):
            websocket_timeout = get_websocket_recv_timeout()
            agent_timeout = get_agent_execution_timeout()
            
            # Production should have even more conservative timeouts
            assert websocket_timeout > agent_timeout, (
                f"Production race condition: WebSocket timeout ({websocket_timeout}s) "
                f"must be > Agent timeout ({agent_timeout}s)"
            )
            
            # Production should have at least 10s buffer
            timeout_gap = websocket_timeout - agent_timeout
            assert timeout_gap >= 10, (
                f"Production needs larger buffer: {timeout_gap}s < 10s minimum"
            )
    
    def test_cloud_run_environment_detection_accurate(self):
        """
        Test that Cloud Run environments are properly detected and configured.
        
        EXPECTED TO FAIL INITIALLY: Environment detection may default to wrong timeouts.
        """
        # Test staging environment detection
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
            manager = CloudNativeTimeoutManager()
            config = manager.get_timeout_config()
            
            # CRITICAL: Staging should have Cloud Run optimized timeouts
            assert config.websocket_recv_timeout >= 30, (
                f"Staging WebSocket timeout too low: {config.websocket_recv_timeout}s. "
                f"Cloud Run needs >= 30s to handle cold starts and network latency."
            )
            
            assert config.agent_execution_timeout >= 25, (
                f"Staging Agent timeout too low: {config.agent_execution_timeout}s. "
                f"Cloud Run needs >= 25s for agent processing."
            )
    
    def test_enterprise_tier_timeout_enhancements(self):
        """
        Test that Enterprise tier gets appropriate timeout enhancements.
        
        EXPECTED TO FAIL INITIALLY: Enterprise tier may not have proper streaming timeouts.
        """
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
            enterprise_config = get_timeout_config(TimeoutTier.ENTERPRISE)
            free_config = get_timeout_config(TimeoutTier.FREE)
            
            # Enterprise should have significantly longer timeouts
            assert enterprise_config.websocket_recv_timeout > free_config.websocket_recv_timeout, (
                f"Enterprise WebSocket timeout not enhanced: "
                f"{enterprise_config.websocket_recv_timeout}s <= {free_config.websocket_recv_timeout}s"
            )
            
            # Enterprise should support 300s streaming
            assert enterprise_config.agent_execution_timeout >= 300, (
                f"Enterprise streaming capability missing: {enterprise_config.agent_execution_timeout}s < 300s"
            )
            
            # Enterprise WebSocket timeout must still be > Agent timeout
            assert enterprise_config.websocket_recv_timeout > enterprise_config.agent_execution_timeout, (
                f"Enterprise timeout hierarchy broken: WebSocket {enterprise_config.websocket_recv_timeout}s "
                f"<= Agent {enterprise_config.agent_execution_timeout}s"
            )
    
    def test_timeout_hierarchy_validation_function(self):
        """
        Test the timeout hierarchy validation function catches misconfigurations.
        
        EXPECTED TO FAIL INITIALLY: Current config may fail validation.
        """
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
            # CRITICAL: This validation should pass after fixes
            hierarchy_valid = validate_timeout_hierarchy()
            
            assert hierarchy_valid, (
                "Timeout hierarchy validation failed. WebSocket timeouts must be > Agent timeouts "
                "to prevent race conditions and 1011 errors in Cloud Run environments."
            )
    
    @pytest.mark.asyncio
    async def test_handshake_validation_timeout_scaling(self):
        """
        Test that handshake validation timeouts scale properly with environment.
        
        EXPECTED TO FAIL INITIALLY: May use hardcoded timeouts instead of environment-aware values.
        """
        mock_websocket = AsyncMock()
        mock_websocket.client_state = Mock()
        mock_websocket.client_state.CONNECTED = "connected"
        mock_websocket.send_json = AsyncMock()
        
        # Mock successful state validation
        with patch('netra_backend.app.websocket_core.utils.is_websocket_connected', return_value=True):
            # Test staging environment uses longer timeout
            with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
                # Should use at least 2.0s timeout for Cloud Run
                start_time = time.time()
                await validate_websocket_handshake_completion(mock_websocket, timeout_seconds=1.0)
                duration = time.time() - start_time
                
                # CRITICAL: Should automatically increase timeout for staging
                # This may FAIL if hardcoded 1.0s timeout is used instead of environment-aware scaling
                assert duration >= 1.8, (
                    f"Staging handshake validation too fast: {duration:.2f}s. "
                    f"Should automatically use >= 2.0s timeout for Cloud Run environment."
                )
    
    @pytest.mark.asyncio
    async def test_progressive_timeout_backoff_cloud_aware(self):
        """
        Test that progressive timeout backoff is aware of Cloud Run timing requirements.
        
        EXPECTED TO FAIL INITIALLY: May use uniform backoff instead of environment-aware delays.
        """
        # Test staging environment gets appropriate delays
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
            delay_0 = get_progressive_delay(0, environment="staging")
            delay_1 = get_progressive_delay(1, environment="staging") 
            delay_2 = get_progressive_delay(2, environment="staging")
            
            # Cloud Run needs longer delays than local development
            assert delay_0 >= 0.02, f"Staging delay 0 too short: {delay_0}s < 0.02s"
            assert delay_1 >= 0.04, f"Staging delay 1 too short: {delay_1}s < 0.04s" 
            assert delay_2 >= 0.06, f"Staging delay 2 too short: {delay_2}s < 0.06s"
            
            # Should be progressive
            assert delay_1 > delay_0, f"Delay not progressive: {delay_1}s <= {delay_0}s"
            assert delay_2 > delay_1, f"Delay not progressive: {delay_2}s <= {delay_1}s"
    
    def test_race_condition_vulnerable_timeout_patterns(self):
        """
        Test detection of race condition vulnerable timeout patterns.
        
        EXPECTED TO FAIL INITIALLY: Current config contains vulnerable patterns.
        """
        vulnerable_patterns = []
        
        # Check multiple environments for vulnerable patterns
        environments = ['staging', 'production', 'development']
        
        for env in environments:
            with patch.dict('os.environ', {'ENVIRONMENT': env}):
                config = get_timeout_config()
                
                # Pattern 1: WebSocket timeout <= Agent timeout (CRITICAL)
                if config.websocket_recv_timeout <= config.agent_execution_timeout:
                    vulnerable_patterns.append(f"{env}: WebSocket {config.websocket_recv_timeout}s <= Agent {config.agent_execution_timeout}s")
                
                # Pattern 2: Too short timeouts for Cloud Run
                if env in ['staging', 'production']:
                    if config.websocket_recv_timeout < 15:
                        vulnerable_patterns.append(f"{env}: WebSocket timeout {config.websocket_recv_timeout}s too short for Cloud Run")
                    
                    if config.agent_execution_timeout < 10:
                        vulnerable_patterns.append(f"{env}: Agent timeout {config.agent_execution_timeout}s too short for Cloud Run")
                
                # Pattern 3: Insufficient timeout gap
                gap = config.websocket_recv_timeout - config.agent_execution_timeout
                if gap < 5 and gap >= 0:
                    vulnerable_patterns.append(f"{env}: Insufficient timeout gap {gap}s < 5s")
        
        # CRITICAL: This assertion will FAIL initially if vulnerable patterns exist
        assert len(vulnerable_patterns) == 0, (
            f"Race condition vulnerable timeout patterns detected:\n" + 
            "\n".join(f"- {pattern}" for pattern in vulnerable_patterns) +
            "\n\nThese patterns can cause 1011 WebSocket errors and affect $500K+ ARR."
        )
    
    @pytest.mark.asyncio 
    async def test_websocket_send_timeout_coordination(self):
        """
        Test that WebSocket send operations coordinate with timeout configuration.
        
        EXPECTED TO FAIL INITIALLY: May use hardcoded retry/timeout values.
        """
        mock_websocket = AsyncMock()
        
        # Mock initial failure then success
        mock_websocket.send_json.side_effect = [
            RuntimeError("WebSocket not ready"),  # First attempt fails
            None  # Second attempt succeeds
        ]
        
        with patch('netra_backend.app.websocket_core.utils.is_websocket_connected', return_value=True):
            with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
                start_time = time.time()
                
                # Should use environment-aware retry logic
                result = await safe_websocket_send(mock_websocket, {"test": "data"}, retry_count=2)
                
                duration = time.time() - start_time
                
                # CRITICAL: Staging should use longer backoff delays
                assert duration >= 0.1, (
                    f"Staging WebSocket send retry too fast: {duration:.3f}s. "
                    f"Should use Cloud Run appropriate backoff delays >= 0.1s"
                )
                
                assert result is True, "WebSocket send should succeed after retry"
    
    def test_timeout_configuration_caching_behavior(self):
        """
        Test that timeout configuration caching works properly across environment changes.
        
        EXPECTED TO FAIL INITIALLY: Cache may not invalidate on environment changes.
        """
        # Get config for staging
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
            staging_config = get_timeout_config()
            staging_websocket_timeout = staging_config.websocket_recv_timeout
        
        # Switch to production  
        with patch.dict('os.environ', {'ENVIRONMENT': 'production'}):
            production_config = get_timeout_config()
            production_websocket_timeout = production_config.websocket_recv_timeout
        
        # CRITICAL: Configs should be different, not cached stale values
        assert staging_websocket_timeout != production_websocket_timeout, (
            f"Timeout config cache not updating on environment change: "
            f"staging={staging_websocket_timeout}s, production={production_websocket_timeout}s"
        )


@pytest.mark.unit
@pytest.mark.timeout_edge_cases
class TestWebSocketTimeoutEdgeCases(BaseIntegrationTest):
    """
    Test edge cases in WebSocket timeout handling that could cause race conditions.
    """
    
    def setup_method(self, method):
        super().setup_method(method)
        reset_timeout_manager()
    
    def teardown_method(self, method):
        reset_timeout_manager()
        super().teardown_method(method)
    
    def test_zero_timeout_handling(self):
        """
        Test handling of zero or negative timeouts.
        
        EXPECTED TO FAIL INITIALLY: May not properly validate timeout values.
        """
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
            config = get_timeout_config()
            
            # All timeouts should be positive
            assert config.websocket_recv_timeout > 0, f"WebSocket timeout invalid: {config.websocket_recv_timeout}"
            assert config.agent_execution_timeout > 0, f"Agent timeout invalid: {config.agent_execution_timeout}"
            assert config.websocket_connection_timeout > 0, f"Connection timeout invalid: {config.websocket_connection_timeout}"
    
    def test_extremely_long_timeout_handling(self):
        """
        Test handling of extremely long timeouts for enterprise customers.
        
        EXPECTED TO FAIL INITIALLY: May not support very long enterprise streaming timeouts.
        """
        with patch.dict('os.environ', {'ENVIRONMENT': 'production'}):
            enterprise_config = get_timeout_config(TimeoutTier.ENTERPRISE)
            
            # Enterprise should support very long streaming (up to 300s)
            assert enterprise_config.agent_execution_timeout <= 300, (
                f"Enterprise timeout too long: {enterprise_config.agent_execution_timeout}s > 300s"
            )
            
            # But WebSocket timeout should still be longer
            assert enterprise_config.websocket_recv_timeout > enterprise_config.agent_execution_timeout, (
                f"Enterprise hierarchy broken: WebSocket {enterprise_config.websocket_recv_timeout}s "
                f"<= Agent {enterprise_config.agent_execution_timeout}s"
            )
    
    def test_timeout_tier_boundary_conditions(self):
        """
        Test timeout configurations at tier boundaries.
        
        EXPECTED TO FAIL INITIALLY: Tier transitions may have gaps or overlaps.
        """
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
            free_config = get_timeout_config(TimeoutTier.FREE)
            early_config = get_timeout_config(TimeoutTier.EARLY)
            mid_config = get_timeout_config(TimeoutTier.MID)
            enterprise_config = get_timeout_config(TimeoutTier.ENTERPRISE)
            
            # Verify progressive enhancement
            configs = [
                (TimeoutTier.FREE, free_config),
                (TimeoutTier.EARLY, early_config), 
                (TimeoutTier.MID, mid_config),
                (TimeoutTier.ENTERPRISE, enterprise_config)
            ]
            
            for i in range(len(configs) - 1):
                current_tier, current_config = configs[i]
                next_tier, next_config = configs[i + 1]
                
                # Higher tiers should have same or better timeouts
                assert next_config.agent_execution_timeout >= current_config.agent_execution_timeout, (
                    f"Tier regression: {next_tier.value} agent timeout "
                    f"{next_config.agent_execution_timeout}s < {current_tier.value} "
                    f"{current_config.agent_execution_timeout}s"
                )
                
                # WebSocket timeout hierarchy must be maintained across all tiers
                assert current_config.websocket_recv_timeout > current_config.agent_execution_timeout, (
                    f"Hierarchy broken at {current_tier.value}: WebSocket "
                    f"{current_config.websocket_recv_timeout}s <= Agent "
                    f"{current_config.agent_execution_timeout}s"
                )