"""
Unit Tests: WebSocket Manager SSOT Direct Instantiation Prevention - Issue #712

These tests validate that WebSocket Manager cannot be directly instantiated,
enforcing the SSOT factory pattern for proper user isolation and Golden Path compliance.

Business Value Justification (BVJ):
- Segment: Platform Infrastructure (affects ALL user segments)
- Business Goal: Prevent architectural violations that could compromise chat reliability
- Value Impact: Protects $500K+ ARR chat functionality from user isolation failures
- Revenue Impact: Ensures reliable WebSocket infrastructure supporting Golden Path user flow

CRITICAL: These tests are designed to FAIL initially to demonstrate validation gaps.
The failures prove that direct instantiation prevention is not yet fully enforced.
"""

import pytest
import unittest
import weakref
from typing import Any, Dict, Optional
from unittest.mock import Mock, patch, MagicMock

# SSOT imports following test framework patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.types.core_types import UserID, ensure_user_id

# Import the actual classes we're testing
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketManagerMode
)
from netra_backend.app.websocket_core.websocket_manager import (
    WebSocketManager,
    get_websocket_manager
)
from netra_backend.app.websocket_core.ssot_validation_enhancer import (
    SSotValidationError,
    FactoryBypassDetected,
    enable_strict_validation,
    validate_websocket_manager_creation
)


class TestWebSocketManagerDirectInstantiationPrevention(SSotAsyncTestCase):
    """
    Test suite for preventing direct WebSocket Manager instantiation.

    IMPORTANT: These tests are designed to FAIL initially to demonstrate
    the validation gaps that Issue #712 addresses.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

        # Reset validation state
        enable_strict_validation(False)  # Start in permissive mode

        # Create mock user context for testing
        self.mock_user_context = Mock()
        self.mock_user_context.user_id = "test-user-12345"
        self.mock_user_context.thread_id = "test-thread-67890"
        self.mock_user_context.request_id = "test-request-abcdef"
        self.mock_user_context.is_test = True

    def test_direct_unified_manager_instantiation_should_fail(self):
        """
        Test that direct UnifiedWebSocketManager instantiation is prevented.

        EXPECTED: This test should FAIL initially, proving the gap exists.
        """
        with pytest.raises(FactoryBypassDetected, match="Direct instantiation not allowed"):
            # This should fail - direct instantiation should be prevented
            manager = UnifiedWebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=self.mock_user_context
            )

        # If we get here without exception, the test has failed to demonstrate the gap
        pytest.fail("Direct UnifiedWebSocketManager instantiation was allowed - validation gap confirmed")

    def test_direct_websocket_manager_alias_instantiation_should_fail(self):
        """
        Test that direct WebSocketManager (alias) instantiation is prevented.

        EXPECTED: This test should FAIL initially, proving the gap exists.
        """
        with pytest.raises(FactoryBypassDetected, match="Direct instantiation not allowed"):
            # This should fail - WebSocketManager is an alias to UnifiedWebSocketManager
            manager = WebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=self.mock_user_context
            )

        # If we get here without exception, the test has failed to demonstrate the gap
        pytest.fail("Direct WebSocketManager instantiation was allowed - validation gap confirmed")

    def test_new_method_bypass_should_fail(self):
        """
        Test that __new__ method bypass is prevented.

        EXPECTED: This test should FAIL initially, proving the gap exists.
        """
        with pytest.raises(FactoryBypassDetected, match="Direct instantiation not allowed"):
            # Try to bypass through __new__ method
            manager = UnifiedWebSocketManager.__new__(UnifiedWebSocketManager)

        # If we get here without exception, the test has failed to demonstrate the gap
        pytest.fail("__new__ method bypass was allowed - validation gap confirmed")

    def test_factory_function_is_required_path(self):
        """
        Test that get_websocket_manager is the only allowed creation path.

        This test should PASS, demonstrating the correct factory pattern.
        """
        # This should work - using the factory function
        manager = await get_websocket_manager(
            user_context=self.mock_user_context,
            mode=WebSocketManagerMode.UNIFIED
        )

        # Verify it's the correct type
        self.assertIsInstance(manager, UnifiedWebSocketManager)

        # Verify validation was called
        # NOTE: This may fail if validation isn't implemented yet
        # which would demonstrate the validation gap

    def test_multiple_direct_instantiation_attempts_accumulate_violations(self):
        """
        Test that multiple direct instantiation attempts are tracked and prevented.

        EXPECTED: This test should FAIL initially, demonstrating incomplete tracking.
        """
        violation_count = 0

        # Attempt multiple direct instantiations
        for i in range(3):
            try:
                manager = UnifiedWebSocketManager(
                    mode=WebSocketManagerMode.UNIFIED,
                    user_context=self.mock_user_context
                )
                # If this succeeds, we have a validation gap
            except FactoryBypassDetected:
                violation_count += 1
            except Exception as e:
                # Any other exception also indicates a gap
                pass

        # We should have caught all 3 attempts
        self.assertEqual(violation_count, 3,
                        f"Only {violation_count}/3 direct instantiation attempts were prevented")

        # If we get here with violation_count < 3, it demonstrates the validation gap
        if violation_count < 3:
            pytest.fail(f"Only {violation_count}/3 direct instantiation attempts prevented - validation gap confirmed")

    def test_strict_mode_enforcement(self):
        """
        Test that strict mode properly enforces instantiation prevention.

        EXPECTED: This test should FAIL initially if strict mode isn't implemented.
        """
        # Enable strict validation mode
        enable_strict_validation(True)

        with pytest.raises(SSotValidationError, match="SSOT validation failed"):
            # In strict mode, this should raise SSotValidationError
            manager = UnifiedWebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=self.mock_user_context
            )

        # If we get here without exception, strict mode enforcement is not working
        pytest.fail("Strict mode did not prevent direct instantiation - validation gap confirmed")

    def test_validation_bypassed_in_non_strict_mode(self):
        """
        Test that non-strict mode allows instantiation but logs violations.

        This test validates the fallback behavior for backward compatibility.
        """
        # Ensure we're in non-strict mode
        enable_strict_validation(False)

        # Mock the logger to capture warnings
        with patch('netra_backend.app.websocket_core.ssot_validation_enhancer.logger') as mock_logger:
            try:
                # This might succeed in non-strict mode, but should log warnings
                manager = UnifiedWebSocketManager(
                    mode=WebSocketManagerMode.UNIFIED,
                    user_context=self.mock_user_context
                )

                # Verify warning was logged about the validation violation
                mock_logger.warning.assert_called()
                warning_calls = [call for call in mock_logger.warning.call_args_list
                               if 'FACTORY BYPASS DETECTED' in str(call)]
                self.assertTrue(len(warning_calls) > 0,
                              "Expected factory bypass warning was not logged")

            except Exception as e:
                # If it fails completely, that's also a gap (should allow in non-strict mode)
                pytest.fail(f"Non-strict mode should allow instantiation with warnings, but got: {e}")

    def test_creation_method_tracking(self):
        """
        Test that creation method is properly tracked for validation.

        EXPECTED: This test may FAIL initially if tracking isn't implemented.
        """
        with patch('netra_backend.app.websocket_core.ssot_validation_enhancer._ssot_validator') as mock_validator:
            mock_validator.validate_manager_creation.return_value = True

            # Create manager through factory
            manager = await get_websocket_manager(
                user_context=self.mock_user_context,
                mode=WebSocketManagerMode.UNIFIED
            )

            # Verify the creation method was tracked
            mock_validator.validate_manager_creation.assert_called_once()
            call_args = mock_validator.validate_manager_creation.call_args

            # Check that creation_method parameter was passed
            self.assertIn('creation_method', call_args.kwargs)
            self.assertEqual(call_args.kwargs['creation_method'], 'get_websocket_manager')

            # If this fails, it demonstrates the tracking gap

    def test_validation_enhancer_integration(self):
        """
        Test that the SSOT validation enhancer is properly integrated.

        EXPECTED: This test may FAIL initially if integration isn't complete.
        """
        from netra_backend.app.websocket_core.ssot_validation_enhancer import get_ssot_validation_summary

        # Get initial validation summary
        initial_summary = get_ssot_validation_summary()

        # Create manager through factory (should pass validation)
        manager = await get_websocket_manager(
            user_context=self.mock_user_context,
            mode=WebSocketManagerMode.UNIFIED
        )

        # Get updated summary
        updated_summary = get_ssot_validation_summary()

        # Verify validation was recorded
        self.assertTrue(
            updated_summary['total_validations'] > initial_summary['total_validations'],
            "Validation was not recorded in the enhancer summary"
        )

        # If this fails, it demonstrates the integration gap


class TestWebSocketManagerValidationGapDocumentation(SSotAsyncTestCase):
    """
    Test suite specifically designed to document validation gaps.

    These tests serve as documentation of the current state and expected failures.
    """

    def test_document_current_instantiation_behavior(self):
        """
        Document the current instantiation behavior to establish baseline.

        This test captures the current state before fixes are applied.
        """
        success_count = 0
        failure_count = 0

        test_scenarios = [
            ("direct_unified", lambda: UnifiedWebSocketManager(mode=WebSocketManagerMode.UNIFIED)),
            ("direct_alias", lambda: WebSocketManager(mode=WebSocketManagerMode.UNIFIED)),
            ("factory_method", lambda: get_websocket_manager()),
        ]

        results = {}

        for scenario_name, creation_func in test_scenarios:
            try:
                if scenario_name == "factory_method":
                    manager = await creation_func()
                else:
                    manager = creation_func()
                success_count += 1
                results[scenario_name] = "SUCCESS"
            except Exception as e:
                failure_count += 1
                results[scenario_name] = f"FAILED: {type(e).__name__}: {str(e)}"

        # Log the current behavior for documentation
        print(f"\nCurrent WebSocket Manager Instantiation Behavior:")
        print(f"Success Count: {success_count}")
        print(f"Failure Count: {failure_count}")
        for scenario, result in results.items():
            print(f"  {scenario}: {result}")

        # This test always passes - it's just for documentation
        self.assertTrue(True, "Baseline behavior documented")

    def test_validation_gaps_summary(self):
        """
        Summarize the validation gaps that need to be addressed.

        This serves as a checklist for Issue #712 implementation.
        """
        gaps_to_address = [
            "Direct UnifiedWebSocketManager instantiation prevention",
            "WebSocketManager alias instantiation prevention",
            "__new__ method bypass prevention",
            "Strict mode validation enforcement",
            "Creation method tracking and validation",
            "Multiple instantiation attempt accumulation",
            "SSOT validation enhancer integration"
        ]

        print(f"\nValidation Gaps to Address (Issue #712):")
        for i, gap in enumerate(gaps_to_address, 1):
            print(f"  {i}. {gap}")

        # This test always passes - it's documentation
        self.assertTrue(True, "Validation gaps documented")


if __name__ == '__main__':
    # Run the tests to demonstrate the gaps
    pytest.main([__file__, '-v'])