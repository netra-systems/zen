"""
Issue #803: UserExecutionContext ID Validation - Thread/Run ID Mismatches
Unit Test Suite for ID Generation Mismatch Reproduction

PURPOSE: Reproduce and validate the ID mismatch issue where thread_id and run_id
have different counter bases and different UUID parts.

ISSUE LOCATION: shared/id_generation/unified_id_generator.py:117-118
- thread_id uses counter_base with random_part
- run_id uses counter_base + 1 with new secrets.token_hex(4)

EXPECTED TEST BEHAVIOR:
- Reproduction tests should PASS (confirming bug exists)
- These tests prove the issue exists and will guide the fix
"""

import pytest
import unittest
from unittest.mock import patch, MagicMock
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

@pytest.mark.unit
class Issue803IDGenerationMismatchReproductionTests(unittest.TestCase):
    """Test suite to reproduce the ID generation mismatch issue."""

    def test_thread_run_id_counter_mismatch_reproduction(self):
        """
        REPRODUCTION TEST: Verify thread_id and run_id use different counter values.
        This test should PASS, confirming the bug exists.
        """
        with patch('shared.id_generation.unified_id_generator._get_next_counter') as mock_counter:
            # Mock counter to return predictable value
            mock_counter.return_value = 12345

            with patch('secrets.token_hex') as mock_token:
                # Mock token_hex to return predictable values for each call
                mock_token.side_effect = ['abcd', 'efgh', 'ijkl']  # Three calls: random_part, run_id, request_id

                thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids('testuser123', 'testop')

                # Extract counter values from the IDs
                thread_counter = int(thread_id.split('_')[2])  # thread_test_operation_12345_abcd
                run_counter = int(run_id.split('_')[2])        # run_test_operation_12346_efgh

                # BUG REPRODUCTION: thread_id uses counter_base, run_id uses counter_base + 1
                self.assertEqual(thread_counter, 12345, "thread_id should use counter_base")
                self.assertEqual(run_counter, 12346, "run_id should use counter_base + 1")
                self.assertNotEqual(thread_counter, run_counter, "Counter mismatch confirms the bug")

    def test_thread_run_id_uuid_mismatch_reproduction(self):
        """
        REPRODUCTION TEST: Verify thread_id and run_id use different UUID parts.
        This test should PASS, confirming the bug exists.
        """
        with patch('shared.id_generation.unified_id_generator._get_next_counter') as mock_counter:
            mock_counter.return_value = 12345

            with patch('secrets.token_hex') as mock_token:
                # Mock token_hex to return different values for each call
                mock_token.side_effect = ['uuid1', 'uuid2', 'uuid3']  # Three calls: random_part, run_id, request_id

                thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids('testuser123', 'testop')

                # Extract UUID parts from the IDs
                thread_uuid = thread_id.split('_')[3]  # thread_test_operation_12345_uuid1
                run_uuid = run_id.split('_')[3]        # run_test_operation_12346_uuid2

                # BUG REPRODUCTION: Different UUID parts used
                self.assertEqual(thread_uuid, 'uuid1', "thread_id should use first UUID")
                self.assertEqual(run_uuid, 'uuid2', "run_id should use second UUID")
                self.assertNotEqual(thread_uuid, run_uuid, "UUID mismatch confirms the bug")

    def test_multiple_invocations_show_consistent_mismatch_pattern(self):
        """
        REPRODUCTION TEST: Verify the mismatch pattern is consistent across multiple calls.
        This test should PASS, confirming the bug pattern.
        """
        mismatches = []

        for i in range(5):
            with patch('shared.id_generation.unified_id_generator._get_next_counter') as mock_counter:
                mock_counter.return_value = 1000 + i

                thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(f'user{i}', f'op{i}')

                thread_counter = int(thread_id.split('_')[2])
                run_counter = int(run_id.split('_')[2])

                # Record the mismatch pattern
                mismatches.append(run_counter - thread_counter)

        # BUG REPRODUCTION: All mismatches should be exactly +1
        self.assertEqual(set(mismatches), {1}, "All run_id counters should be thread_id + 1")
        self.assertEqual(len(mismatches), 5, "Should have 5 mismatch patterns")

    def test_request_id_follows_expected_pattern(self):
        """
        REPRODUCTION TEST: Verify request_id follows counter_base + 2 pattern.
        This test should PASS, documenting the complete pattern.
        """
        with patch('shared.id_generation.unified_id_generator._get_next_counter') as mock_counter:
            mock_counter.return_value = 50000

            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids('requser', 'reqtest')

            # Extract counters from all IDs
            thread_parts = thread_id.split('_')
            run_parts = run_id.split('_')
            request_parts = request_id.split('_')
            thread_counter = int(thread_parts[-2])    # Second to last part is counter
            run_counter = int(run_parts[-2])          # Second to last part is counter
            request_counter = int(request_parts[-2])  # Second to last part is counter

            # Document the complete ID generation pattern
            self.assertEqual(thread_counter, 50000, "thread_id uses counter_base")
            self.assertEqual(run_counter, 50001, "run_id uses counter_base + 1")
            self.assertEqual(request_counter, 50002, "request_id uses counter_base + 2")

            # Verify the progressive increment pattern
            self.assertEqual(run_counter - thread_counter, 1, "run_id increments by 1")
            self.assertEqual(request_counter - thread_counter, 2, "request_id increments by 2")

if __name__ == '__main__':
    unittest.main()
