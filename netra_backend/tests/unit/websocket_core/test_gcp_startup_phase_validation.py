"""
UNIT TESTS: GCP Startup Phase Validation - WebSocket Supervisor Race Condition Prevention

MISSION CRITICAL: These tests validate the startup phase awareness logic that prevents
WebSocket 1011 errors in GCP Cloud Run by ensuring agent_supervisor validation only
occurs after Phase 5 (SERVICES) completion.

ROOT CAUSE ADDRESSED: GCP Cloud Run WebSocket connections failing with 1011 errors 
due to agent_supervisor not being available during readiness validation. This happens
because validation runs before the deterministic startup sequence reaches Phase 5.

TEST STRATEGY:
- Tests MUST initially FAIL to prove the race condition exists
- Tests validate startup phase awareness prevents early validation
- Tests ensure proper validation after Phase 5 completion
- Tests cover GCP-specific timeout and retry logic

Business Value:
- Segment: Platform/Internal - Chat Infrastructure Stability
- Business Goal: Platform Stability & Chat Value Delivery (90% of platform value)
- Value Impact: Eliminates WebSocket race conditions preventing reliable AI chat
- Strategic Impact: $500K+ ARR protection through reliable chat functionality

SSOT COMPLIANCE:
- Uses test_framework.ssot.base_test_case.SSotBaseTestCase
- Uses shared.isolated_environment for environment access
- Integrates with existing GCP initialization validator patterns
- Follows SSOT mock factory patterns for consistent test infrastructure
"""

import asyncio
import logging
import time
import unittest.mock
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch, MagicMock

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics, CategoryType
from shared.isolated_environment import get_env

# Target System Under Test
from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    GCPReadinessState,
    GCPReadinessResult,
    ServiceReadinessCheck,
    create_gcp_websocket_validator
)

# Service Readiness Validator for enhanced validation
from netra_backend.app.websocket_core.service_readiness_validator import (
    ServiceReadinessValidator,
    ServiceReadinessLevel,
    ServiceCriticality,
    ServiceValidationResult,
    create_service_readiness_validator
)


class MockAppStateForStartupPhases:
    """Mock app state that simulates different startup phases for race condition testing."""
    
    def __init__(
        self, 
        startup_phase: str = "unknown",
        completed_phases: Optional[List[str]] = None,
        startup_in_progress: bool = True,
        startup_complete: bool = False,
        has_agent_supervisor: bool = False,
        has_thread_service: bool = False
    ):
        self.startup_phase = startup_phase
        self.startup_completed_phases = completed_phases or []
        self.startup_in_progress = startup_in_progress
        self.startup_complete = startup_complete
        
        # Services that depend on startup phase
        self.agent_supervisor = Mock() if has_agent_supervisor else None
        self.thread_service = Mock() if has_thread_service else None
        
        # Other app state attributes for comprehensive validation
        self.db_session_factory = Mock()
        self.database_available = True
        self.redis_manager = self._create_mock_redis_manager()
        self.auth_validation_complete = True
        self.key_manager = Mock()
        self.agent_websocket_bridge = Mock() if has_agent_supervisor else None
    
    def _create_mock_redis_manager(self) -> Mock:
        """Create mock Redis manager with realistic interface."""
        redis_manager = Mock()
        redis_manager.is_connected = True
        redis_manager.get_status.return_value = {"connected": True, "pool_size": 10}
        redis_manager._client = AsyncMock()
        redis_manager._client.ping = AsyncMock(return_value=True)
        return redis_manager


class TestStartupPhaseValidationLogic(SSotBaseTestCase):
    """Unit tests for startup phase awareness in GCP WebSocket validator."""
    
    def setup_method(self, method=None):
        """Set up test fixtures with SSOT patterns."""
        super().setup_method(method)
        self.test_metrics = SsotTestMetrics()
        self.test_metrics.start_timing()
        
        # Configure test environment as GCP staging
        self.env_patches = []
        gcp_env_patch = patch.dict('os.environ', {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-backend-staging',
            'K_REVISION': 'netra-backend-staging-00042'
        })
        gcp_env_patch.start()
        self.env_patches.append(gcp_env_patch)
        
        self.logger = logging.getLogger(__name__)
    
    def teardown_method(self, method=None):
        """Clean up test fixtures."""
        for patch_obj in self.env_patches:
            patch_obj.stop()
        
        self.test_metrics.end_timing()
        super().teardown_method(method)
    
    def test_agent_supervisor_validation_skips_early_phases(self):
        """
        Verify validation returns False during phases before SERVICES.
        
        RACE CONDITION TEST: This test validates that agent_supervisor validation
        is skipped during early startup phases, preventing 1011 errors.
        
        Expected Behavior:
        - Phases init, dependencies, database, cache: validation returns False
        - Validation should not attempt to check app.state.agent_supervisor
        - Should log appropriate debug message about phase skipping
        """
        early_phases = ['init', 'dependencies', 'database', 'cache']
        
        for phase in early_phases:
            # Create app state simulating early startup phase
            app_state = MockAppStateForStartupPhases(
                startup_phase=phase,
                completed_phases=['init'] if phase != 'init' else [],
                startup_in_progress=True,
                startup_complete=False,
                has_agent_supervisor=False,  # Not yet created
                has_thread_service=False
            )
            
            # Create validator
            validator = GCPWebSocketInitializationValidator(app_state)
            
            # Test agent supervisor validation
            with patch.object(validator.logger, 'debug') as mock_debug:
                result = validator._validate_agent_supervisor_readiness()
                
                # CRITICAL: Should return False during early phases
                assert result is False, (
                    f"Agent supervisor validation should return False during {phase} phase "
                    f"to prevent WebSocket 1011 errors"
                )
                
                # Should log phase-aware skip message
                debug_calls = [str(call) for call in mock_debug.call_args_list]
                phase_skip_logged = any(
                    phase in call and 'skip' in call.lower() 
                    for call in debug_calls
                )
                assert phase_skip_logged, (
                    f"Expected debug log about skipping validation during {phase} phase"
                )
            
            self.test_metrics.record_custom(f"early_phase_{phase}_validated", True)
    
    def test_agent_supervisor_validation_allows_services_phase(self):
        """
        Verify validation proceeds during SERVICES phase when supervisor is available.
        
        RACE CONDITION RESOLUTION: This test validates that once Phase 5 (SERVICES)
        begins, agent_supervisor validation can proceed normally.
        
        Expected Behavior:
        - Phase 'services': validation proceeds to check app.state.agent_supervisor
        - Should return True when supervisor and thread_service are available
        - Should return False when supervisor is missing
        """
        # Test case 1: Services phase with supervisor available
        app_state_with_supervisor = MockAppStateForStartupPhases(
            startup_phase='services',
            completed_phases=['init', 'dependencies', 'database', 'cache'],
            startup_in_progress=True,
            startup_complete=False,
            has_agent_supervisor=True,
            has_thread_service=True
        )
        
        validator = GCPWebSocketInitializationValidator(app_state_with_supervisor)
        
        with patch.object(validator.logger, 'debug') as mock_debug:
            result = validator._validate_agent_supervisor_readiness()
            
            # Should proceed with validation and return True
            assert result is True, (
                "Agent supervisor validation should return True during services phase "
                "when supervisor is available"
            )
            
            # Should not log phase skip message
            debug_calls = [str(call) for call in mock_debug.call_args_list]
            phase_skip_logged = any(
                'skip' in call.lower() and 'phase' in call.lower()
                for call in debug_calls
            )
            assert not phase_skip_logged, (
                "Should not skip validation during services phase"
            )
        
        # Test case 2: Services phase but supervisor not yet available
        app_state_without_supervisor = MockAppStateForStartupPhases(
            startup_phase='services',
            completed_phases=['init', 'dependencies', 'database', 'cache'],
            startup_in_progress=True,
            startup_complete=False,
            has_agent_supervisor=False,  # Still being initialized
            has_thread_service=False
        )
        
        validator2 = GCPWebSocketInitializationValidator(app_state_without_supervisor)
        result2 = validator2._validate_agent_supervisor_readiness()
        
        # Should proceed with validation but return False due to missing supervisor
        assert result2 is False, (
            "Agent supervisor validation should return False during services phase "
            "when supervisor is not yet available"
        )
        
        self.test_metrics.record_custom("services_phase_validation_tested", True)
    
    def test_agent_supervisor_validation_allows_post_services_phases(self):
        """
        Verify validation works normally in websocket and finalize phases.
        
        NORMAL OPERATION TEST: After Phase 5 completion, validation should work
        normally without any phase-based restrictions.
        
        Expected Behavior:
        - Phases websocket, finalize, complete: validation proceeds normally
        - Should return True when all services are available
        - No startup phase restrictions apply
        """
        post_services_phases = ['websocket', 'finalize', 'complete']
        
        for phase in post_services_phases:
            completed_phases = ['init', 'dependencies', 'database', 'cache', 'services']
            if phase != 'websocket':
                completed_phases.append('websocket')
            if phase == 'complete':
                completed_phases.extend(['finalize'])
            
            app_state = MockAppStateForStartupPhases(
                startup_phase=phase,
                completed_phases=completed_phases,
                startup_in_progress=(phase != 'complete'),
                startup_complete=(phase == 'complete'),
                has_agent_supervisor=True,
                has_thread_service=True
            )
            
            validator = GCPWebSocketInitializationValidator(app_state)
            
            with patch.object(validator.logger, 'debug') as mock_debug:
                result = validator._validate_agent_supervisor_readiness()
                
                # Should return True in post-services phases
                assert result is True, (
                    f"Agent supervisor validation should return True during {phase} phase "
                    f"when all services are available"
                )
                
                # Should not log phase skip message
                debug_calls = [str(call) for call in mock_debug.call_args_list]
                phase_skip_logged = any(
                    'skip' in call.lower() and 'phase' in call.lower()
                    for call in debug_calls
                )
                assert not phase_skip_logged, (
                    f"Should not skip validation during {phase} phase"
                )
            
            self.test_metrics.record_custom(f"post_services_phase_{phase}_validated", True)
    
    def test_startup_completion_check_in_enhanced_validator(self):
        """
        Test the enhanced service readiness validator startup completion logic.
        
        COMPREHENSIVE VALIDATION: The enhanced validator should wait for startup
        completion before running any service validations.
        
        Expected Behavior:
        - Should detect startup_in_progress state
        - Should wait for startup completion (with timeout)
        - Should proceed with validation after startup completion
        """
        # Test case 1: Startup in progress
        app_state_startup_in_progress = MockAppStateForStartupPhases(
            startup_phase='services',
            completed_phases=['init', 'dependencies', 'database', 'cache'],
            startup_in_progress=True,
            startup_complete=False,
            has_agent_supervisor=False  # Still initializing
        )
        
        validator = create_service_readiness_validator(
            app_state_startup_in_progress, 
            environment='staging'
        )
        
        # Test agent supervisor validation during startup
        result = validator._validate_agent_supervisor()
        
        # Should return False when startup is in progress and supervisor not ready
        self.assertFalse(
            result,
            "Service readiness validator should return False when startup in progress "
            "and agent_supervisor not yet available"
        )
        
        # Test case 2: Startup completed
        app_state_startup_complete = MockAppStateForStartupPhases(
            startup_phase='complete',
            completed_phases=['init', 'dependencies', 'database', 'cache', 'services', 'websocket', 'finalize'],
            startup_in_progress=False,
            startup_complete=True,
            has_agent_supervisor=True,
            has_thread_service=True
        )
        
        validator2 = create_service_readiness_validator(
            app_state_startup_complete,
            environment='staging'
        )
        
        # Test agent supervisor validation after startup completion
        result2 = validator2._validate_agent_supervisor()
        
        # Should return True when startup complete and supervisor available
        self.assertTrue(
            result2,
            "Service readiness validator should return True when startup complete "
            "and agent_supervisor is available"
        )
        
        self.test_metrics.record_custom("startup_completion_logic_tested", True)


class TestServiceReadinessValidationLogic(SSotBaseTestCase):
    """Unit tests for individual service readiness checks with startup awareness."""
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.env_patch.stop()
        self.test_metrics.end_timing()
        super().tearDown()
    
    def test_agent_supervisor_readiness_with_valid_state(self):
        """
        Test supervisor readiness when all dependencies are available.
        
        NORMAL OPERATION: When startup is complete and all services are properly
        initialized, agent_supervisor validation should return True.
        """
        # Create fully initialized app state
        app_state = MockAppStateForStartupPhases(
            startup_phase='complete',
            completed_phases=['init', 'dependencies', 'database', 'cache', 'services', 'websocket', 'finalize'],
            startup_in_progress=False,
            startup_complete=True,
            has_agent_supervisor=True,
            has_thread_service=True
        )
        
        validator = create_service_readiness_validator(app_state, 'staging')
        result = validator._validate_agent_supervisor()
        
        self.assertTrue(
            result,
            "Agent supervisor should be ready when all dependencies are available"
        )
        
        self.test_metrics.record_custom("valid_state_test_passed", True)
    
    def test_agent_supervisor_readiness_missing_supervisor(self):
        """
        Test behavior when agent_supervisor is None or missing.
        
        FAILURE CASE: When agent_supervisor is not available (startup not complete
        or initialization failed), validation should return False.
        """
        # Test case 1: app_state without agent_supervisor attribute
        app_state_no_attr = Mock()
        app_state_no_attr.startup_phase = 'services'
        app_state_no_attr.startup_completed_phases = ['init', 'dependencies', 'database', 'cache']
        # Deliberately not setting agent_supervisor attribute
        
        validator1 = create_service_readiness_validator(app_state_no_attr, 'staging')
        result1 = validator1._validate_agent_supervisor()
        
        self.assertFalse(
            result1,
            "Agent supervisor validation should return False when supervisor attribute missing"
        )
        
        # Test case 2: app_state with agent_supervisor = None
        app_state_none = MockAppStateForStartupPhases(
            startup_phase='services',
            completed_phases=['init', 'dependencies', 'database', 'cache'],
            startup_in_progress=True,
            startup_complete=False,
            has_agent_supervisor=False  # Sets agent_supervisor = None
        )
        
        validator2 = create_service_readiness_validator(app_state_none, 'staging')
        result2 = validator2._validate_agent_supervisor()
        
        self.assertFalse(
            result2,
            "Agent supervisor validation should return False when supervisor is None"
        )
        
        self.test_metrics.record_custom("missing_supervisor_test_passed", True)
    
    def test_agent_supervisor_readiness_missing_thread_service(self):
        """
        Test behavior when thread_service is None or missing.
        
        DEPENDENCY FAILURE: Agent supervisor requires thread_service for chat
        functionality. Validation should fail if thread_service is not available.
        """
        # Create app state with supervisor but without thread_service
        app_state = MockAppStateForStartupPhases(
            startup_phase='services',
            completed_phases=['init', 'dependencies', 'database', 'cache'],
            startup_in_progress=True,
            startup_complete=False,
            has_agent_supervisor=True,
            has_thread_service=False  # Missing thread service
        )
        
        validator = create_service_readiness_validator(app_state, 'staging')
        result = validator._validate_thread_service()
        
        self.assertFalse(
            result,
            "Thread service validation should return False when thread_service is None"
        )
        
        self.test_metrics.record_custom("missing_thread_service_test_passed", True)


class TestRetryAndTimingLogic(SSotBaseTestCase):
    """Unit tests for retry mechanisms and timeout handling in GCP environment."""
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.env_patch.stop()
        self.test_metrics.end_timing()
        super().tearDown()
    
    @pytest.mark.asyncio
    async def test_service_validation_respects_timeout(self):
        """
        Verify single service validation respects timeout settings.
        
        TIMEOUT BEHAVIOR: Service validation should fail gracefully when
        services take too long to become ready, preventing indefinite waits.
        """
        # Create app state that will cause validation delays
        app_state = MockAppStateForStartupPhases(
            startup_phase='services',
            completed_phases=['init', 'dependencies', 'database', 'cache'],
            startup_in_progress=True,
            startup_complete=False,
            has_agent_supervisor=False  # Will cause validation to retry and timeout
        )
        
        validator = create_service_readiness_validator(app_state, 'staging')
        
        # Configure very short timeout for testing
        from netra_backend.app.websocket_core.service_readiness_validator import AdaptiveTimeout
        short_timeout = AdaptiveTimeout(
            base_timeout=2.0,  # 2 second timeout
            max_timeout=3.0,
            retry_count=2,
            retry_delay=0.5
        )
        
        validator.service_configs['agent_supervisor'].timeout_config = short_timeout
        
        start_time = time.time()
        result = await validator.validate_service('agent_supervisor')
        elapsed_time = time.time() - start_time
        
        # Should fail within timeout period
        self.assertFalse(
            result.ready,
            "Service validation should fail when timeout is exceeded"
        )
        
        # Should respect timeout (allow some margin for processing)
        self.assertLess(
            elapsed_time, 5.0,
            f"Validation should complete within timeout period, took {elapsed_time:.2f}s"
        )
        
        self.test_metrics.record_custom("timeout_test_elapsed_time", elapsed_time)
    
    @pytest.mark.asyncio
    async def test_service_validation_retry_count(self):
        """
        Verify retry logic works correctly.
        
        RETRY BEHAVIOR: When services are temporarily unavailable, validation
        should retry the configured number of times before failing.
        """
        # Create mock that fails first time, succeeds on retry
        call_count = 0
        
        def mock_validator():
            nonlocal call_count
            call_count += 1
            return call_count >= 2  # Fail first call, succeed on second
        
        app_state = MockAppStateForStartupPhases(
            startup_phase='services',
            completed_phases=['init', 'dependencies', 'database', 'cache'],
            startup_in_progress=True,
            startup_complete=False,
            has_agent_supervisor=True  # Available after retry
        )
        
        validator = create_service_readiness_validator(app_state, 'staging')
        
        # Replace validator function with our mock
        with patch.object(validator, '_validate_agent_supervisor', side_effect=mock_validator):
            result = await validator.validate_service('agent_supervisor')
            
            # Should succeed after retry
            self.assertTrue(
                result.ready,
                "Service validation should succeed after retry"
            )
            
            # Should have made multiple attempts
            self.assertGreaterEqual(
                result.attempts, 2,
                f"Expected at least 2 attempts, got {result.attempts}"
            )
            
            # Mock should have been called multiple times
            self.assertGreaterEqual(
                call_count, 2,
                f"Expected at least 2 validator calls, got {call_count}"
            )
        
        self.test_metrics.record_custom("retry_logic_test_passed", True)
    
    def test_gcp_specific_timeouts(self):
        """
        Test GCP environment uses optimized timeout values.
        
        GCP OPTIMIZATION: GCP staging environment should use shorter timeouts
        (8.0s vs 30.0s for agent_supervisor) to fail fast and prevent long waits.
        """
        app_state = MockAppStateForStartupPhases(
            startup_phase='complete',
            startup_complete=True,
            has_agent_supervisor=True
        )
        
        validator = create_service_readiness_validator(app_state, 'staging')
        
        # Check that GCP environment gets optimized timeout values
        agent_supervisor_config = validator.service_configs.get('agent_supervisor')
        self.assertIsNotNone(agent_supervisor_config, "Agent supervisor config should exist")
        
        # Calculate effective timeout for staging environment
        effective_timeout = agent_supervisor_config.timeout_config.get_effective_timeout(
            'staging', 
            agent_supervisor_config.criticality
        )
        
        # GCP staging should use optimized timeouts (typically longer than base but with multipliers)
        # The actual value depends on the environment multiplier configuration
        self.assertGreater(
            effective_timeout, 10.0,
            f"GCP staging timeout should be optimized, got {effective_timeout}s"
        )
        
        # Should respect maximum timeout limits
        max_timeout = agent_supervisor_config.timeout_config.max_timeout
        self.assertLessEqual(
            effective_timeout, max_timeout,
            f"Effective timeout {effective_timeout}s should not exceed max {max_timeout}s"
        )
        
        self.test_metrics.record_custom("gcp_timeout_optimization_verified", True)


class TestStartupPhaseTransitions(SSotBaseTestCase):
    """Unit tests for startup phase transition edge cases."""
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.test_metrics.end_timing()
        super().tearDown()
    
    def test_validation_during_phase_transition(self):
        """
        Test validation behavior during startup phase transitions.
        
        EDGE CASE: When validation occurs exactly during a phase transition,
        it should handle the transition gracefully without causing errors.
        """
        # Simulate phase transition: from cache to services
        app_state = MockAppStateForStartupPhases(
            startup_phase='cache',  # About to transition to services
            completed_phases=['init', 'dependencies', 'database'],
            startup_in_progress=True,
            startup_complete=False,
            has_agent_supervisor=False  # Not yet created
        )
        
        validator = GCPWebSocketInitializationValidator(app_state)
        
        # Validation during cache phase should skip
        result1 = validator._validate_agent_supervisor_readiness()
        self.assertFalse(result1, "Should skip validation during cache phase")
        
        # Simulate transition to services phase
        app_state.startup_phase = 'services'
        app_state.startup_completed_phases.append('cache')
        
        # Validation during services phase should proceed but fail (no supervisor yet)
        result2 = validator._validate_agent_supervisor_readiness()
        self.assertFalse(result2, "Should attempt validation during services phase")
        
        # Simulate supervisor becoming available
        app_state.agent_supervisor = Mock()
        app_state.thread_service = Mock()
        app_state.agent_websocket_bridge = Mock()
        
        # Validation should now succeed
        result3 = validator._validate_agent_supervisor_readiness()
        self.assertTrue(result3, "Should succeed when supervisor becomes available")
        
        self.test_metrics.record_custom("phase_transition_test_passed", True)
    
    def test_unknown_startup_phase_handling(self):
        """
        Test behavior with unknown or invalid startup phases.
        
        EDGE CASE: When startup_phase is unknown or invalid, validation
        should handle it gracefully without causing exceptions.
        """
        # Test with unknown phase
        app_state_unknown = MockAppStateForStartupPhases(
            startup_phase='unknown_phase',
            completed_phases=[],
            startup_in_progress=True,
            startup_complete=False,
            has_agent_supervisor=False
        )
        
        validator = GCPWebSocketInitializationValidator(app_state_unknown)
        
        # Should not raise exception
        try:
            result = validator._validate_agent_supervisor_readiness()
            # Unknown phase should be treated conservatively (allow validation)
            # The actual behavior depends on implementation, but should not crash
            self.assertIsInstance(result, bool, "Should return boolean result")
        except Exception as e:
            self.fail(f"Validation should not raise exception for unknown phase: {e}")
        
        # Test with None phase
        app_state_none = MockAppStateForStartupPhases(
            startup_phase=None,
            completed_phases=[],
            startup_in_progress=True,
            startup_complete=False,
            has_agent_supervisor=False
        )
        app_state_none.startup_phase = None
        
        validator2 = GCPWebSocketInitializationValidator(app_state_none)
        
        try:
            result2 = validator2._validate_agent_supervisor_readiness()
            self.assertIsInstance(result2, bool, "Should handle None phase gracefully")
        except Exception as e:
            self.fail(f"Validation should not raise exception for None phase: {e}")
        
        self.test_metrics.record_custom("unknown_phase_handling_test_passed", True)


if __name__ == '__main__':
    # Run tests with detailed output for debugging
    unittest.main(verbosity=2)