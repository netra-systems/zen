"""
UNIT TESTS: GCP Startup Phase Validation - WebSocket Supervisor Race Condition Prevention (FIXED)

MISSION CRITICAL: These tests validate the startup phase awareness logic that prevents
WebSocket 1011 errors in GCP Cloud Run by ensuring agent_supervisor validation only
occurs after Phase 5 (SERVICES) completion.

ROOT CAUSE ADDRESSED: GCP Cloud Run WebSocket connections failing with 1011 errors 
due to agent_supervisor not being available during readiness validation. This happens
because validation runs before the deterministic startup sequence reaches Phase 5.

FIXES APPLIED:
- Replaced self.subTest() with loop-based testing (SSOT BaseTestCase compatibility)
- Changed setUp/tearDown to setup_method/teardown_method (SSOT pattern)
- Replaced self.assert* with standard assert statements
- Maintained all business value and race condition detection logic

Business Value:
- Segment: Platform/Internal - Chat Infrastructure Stability
- Business Goal: Platform Stability & Chat Value Delivery (90% of platform value)
- Value Impact: Eliminates WebSocket race conditions preventing reliable AI chat
- Strategic Impact: $500K+ ARR protection through reliable chat functionality
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


class TestStartupPhaseValidationLogicFixed(SSotBaseTestCase):
    """Unit tests for startup phase awareness in GCP WebSocket validator (FIXED VERSION)."""
    
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

    def test_race_condition_detection_comprehensive(self):
        """
        CRITICAL: Comprehensive test that will FAIL before fix, PASS after fix.
        
        This test specifically validates the startup race condition is detected
        and prevented by the phase-aware validation logic.
        """
        # Race condition prevention scenario: Early startup phases should pass
        early_phases = ['init', 'dependencies', 'database', 'cache']
        race_condition_detected = False
        early_phases_pass = True  # Track if early phases pass validation
        
        for phase in early_phases:
            app_state = MockAppStateForStartupPhases(
                startup_phase=phase,
                startup_in_progress=True,
                startup_complete=False,
                has_agent_supervisor=False  # This would cause race condition without fix
            )
            
            validator = create_gcp_websocket_validator(app_state)
            
            # Configure as GCP environment to enable validation
            validator.update_environment_configuration('staging', True)
            
            # This should PREVENT the race condition by skipping agent_supervisor validation
            try:
                readiness_result = validator.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)
                if hasattr(readiness_result, '__await__'):
                    # If it's async, we need to handle it properly
                    import asyncio
                    readiness_result = asyncio.run(readiness_result)
                
                # With the fix, early phases should pass even without agent_supervisor
                if not readiness_result.ready:
                    # Check if agent_supervisor is specifically mentioned as a failure
                    if 'agent_supervisor' in readiness_result.failed_services:
                        race_condition_detected = True
                        early_phases_pass = False
                        break
                    # Other failures are acceptable during early phases
                else:
                    # Validation passed - this is what we expect with the fix
                    continue
            except Exception as e:
                # Exceptions related to agent_supervisor during early phases indicate race condition
                if 'agent_supervisor' in str(e):
                    race_condition_detected = True
                    early_phases_pass = False
                    break
        
        # CRITICAL: Race condition must be PREVENTED (validation should pass during early phases)
        # The fix skips agent_supervisor validation during early phases, so it should NOT be detected
        assert not race_condition_detected, (
            "Race condition should be PREVENTED: agent_supervisor validation should be skipped during early startup phases, "
            "making validation pass even when supervisor is unavailable"
        )
        
        # Verify fix: Post-Phase 5 should work
        post_phase5_app_state = MockAppStateForStartupPhases(
            startup_phase='websocket',
            completed_phases=['init', 'dependencies', 'database', 'cache', 'services'],
            startup_in_progress=True,
            startup_complete=False,
            has_agent_supervisor=True,  # Available after Phase 5
            has_thread_service=True
        )
        
        validator_post_fix = create_gcp_websocket_validator(post_phase5_app_state)
        
        # Configure as GCP environment to enable validation
        validator_post_fix.update_environment_configuration('staging', True)
        
        try:
            readiness_result_post = validator_post_fix.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)
            if hasattr(readiness_result_post, '__await__'):
                readiness_result_post = asyncio.run(readiness_result_post)
            
            # Should be ready after Phase 5 completion
            assert readiness_result_post.ready, (
                f"WebSocket should be ready after Phase 5 completion. "
                f"Failed services: {readiness_result_post.failed_services}"
            )
        except Exception as e:
            # Post-Phase 5 should not raise exceptions
            assert False, f"Post-Phase 5 validation should succeed, got: {e}"
        
        self.test_metrics.record_custom("race_condition_comprehensive_test_passed", True)


# Fast test runner for validation
if __name__ == '__main__':
    # Run just the critical tests for quick validation
    import unittest
    
    # Create test suite with just the critical test
    suite = unittest.TestSuite()
    suite.addTest(TestStartupPhaseValidationLogicFixed('test_race_condition_detection_comprehensive'))
    
    # Run the test
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with error code if tests failed
    import sys
    sys.exit(0 if result.wasSuccessful() else 1)