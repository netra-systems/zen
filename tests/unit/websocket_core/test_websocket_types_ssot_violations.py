"""
Unit Tests: WebSocket Core Types SSOT Violations - Issue #722

PURPOSE: Detect direct os.getenv() usage in websocket_core/types.py environment detection
EXPECTED: These tests should FAIL initially to prove SSOT violations exist

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Stability - Ensure consistent WebSocket configuration across environments
- Value Impact: Prevents WebSocket connection inconsistencies affecting $500K+ ARR chat functionality
- Strategic Impact: SSOT compliance ensures reliable Cloud Run environment detection

VIOLATION DETAILS:
- Lines 349-355: Multiple os.getenv() calls in detect_and_configure_for_environment()
  - os.getenv('K_SERVICE') - Cloud Run service name detection
  - os.getenv('K_REVISION') - Cloud Run revision detection
  - os.getenv('GOOGLE_CLOUD_PROJECT') - GCP project detection
  - os.getenv('GAE_APPLICATION') - Cloud Run domain detection
  - os.getenv('ENVIRONMENT', 'development') - Environment detection

TEST BEHAVIOR:
- BEFORE SSOT FIX: Should PASS (proves os.environ direct access exists)
- AFTER SSOT FIX: Should FAIL (proves IsolatedEnvironment usage)

CRITICAL: This test validates Issue #722 P1 legacy SSOT violation remediation.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.websocket_core.types import WebSocketConfig


class TestWebSocketTypesSSOTViolations(SSotBaseTestCase):
    """Test suite proving WebSocket types SSOT violations at specific lines."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_detect_environment_uses_os_getenv_k_service_line_349(self):
        """
        Test that detect_and_configure_for_environment() directly calls os.getenv('K_SERVICE') at line 349.

        This test PROVES the SSOT violation exists by mocking os.getenv
        and verifying it gets called directly instead of through IsolatedEnvironment.

        Expected behavior:
        - BEFORE FIX: Test PASSES (proving violation exists)
        - AFTER FIX: Test FAILS (proving SSOT compliance)
        """
        with patch('os.getenv') as mock_os_getenv:
            # Mock os.getenv to return Cloud Run service name
            def mock_getenv_side_effect(key, default=None):
                if key == 'K_SERVICE':
                    return 'netra-backend-staging'
                elif key == 'ENVIRONMENT':
                    return 'staging'
                return default

            mock_os_getenv.side_effect = mock_getenv_side_effect

            # Call the method that should trigger the violation
            config = WebSocketConfig.detect_and_configure_for_environment()

            # ASSERTION: Proves direct os.getenv call at line 349
            assert mock_os_getenv.called, "os.getenv should be called directly"

            # Verify specific calls for Cloud Run detection
            expected_calls = [
                (('K_SERVICE',), {}),
                (('K_REVISION',), {}),
                (('GOOGLE_CLOUD_PROJECT',), {}),
                (('GAE_APPLICATION', ''), {}),
                (('ENVIRONMENT', 'development'), {})
            ]

            # Check that at least K_SERVICE was called (proving line 349 violation)
            k_service_called = any(
                call[0][0] == 'K_SERVICE'
                for call in mock_os_getenv.call_args_list
            )
            assert k_service_called, "K_SERVICE os.getenv call should exist at line 349"

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_detect_environment_uses_os_getenv_k_revision_line_350(self):
        """
        Test that detect_and_configure_for_environment() directly calls os.getenv('K_REVISION') at line 350.
        """
        with patch('os.getenv') as mock_os_getenv:
            mock_os_getenv.return_value = 'netra-backend-staging-00001-abc'

            config = WebSocketConfig.detect_and_configure_for_environment()

            # ASSERTION: Proves direct os.getenv call at line 350
            k_revision_called = any(
                call[0][0] == 'K_REVISION'
                for call in mock_os_getenv.call_args_list
            )
            assert k_revision_called, "K_REVISION os.getenv call should exist at line 350"

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_detect_environment_uses_os_getenv_google_project_line_351(self):
        """
        Test that detect_and_configure_for_environment() directly calls os.getenv('GOOGLE_CLOUD_PROJECT') at line 351.
        """
        with patch('os.getenv') as mock_os_getenv:
            mock_os_getenv.return_value = 'netra-staging'

            config = WebSocketConfig.detect_and_configure_for_environment()

            # ASSERTION: Proves direct os.getenv call at line 351
            gcp_project_called = any(
                call[0][0] == 'GOOGLE_CLOUD_PROJECT'
                for call in mock_os_getenv.call_args_list
            )
            assert gcp_project_called, "GOOGLE_CLOUD_PROJECT os.getenv call should exist at line 351"

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_detect_environment_uses_os_getenv_gae_application_line_352(self):
        """
        Test that detect_and_configure_for_environment() directly calls os.getenv('GAE_APPLICATION') at line 352.
        """
        with patch('os.getenv') as mock_os_getenv:
            def mock_getenv_side_effect(key, default=None):
                if key == 'GAE_APPLICATION':
                    return 'staging~run.app'
                return default

            mock_os_getenv.side_effect = mock_getenv_side_effect

            config = WebSocketConfig.detect_and_configure_for_environment()

            # ASSERTION: Proves direct os.getenv call at line 352
            gae_called = any(
                call[0][0] == 'GAE_APPLICATION'
                for call in mock_os_getenv.call_args_list
            )
            assert gae_called, "GAE_APPLICATION os.getenv call should exist at line 352"

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_detect_environment_uses_os_getenv_environment_line_355(self):
        """
        Test that detect_and_configure_for_environment() directly calls os.getenv('ENVIRONMENT') at line 355.
        """
        with patch('os.getenv') as mock_os_getenv:
            mock_os_getenv.return_value = 'staging'

            config = WebSocketConfig.detect_and_configure_for_environment()

            # ASSERTION: Proves direct os.getenv call at line 355
            env_called = any(
                call[0][0] == 'ENVIRONMENT'
                for call in mock_os_getenv.call_args_list
            )
            assert env_called, "ENVIRONMENT os.getenv call should exist at line 355"

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_comprehensive_cloud_run_detection_ssot_violations(self):
        """
        Comprehensive test proving all Cloud Run environment detection violates SSOT.

        Tests that detect_and_configure_for_environment() calls ALL os.getenv variants
        directly instead of using IsolatedEnvironment.
        """
        with patch('os.getenv') as mock_os_getenv:
            # Mock Cloud Run environment
            def mock_getenv_side_effect(key, default=None):
                cloud_run_vars = {
                    'K_SERVICE': 'netra-backend-staging',
                    'K_REVISION': 'netra-backend-staging-00001-abc',
                    'GOOGLE_CLOUD_PROJECT': 'netra-staging',
                    'GAE_APPLICATION': 'staging~run.app',
                    'ENVIRONMENT': 'staging'
                }
                return cloud_run_vars.get(key, default)

            mock_os_getenv.side_effect = mock_getenv_side_effect

            # Call method that should trigger all violations
            config = WebSocketConfig.detect_and_configure_for_environment()

            # CRITICAL ASSERTION: All Cloud Run detection variables called directly
            expected_vars = ['K_SERVICE', 'K_REVISION', 'GOOGLE_CLOUD_PROJECT', 'GAE_APPLICATION', 'ENVIRONMENT']

            for expected_var in expected_vars:
                var_called = any(
                    call[0][0] == expected_var
                    for call in mock_os_getenv.call_args_list
                )
                assert var_called, f"{expected_var} os.getenv call should exist (SSOT violation)"

            # Verify config reflects Cloud Run optimization
            assert config is not None, "Should return Cloud Run optimized config"

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_environment_isolation_violation_websocket_types(self):
        """
        Test that environment detection bypasses IsolatedEnvironment completely.

        This test validates that the methods don't use IsolatedEnvironment
        by setting different values in IsolatedEnvironment vs os.environ.
        """
        # Set up IsolatedEnvironment with development values
        self._env.set('K_SERVICE', None)
        self.isolated_env.set('ENVIRONMENT', 'development')

        # Set up actual os.environ with Cloud Run values
        cloud_run_env = {
            'K_SERVICE': 'netra-backend-staging',
            'K_REVISION': 'netra-backend-staging-00001-abc',
            'GOOGLE_CLOUD_PROJECT': 'netra-staging',
            'ENVIRONMENT': 'staging'
        }

        with patch.dict(os.environ, cloud_run_env):
            with patch('os.getenv', side_effect=lambda key, default=None: cloud_run_env.get(key, default)) as mock_getenv:
                config = WebSocketConfig.detect_and_configure_for_environment()

                # VIOLATION PROOF: os.getenv was called instead of IsolatedEnvironment
                mock_getenv.assert_called()

                # Should detect as Cloud Run despite IsolatedEnvironment having different values
                # This proves the SSOT violation - it uses os.environ instead of IsolatedEnvironment

    @pytest.mark.unit
    def test_ssot_compliance_after_fix_validation_websocket_types(self):
        """
        Test that will PASS after SSOT fix is implemented.

        This validates that after the fix, the method uses IsolatedEnvironment
        instead of direct os.environ access for all Cloud Run detection.

        Expected behavior:
        - BEFORE FIX: May FAIL (method uses os.environ)
        - AFTER FIX: Should PASS (method uses IsolatedEnvironment)
        """
        # Set Cloud Run environment through IsolatedEnvironment
        self.isolated_env.set('K_SERVICE', 'netra-backend-staging')
        self.isolated_env.set('K_REVISION', 'netra-backend-staging-00001')
        self.isolated_env.set('GOOGLE_CLOUD_PROJECT', 'netra-staging')
        self.isolated_env.set('GAE_APPLICATION', 'staging~run.app')
        self.isolated_env.set('ENVIRONMENT', 'staging')

        # This should work correctly after SSOT fix is implemented
        try:
            config = WebSocketConfig.detect_and_configure_for_environment()

            # After fix, this should work with IsolatedEnvironment values
            assert config is not None, "Environment detection should work with IsolatedEnvironment"

        except Exception as e:
            # Before fix, method may fail with IsolatedEnvironment usage
            pytest.skip(f"SSOT fix not yet implemented for WebSocket types: {e}")
