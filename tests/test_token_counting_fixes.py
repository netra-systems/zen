#!/usr/bin/env python3
"""
Comprehensive validation tests for token counting accuracy fixes in claude-instance-orchestrator.py

Tests the 6 critical fixes:
1. Message ID deduplication
2. Cache token separation (read vs creation)
3. SDK-compliant parsing with max() instead of +=
4. Authoritative cost support
5. Updated cost calculations
6. Backward compatibility
"""

import json
import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import asyncio
import tempfile

# Add the scripts directory to the path to import the orchestrator
scripts_path = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_path))

try:
    # Import the module with hyphens in filename
    import importlib.util
    orchestrator_path = scripts_path / "claude-instance-orchestrator.py"

    if not orchestrator_path.exists():
        raise ImportError(f"File not found: {orchestrator_path}")

    spec = importlib.util.spec_from_file_location("claude_instance_orchestrator", orchestrator_path)
    orchestrator_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(orchestrator_module)

    # Extract the classes we need
    ClaudeInstanceOrchestrator = orchestrator_module.ClaudeInstanceOrchestrator
    InstanceConfig = orchestrator_module.InstanceConfig
    InstanceStatus = orchestrator_module.InstanceStatus
    parse_start_time = orchestrator_module.parse_start_time

except Exception as e:
    print(f"❌ Could not import claude-instance-orchestrator.py: {e}")
    print(f"Expected path: {scripts_path / 'claude-instance-orchestrator.py'}")
    print(f"File exists: {(scripts_path / 'claude-instance-orchestrator.py').exists()}")
    sys.exit(1)

class TestTokenCountingFixes(unittest.TestCase):
    """Test suite for token counting accuracy fixes"""

    def setUp(self):
        """Set up test environment"""
        self.temp_workspace = Path(tempfile.mkdtemp())
        self.orchestrator = ClaudeInstanceOrchestrator(
            workspace_dir=self.temp_workspace,
            max_console_lines=0,  # Quiet mode for testing
            quiet=True
        )

        # Create a test instance status
        self.test_status = InstanceStatus(name="test_instance")

    def tearDown(self):
        """Clean up test environment"""
        import shutil
        if self.temp_workspace.exists():
            shutil.rmtree(self.temp_workspace)

    # Test 1: Message ID Deduplication
    def test_message_id_deduplication(self):
        """Test Fix 1: Duplicate message IDs are properly handled"""

        # Test case 1: Same message ID should not duplicate token counts
        json_line1 = json.dumps({
            "id": "msg_12345",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150
            }
        })

        # Process first occurrence
        result1 = self.orchestrator._try_parse_json_token_usage(json_line1, self.test_status)
        self.assertTrue(result1)
        self.assertEqual(self.test_status.input_tokens, 100)
        self.assertEqual(self.test_status.output_tokens, 50)
        self.assertEqual(self.test_status.total_tokens, 150)

        # Process duplicate - should be skipped
        result2 = self.orchestrator._try_parse_json_token_usage(json_line1, self.test_status)
        self.assertTrue(result2)  # Returns True but doesn't update counts
        self.assertEqual(self.test_status.input_tokens, 100)  # Should not change
        self.assertEqual(self.test_status.output_tokens, 50)   # Should not change
        self.assertEqual(self.test_status.total_tokens, 150)   # Should not change

        # Verify message ID was tracked
        self.assertIn("msg_12345", self.test_status.processed_message_ids)

    def test_message_id_extraction(self):
        """Test message ID extraction from various JSON formats"""

        # Test direct ID field
        json_data1 = {"id": "direct_123", "usage": {"input_tokens": 10}}
        msg_id1 = self.orchestrator._extract_message_id(json_data1)
        self.assertEqual(msg_id1, "direct_123")

        # Test nested message ID
        json_data2 = {"message": {"id": "nested_456"}, "usage": {"input_tokens": 10}}
        msg_id2 = self.orchestrator._extract_message_id(json_data2)
        self.assertEqual(msg_id2, "nested_456")

        # Test response ID
        json_data3 = {"response": {"id": "response_789"}, "usage": {"input_tokens": 10}}
        msg_id3 = self.orchestrator._extract_message_id(json_data3)
        self.assertEqual(msg_id3, "response_789")

        # Test no ID
        json_data4 = {"usage": {"input_tokens": 10}}
        msg_id4 = self.orchestrator._extract_message_id(json_data4)
        self.assertIsNone(msg_id4)

    # Test 2: Cache Token Separation
    def test_cache_token_separation(self):
        """Test Fix 2: Cache read and creation tokens are tracked separately"""

        json_line = json.dumps({
            "id": "cache_test_123",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_read_input_tokens": 30,
                "cache_creation_input_tokens": 20,
                "total_tokens": 200
            }
        })

        result = self.orchestrator._try_parse_json_token_usage(json_line, self.test_status)

        self.assertTrue(result)
        self.assertEqual(self.test_status.cache_read_tokens, 30)
        self.assertEqual(self.test_status.cache_creation_tokens, 20)
        # Backward compatibility field should be sum of both
        self.assertEqual(self.test_status.cached_tokens, 50)

    def test_legacy_cached_field_handling(self):
        """Test handling of legacy 'cached' field when separate fields not available"""

        json_line = json.dumps({
            "id": "legacy_cache_123",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cached": 40,  # Legacy format
                "total_tokens": 190
            }
        })

        result = self.orchestrator._try_parse_json_token_usage(json_line, self.test_status)

        self.assertTrue(result)
        # Should map to cache_read_tokens when separate fields not available
        self.assertEqual(self.test_status.cache_read_tokens, 40)
        self.assertEqual(self.test_status.cache_creation_tokens, 0)
        self.assertEqual(self.test_status.cached_tokens, 40)

    # Test 3: SDK-Compliant Parsing with max()
    def test_max_instead_of_accumulation(self):
        """Test Fix 3: Using max() instead of += for same message processing"""

        # First message with base tokens
        json_line1 = json.dumps({
            "id": "max_test_123",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150
            }
        })

        # Second message with higher token counts (different ID)
        json_line2 = json.dumps({
            "id": "max_test_456",
            "usage": {
                "input_tokens": 200,
                "output_tokens": 80,
                "total_tokens": 280
            }
        })

        # Process first message
        result1 = self.orchestrator._try_parse_json_token_usage(json_line1, self.test_status)
        self.assertTrue(result1)
        self.assertEqual(self.test_status.input_tokens, 100)
        self.assertEqual(self.test_status.output_tokens, 50)
        self.assertEqual(self.test_status.total_tokens, 150)

        # Process second message - should use max()
        result2 = self.orchestrator._try_parse_json_token_usage(json_line2, self.test_status)
        self.assertTrue(result2)
        self.assertEqual(self.test_status.input_tokens, 200)  # max(100, 200)
        self.assertEqual(self.test_status.output_tokens, 80)   # max(50, 80)
        self.assertEqual(self.test_status.total_tokens, 280)   # max(150, 280)

    def test_max_with_lower_values(self):
        """Test that max() correctly handles lower values from newer messages"""

        # First message with higher tokens
        json_line1 = json.dumps({
            "id": "max_lower_123",
            "usage": {
                "input_tokens": 200,
                "output_tokens": 100,
                "total_tokens": 300
            }
        })

        # Second message with lower tokens (different ID)
        json_line2 = json.dumps({
            "id": "max_lower_456",
            "usage": {
                "input_tokens": 50,  # Lower than first
                "output_tokens": 25, # Lower than first
                "total_tokens": 75   # Lower than first
            }
        })

        # Process first message
        self.orchestrator._try_parse_json_token_usage(json_line1, self.test_status)
        initial_input = self.test_status.input_tokens
        initial_output = self.test_status.output_tokens
        initial_total = self.test_status.total_tokens

        # Process second message - should maintain higher values
        self.orchestrator._try_parse_json_token_usage(json_line2, self.test_status)
        self.assertEqual(self.test_status.input_tokens, initial_input)   # Should stay 200
        self.assertEqual(self.test_status.output_tokens, initial_output) # Should stay 100
        self.assertEqual(self.test_status.total_tokens, initial_total)   # Should stay 300

    # Test 4: Authoritative Cost Support
    def test_authoritative_cost_support(self):
        """Test Fix 4: Authoritative cost from SDK when available"""

        json_line = json.dumps({
            "id": "cost_test_123",
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 500,
                "total_tokens": 1500,
                "total_cost_usd": 0.075  # Authoritative cost from SDK
            }
        })

        result = self.orchestrator._try_parse_json_token_usage(json_line, self.test_status)

        self.assertTrue(result)
        self.assertEqual(self.test_status.total_cost_usd, 0.075)

        # Test that cost calculation uses authoritative cost
        calculated_cost = self.orchestrator._calculate_cost(self.test_status)
        self.assertEqual(calculated_cost, 0.075)

    def test_fallback_cost_calculation(self):
        """Test fallback cost calculation when authoritative cost not available"""

        json_line = json.dumps({
            "id": "fallback_cost_123",
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_read_input_tokens": 200,
                "cache_creation_input_tokens": 100,
                "total_tokens": 1800
                # No total_cost_usd field
            }
        })

        self.orchestrator._try_parse_json_token_usage(json_line, self.test_status)

        # Should calculate cost using pricing rates
        calculated_cost = self.orchestrator._calculate_cost(self.test_status)

        # Expected: (1000/1M * $3) + (500/1M * $15) + (200/1M * $0.30) + (100/1M * $0.75)
        # = 0.003 + 0.0075 + 0.00006 + 0.000075 = 0.010635
        expected_cost = (1000/1_000_000 * 3.00) + (500/1_000_000 * 15.00) + (200/1_000_000 * 0.30) + (100/1_000_000 * 0.75)
        self.assertAlmostEqual(calculated_cost, expected_cost, places=6)

    # Test 5: Cost Calculation Accuracy
    def test_updated_cost_calculations(self):
        """Test Fix 5: Updated cost calculations with proper cache handling"""

        # Set up status with token counts
        status = InstanceStatus(name="cost_calc_test")
        status.input_tokens = 10000      # 10K input tokens
        status.output_tokens = 5000      # 5K output tokens
        status.cache_read_tokens = 2000  # 2K cache read tokens
        status.cache_creation_tokens = 1000  # 1K cache creation tokens

        cost = self.orchestrator._calculate_cost(status)

        # Expected cost calculation:
        # Input: 10,000 / 1M * $3.00 = $0.030
        # Output: 5,000 / 1M * $15.00 = $0.075
        # Cache read: 2,000 / 1M * $0.30 = $0.0006
        # Cache creation: 1,000 / 1M * $0.75 = $0.00075
        # Total: $0.10635
        expected = 0.030 + 0.075 + 0.0006 + 0.00075
        self.assertAlmostEqual(cost, expected, places=5)

    # Test 6: Backward Compatibility
    def test_backward_compatibility(self):
        """Test Fix 6: Backward compatibility is maintained"""

        # Test that cached_tokens field is properly maintained
        status = InstanceStatus(name="compat_test")
        status.cache_read_tokens = 300
        status.cache_creation_tokens = 200

        self.orchestrator._update_cache_tokens_for_compatibility(status)

        # cached_tokens should be sum of read and creation
        self.assertEqual(status.cached_tokens, 500)

    def test_legacy_parsing_fallback(self):
        """Test that legacy regex parsing still works as fallback"""

        # Test with non-JSON line that should trigger fallback parsing
        legacy_line = "Input: 150 tokens, Output: 75 tokens, Total: 225 tokens"

        self.orchestrator._parse_token_usage_fallback(legacy_line, self.test_status)

        self.assertEqual(self.test_status.input_tokens, 150)
        self.assertEqual(self.test_status.output_tokens, 75)
        self.assertEqual(self.test_status.total_tokens, 225)

    # Edge Cases and Error Handling
    def test_malformed_json_handling(self):
        """Test handling of malformed JSON"""

        malformed_lines = [
            '{"incomplete": json',  # Invalid JSON
            '{"usage": {"input_tokens": "not_a_number"}}',  # Invalid number
            '{"usage": null}',  # Null usage
            '',  # Empty line
            'not json at all'  # Plain text
        ]

        for line in malformed_lines:
            with self.subTest(line=line):
                initial_tokens = self.test_status.total_tokens
                result = self.orchestrator._try_parse_json_token_usage(line, self.test_status)
                self.assertFalse(result)
                # Tokens should not change on malformed input
                self.assertEqual(self.test_status.total_tokens, initial_tokens)

    def test_missing_usage_fields(self):
        """Test handling of JSON with missing usage fields"""

        json_line = json.dumps({
            "id": "missing_fields_123",
            "type": "message",
            # Missing usage field entirely
        })

        result = self.orchestrator._try_parse_json_token_usage(json_line, self.test_status)
        # Should return False when no valid token data is found
        self.assertFalse(result)

    def test_alternative_field_formats(self):
        """Test handling of alternative field formats"""

        # Test alternative field names
        json_line = json.dumps({
            "id": "alt_format_123",
            "usage": {
                "input": 100,    # Alternative to input_tokens
                "output": 50,    # Alternative to output_tokens
                "total": 150     # Alternative to total_tokens
            }
        })

        result = self.orchestrator._try_parse_json_token_usage(json_line, self.test_status)

        self.assertTrue(result)
        self.assertEqual(self.test_status.input_tokens, 100)
        self.assertEqual(self.test_status.output_tokens, 50)
        self.assertEqual(self.test_status.total_tokens, 150)

    def test_tool_call_counting(self):
        """Test tool call counting with message ID deduplication"""

        # Tool execution message
        json_line1 = json.dumps({
            "id": "tool_123",
            "type": "tool_use"
        })

        # Same tool execution (duplicate ID)
        json_line2 = json.dumps({
            "id": "tool_123",  # Same ID
            "type": "tool_use"
        })

        # Different tool execution
        json_line3 = json.dumps({
            "id": "tool_456",  # Different ID
            "type": "tool_call"
        })

        # Process first tool call
        result1 = self.orchestrator._try_parse_json_token_usage(json_line1, self.test_status)
        self.assertTrue(result1)
        self.assertEqual(self.test_status.tool_calls, 1)

        # Process duplicate - should not increment
        result2 = self.orchestrator._try_parse_json_token_usage(json_line2, self.test_status)
        self.assertTrue(result2)
        self.assertEqual(self.test_status.tool_calls, 1)  # Should not change

        # Process different tool call
        result3 = self.orchestrator._try_parse_json_token_usage(json_line3, self.test_status)
        self.assertTrue(result3)
        self.assertEqual(self.test_status.tool_calls, 2)  # Should increment

    def test_no_message_id_processing(self):
        """Test processing of JSON without message ID (should still work)"""

        json_line = json.dumps({
            "input_tokens": 100,
            "output_tokens": 50,
            "cached_tokens": 25,
            "total_tokens": 175
        })

        result = self.orchestrator._try_parse_json_token_usage(json_line, self.test_status)

        self.assertTrue(result)
        self.assertEqual(self.test_status.input_tokens, 100)
        self.assertEqual(self.test_status.output_tokens, 50)
        self.assertEqual(self.test_status.cache_read_tokens, 25)
        self.assertEqual(self.test_status.total_tokens, 175)


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests with realistic Claude API response scenarios"""

    def setUp(self):
        """Set up test environment"""
        self.temp_workspace = Path(tempfile.mkdtemp())
        self.orchestrator = ClaudeInstanceOrchestrator(
            workspace_dir=self.temp_workspace,
            max_console_lines=0,
            quiet=True
        )

    def tearDown(self):
        """Clean up test environment"""
        import shutil
        if self.temp_workspace.exists():
            shutil.rmtree(self.temp_workspace)

    def test_realistic_claude_api_response(self):
        """Test with realistic Claude API response format"""

        status = InstanceStatus(name="realistic_test")

        # Simulate realistic Claude API response sequence
        responses = [
            # Initial thinking response
            {
                "type": "message_start",
                "message": {
                    "id": "msg_01ABC123",
                    "type": "message",
                    "role": "assistant",
                    "content": [],
                    "model": "claude-3-5-sonnet-20241022",
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": 1247,
                        "cache_creation_input_tokens": 1200,
                        "cache_read_input_tokens": 0,
                        "output_tokens": 0
                    }
                }
            },
            # Content delta
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "text",
                    "text": "I'll help you create comprehensive validation tests..."
                }
            },
            # Tool use
            {
                "type": "content_block_start",
                "index": 1,
                "content_block": {
                    "type": "tool_use",
                    "id": "toolu_01234567890abcdef",
                    "name": "Read",
                    "input": {"file_path": "/some/path/file.py"}
                }
            },
            # Final message with complete usage
            {
                "type": "message_delta",
                "delta": {
                    "stop_reason": "end_turn",
                    "stop_sequence": None
                },
                "usage": {
                    "output_tokens": 856
                }
            },
            # Message stop
            {
                "type": "message_stop"
            }
        ]

        # Process each response
        for response in responses:
            json_line = json.dumps(response)
            self.orchestrator._try_parse_json_token_usage(json_line, status)

        # Verify final token counts
        self.assertEqual(status.input_tokens, 1247)
        self.assertEqual(status.output_tokens, 856)
        self.assertEqual(status.cache_creation_tokens, 1200)
        self.assertEqual(status.cache_read_tokens, 0)
        self.assertEqual(status.cached_tokens, 1200)  # Backward compatibility

        # In this case, no explicit total_tokens was provided, so it should remain 0
        # The realistic API doesn't always provide total_tokens in streaming responses
        # Note: The implementation uses max() so if no total is provided, it stays 0
        self.assertEqual(status.total_tokens, 0)  # No explicit total_tokens provided

    def test_multiple_turns_conversation(self):
        """Test multi-turn conversation with cumulative token tracking"""

        status = InstanceStatus(name="multi_turn_test")

        # Turn 1
        turn1 = {
            "id": "msg_turn1",
            "usage": {
                "input_tokens": 500,
                "output_tokens": 200,
                "cache_read_input_tokens": 100,
                "total_tokens": 800
            }
        }

        # Turn 2 (should use max for cumulative totals)
        turn2 = {
            "id": "msg_turn2",
            "usage": {
                "input_tokens": 800,  # Cumulative, higher
                "output_tokens": 450, # Cumulative, higher
                "cache_read_input_tokens": 150, # Cumulative, higher
                "total_tokens": 1400  # Cumulative total
            }
        }

        # Process turns
        self.orchestrator._try_parse_json_token_usage(json.dumps(turn1), status)
        self.orchestrator._try_parse_json_token_usage(json.dumps(turn2), status)

        # Should have cumulative maximums
        self.assertEqual(status.input_tokens, 800)   # max(500, 800)
        self.assertEqual(status.output_tokens, 450)  # max(200, 450)
        self.assertEqual(status.cache_read_tokens, 150)  # max(100, 150)
        self.assertEqual(status.total_tokens, 1400)  # max(800, 1400)

    def test_mixed_response_formats(self):
        """Test handling of mixed response formats in single session"""

        status = InstanceStatus(name="mixed_format_test")

        # JSON format response
        json_response = {
            "id": "json_msg_123",
            "usage": {
                "input_tokens": 300,
                "output_tokens": 150
            }
        }

        # Text format response (fallback parsing - note: this ADDS to tokens, not max)
        text_response = "Input: 100 tokens, Output: 50 tokens, Cached: 50 tokens"

        # Process both
        self.orchestrator._try_parse_json_token_usage(json.dumps(json_response), status)
        self.orchestrator._parse_token_usage_fallback(text_response, status)

        # Fallback parsing adds to existing tokens (this is the expected behavior for non-JSON)
        self.assertEqual(status.input_tokens, 400)   # 300 + 100
        self.assertEqual(status.output_tokens, 200)  # 150 + 50
        self.assertEqual(status.cache_read_tokens, 50)  # 0 + 50


def run_test_suite():
    """Run the complete test suite and return results"""

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTest(loader.loadTestsFromTestCase(TestTokenCountingFixes))
    suite.addTest(loader.loadTestsFromTestCase(TestIntegrationScenarios))

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    print("RUNNING: Token Counting Fixes Validation Tests")
    print("=" * 60)

    result = run_test_suite()

    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError: ')[-1].split('\n')[0]}")

    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('\n')[-2]}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'ALL TESTS PASSED' if success else 'TESTS FAILED'}")

    exit_code = 0 if success else 1
    exit(exit_code)