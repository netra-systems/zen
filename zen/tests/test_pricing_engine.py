#!/usr/bin/env python3
"""
Comprehensive Tests for Claude Pricing Engine

Tests ensure pricing compliance with official Claude documentation
and verify accurate cost calculations across different scenarios.
"""

import unittest
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from token_transparency import (
        ClaudePricingEngine,
        ClaudePricingConfig,
        TokenUsageData,
        CostBreakdown
    )
except ImportError as e:
    print(f"Warning: Could not import token_transparency module: {e}")
    ClaudePricingEngine = None


class TestClaudePricingEngine(unittest.TestCase):
    """Test suite for Claude pricing engine"""

    def setUp(self):
        """Set up test fixtures"""
        if ClaudePricingEngine is None:
            self.skipTest("Token transparency module not available")

        self.engine = ClaudePricingEngine()
        self.config = ClaudePricingConfig()

    def test_model_detection_from_response(self):
        """Test model detection from various API response formats"""
        test_cases = [
            # Test case: (response_data, expected_model)
            ({"model": "claude-3-5-sonnet"}, "claude-3-5-sonnet"),
            ({"model_name": "claude-haiku-3.5"}, "claude-haiku-3.5"),
            ({"usage": {"model": "claude-opus-4.1"}}, "claude-opus-4.1"),
            ({"message": {"model": "claude-sonnet-4"}}, "claude-sonnet-4"),
            ({"metadata": {"model": "claude-3-5-sonnet"}}, "claude-3-5-sonnet"),
            ({}, "claude-3-5-sonnet"),  # Default fallback
        ]

        for response_data, expected_model in test_cases:
            with self.subTest(response=response_data):
                detected = self.engine.detect_model_from_response(response_data)
                self.assertEqual(detected, expected_model)

    def test_model_name_normalization(self):
        """Test model name normalization"""
        test_cases = [
            # Test case: (input_name, expected_normalized)
            ("Claude-3.5-Sonnet", "claude-3-5-sonnet"),
            ("CLAUDE OPUS 4.1", "claude-opus-4.1"),
            ("claude haiku 3.5", "claude-haiku-3.5"),
            ("opus-4", "claude-opus-4"),
            ("sonnet-3.7", "claude-sonnet-3.7"),
        ]

        for input_name, expected in test_cases:
            with self.subTest(input=input_name):
                normalized = self.engine._normalize_model_name(input_name)
                self.assertEqual(normalized, expected)

    def test_cache_type_detection(self):
        """Test cache type detection from response data"""
        test_cases = [
            # Test case: (response_data, expected_cache_type)
            ({"cache_type": "1hour"}, "1hour"),
            ({"cache_type": "5min"}, "5min"),
            ({"usage": {"cache_type": "60min"}}, "1hour"),
            ({"metadata": {"cache_type": "5min"}}, "5min"),
            ({}, "5min"),  # Default fallback
        ]

        for response_data, expected_cache_type in test_cases:
            with self.subTest(response=response_data):
                detected = self.engine.detect_cache_type(response_data)
                self.assertEqual(detected, expected_cache_type)

    def test_cost_calculation_claude_3_5_sonnet(self):
        """Test cost calculation for Claude 3.5 Sonnet"""
        usage_data = TokenUsageData(
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=200,
            cache_creation_tokens=100,
            cache_type="5min",
            model="claude-3-5-sonnet"
        )

        cost_breakdown = self.engine.calculate_cost(usage_data)

        # Expected costs based on Claude 3.5 Sonnet pricing
        expected_input_cost = (1000 / 1_000_000) * 3.0  # $0.003
        expected_output_cost = (500 / 1_000_000) * 15.0  # $0.0075
        expected_cache_read_cost = (200 / 1_000_000) * (3.0 * 0.1)  # $0.00006
        expected_cache_creation_cost = (100 / 1_000_000) * (3.0 * 1.25)  # $0.000375

        self.assertAlmostEqual(cost_breakdown.input_cost, expected_input_cost, places=6)
        self.assertAlmostEqual(cost_breakdown.output_cost, expected_output_cost, places=6)
        self.assertAlmostEqual(cost_breakdown.cache_read_cost, expected_cache_read_cost, places=6)
        self.assertAlmostEqual(cost_breakdown.cache_creation_cost, expected_cache_creation_cost, places=6)
        self.assertEqual(cost_breakdown.model_used, "claude-3-5-sonnet")
        self.assertEqual(cost_breakdown.cache_type, "5min")

    def test_cost_calculation_claude_haiku(self):
        """Test cost calculation for Claude Haiku"""
        usage_data = TokenUsageData(
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=200,
            cache_creation_tokens=100,
            cache_type="1hour",
            model="claude-haiku-3.5"
        )

        cost_breakdown = self.engine.calculate_cost(usage_data)

        # Expected costs based on Claude Haiku pricing
        expected_input_cost = (1000 / 1_000_000) * 0.8  # $0.0008
        expected_output_cost = (500 / 1_000_000) * 4.0  # $0.002
        expected_cache_read_cost = (200 / 1_000_000) * (0.8 * 0.1)  # $0.000016
        expected_cache_creation_cost = (100 / 1_000_000) * (0.8 * 2.0)  # $0.00016

        self.assertAlmostEqual(cost_breakdown.input_cost, expected_input_cost, places=6)
        self.assertAlmostEqual(cost_breakdown.output_cost, expected_output_cost, places=6)
        self.assertAlmostEqual(cost_breakdown.cache_read_cost, expected_cache_read_cost, places=6)
        self.assertAlmostEqual(cost_breakdown.cache_creation_cost, expected_cache_creation_cost, places=6)
        self.assertEqual(cost_breakdown.model_used, "claude-haiku-3.5")
        self.assertEqual(cost_breakdown.cache_type, "1hour")

    def test_cost_calculation_claude_opus(self):
        """Test cost calculation for Claude Opus"""
        usage_data = TokenUsageData(
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            model="claude-opus-4.1"
        )

        cost_breakdown = self.engine.calculate_cost(usage_data)

        # Expected costs based on Claude Opus pricing
        expected_input_cost = (1000 / 1_000_000) * 15.0  # $0.015
        expected_output_cost = (500 / 1_000_000) * 75.0  # $0.0375

        self.assertAlmostEqual(cost_breakdown.input_cost, expected_input_cost, places=6)
        self.assertAlmostEqual(cost_breakdown.output_cost, expected_output_cost, places=6)
        self.assertEqual(cost_breakdown.cache_read_cost, 0.0)
        self.assertEqual(cost_breakdown.cache_creation_cost, 0.0)
        self.assertEqual(cost_breakdown.model_used, "claude-opus-4.1")

    def test_authoritative_cost_override(self):
        """Test that authoritative cost from SDK takes precedence"""
        usage_data = TokenUsageData(
            input_tokens=1000,
            output_tokens=500,
            model="claude-3-5-sonnet"
        )

        authoritative_cost = 0.12345
        cost_breakdown = self.engine.calculate_cost(usage_data, authoritative_cost)

        self.assertEqual(cost_breakdown.total_cost, authoritative_cost)

    def test_parse_claude_response_valid_json(self):
        """Test parsing valid Claude Code JSON response"""
        response_line = json.dumps({
            "usage": {
                "input_tokens": 150,
                "output_tokens": 75,
                "cache_read_input_tokens": 25,
                "cache_creation_input_tokens": 10,
                "total_tokens": 260
            },
            "model": "claude-3-5-sonnet",
            "cache_type": "5min"
        })

        usage_data = self.engine.parse_claude_response(response_line)

        self.assertIsNotNone(usage_data)
        self.assertEqual(usage_data.input_tokens, 150)
        self.assertEqual(usage_data.output_tokens, 75)
        self.assertEqual(usage_data.cache_read_tokens, 25)
        self.assertEqual(usage_data.cache_creation_tokens, 10)
        self.assertEqual(usage_data.total_tokens, 260)
        self.assertEqual(usage_data.model, "claude-3-5-sonnet")
        self.assertEqual(usage_data.cache_type, "5min")

    def test_parse_claude_response_nested_usage(self):
        """Test parsing Claude response with nested usage data"""
        response_line = json.dumps({
            "message": {
                "usage": {
                    "input_tokens": 200,
                    "output_tokens": 100
                }
            }
        })

        usage_data = self.engine.parse_claude_response(response_line)

        self.assertIsNotNone(usage_data)
        self.assertEqual(usage_data.input_tokens, 200)
        self.assertEqual(usage_data.output_tokens, 100)

    def test_parse_claude_response_invalid_json(self):
        """Test parsing invalid JSON returns None"""
        invalid_responses = [
            "not json at all",
            "{invalid json}",
            '{"incomplete": json',
            "",
            "some regular text output"
        ]

        for response in invalid_responses:
            with self.subTest(response=response):
                usage_data = self.engine.parse_claude_response(response)
                self.assertIsNone(usage_data)

    def test_transparency_report_generation(self):
        """Test generation of transparency report"""
        usage_data = TokenUsageData(
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=200,
            cache_creation_tokens=100,
            total_tokens=1800,
            cache_type="5min",
            model="claude-3-5-sonnet"
        )

        cost_breakdown = self.engine.calculate_cost(usage_data)
        report = self.engine.get_transparency_report(usage_data, cost_breakdown)

        # Verify report structure
        self.assertIn("model_used", report)
        self.assertIn("cache_type", report)
        self.assertIn("token_breakdown", report)
        self.assertIn("cost_breakdown", report)
        self.assertIn("pricing_rates", report)
        self.assertIn("compliance_info", report)

        # Verify report content
        self.assertEqual(report["model_used"], "claude-3-5-sonnet")
        self.assertEqual(report["cache_type"], "5min")
        self.assertEqual(report["token_breakdown"]["input_tokens"], 1000)
        self.assertEqual(report["token_breakdown"]["output_tokens"], 500)
        self.assertGreater(report["cost_breakdown"]["total_cost_usd"], 0)

    def test_pricing_config_values(self):
        """Test that pricing config has expected values"""
        config = ClaudePricingConfig()

        # Test model pricing exists for key models
        self.assertIn("claude-3-5-sonnet", config.MODEL_PRICING)
        self.assertIn("claude-haiku-3.5", config.MODEL_PRICING)
        self.assertIn("claude-opus-4.1", config.MODEL_PRICING)

        # Test Claude 3.5 Sonnet pricing matches documentation
        sonnet_pricing = config.MODEL_PRICING["claude-3-5-sonnet"]
        self.assertEqual(sonnet_pricing["input"], 3.0)
        self.assertEqual(sonnet_pricing["output"], 15.0)

        # Test cache multipliers
        self.assertEqual(config.CACHE_READ_MULTIPLIER, 0.1)
        self.assertEqual(config.CACHE_5MIN_WRITE_MULTIPLIER, 1.25)
        self.assertEqual(config.CACHE_1HOUR_WRITE_MULTIPLIER, 2.0)

    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        # Zero tokens
        usage_data = TokenUsageData(
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            model="claude-3-5-sonnet"
        )
        cost_breakdown = self.engine.calculate_cost(usage_data)
        self.assertEqual(cost_breakdown.total_cost, 0.0)

        # Unknown model falls back to default
        usage_data = TokenUsageData(
            input_tokens=100,
            output_tokens=50,
            model="unknown-model"
        )
        cost_breakdown = self.engine.calculate_cost(usage_data)
        self.assertGreater(cost_breakdown.total_cost, 0.0)

    def test_claude_pricing_compliance(self):
        """Test compliance with official Claude pricing documentation"""
        # This test verifies that our pricing matches the official docs
        # as of the documentation fetch date

        config = ClaudePricingConfig()

        # Verify Opus 4.1 pricing
        opus_pricing = config.MODEL_PRICING["claude-opus-4.1"]
        self.assertEqual(opus_pricing["input"], 15.0, "Opus input pricing should be $15/M tokens")
        self.assertEqual(opus_pricing["output"], 75.0, "Opus output pricing should be $75/M tokens")

        # Verify Sonnet pricing
        sonnet_pricing = config.MODEL_PRICING["claude-3-5-sonnet"]
        self.assertEqual(sonnet_pricing["input"], 3.0, "Sonnet input pricing should be $3/M tokens")
        self.assertEqual(sonnet_pricing["output"], 15.0, "Sonnet output pricing should be $15/M tokens")

        # Verify Haiku pricing
        haiku_pricing = config.MODEL_PRICING["claude-haiku-3.5"]
        self.assertEqual(haiku_pricing["input"], 0.8, "Haiku input pricing should be $0.8/M tokens")
        self.assertEqual(haiku_pricing["output"], 4.0, "Haiku output pricing should be $4/M tokens")


class TestTokenUsageData(unittest.TestCase):
    """Test TokenUsageData class"""

    def test_token_usage_data_creation(self):
        """Test TokenUsageData creation and defaults"""
        usage = TokenUsageData(
            input_tokens=100,
            output_tokens=50
        )

        self.assertEqual(usage.input_tokens, 100)
        self.assertEqual(usage.output_tokens, 50)
        self.assertEqual(usage.cache_read_tokens, 0)
        self.assertEqual(usage.cache_creation_tokens, 0)
        self.assertEqual(usage.cache_type, "5min")
        self.assertEqual(usage.model, "claude-3-5-sonnet")

    def test_total_tokens_calculation(self):
        """Test automatic total tokens calculation"""
        usage = TokenUsageData(
            input_tokens=100,
            output_tokens=50,
            cache_read_tokens=25,
            cache_creation_tokens=10
        )

        self.assertEqual(usage.total_tokens, 185)


class TestCostBreakdown(unittest.TestCase):
    """Test CostBreakdown class"""

    def test_cost_breakdown_creation(self):
        """Test CostBreakdown creation and total calculation"""
        breakdown = CostBreakdown(
            input_cost=0.003,
            output_cost=0.0075,
            cache_read_cost=0.0001,
            cache_creation_cost=0.0002,
            tool_cost=0.001
        )

        expected_total = 0.003 + 0.0075 + 0.0001 + 0.0002 + 0.001
        self.assertAlmostEqual(breakdown.total_cost, expected_total, places=6)


if __name__ == '__main__':
    unittest.main()