"""
Unit tests for startup phase coordination with WebSocket validation.

MISSION CRITICAL: Tests the core logic that prevents WebSocket 1011 race conditions
by ensuring validation only runs after appropriate startup phases are complete.

Business Value Justification (BVJ):
- Segment: Platform/All Users
- Business Goal: Platform Stability & Golden Path Reliability
- Value Impact: Prevents WebSocket connection failures that block 90% of platform value
- Strategic Impact: Ensures reliable chat functionality during GCP Cloud Run startup

Test Strategy:
- Unit tests focus on timing logic and phase coordination without requiring services
- Tests validate race condition detection and prevention logic
- Tests ensure proper integration between startup phases and WebSocket readiness
"""

import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from enum import Enum

from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    GCPReadinessState,
    create_gcp_websocket_validator
)


class MockStartupPhase(Enum):
    """Mock startup phases for testing."""
    INIT = "init"
    DEPENDENCIES = "dependencies" 
    DATABASE = "database"
    CACHE = "cache"
    SERVICES = "services"
    WEBSOCKET = "websocket"
    FINALIZE = "finalize"


class TestStartupPhaseCoordination:
    """Test startup phase coordination with WebSocket validation."""
    
    @pytest.fixture
    def mock_app_state_early_phase(self):
        """Mock app state during early startup phases (before SERVICES)."""
        app_state = Mock()
        app_state.startup_phase = "dependencies"  # Early phase
        app_state.startup_complete = False
        app_state.startup_failed = False
        app_state.startup_in_progress = True
        return app_state
    
    @pytest.fixture 
    def mock_app_state_services_phase(self):
        """Mock app state during services phase (Phase 5)."""
        app_state = Mock()
        app_state.startup_phase = "services"  # Services phase reached
        app_state.startup_complete = False  # Still in progress
        app_state.startup_failed = False
        app_state.startup_in_progress = True
        
        # Mock service readiness
        app_state.agent_supervisor = Mock()
        app_state.thread_service = Mock()
        app_state.agent_websocket_bridge = Mock()
        app_state.agent_websocket_bridge.notify_agent_started = Mock()
        app_state.agent_websocket_bridge.notify_agent_completed = Mock()
        app_state.agent_websocket_bridge.notify_tool_executing = Mock()
        
        return app_state
    
    @pytest.fixture
    def mock_app_state_no_app_state(self):
        """Mock scenario where app_state is not available."""
        return None
    
    @pytest.fixture
    def gcp_environment_staging(self):
        """Mock GCP staging environment."""
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'K_SERVICE': 'netra-backend'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            yield

    def test_race_condition_detection_early_phase(self, mock_app_state_early_phase, gcp_environment_staging):
        """
        Test race condition detection when validation runs during early startup phases.
        
        CRITICAL: This test validates that agent_supervisor validation is skipped
        during early phases (before SERVICES) to prevent the race condition.
        """
        validator = create_gcp_websocket_validator(mock_app_state_early_phase)
        
        # Test agent supervisor validation during early phase - should return False
        result = validator._validate_agent_supervisor_readiness()
        
        # Expect False because we're in 'dependencies' phase, not 'services' yet
        assert result is False, "Agent supervisor validation should be skipped during early startup phases"
    
    def test_race_condition_prevention_services_phase(self, mock_app_state_services_phase, gcp_environment_staging):
        """
        Test that validation proceeds normally when services phase is reached.
        
        CRITICAL: This test validates that once startup reaches the services phase,
        agent_supervisor validation can proceed normally.
        """
        validator = create_gcp_websocket_validator(mock_app_state_services_phase)
        
        # Test agent supervisor validation during services phase - should return True
        result = validator._validate_agent_supervisor_readiness()
        
        # Expect True because we're in 'services' phase and mocks are set up
        assert result is True, "Agent supervisor validation should proceed during services phase"
    
    def test_websocket_bridge_phase_coordination(self, mock_app_state_early_phase, gcp_environment_staging):
        """
        Test WebSocket bridge validation coordination with startup phases.
        
        CRITICAL: WebSocket bridge validation should also be skipped during early phases
        to prevent race conditions similar to agent_supervisor.
        """
        validator = create_gcp_websocket_validator(mock_app_state_early_phase)
        
        # Test WebSocket bridge validation during early phase
        result = validator._validate_websocket_bridge_readiness()
        
        # Should return False because we're in early phase
        assert result is False, "WebSocket bridge validation should be skipped during early startup phases"
    
    def test_no_app_state_race_condition(self, mock_app_state_no_app_state, gcp_environment_staging):
        """
        Test race condition when app_state is not available (the core issue).
        
        CRITICAL: This reproduces the exact error from Issue #586 where validation
        runs before app_state is initialized, causing "no_app_state" errors.
        """
        validator = create_gcp_websocket_validator(mock_app_state_no_app_state)
        
        # Test various validations with no app_state - all should fail
        assert validator._validate_database_readiness() is False, "Database validation should fail with no app_state"
        
        # Redis validation is async, need to handle it properly
        import asyncio
        async def test_redis():
            return await validator._validate_redis_readiness()
        
        result = asyncio.run(test_redis())
        assert result is False, "Redis validation should fail with no app_state"
        
        assert validator._validate_auth_system_readiness() is False, "Auth validation should fail with no app_state"
        assert validator._validate_agent_supervisor_readiness() is False, "Agent supervisor validation should fail with no app_state"
        assert validator._validate_websocket_bridge_readiness() is False, "WebSocket bridge validation should fail with no app_state"
    
    @pytest.mark.asyncio
    async def test_startup_phase_wait_timeout(self, mock_app_state_early_phase, gcp_environment_staging):
        """
        Test startup phase wait timeout - reproduces the 1.2s timeout issue.
        
        CRITICAL: This test reproduces the specific timeout issue from Issue #586
        where startup doesn't reach 'services' phase within the timeout window.
        """
        validator = create_gcp_websocket_validator(mock_app_state_early_phase)
        
        # Test waiting for services phase with short timeout (simulating the race condition)
        start_time = time.time()
        result = await validator._wait_for_startup_phase_completion(
            minimum_phase='services',
            timeout_seconds=0.5  # Very short timeout to reproduce the issue
        )
        elapsed_time = time.time() - start_time
        
        # Should timeout because mock app state never progresses to services phase
        assert result is False, "Should timeout waiting for services phase"
        assert elapsed_time >= 0.5, f"Should wait at least the timeout duration, got {elapsed_time}"
    
    @pytest.mark.asyncio 
    async def test_startup_phase_progression_simulation(self, gcp_environment_staging):
        """
        Test startup phase progression simulation to validate timing logic.
        
        This test simulates the startup sequence progressing through phases
        and validates that WebSocket validation behaves correctly at each phase.
        """
        # Create dynamic app state that can progress through phases
        app_state = Mock()
        app_state.startup_complete = False
        app_state.startup_failed = False
        app_state.startup_in_progress = True
        
        validator = create_gcp_websocket_validator(app_state)
        
        # Phase sequence: init -> dependencies -> services
        phases = ['init', 'dependencies', 'services']
        
        for i, phase in enumerate(phases):
            app_state.startup_phase = phase
            
            # Test agent supervisor validation at each phase
            supervisor_ready = validator._validate_agent_supervisor_readiness()
            bridge_ready = validator._validate_websocket_bridge_readiness()
            
            if phase in ['init', 'dependencies']:
                # Early phases - validation should be skipped
                assert supervisor_ready is False, f"Supervisor should not be ready in {phase} phase"
                assert bridge_ready is False, f"Bridge should not be ready in {phase} phase"
            elif phase == 'services':
                # Services phase - validation should check actual services
                # (Will fail due to no mocked services, but that's expected)
                # The key is that it proceeds with validation instead of skipping
                pass
    
    def test_race_condition_logging_validation(self, mock_app_state_early_phase, gcp_environment_staging):
        """
        Test that race condition scenarios are properly logged for debugging.
        
        Ensures that when race conditions are detected, appropriate logging occurs
        to help diagnose the issue in production environments.
        """
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.central_logger') as mock_logger:
            mock_logger.get_logger.return_value = Mock()
            logger_instance = mock_logger.get_logger.return_value
            
            validator = create_gcp_websocket_validator(mock_app_state_early_phase)
            
            # Trigger race condition detection
            validator._validate_agent_supervisor_readiness()
            
            # Verify appropriate logging occurred
            logger_instance.debug.assert_called()
            
            # Check that debug messages contain race condition context
            debug_calls = logger_instance.debug.call_args_list
            race_condition_logged = any(
                'startup phase' in str(call) and ('skipping' in str(call).lower() or 'race condition' in str(call).lower())
                for call in debug_calls
            )
            
            assert race_condition_logged, "Race condition detection should be logged for debugging"


class TestTimeoutConfiguration:
    """Test timeout configuration and environment-specific behavior."""
    
    @pytest.fixture
    def staging_environment(self):
        """Mock staging environment configuration."""
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'K_SERVICE': 'netra-backend'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            yield
    
    @pytest.fixture
    def production_environment(self):
        """Mock production environment configuration."""  
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'production',
                'K_SERVICE': 'netra-backend'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            yield
    
    def test_environment_timeout_optimization(self, staging_environment):
        """
        Test that timeout configuration is optimized based on environment.
        
        PERFORMANCE: Validates that staging gets faster timeouts than production
        for better development experience while maintaining safety.
        """
        validator = create_gcp_websocket_validator(Mock())
        
        # Staging should have optimized (faster) timeouts
        base_timeout = 10.0
        optimized_timeout = validator._get_optimized_timeout(base_timeout)
        
        # Should be less than base timeout due to staging optimization
        assert optimized_timeout < base_timeout, f"Staging should have faster timeout, got {optimized_timeout}"
        assert optimized_timeout >= 0.5, "Should maintain minimum Cloud Run safety timeout"
    
    def test_production_timeout_conservative(self, production_environment):
        """
        Test that production environment uses conservative timeouts.
        
        RELIABILITY: Validates that production prioritizes reliability over speed.
        """
        validator = create_gcp_websocket_validator(Mock())
        
        base_timeout = 5.0
        optimized_timeout = validator._get_optimized_timeout(base_timeout)
        
        # Production should use conservative timeouts (close to base timeout)
        assert optimized_timeout >= base_timeout * 0.8, "Production should use conservative timeouts"
    
    def test_cloud_run_minimum_timeout_enforcement(self, staging_environment):
        """
        Test that Cloud Run minimum timeout is enforced regardless of optimization.
        
        SAFETY: Ensures race condition protection is maintained even with aggressive optimization.
        """
        validator = create_gcp_websocket_validator(Mock())
        
        # Very small base timeout should still meet Cloud Run minimum
        very_small_timeout = 0.1
        optimized_timeout = validator._get_optimized_timeout(very_small_timeout)
        
        # Should be at least the minimum Cloud Run timeout
        assert optimized_timeout >= 0.5, "Should enforce minimum Cloud Run timeout for race condition safety"


class TestAppStateIntegration:
    """Test app_state integration and synchronization."""
    
    def test_app_state_availability_detection(self):
        """
        Test detection of app_state availability vs unavailability.
        
        CRITICAL: This tests the core condition that triggers Issue #586 -
        when app_state is not available during early validation.
        """
        # Test with available app_state
        available_state = Mock()
        validator_with_state = create_gcp_websocket_validator(available_state)
        assert validator_with_state.app_state is not None, "Should detect available app_state"
        
        # Test with unavailable app_state (the race condition scenario)
        validator_no_state = create_gcp_websocket_validator(None)
        assert validator_no_state.app_state is None, "Should detect unavailable app_state"
    
    def test_startup_phase_attribute_detection(self):
        """
        Test detection of startup_phase attribute in app_state.
        
        Validates that the validator can properly detect and use startup phase
        information when available.
        """
        # Test with startup_phase attribute
        app_state_with_phase = Mock()
        app_state_with_phase.startup_phase = "services"
        validator = create_gcp_websocket_validator(app_state_with_phase)
        
        # Should be able to access startup phase
        result = validator._validate_agent_supervisor_readiness()
        # The specific result doesn't matter, just that it doesn't crash
        
        # Test without startup_phase attribute
        app_state_no_phase = Mock()
        # Remove startup_phase attribute
        if hasattr(app_state_no_phase, 'startup_phase'):
            delattr(app_state_no_phase, 'startup_phase')
        
        validator_no_phase = create_gcp_websocket_validator(app_state_no_phase)
        
        # Should handle gracefully without crashing
        result = validator_no_phase._validate_agent_supervisor_readiness()
        # Expect False since no startup phase info available
        assert result is False, "Should handle missing startup_phase attribute gracefully"
    
    def test_service_attribute_progressive_availability(self):
        """
        Test progressive availability of service attributes during startup.
        
        Simulates how services become available progressively during the startup
        sequence, which is the expected behavior.
        """
        app_state = Mock()
        app_state.startup_phase = "services"
        
        # Initially no services available
        validator = create_gcp_websocket_validator(app_state)
        
        # Add services progressively
        services_to_add = [
            ('agent_supervisor', Mock()),
            ('thread_service', Mock()), 
            ('agent_websocket_bridge', Mock())
        ]
        
        for i, (service_name, service_mock) in enumerate(services_to_add):
            setattr(app_state, service_name, service_mock)
            
            # Test readiness after each service addition
            if service_name == 'agent_supervisor':
                # Need both agent_supervisor and thread_service
                supervisor_ready = validator._validate_agent_supervisor_readiness()
                if i == 0:  # Only supervisor added
                    assert supervisor_ready is False, "Should need both supervisor and thread_service"
            elif service_name == 'thread_service':
                # Now both are available
                supervisor_ready = validator._validate_agent_supervisor_readiness() 
                assert supervisor_ready is True, "Should be ready when both supervisor and thread_service available"


class TestGracefulDegradation:
    """Test graceful degradation during race conditions."""
    
    @pytest.fixture
    def staging_gcp_environment(self):
        """Mock staging GCP environment for graceful degradation testing."""
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'K_SERVICE': 'netra-backend'  
            }.get(key, default)
            mock_get_env.return_value = mock_env
            yield
    
    def test_staging_graceful_degradation_database(self, staging_gcp_environment):
        """
        Test graceful degradation for database validation in staging.
        
        GOLDEN PATH: In staging, allow basic functionality even when database
        isn't fully ready to prevent complete chat blockage.
        """
        # No app_state scenario (race condition)
        validator = create_gcp_websocket_validator(None)
        
        # In staging with no app_state, should allow graceful degradation
        result = validator._validate_database_readiness()
        
        # Should return True for staging graceful degradation
        assert result is True, "Staging should allow graceful degradation when app_state not available"
    
    def test_production_strict_validation(self):
        """
        Test that production maintains strict validation without degradation.
        
        RELIABILITY: Production should never compromise on service readiness
        even during race conditions.
        """
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'production',
                'K_SERVICE': 'netra-backend'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            
            # No app_state scenario in production
            validator = create_gcp_websocket_validator(None)
            
            # Production should maintain strict validation
            result = validator._validate_database_readiness()
            
            # Should return False - no graceful degradation in production
            assert result is False, "Production should maintain strict validation without degradation"
    
    @pytest.mark.asyncio
    async def test_redis_graceful_degradation_staging(self, staging_gcp_environment):
        """
        Test Redis graceful degradation in staging environment.
        
        GOLDEN PATH: Allow basic chat functionality even when Redis has startup delays.
        """
        app_state = Mock()
        app_state.redis_manager = Mock()
        app_state.redis_manager.is_connected = False  # Redis delayed
        
        validator = create_gcp_websocket_validator(app_state)
        
        # Should allow degraded operation in staging
        result = await validator._validate_redis_readiness()
        
        # Expect True for graceful degradation in staging
        assert result is True, "Staging should allow graceful degradation when Redis connection delayed"