"""
Test suite for reproducing Issue #406: defensive_auth request ID validation failures.

This test suite reproduces the specific validation failures observed in production logs
where defensive_auth request IDs are being rejected by is_valid_id_format validation.

Business Impact:
- Golden Path authentication failures for defensive_auth patterns
- User authentication blocking legitimate request IDs
- $500K+ ARR at risk due to auth validation overreach

Test Strategy:
1. Test exact failing patterns from production logs
2. Test UserExecutionContext validation with defensive_auth patterns  
3. Test broader defensive_auth pattern validation
4. Test patterns that should work vs patterns that should fail

Expected Behavior:
- Tests SHOULD FAIL initially (reproducing the issue)
- defensive_auth patterns currently rejected by validation
- Need to understand scope and severity of validation failures
"""
import pytest
import uuid
from typing import List, Dict, Any
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError, validate_user_context
from netra_backend.app.core.unified_id_manager import is_valid_id_format, is_valid_id_format_compatible
from shared.types.core_types import UserID, ensure_user_id

class DefensiveAuthIDValidationTests(SSotBaseTestCase):
    """
    Test suite reproducing defensive_auth request ID validation failures from Issue #406.
    
    CRITICAL: These tests are EXPECTED TO FAIL initially, reproducing the exact production issue.
    """

    def setUp(self):
        """Set up test with defensive auth patterns."""
        super().setUp()
        self.failing_production_patterns = ['defensive_auth_105945141827451681156_prelim_4280fd7d', 'defensive_auth_209856372745383926234_prelim_8f94a1b2', 'defensive_auth_345267483856194837456_prelim_c3e7f9d4']
        self.defensive_auth_patterns = ['defensive_auth_123456789012345678901_prelim_abcd1234', 'defensive_auth_987654321098765432109_prelim_wxyz9876', 'defensive_auth_555666777888999000111_prelim_feed4567', 'defensive_auth_100200300400500600700_interim_dead8901', 'defensive_auth_800900100200300400500_final_beef2345']
        self.valid_control_patterns = [str(uuid.uuid4()), 'test-user-123', '123456789012345678901']
        self.invalid_control_patterns = ['', 'invalid pattern with spaces', 'short', 'placeholder']

    def test_exact_production_failing_pattern_is_valid_id_format(self):
        """
        Test the exact failing pattern from production logs with is_valid_id_format().
        
        EXPECTED: This test SHOULD FAIL, reproducing the validation issue.
        PATTERN: defensive_auth_105945141827451681156_prelim_4280fd7d
        """
        failing_pattern = 'defensive_auth_105945141827451681156_prelim_4280fd7d'
        result = is_valid_id_format(failing_pattern)
        self.assertTrue(result, f"REPRODUCTION TEST: Pattern '{failing_pattern}' should be valid but is rejected. This reproduces Issue #406 - defensive_auth patterns incorrectly failed validation. Result: {result}")

    def test_production_patterns_with_is_valid_id_format_compatible(self):
        """
        Test production failing patterns with the compatible validation function.
        
        EXPECTED: These tests SHOULD FAIL, reproducing the issue across validation functions.
        """
        for pattern in self.failing_production_patterns:
            with self.subTest(pattern=pattern):
                result = is_valid_id_format_compatible(pattern)
                self.assertTrue(result, f"REPRODUCTION TEST: Pattern '{pattern}' should be valid with compatible validation. This reproduces Issue #406. Result: {result}")

    def test_user_execution_context_with_defensive_auth_request_id(self):
        """
        Test UserExecutionContext creation with defensive_auth request IDs.
        
        EXPECTED: This test SHOULD FAIL with InvalidContextError during validation.
        """
        failing_request_id = 'defensive_auth_105945141827451681156_prelim_4280fd7d'
        user_id = str(uuid.uuid4())
        thread_id = f'thread-{uuid.uuid4()}'
        run_id = f'run-{uuid.uuid4()}'
        with self.assertRaises(InvalidContextError, msg='REPRODUCTION CONFIRMED: UserExecutionContext rejects defensive_auth request_ids'):
            context = UserExecutionContext(user_id=user_id, thread_id=thread_id, run_id=run_id, request_id=failing_request_id)

    def test_user_execution_context_validation_with_all_defensive_patterns(self):
        """
        Test all defensive_auth patterns with UserExecutionContext validation.
        
        EXPECTED: All patterns SHOULD FAIL with InvalidContextError.
        """
        user_id = str(uuid.uuid4())
        thread_id = f'thread-{uuid.uuid4()}'
        run_id = f'run-{uuid.uuid4()}'
        failed_patterns = []
        success_patterns = []
        for pattern in self.failing_production_patterns + self.defensive_auth_patterns:
            with self.subTest(pattern=pattern):
                try:
                    context = UserExecutionContext(user_id=user_id, thread_id=thread_id, run_id=run_id, request_id=pattern)
                    success_patterns.append(pattern)
                    self.fail(f"UNEXPECTED SUCCESS: Pattern '{pattern}' should fail validation but passed. This means the issue may be partially resolved or pattern is actually valid.")
                except InvalidContextError as e:
                    failed_patterns.append((pattern, str(e)))
        self.assertGreater(len(failed_patterns), 0, 'REPRODUCTION VERIFICATION: At least some defensive_auth patterns should fail validation, confirming Issue #406 reproduction.')
        if failed_patterns:
            print(f'\n=== ISSUE #406 REPRODUCTION CONFIRMED ===')
            print(f'Failed patterns (reproducing issue): {len(failed_patterns)}')
            for pattern, error in failed_patterns:
                print(f'  - {pattern}: {error}')
        if success_patterns:
            print(f'Successful patterns (unexpected): {len(success_patterns)}')
            for pattern in success_patterns:
                print(f'  - {pattern}')

    def test_core_types_ensure_user_id_with_defensive_auth(self):
        """
        Test shared.types.core_types.ensure_user_id() with defensive_auth patterns.
        
        EXPECTED: This test SHOULD FAIL, showing validation rejection in core types.
        """
        failing_pattern = 'defensive_auth_105945141827451681156_prelim_4280fd7d'
        with self.assertRaises((ValueError, TypeError), msg='REPRODUCTION CONFIRMED: core_types.ensure_user_id rejects defensive_auth patterns'):
            validated_user_id = ensure_user_id(failing_pattern)

    def test_defensive_auth_pattern_analysis(self):
        """
        Analyze the structure of defensive_auth patterns to understand validation failure.
        
        This test provides diagnostic information about why patterns fail.
        """
        failing_pattern = 'defensive_auth_105945141827451681156_prelim_4280fd7d'
        parts = failing_pattern.split('_')
        pattern_analysis = {'full_pattern': failing_pattern, 'parts': parts, 'part_count': len(parts), 'starts_with_defensive_auth': failing_pattern.startswith('defensive_auth'), 'contains_numeric_id': any((part.isdigit() and len(part) >= 15 for part in parts)), 'ends_with_hex': len(parts[-1]) >= 6 and all((c in '0123456789abcdef' for c in parts[-1])), 'has_prelim_or_interim': any((part in ['prelim', 'interim', 'final'] for part in parts))}
        is_uuid = False
        try:
            uuid.UUID(failing_pattern)
            is_uuid = True
        except ValueError:
            pass
        validation_results = {'is_uuid_format': is_uuid, 'is_valid_id_format': is_valid_id_format(failing_pattern), 'is_valid_id_format_compatible': is_valid_id_format_compatible(failing_pattern), 'pattern_analysis': pattern_analysis}
        print(f'\n=== DEFENSIVE_AUTH PATTERN ANALYSIS ===')
        for key, value in validation_results.items():
            print(f'{key}: {value}')
        self.assertFalse(validation_results['is_valid_id_format'], f'CONFIRMED: Pattern {failing_pattern} fails is_valid_id_format validation. Analysis: {validation_results}')

    def test_control_patterns_work_correctly(self):
        """
        Test control patterns to ensure our test setup is correct.
        
        Valid patterns should pass, invalid patterns should fail.
        """
        for pattern in self.valid_control_patterns:
            with self.subTest(pattern=pattern, expected='valid'):
                result = is_valid_id_format(pattern)
                self.assertTrue(result, f"CONTROL TEST: Valid pattern '{pattern}' should pass validation but failed. This indicates a broader validation issue.")
        for pattern in self.invalid_control_patterns:
            with self.subTest(pattern=pattern, expected='invalid'):
                result = is_valid_id_format(pattern)
                self.assertFalse(result, f"CONTROL TEST: Invalid pattern '{pattern}' should fail validation but passed. This indicates validation is too permissive.")

    def test_user_execution_context_with_valid_controls(self):
        """
        Test UserExecutionContext creation with valid control patterns.
        
        These should work to confirm our test setup.
        """
        thread_id = f'thread-{uuid.uuid4()}'
        run_id = f'run-{uuid.uuid4()}'
        for pattern in self.valid_control_patterns:
            with self.subTest(pattern=pattern):
                try:
                    context = UserExecutionContext(user_id=pattern, thread_id=thread_id, run_id=run_id, request_id=str(uuid.uuid4()))
                    self.assertEqual(context.user_id, pattern)
                    self.assertIsNotNone(context.request_id)
                except Exception as e:
                    self.fail(f"CONTROL TEST FAILED: Valid pattern '{pattern}' should create context successfully. Error: {e}")

    def test_broader_defensive_auth_pattern_scope(self):
        """
        Test broader scope of defensive_auth patterns to understand the full impact.
        
        This helps determine if it's just specific patterns or all defensive_auth patterns.
        """
        pattern_variations = ['defensive_auth_12345678901234567890_prelim_abcd1234', 'defensive_auth_123456789012345678901_prelim_abcd1234', 'defensive_auth_1234567890123456789012_prelim_abcd1234', 'defensive_auth_123456789012345678901_interim_abcd1234', 'defensive_auth_123456789012345678901_final_abcd1234', 'defensive_auth_123456789012345678901_temp_abcd1234', 'defensive_auth_123456789012345678901_prelim_ab', 'defensive_auth_123456789012345678901_prelim_abcd', 'defensive_auth_123456789012345678901_prelim_abcdef12', 'defensive_auth_123456789012345678901_prelim', 'auth_defensive_123456789012345678901_prelim_abcd1234']
        failed_count = 0
        passed_count = 0
        results = []
        for pattern in pattern_variations:
            result = is_valid_id_format(pattern)
            results.append((pattern, result))
            if result:
                passed_count += 1
            else:
                failed_count += 1
        print(f'\n=== BROADER DEFENSIVE_AUTH PATTERN ANALYSIS ===')
        print(f'Total patterns tested: {len(pattern_variations)}')
        print(f'Passed validation: {passed_count}')
        print(f'Failed validation: {failed_count}')
        print(f'Failure rate: {failed_count / len(pattern_variations) * 100:.1f}%')
        print('\nDetailed results:')
        for pattern, result in results:
            status = 'PASS' if result else 'FAIL'
            print(f'  {status}: {pattern}')
        self.assertGreater(failed_count, 0, 'ISSUE SCOPE: At least some defensive_auth pattern variations should fail, confirming this is a systematic validation issue.')

    def test_suggested_fix_patterns(self):
        """
        Test patterns that might work as fixes for defensive_auth validation.
        
        This explores potential regex patterns that could allow defensive_auth IDs.
        """
        failing_pattern = 'defensive_auth_105945141827451681156_prelim_4280fd7d'
        import re
        suggested_patterns = ['^defensive_auth_\\d{15,25}_[a-zA-Z]+_[a-fA-F0-9]{4,8}$', '^defensive_auth_\\d+_[a-zA-Z]+_[a-fA-F0-9]+$', '^[a-zA-Z]+_auth_\\d+_[a-zA-Z]+_[a-fA-F0-9]+$', '^[a-zA-Z_]+\\d+_[a-zA-Z]+_[a-fA-F0-9]+$']
        matching_patterns = []
        non_matching_patterns = []
        for regex_pattern in suggested_patterns:
            if re.match(regex_pattern, failing_pattern):
                matching_patterns.append(regex_pattern)
            else:
                non_matching_patterns.append(regex_pattern)
        print(f'\n=== POTENTIAL FIX ANALYSIS ===')
        print(f'Testing pattern: {failing_pattern}')
        print(f'Matching regex patterns: {len(matching_patterns)}')
        for pattern in matching_patterns:
            print(f'  MATCH: {pattern}')
        print(f'Non-matching patterns: {len(non_matching_patterns)}')
        for pattern in non_matching_patterns:
            print(f'  NO MATCH: {pattern}')
        self.assertGreater(len(matching_patterns), 0, f'FIX ANALYSIS: At least one regex pattern should match {failing_pattern} to provide direction for fixing the validation.')

    def tearDown(self):
        """Clean up after each test."""
        super().tearDown()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')