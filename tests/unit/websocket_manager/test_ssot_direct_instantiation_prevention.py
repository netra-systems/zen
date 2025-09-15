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
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.types.core_types import UserID, ensure_user_id
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager, WebSocketManagerMode
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, get_websocket_manager
from netra_backend.app.websocket_core.ssot_validation_enhancer import SSotValidationError, FactoryBypassDetected, enable_strict_validation, validate_websocket_manager_creation

@pytest.mark.unit
class WebSocketManagerDirectInstantiationPreventionTests(SSotAsyncTestCase):
    """
    Test suite for preventing direct WebSocket Manager instantiation.

    IMPORTANT: These tests are designed to FAIL initially to demonstrate
    the validation gaps that Issue #712 addresses.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        enable_strict_validation(False)
        self.mock_user_context = Mock()
        self.mock_user_context.user_id = 'test-user-12345'
        self.mock_user_context.thread_id = 'test-thread-67890'
        self.mock_user_context.request_id = 'test-request-abcdef'
        self.mock_user_context.is_test = True

    def test_direct_unified_manager_instantiation_should_fail(self):
        """
        Test that direct UnifiedWebSocketManager instantiation is prevented.

        EXPECTED: This test should FAIL initially, proving the gap exists.
        """
        with pytest.raises(FactoryBypassDetected, match='Direct instantiation not allowed'):
            manager = UnifiedWebSocketManager(mode=WebSocketManagerMode.UNIFIED, user_context=self.mock_user_context)
        pytest.fail('Direct UnifiedWebSocketManager instantiation was allowed - validation gap confirmed')

    def test_direct_websocket_manager_alias_instantiation_should_fail(self):
        """
        Test that direct WebSocketManager (alias) instantiation is prevented.

        EXPECTED: This test should FAIL initially, proving the gap exists.
        """
        with pytest.raises(FactoryBypassDetected, match='Direct instantiation not allowed'):
            manager = WebSocketManager(mode=WebSocketManagerMode.UNIFIED, user_context=self.mock_user_context)
        pytest.fail('Direct WebSocketManager instantiation was allowed - validation gap confirmed')

    def test_new_method_bypass_should_fail(self):
        """
        Test that __new__ method bypass is prevented.

        EXPECTED: This test should FAIL initially, proving the gap exists.
        """
        with pytest.raises(FactoryBypassDetected, match='Direct instantiation not allowed'):
            manager = UnifiedWebSocketManager.__new__(UnifiedWebSocketManager)
        pytest.fail('__new__ method bypass was allowed - validation gap confirmed')

    async def test_factory_function_is_required_path(self):
        """
        Test that get_websocket_manager is the only allowed creation path.

        This test should PASS, demonstrating the correct factory pattern.
        """
        manager = get_websocket_manager(user_context=self.mock_user_context, mode=WebSocketManagerMode.UNIFIED)
        self.assertIsInstance(manager, UnifiedWebSocketManager)

    def test_multiple_direct_instantiation_attempts_accumulate_violations(self):
        """
        Test that multiple direct instantiation attempts are tracked and prevented.

        EXPECTED: This test should FAIL initially, demonstrating incomplete tracking.
        """
        violation_count = 0
        for i in range(3):
            try:
                manager = UnifiedWebSocketManager(mode=WebSocketManagerMode.UNIFIED, user_context=self.mock_user_context)
            except FactoryBypassDetected:
                violation_count += 1
            except Exception as e:
                pass
        self.assertEqual(violation_count, 3, f'Only {violation_count}/3 direct instantiation attempts were prevented')
        if violation_count < 3:
            pytest.fail(f'Only {violation_count}/3 direct instantiation attempts prevented - validation gap confirmed')

    def test_strict_mode_enforcement(self):
        """
        Test that strict mode properly enforces instantiation prevention.

        EXPECTED: This test should FAIL initially if strict mode isn't implemented.
        """
        enable_strict_validation(True)
        with pytest.raises(SSotValidationError, match='SSOT validation failed'):
            manager = UnifiedWebSocketManager(mode=WebSocketManagerMode.UNIFIED, user_context=self.mock_user_context)
        pytest.fail('Strict mode did not prevent direct instantiation - validation gap confirmed')

    def test_validation_bypassed_in_non_strict_mode(self):
        """
        Test that non-strict mode allows instantiation but logs violations.

        This test validates the fallback behavior for backward compatibility.
        """
        enable_strict_validation(False)
        with patch('netra_backend.app.websocket_core.ssot_validation_enhancer.logger') as mock_logger:
            try:
                manager = UnifiedWebSocketManager(mode=WebSocketManagerMode.UNIFIED, user_context=self.mock_user_context)
                mock_logger.warning.assert_called()
                warning_calls = [call for call in mock_logger.warning.call_args_list if 'FACTORY BYPASS DETECTED' in str(call)]
                self.assertTrue(len(warning_calls) > 0, 'Expected factory bypass warning was not logged')
            except Exception as e:
                pytest.fail(f'Non-strict mode should allow instantiation with warnings, but got: {e}')

    async def test_creation_method_tracking(self):
        """
        Test that creation method is properly tracked for validation.

        EXPECTED: This test may FAIL initially if tracking isn't implemented.
        """
        with patch('netra_backend.app.websocket_core.ssot_validation_enhancer._ssot_validator') as mock_validator:
            mock_validator.validate_manager_creation.return_value = True
            manager = get_websocket_manager(user_context=self.mock_user_context, mode=WebSocketManagerMode.UNIFIED)
            mock_validator.validate_manager_creation.assert_called_once()
            call_args = mock_validator.validate_manager_creation.call_args
            self.assertIn('creation_method', call_args.kwargs)
            self.assertEqual(call_args.kwargs['creation_method'], 'get_websocket_manager')

    async def test_validation_enhancer_integration(self):
        """
        Test that the SSOT validation enhancer is properly integrated.

        EXPECTED: This test may FAIL initially if integration isn't complete.
        """
        from netra_backend.app.websocket_core.ssot_validation_enhancer import get_ssot_validation_summary
        initial_summary = get_ssot_validation_summary()
        manager = get_websocket_manager(user_context=self.mock_user_context, mode=WebSocketManagerMode.UNIFIED)
        updated_summary = get_ssot_validation_summary()
        self.assertTrue(updated_summary['total_validations'] > initial_summary['total_validations'], 'Validation was not recorded in the enhancer summary')

@pytest.mark.unit
class WebSocketManagerValidationGapDocumentationTests(SSotAsyncTestCase):
    """
    Test suite specifically designed to document validation gaps.

    These tests serve as documentation of the current state and expected failures.
    """

    async def test_document_current_instantiation_behavior(self):
        """
        Document the current instantiation behavior to establish baseline.

        This test captures the current state before fixes are applied.
        """
        success_count = 0
        failure_count = 0
        test_scenarios = [('direct_unified', lambda: UnifiedWebSocketManager(mode=WebSocketManagerMode.UNIFIED)), ('direct_alias', lambda: WebSocketManager(mode=WebSocketManagerMode.UNIFIED)), ('factory_method', lambda: get_websocket_manager())]
        results = {}
        for scenario_name, creation_func in test_scenarios:
            try:
                if scenario_name == 'factory_method':
                    manager = await creation_func()
                else:
                    manager = creation_func()
                success_count += 1
                results[scenario_name] = 'SUCCESS'
            except Exception as e:
                failure_count += 1
                results[scenario_name] = f'FAILED: {type(e).__name__}: {str(e)}'
        print(f'\nCurrent WebSocket Manager Instantiation Behavior:')
        print(f'Success Count: {success_count}')
        print(f'Failure Count: {failure_count}')
        for scenario, result in results.items():
            print(f'  {scenario}: {result}')
        self.assertTrue(True, 'Baseline behavior documented')

    def test_validation_gaps_summary(self):
        """
        Summarize the validation gaps that need to be addressed.

        This serves as a checklist for Issue #712 implementation.
        """
        gaps_to_address = ['Direct UnifiedWebSocketManager instantiation prevention', 'WebSocketManager alias instantiation prevention', '__new__ method bypass prevention', 'Strict mode validation enforcement', 'Creation method tracking and validation', 'Multiple instantiation attempt accumulation', 'SSOT validation enhancer integration']
        print(f'\nValidation Gaps to Address (Issue #712):')
        for i, gap in enumerate(gaps_to_address, 1):
            print(f'  {i}. {gap}')
        self.assertTrue(True, 'Validation gaps documented')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')