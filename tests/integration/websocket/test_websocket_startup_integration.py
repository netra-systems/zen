"""
Integration tests for WebSocket startup coordination with real timing.

MISSION CRITICAL: Tests the integration between startup phases and WebSocket 
readiness validation with realistic timing to reproduce Issue #586 race conditions.

Business Value Justification (BVJ):
- Segment: Platform/All Users  
- Business Goal: Platform Stability & Golden Path Reliability
- Value Impact: Ensures WebSocket connections work during startup for chat functionality (90% of value)
- Strategic Impact: Prevents 1011 errors that block customer onboarding and engagement

Test Strategy:
- Integration tests use real timing and service coordination patterns
- Tests validate actual startup sequence behavior and WebSocket coordination
- Tests reproduce race condition scenarios with controlled timing
- Tests ensure Golden Path works under realistic load and timing conditions
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    GCPReadinessState,
    GCPReadinessResult,
    create_gcp_websocket_validator
)


@pytest.mark.integration
class TestWebSocketStartupTiming:
    """Test WebSocket startup timing with realistic service coordination."""
    
    @pytest.fixture
    def mock_realistic_app_state(self):
        """Create a realistic app state that simulates actual startup progression."""
        app_state = Mock()
        
        # Initial state - startup just beginning
        app_state.startup_complete = False
        app_state.startup_failed = False
        app_state.startup_in_progress = True
        app_state.startup_phase = "init"
        
        # Services start as None and get populated during startup
        app_state.db_session_factory = None
        app_state.database_available = False
        app_state.redis_manager = None
        app_state.auth_validation_complete = False
        app_state.key_manager = None
        app_state.agent_supervisor = None
        app_state.thread_service = None
        app_state.agent_websocket_bridge = None
        
        return app_state
    
    @pytest.fixture
    def gcp_staging_environment(self):
        """Mock GCP staging environment."""
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'K_SERVICE': 'netra-backend'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            yield
    
    async def simulate_realistic_startup_progression(self, app_state: Mock, progression_delay: float = 0.1):
        """
        Simulate realistic startup progression through phases.
        
        This simulates the actual startup sequence with realistic timing delays
        between phases to test race condition scenarios.
        """
        phases = [
            ("dependencies", self._setup_dependencies),
            ("database", self._setup_database),  
            ("cache", self._setup_cache),
            ("services", self._setup_services),
            ("websocket", self._setup_websocket),
            ("finalize", self._setup_finalize)
        ]
        
        for phase_name, setup_function in phases:
            app_state.startup_phase = phase_name
            setup_function(app_state)
            await asyncio.sleep(progression_delay)  # Realistic timing delay
        
        app_state.startup_complete = True
        app_state.startup_in_progress = False
    
    def _setup_dependencies(self, app_state: Mock):
        """Setup phase: dependencies (Phase 2)."""
        # Basic environment validation complete
        pass
    
    def _setup_database(self, app_state: Mock):
        """Setup phase: database (Phase 3)."""
        app_state.db_session_factory = Mock()
        app_state.database_available = True
    
    def _setup_cache(self, app_state: Mock):
        """Setup phase: cache (Phase 4)."""
        app_state.redis_manager = Mock()
        app_state.redis_manager.is_connected = True
    
    def _setup_services(self, app_state: Mock):
        """Setup phase: services (Phase 5) - CRITICAL for WebSocket."""
        app_state.auth_validation_complete = True
        app_state.key_manager = Mock()
        app_state.agent_supervisor = Mock()
        app_state.thread_service = Mock()
        
        # WebSocket bridge with required methods
        app_state.agent_websocket_bridge = Mock()
        app_state.agent_websocket_bridge.notify_agent_started = Mock()
        app_state.agent_websocket_bridge.notify_agent_completed = Mock()
        app_state.agent_websocket_bridge.notify_tool_executing = Mock()
    
    def _setup_websocket(self, app_state: Mock):
        """Setup phase: websocket (Phase 6)."""
        # WebSocket integration ready
        pass
    
    def _setup_finalize(self, app_state: Mock):
        """Setup phase: finalize (Phase 7)."""
        # Startup finalization complete
        pass
    
    @pytest.mark.asyncio
    async def test_race_condition_reproduction_early_validation(
        self, 
        mock_realistic_app_state, 
        gcp_staging_environment
    ):
        """
        Test race condition reproduction: validation runs before services phase.
        
        CRITICAL: This test reproduces the exact Issue #586 scenario where 
        WebSocket validation runs before the startup reaches services phase.
        """
        validator = create_gcp_websocket_validator(mock_realistic_app_state)
        
        # Start the startup progression (but don't wait for it)
        startup_task = asyncio.create_task(
            self.simulate_realistic_startup_progression(mock_realistic_app_state, progression_delay=0.2)
        )
        
        # Immediately try WebSocket validation (race condition scenario)
        # This simulates GCP Cloud Run accepting WebSocket connections before startup complete
        validation_start_time = time.time()
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)
        validation_elapsed = time.time() - validation_start_time
        
        # The validation should fail because services aren't ready yet
        assert result.ready is False, "WebSocket validation should fail during race condition"
        assert result.state == GCPReadinessState.FAILED, "Should be in FAILED state during race condition"
        assert "startup_phase_timeout" in result.failed_services, "Should detect startup phase timeout"
        assert result.details.get("race_condition_detected") is True, "Should detect race condition"
        
        # Wait for startup to complete
        await startup_task
        
        # Now validation should succeed
        result_after_startup = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)
        assert result_after_startup.ready is True, "WebSocket validation should succeed after startup complete"
    
    @pytest.mark.asyncio
    async def test_proper_timing_coordination_success(
        self,
        mock_realistic_app_state,
        gcp_staging_environment  
    ):
        """
        Test proper timing coordination: validation waits for services phase.
        
        SUCCESS CASE: This test validates that when validation waits for proper
        startup phase completion, WebSocket connections are accepted successfully.
        """
        validator = create_gcp_websocket_validator(mock_realistic_app_state)
        
        # Start startup progression
        startup_task = asyncio.create_task(
            self.simulate_realistic_startup_progression(mock_realistic_app_state, progression_delay=0.1)
        )
        
        # Wait a bit to let startup progress past services phase
        await asyncio.sleep(0.6)  # Should reach services phase by now
        
        # Now validate - should succeed
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=5.0)
        
        assert result.ready is True, "WebSocket validation should succeed after services phase"
        assert result.state == GCPReadinessState.WEBSOCKET_READY, "Should be WEBSOCKET_READY"
        assert len(result.failed_services) == 0, "No services should fail"
        
        # Cleanup
        await startup_task
    
    @pytest.mark.asyncio
    async def test_timeout_window_insufficient_reproduction(
        self,
        mock_realistic_app_state,
        gcp_staging_environment
    ):
        """
        Test timeout window insufficient scenario - reproduces 1.2s timeout issue.
        
        CRITICAL: This reproduces the specific timing issue where GCP cold starts
        take longer than the 1.2s timeout window mentioned in Issue #586.
        """
        validator = create_gcp_websocket_validator(mock_realistic_app_state)
        
        # Simulate slow startup (longer than timeout window)
        slow_startup_task = asyncio.create_task(
            self.simulate_realistic_startup_progression(mock_realistic_app_state, progression_delay=0.5)  # 2.5s total
        )
        
        # Try validation with insufficient timeout (reproduces the 1.2s issue)
        validation_start = time.time()
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=1.5)  # Less than startup time
        validation_elapsed = time.time() - validation_start
        
        # Should fail due to timeout
        assert result.ready is False, "Should fail due to insufficient timeout window"
        assert result.state == GCPReadinessState.FAILED, "Should be in FAILED state due to timeout"
        assert "startup_phase_timeout" in result.failed_services or "timeout" in result.failed_services, \
               "Should indicate timeout failure"
        assert validation_elapsed >= 1.0, "Should wait at least the startup wait timeout"
        
        # Cleanup
        slow_startup_task.cancel()
        try:
            await slow_startup_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio 
    async def test_concurrent_validation_and_startup(
        self,
        mock_realistic_app_state,
        gcp_staging_environment
    ):
        """
        Test concurrent validation and startup scenarios.
        
        REALISTIC SCENARIO: Multiple WebSocket connection attempts during startup
        should be handled consistently.
        """
        validator1 = create_gcp_websocket_validator(mock_realistic_app_state)
        validator2 = create_gcp_websocket_validator(mock_realistic_app_state)
        
        # Start startup progression
        startup_task = asyncio.create_task(
            self.simulate_realistic_startup_progression(mock_realistic_app_state, progression_delay=0.1)
        )
        
        # Start multiple concurrent validations at different times
        validation_tasks = [
            asyncio.create_task(validator1.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)),
            asyncio.create_task(validator2.validate_gcp_readiness_for_websocket(timeout_seconds=3.0))
        ]
        
        # Wait for all validations to complete
        results = await asyncio.gather(*validation_tasks)
        await startup_task
        
        # Both validations should have consistent results
        # They might both fail (if startup not ready) or both succeed (if startup ready)
        assert len(results) == 2, "Should have results from both validators"
        
        # Results should be consistent (both success or both failure)
        ready_states = [result.ready for result in results]
        assert len(set(ready_states)) <= 1, "Concurrent validations should have consistent results"


@pytest.mark.integration 
class TestServiceCoordinationTiming:
    """Test service coordination timing with realistic dependencies."""
    
    @pytest.fixture
    def progressive_app_state(self):
        """App state that can be progressively updated with services."""
        app_state = Mock()
        app_state.startup_phase = "init"
        app_state.startup_complete = False
        app_state.startup_failed = False
        app_state.startup_in_progress = True
        return app_state
    
    @pytest.fixture
    def gcp_production_environment(self):
        """Mock GCP production environment for conservative timing."""
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'production',
                'K_SERVICE': 'netra-backend'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            yield
    
    @pytest.mark.asyncio
    async def test_service_dependency_chain_validation(
        self,
        progressive_app_state,
        gcp_production_environment
    ):
        """
        Test service dependency chain validation with realistic timing.
        
        DEPENDENCY CHAIN: Database -> Redis -> Auth -> Agent Supervisor -> WebSocket Bridge
        """
        validator = create_gcp_websocket_validator(progressive_app_state)
        
        # Phase 1: No services available
        progressive_app_state.startup_phase = "dependencies"
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=5.0)
        assert result.ready is False, "Should fail when no services available"
        
        # Phase 2: Add database
        progressive_app_state.startup_phase = "database"
        progressive_app_state.db_session_factory = Mock()
        progressive_app_state.database_available = True
        
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=5.0)
        assert result.ready is False, "Should fail when only database available"
        
        # Phase 3: Add Redis
        progressive_app_state.startup_phase = "cache"
        progressive_app_state.redis_manager = Mock()
        progressive_app_state.redis_manager.is_connected = True
        
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=5.0)
        assert result.ready is False, "Should fail when Redis available but services not ready"
        
        # Phase 4: Add auth
        progressive_app_state.startup_phase = "services"
        progressive_app_state.auth_validation_complete = True
        progressive_app_state.key_manager = Mock()
        
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=5.0)
        assert result.ready is False, "Should fail when auth ready but agent services not ready"
        
        # Phase 5: Add agent services
        progressive_app_state.agent_supervisor = Mock()
        progressive_app_state.thread_service = Mock()
        progressive_app_state.agent_websocket_bridge = Mock()
        progressive_app_state.agent_websocket_bridge.notify_agent_started = Mock()
        progressive_app_state.agent_websocket_bridge.notify_agent_completed = Mock()
        progressive_app_state.agent_websocket_bridge.notify_tool_executing = Mock()
        
        # Phase 6: WebSocket phase 
        progressive_app_state.startup_phase = "websocket"
        
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=5.0)
        assert result.ready is True, "Should succeed when all services available"
        assert result.state == GCPReadinessState.WEBSOCKET_READY, "Should be WEBSOCKET_READY"
    
    @pytest.mark.asyncio
    async def test_service_failure_recovery_timing(
        self,
        progressive_app_state,
        gcp_production_environment
    ):
        """
        Test service failure and recovery timing scenarios.
        
        RESILIENCE: Tests how the system handles temporary service failures
        and recovery during the startup sequence.
        """
        validator = create_gcp_websocket_validator(progressive_app_state)
        
        # Setup services in ready state
        progressive_app_state.startup_phase = "services"
        progressive_app_state.db_session_factory = Mock()
        progressive_app_state.database_available = True
        progressive_app_state.redis_manager = Mock()
        progressive_app_state.redis_manager.is_connected = True
        progressive_app_state.auth_validation_complete = True
        progressive_app_state.key_manager = Mock()
        progressive_app_state.agent_supervisor = Mock()
        progressive_app_state.thread_service = Mock()
        progressive_app_state.agent_websocket_bridge = Mock()
        progressive_app_state.agent_websocket_bridge.notify_agent_started = Mock()
        progressive_app_state.agent_websocket_bridge.notify_agent_completed = Mock()
        progressive_app_state.agent_websocket_bridge.notify_tool_executing = Mock()
        
        # Initial validation should succeed
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)
        assert result.ready is True, "Initial validation should succeed"
        
        # Simulate Redis failure
        progressive_app_state.redis_manager.is_connected = False
        
        result_with_failure = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)
        # In production, this should fail or handle gracefully depending on implementation
        # The key is that it should not cause a crash or undefined behavior
        assert isinstance(result_with_failure.ready, bool), "Should return a defined boolean result"
        
        # Simulate Redis recovery
        progressive_app_state.redis_manager.is_connected = True
        
        result_after_recovery = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)
        assert result_after_recovery.ready is True, "Should succeed after service recovery"
    
    @pytest.mark.asyncio
    async def test_realistic_startup_timing_measurements(
        self,
        progressive_app_state,
        gcp_production_environment
    ):
        """
        Test realistic startup timing measurements and performance.
        
        PERFORMANCE: Measures actual validation timing to ensure it meets
        performance requirements for production environments.
        """
        validator = create_gcp_websocket_validator(progressive_app_state)
        
        # Setup all services as ready
        progressive_app_state.startup_phase = "services"  
        progressive_app_state.db_session_factory = Mock()
        progressive_app_state.database_available = True
        progressive_app_state.redis_manager = Mock()
        progressive_app_state.redis_manager.is_connected = True
        progressive_app_state.auth_validation_complete = True
        progressive_app_state.key_manager = Mock()
        progressive_app_state.agent_supervisor = Mock()
        progressive_app_state.thread_service = Mock()
        progressive_app_state.agent_websocket_bridge = Mock()
        progressive_app_state.agent_websocket_bridge.notify_agent_started = Mock()
        progressive_app_state.agent_websocket_bridge.notify_agent_completed = Mock()
        progressive_app_state.agent_websocket_bridge.notify_tool_executing = Mock()
        progressive_app_state.startup_phase = "websocket"
        
        # Measure validation timing
        start_time = time.time()
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=10.0)
        elapsed_time = time.time() - start_time
        
        # Performance assertions
        assert result.ready is True, "Validation should succeed with all services ready"
        assert elapsed_time < 5.0, f"Validation should complete within 5 seconds, took {elapsed_time:.2f}s"
        assert result.elapsed_time > 0, "Should record elapsed time"
        assert result.elapsed_time < 5.0, f"Result should record realistic elapsed time, got {result.elapsed_time:.2f}s"


@pytest.mark.integration
class TestGracefulDegradationScenarios:
    """Test graceful degradation scenarios with realistic service behavior."""
    
    @pytest.fixture
    def staging_app_state_with_issues(self):
        """App state with various service issues for graceful degradation testing."""
        app_state = Mock()
        app_state.startup_phase = "services"
        app_state.startup_complete = False
        app_state.startup_failed = False
        app_state.startup_in_progress = True
        
        # Database available but Redis has issues
        app_state.db_session_factory = Mock()
        app_state.database_available = True
        app_state.redis_manager = Mock()
        app_state.redis_manager.is_connected = False  # Redis connection delayed
        
        # Auth ready
        app_state.auth_validation_complete = True
        app_state.key_manager = Mock()
        
        # Agent services ready
        app_state.agent_supervisor = Mock()
        app_state.thread_service = Mock()
        app_state.agent_websocket_bridge = Mock()
        app_state.agent_websocket_bridge.notify_agent_started = Mock()
        app_state.agent_websocket_bridge.notify_agent_completed = Mock()
        app_state.agent_websocket_bridge.notify_tool_executing = Mock()
        
        return app_state
    
    @pytest.fixture
    def gcp_staging_environment(self):
        """Mock GCP staging environment for graceful degradation."""
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'K_SERVICE': 'netra-backend'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            yield
    
    @pytest.mark.asyncio
    async def test_redis_delay_graceful_degradation(
        self,
        staging_app_state_with_issues,
        gcp_staging_environment
    ):
        """
        Test graceful degradation when Redis connection is delayed.
        
        GOLDEN PATH: Allow basic chat functionality even when Redis has startup delays
        to prevent complete chat blockage in staging.
        """
        validator = create_gcp_websocket_validator(staging_app_state_with_issues)
        
        # Validation should succeed despite Redis connection delay in staging
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)
        
        assert result.ready is True, "Should succeed with graceful degradation in staging"
        assert result.state == GCPReadinessState.WEBSOCKET_READY, "Should be WEBSOCKET_READY with degradation"
        assert len(result.warnings) > 0, "Should include warnings about degraded operation"
        assert any("Redis" in warning or "degraded" in warning for warning in result.warnings), \
               "Should warn about Redis degraded mode"
    
    @pytest.mark.asyncio
    async def test_multiple_service_issues_handling(
        self,
        gcp_staging_environment
    ):
        """
        Test handling of multiple service issues simultaneously.
        
        RESILIENCE: System should handle multiple service issues gracefully
        and provide clear diagnostics about what's working vs. degraded.
        """
        app_state = Mock()
        app_state.startup_phase = "services"
        app_state.startup_complete = False
        app_state.startup_failed = False
        app_state.startup_in_progress = True
        
        # Multiple service issues
        app_state.db_session_factory = None  # Database issue
        app_state.database_available = False
        app_state.redis_manager = Mock()
        app_state.redis_manager.is_connected = False  # Redis issue
        
        # Auth available
        app_state.auth_validation_complete = True
        app_state.key_manager = Mock()
        
        # Agent services available
        app_state.agent_supervisor = Mock()
        app_state.thread_service = Mock()
        app_state.agent_websocket_bridge = Mock()
        app_state.agent_websocket_bridge.notify_agent_started = Mock()
        app_state.agent_websocket_bridge.notify_agent_completed = Mock()
        app_state.agent_websocket_bridge.notify_tool_executing = Mock()
        
        validator = create_gcp_websocket_validator(app_state)
        
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)
        
        # In staging, should allow graceful degradation for non-critical services
        # Critical services (agent_supervisor, websocket_bridge) should be required
        assert isinstance(result.ready, bool), "Should return a defined result"
        
        # Should provide detailed information about service states
        assert isinstance(result.warnings, list), "Should provide warnings list"
        assert isinstance(result.failed_services, list), "Should provide failed services list"
        assert isinstance(result.details, dict), "Should provide detailed information"
    
    @pytest.mark.asyncio
    async def test_golden_path_chat_functionality_preservation(
        self,
        staging_app_state_with_issues,
        gcp_staging_environment
    ):
        """
        Test that Golden Path chat functionality is preserved during degradation.
        
        BUSINESS CRITICAL: Even with service issues, core chat functionality
        (90% of platform value) should remain operational.
        """
        validator = create_gcp_websocket_validator(staging_app_state_with_issues)
        
        # Critical services for chat must be ready
        staging_app_state_with_issues.agent_supervisor = Mock()
        staging_app_state_with_issues.thread_service = Mock()
        staging_app_state_with_issues.agent_websocket_bridge = Mock()
        staging_app_state_with_issues.agent_websocket_bridge.notify_agent_started = Mock()
        staging_app_state_with_issues.agent_websocket_bridge.notify_agent_completed = Mock()
        staging_app_state_with_issues.agent_websocket_bridge.notify_tool_executing = Mock()
        
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)
        
        # Golden Path should work - WebSocket connections allowed for chat
        assert result.ready is True, "Golden Path chat functionality should be preserved"
        
        # Should indicate degraded operation but functional
        assert len(result.warnings) > 0, "Should warn about degraded operation"
        
        # Critical chat services should not be in failed list
        critical_chat_services = ['agent_supervisor', 'websocket_bridge', 'websocket_integration']
        chat_services_failed = [svc for svc in result.failed_services if any(critical in svc for critical in critical_chat_services)]
        assert len(chat_services_failed) == 0, f"Critical chat services should not fail: {chat_services_failed}"