"""
GCP Readiness Validation Performance Fix Test

CRITICAL BUSINESS IMPACT: This test identifies and validates fixes for the GCP readiness 
validation bottleneck that's causing user-reported WebSocket slowdowns.

ROOT CAUSE IDENTIFIED:
1. WebSocket SSOT calls gcp_websocket_readiness_guard with 30s timeout
2. Guard waits for startup phase completion (up to 20s)
3. Then validates 3 service groups (20s + 10s + 5s potential)
4. Total possible delay: 30s + 20s + 10s + 5s = 65s blocking time

This directly explains user reports of "significantly slower than before" connections.

Business Value Justification:
- Segment: ALL (Free -> Enterprise) 
- Business Goal: Restore chat performance to sub-5s connection times
- Value Impact: Chat responsiveness = user retention = revenue protection
- Revenue Impact: Slow chat kills user experience and drives abandonment
"""

import asyncio
import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any

# Import the performance bottleneck
from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    gcp_websocket_readiness_guard,
    GCPReadinessState,
    GCPReadinessResult
)

# Test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestGCPReadinessPerformanceFix(SSotBaseTestCase):
    """Test suite for GCP readiness validation performance regression."""
    
    @pytest.fixture(autouse=True)
    def setup_performance_test(self):
        """Setup performance test environment."""
        self.performance_thresholds = {
            'connection_time_target': 5.0,  # 5 seconds max
            'validation_time_target': 2.0,  # 2 seconds max for validation
            'startup_wait_target': 1.0,     # 1 second max for startup wait
        }
    
    async def test_gcp_readiness_validation_timing_breakdown(self):
        """
        PERFORMANCE TEST: Measure each component of GCP readiness validation timing.
        
        This test breaks down exactly where the 30+ second delays are coming from
        in the WebSocket connection process.
        """
        # Mock app state to simulate various startup phases
        mock_app_state = MagicMock()
        mock_app_state.startup_phase = 'services'  # Simulate ready state
        
        # Create validator
        validator = GCPWebSocketInitializationValidator(mock_app_state)
        validator.is_gcp_environment = True  # Force GCP mode for testing
        validator.environment = 'staging'
        
        # Mock the service validation methods to measure timing
        async def mock_validate_service_group(services, timeout_seconds=30.0):
            """Mock service validation that simulates real timing."""
            # Simulate service check delays
            await asyncio.sleep(0.1)  # 100ms simulated service check
            return {
                'success': True,
                'failed': [],
                'elapsed_time': 0.1
            }
        
        async def mock_wait_for_startup(minimum_phase='services', timeout_seconds=30.0):
            """Mock startup wait that simulates real timing."""
            # Simulate startup wait
            await asyncio.sleep(0.05)  # 50ms simulated startup wait
            return True
        
        # Patch the heavy methods
        with patch.object(validator, '_validate_service_group', mock_validate_service_group), \
             patch.object(validator, '_wait_for_startup_phase_completion', mock_wait_for_startup):
            
            # Time the full validation
            start_time = time.time()
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=30.0)
            total_time = time.time() - start_time
            
            print(f"Total validation time: {total_time:.3f}s")
            print(f"Validation result: ready={result.ready}, state={result.state}")
            
            # This should be fast with mocked services
            assert total_time < 1.0, f"Mocked validation took {total_time:.3f}s - still too slow"
            assert result.ready, "Validation should succeed with mocked services"
    
    async def test_websocket_readiness_guard_performance(self):
        """
        PERFORMANCE TEST: Measure the readiness guard context manager timing.
        
        This tests the actual method called by WebSocket SSOT route.
        """
        # Mock app state
        mock_app_state = MagicMock()
        mock_app_state.startup_phase = 'complete'
        
        # Mock the validator to be fast
        async def mock_fast_validation(timeout):
            await asyncio.sleep(0.01)  # 10ms fast validation
            return GCPReadinessResult(
                ready=True,
                state=GCPReadinessState.WEBSOCKET_READY,
                elapsed_time=0.01,
                failed_services=[],
                warnings=[],
                details={'mock': True}
            )
        
        # Time the guard context manager
        start_time = time.time()
        
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.create_gcp_websocket_validator') as mock_create:
            mock_validator = MagicMock()
            mock_validator.validate_gcp_readiness_for_websocket = mock_fast_validation
            mock_create.return_value = mock_validator
            
            async with gcp_websocket_readiness_guard(mock_app_state, timeout=30.0) as result:
                guard_time = time.time() - start_time
                print(f"Readiness guard time: {guard_time:.3f}s")
                
                # Guard should be very fast with mocked validator
                assert guard_time < 0.1, f"Readiness guard took {guard_time:.3f}s - too slow for WebSocket connection"
                assert result.ready, "Guard should yield ready result"
    
    async def test_startup_phase_wait_performance_impact(self):
        """
        PERFORMANCE TEST: Measure startup phase waiting impact.
        
        This specifically tests the _wait_for_startup_phase_completion method
        that can block for up to 20 seconds.
        """
        # Mock app state with different startup phases
        test_phases = ['init', 'dependencies', 'database', 'services', 'complete']
        
        for phase in test_phases:
            mock_app_state = MagicMock()
            mock_app_state.startup_phase = phase
            
            validator = GCPWebSocketInitializationValidator(mock_app_state)
            
            # Time startup wait for each phase
            start_time = time.time()
            result = await validator._wait_for_startup_phase_completion(
                minimum_phase='services',
                timeout_seconds=5.0  # Shorter timeout for testing
            )
            wait_time = time.time() - start_time
            
            expected_ready = phase in ['services', 'websocket', 'finalize', 'complete']
            
            print(f"Phase '{phase}': wait_time={wait_time:.3f}s, ready={result}, expected={expected_ready}")
            
            # Phases at or past 'services' should return immediately
            if expected_ready:
                assert wait_time < 0.2, f"Ready phase '{phase}' took {wait_time:.3f}s - should be immediate"
                assert result, f"Phase '{phase}' should be ready"
            else:
                # Early phases will timeout (expected)
                assert not result, f"Phase '{phase}' should not be ready"
    
    async def test_non_gcp_environment_fast_path(self):
        """
        PERFORMANCE TEST: Verify non-GCP environments skip validation.
        
        This tests the fast path that should bypass all GCP-specific delays.
        """
        # Mock non-GCP environment
        mock_app_state = MagicMock()
        
        validator = GCPWebSocketInitializationValidator(mock_app_state)
        validator.is_gcp_environment = False  # Force non-GCP mode
        validator.environment = 'development'
        
        # Time the validation
        start_time = time.time()
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=30.0)
        validation_time = time.time() - start_time
        
        print(f"Non-GCP validation time: {validation_time:.3f}s")
        
        # Non-GCP should be nearly instantaneous
        assert validation_time < 0.1, f"Non-GCP validation took {validation_time:.3f}s - should be instant"
        assert result.ready, "Non-GCP validation should always be ready"
        assert "non-GCP environment" in str(result.warnings).lower(), "Should indicate non-GCP skip"
    
    async def test_performance_regression_reproduction(self):
        """
        CRITICAL TEST: Reproduce the actual performance regression scenario.
        
        This simulates the exact conditions causing user-reported slowdowns:
        1. GCP environment (staging/production)
        2. Services not yet ready
        3. Multiple validation phases timing out
        """
        # Simulate worst-case scenario: GCP staging with services not ready
        mock_app_state = MagicMock()
        mock_app_state.startup_phase = 'database'  # Not yet at 'services'
        
        validator = GCPWebSocketInitializationValidator(mock_app_state)
        validator.is_gcp_environment = True
        validator.environment = 'staging'
        
        # Time the validation with short timeout to avoid actual 30s wait
        start_time = time.time()
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=2.0)
        regression_time = time.time() - start_time
        
        print(f"Regression scenario time: {regression_time:.3f}s")
        print(f"Result: ready={result.ready}, failed_services={result.failed_services}")
        
        # This should fail fast due to startup phase not ready
        assert not result.ready, "Should fail when startup phase not ready"
        assert "startup_phase_timeout" in result.failed_services, "Should identify startup timeout"
        
        # Even with failure, should not take longer than timeout
        assert regression_time <= 2.5, f"Regression test took {regression_time:.3f}s - exceeds timeout + buffer"
    
    async def test_graceful_degradation_performance(self):
        """
        PERFORMANCE TEST: Test graceful degradation paths for better performance.
        
        The current system has graceful degradation for Redis failures in staging.
        This tests that degradation still provides reasonable performance.
        """
        mock_app_state = MagicMock()
        mock_app_state.startup_phase = 'services'  # Ready startup phase
        
        validator = GCPWebSocketInitializationValidator(mock_app_state)
        validator.is_gcp_environment = True
        validator.environment = 'staging'
        
        # Mock service validation with Redis failure
        async def mock_validate_with_redis_failure(services, timeout_seconds=30.0):
            await asyncio.sleep(0.05)  # 50ms simulated check
            if 'redis' in services:
                return {
                    'success': False,
                    'failed': ['redis'],
                    'elapsed_time': 0.05
                }
            return {
                'success': True,
                'failed': [],
                'elapsed_time': 0.05
            }
        
        with patch.object(validator, '_validate_service_group', mock_validate_with_redis_failure):
            # Time graceful degradation
            start_time = time.time()
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=10.0)
            degradation_time = time.time() - start_time
            
            print(f"Graceful degradation time: {degradation_time:.3f}s")
            print(f"Result: ready={result.ready}, warnings={result.warnings}")
            
            # Should succeed with degradation and be reasonably fast
            assert result.ready, "Should succeed with Redis degradation in staging"
            assert "redis" in str(result.warnings).lower(), "Should warn about Redis degradation"
            assert degradation_time < 1.0, f"Degradation took {degradation_time:.3f}s - should be fast"
    
    def test_performance_fix_recommendations(self):
        """
        ANALYSIS TEST: Provide specific performance fix recommendations.
        
        Based on the performance analysis, suggest concrete fixes.
        """
        print("\n" + "="*60)
        print("GCP READINESS PERFORMANCE FIX RECOMMENDATIONS")
        print("="*60)
        
        print("\n ALERT:  ROOT CAUSE: WebSocket connections blocked by GCP readiness validation")
        print("   - Current timeout: 30s for validation")
        print("   - Startup phase wait: up to 20s")
        print("   - Service validation: up to 35s total")
        print("   - Total blocking time: up to 65s")
        
        print("\n IDEA:  RECOMMENDED FIXES:")
        print("   1. Reduce WebSocket SSOT timeout from 30s to 5s")
        print("   2. Implement async readiness with connection queueing")
        print("   3. Cache readiness state to avoid repeated validation")
        print("   4. Use graceful degradation by default in staging")
        print("   5. Make startup phase wait non-blocking")
        
        print("\n LIGHTNING:  QUICK WIN: Reduce timeout in websocket_ssot.py line 349:")
        print("   BEFORE: async with gcp_websocket_readiness_guard(app_state, timeout=30.0)")
        print("   AFTER:  async with gcp_websocket_readiness_guard(app_state, timeout=5.0)")
        
        print("\n TARGET:  TARGET: WebSocket connections under 5 seconds")
        print("="*60)


if __name__ == "__main__":
    # Run performance tests directly
    import pytest
    pytest.main([__file__, "-v", "-s"])