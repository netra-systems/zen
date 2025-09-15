"""
Comprehensive unit tests for ChatOrchestrator confidence management module.

Business Value: Tests the confidence scoring and threshold management that determines
routing decisions and quality requirements for AI optimization workflows.

Coverage Areas:
- Confidence threshold management for different intent types
- Quality requirement mapping based on intent criticality
- Cache TTL (time-to-live) configuration for different intents
- Cache key generation and validation
- Escalation decision logic based on confidence levels
- Business-critical confidence boundaries and edge cases

SSOT Compliance: Uses SSotAsyncTestCase, real service integration, no mocks for core logic
"""

import hashlib
import pytest
import unittest
from unittest.mock import patch
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.agents.chat_orchestrator.confidence_manager import (
    ConfidenceManager,
    ConfidenceLevel
)
from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentType
from netra_backend.app.agents.base.interface import ExecutionContext
from dataclasses import dataclass

@dataclass
class AgentState:
    """Simple agent state for testing ChatOrchestrator."""
    user_request: str = ""
    accumulated_data: dict = None

    def __post_init__(self):
        if self.accumulated_data is None:
            self.accumulated_data = {}


class TestChatOrchestratorConfidenceManagement(SSotAsyncTestCase, unittest.TestCase):
    """Comprehensive tests for ChatOrchestrator confidence management business logic."""

    def setUp(self):
        """Set up test environment with confidence manager."""
        super().setUp()

        self.confidence_manager = ConfidenceManager()

        # Create test execution contexts for different scenarios
        self.tco_context = self._create_test_context(
            "Calculate the total cost of ownership for our AI infrastructure",
            user_id="tco_user_123"
        )
        self.optimization_context = self._create_test_context(
            "How can I optimize my model performance and reduce costs?",
            user_id="opt_user_456"
        )
        self.general_context = self._create_test_context(
            "Tell me about your platform",
            user_id="general_user_789"
        )

    def _create_test_context(self, user_request: str, user_id: str = "test_user") -> ExecutionContext:
        """Create test execution context with user request."""
        state = AgentState()
        state.user_request = user_request

        context = ExecutionContext(
            request_id=f"test_req_{id(user_request)}",
            state=state,
            user_id=user_id
        )
        return context

    def test_confidence_threshold_initialization(self):
        """Test proper initialization of confidence thresholds for all intent types."""
        # Test that all intent types have defined thresholds
        for intent_type in IntentType:
            threshold = self.confidence_manager.get_threshold(intent_type)

            # Assert business logic: all thresholds are valid confidence values
            self.assertGreaterEqual(threshold, 0.0,
                                   f"{intent_type.value} threshold should be >= 0.0")
            self.assertLessEqual(threshold, 1.0,
                                f"{intent_type.value} threshold should be <= 1.0")

    def test_high_criticality_intent_thresholds(self):
        """Test that business-critical intents have appropriately high thresholds."""
        # High-criticality intents requiring high confidence
        high_criticality_intents = [
            IntentType.TCO_ANALYSIS,
            IntentType.BENCHMARKING,
            IntentType.OPTIMIZATION_ADVICE
        ]

        for intent in high_criticality_intents:
            threshold = self.confidence_manager.get_threshold(intent)

            # Assert business logic: critical intents need high confidence
            self.assertGreaterEqual(threshold, ConfidenceLevel.HIGH.value,
                                   f"{intent.value} should require HIGH confidence")

    def test_medium_criticality_intent_thresholds(self):
        """Test that medium-criticality intents have appropriate thresholds."""
        # Medium-criticality intents
        medium_criticality_intents = [
            IntentType.PRICING_INQUIRY,
            IntentType.MARKET_RESEARCH,
            IntentType.TECHNICAL_QUESTION
        ]

        for intent in medium_criticality_intents:
            threshold = self.confidence_manager.get_threshold(intent)

            # Assert business logic: medium intents need medium confidence
            self.assertGreaterEqual(threshold, ConfidenceLevel.MEDIUM.value,
                                   f"{intent.value} should require MEDIUM confidence")
            self.assertLess(threshold, ConfidenceLevel.HIGH.value,
                           f"{intent.value} should not require HIGH confidence")

    def test_low_criticality_intent_thresholds(self):
        """Test that low-criticality intents have lower thresholds."""
        # Low-criticality intents
        low_criticality_intents = [IntentType.GENERAL_INQUIRY]

        for intent in low_criticality_intents:
            threshold = self.confidence_manager.get_threshold(intent)

            # Assert business logic: general inquiries have lower threshold
            self.assertEqual(threshold, ConfidenceLevel.LOW.value,
                           f"{intent.value} should require LOW confidence")

    def test_escalation_decision_logic_high_confidence(self):
        """Test escalation decisions for high-confidence scenarios."""
        # High confidence scenarios should not escalate
        test_cases = [
            (IntentType.TCO_ANALYSIS, 0.90),  # Above HIGH threshold
            (IntentType.OPTIMIZATION_ADVICE, 0.87),  # Above HIGH threshold
            (IntentType.PRICING_INQUIRY, 0.75),  # Above MEDIUM threshold
            (IntentType.GENERAL_INQUIRY, 0.60)  # Above LOW threshold
        ]

        for intent, confidence in test_cases:
            should_escalate = self.confidence_manager.should_escalate(confidence, intent)

            # Assert business logic: high confidence should not escalate
            self.assertFalse(should_escalate,
                           f"{intent.value} with confidence {confidence} should not escalate")

    def test_escalation_decision_logic_low_confidence(self):
        """Test escalation decisions for low-confidence scenarios."""
        # Low confidence scenarios should escalate
        test_cases = [
            (IntentType.TCO_ANALYSIS, 0.70),  # Below HIGH threshold
            (IntentType.OPTIMIZATION_ADVICE, 0.75),  # Below HIGH threshold
            (IntentType.PRICING_INQUIRY, 0.60),  # Below MEDIUM threshold
            (IntentType.TECHNICAL_QUESTION, 0.65),  # Below MEDIUM threshold
            (IntentType.GENERAL_INQUIRY, 0.40)  # Below LOW threshold
        ]

        for intent, confidence in test_cases:
            should_escalate = self.confidence_manager.should_escalate(confidence, intent)

            # Assert business logic: low confidence should escalate
            self.assertTrue(should_escalate,
                          f"{intent.value} with confidence {confidence} should escalate")

    def test_cache_ttl_configuration(self):
        """Test cache TTL (time-to-live) configuration for different intent types."""
        # Test that all intent types have defined cache TTLs
        for intent_type in IntentType:
            ttl = self.confidence_manager.get_cache_ttl(intent_type)

            # Assert business logic: TTLs are positive and reasonable
            self.assertGreater(ttl, 0, f"{intent_type.value} TTL should be positive")
            self.assertLessEqual(ttl, 7200, f"{intent_type.value} TTL should be <= 2 hours")

    def test_cache_ttl_business_logic(self):
        """Test that cache TTL values reflect business requirements."""
        # Pricing should have shorter TTL (data changes frequently)
        pricing_ttl = self.confidence_manager.get_cache_ttl(IntentType.PRICING_INQUIRY)
        market_ttl = self.confidence_manager.get_cache_ttl(IntentType.MARKET_RESEARCH)

        # Assert business logic: pricing has shorter TTL than market research
        self.assertLess(pricing_ttl, market_ttl,
                       "Pricing TTL should be shorter than market research TTL")

        # Technical questions should have reasonable TTL
        technical_ttl = self.confidence_manager.get_cache_ttl(IntentType.TECHNICAL_QUESTION)
        self.assertGreaterEqual(technical_ttl, 3600,  # At least 1 hour
                               "Technical questions should cache for at least 1 hour")

    def test_cache_key_generation_consistency(self):
        """Test that cache key generation is consistent and deterministic."""
        # Generate multiple keys for same context
        keys = []
        for _ in range(5):
            key = self.confidence_manager.generate_cache_key(
                self.tco_context, IntentType.TCO_ANALYSIS
            )
            keys.append(key)

        # Assert business logic: same context generates same key
        self.assertTrue(all(key == keys[0] for key in keys),
                       "Cache keys should be consistent for same context")

    def test_cache_key_generation_uniqueness(self):
        """Test that different contexts generate different cache keys."""
        # Generate keys for different contexts
        tco_key = self.confidence_manager.generate_cache_key(
            self.tco_context, IntentType.TCO_ANALYSIS
        )
        opt_key = self.confidence_manager.generate_cache_key(
            self.optimization_context, IntentType.OPTIMIZATION_ADVICE
        )
        general_key = self.confidence_manager.generate_cache_key(
            self.general_context, IntentType.GENERAL_INQUIRY
        )

        # Assert business logic: different contexts have different keys
        keys = [tco_key, opt_key, general_key]
        unique_keys = set(keys)
        self.assertEqual(len(unique_keys), len(keys),
                        "Different contexts should generate unique cache keys")

    def test_cache_key_format_validation(self):
        """Test that generated cache keys have proper format."""
        key = self.confidence_manager.generate_cache_key(
            self.tco_context, IntentType.TCO_ANALYSIS
        )

        # Assert business logic: key is MD5 hash format
        self.assertEqual(len(key), 32, "Cache key should be 32-character MD5 hash")
        self.assertTrue(all(c in '0123456789abcdef' for c in key),
                       "Cache key should contain only hex characters")

    def test_cache_key_components_validation(self):
        """Test that cache keys properly incorporate all relevant components."""
        # Test key generation with different user IDs
        context1 = self._create_test_context("same request", "user1")
        context2 = self._create_test_context("same request", "user2")

        key1 = self.confidence_manager.generate_cache_key(context1, IntentType.TCO_ANALYSIS)
        key2 = self.confidence_manager.generate_cache_key(context2, IntentType.TCO_ANALYSIS)

        # Assert business logic: different users should have different cache keys
        self.assertNotEqual(key1, key2,
                          "Different users should generate different cache keys")

    def test_quality_requirement_mapping(self):
        """Test quality requirement mapping based on intent criticality."""
        # Test all intent types have quality requirements
        for intent_type in IntentType:
            quality_req = self.confidence_manager.get_quality_requirement(intent_type)

            # Assert business logic: quality requirements are valid
            self.assertGreaterEqual(quality_req, 0.0,
                                   f"{intent_type.value} quality requirement should be >= 0.0")
            self.assertLessEqual(quality_req, 1.0,
                                f"{intent_type.value} quality requirement should be <= 1.0")

    def test_quality_requirement_business_criticality(self):
        """Test that quality requirements reflect business criticality."""
        # High-criticality intents should have high quality requirements
        tco_quality = self.confidence_manager.get_quality_requirement(IntentType.TCO_ANALYSIS)
        benchmark_quality = self.confidence_manager.get_quality_requirement(IntentType.BENCHMARKING)
        optimization_quality = self.confidence_manager.get_quality_requirement(IntentType.OPTIMIZATION_ADVICE)

        # Assert business logic: critical intents have high quality requirements
        self.assertGreaterEqual(tco_quality, 0.85, "TCO analysis needs high quality")
        self.assertGreaterEqual(benchmark_quality, 0.85, "Benchmarking needs high quality")
        self.assertGreaterEqual(optimization_quality, 0.85, "Optimization needs high quality")

        # General inquiries should have lower quality requirements
        general_quality = self.confidence_manager.get_quality_requirement(IntentType.GENERAL_INQUIRY)
        self.assertLessEqual(general_quality, 0.7, "General inquiries have lower quality requirements")

    def test_quality_vs_confidence_relationship(self):
        """Test the relationship between quality requirements and confidence thresholds."""
        for intent_type in IntentType:
            quality_req = self.confidence_manager.get_quality_requirement(intent_type)
            confidence_threshold = self.confidence_manager.get_threshold(intent_type)

            # Assert business logic: quality and confidence should be reasonably aligned
            # Quality requirements can be higher than confidence thresholds, but should be related
            if quality_req >= 0.85:  # High quality requirement
                self.assertGreaterEqual(confidence_threshold, ConfidenceLevel.MEDIUM.value,
                                       f"High quality intent {intent_type.value} should have medium+ confidence threshold")

    def test_confidence_level_enum_values(self):
        """Test that ConfidenceLevel enum values are properly ordered."""
        levels = [
            ConfidenceLevel.LOW.value,
            ConfidenceLevel.MEDIUM.value,
            ConfidenceLevel.HIGH.value,
            ConfidenceLevel.VERY_HIGH.value
        ]

        # Assert business logic: confidence levels are properly ordered
        for i in range(1, len(levels)):
            self.assertGreater(levels[i], levels[i-1],
                             f"Confidence level {i} should be greater than level {i-1}")

    def test_unknown_intent_fallback_behavior(self):
        """Test fallback behavior for unknown or invalid intent types."""
        # Create a mock intent type (since we can't add to enum in test)
        # Test with None as fallback scenario
        threshold = self.confidence_manager.get_threshold(None)
        ttl = self.confidence_manager.get_cache_ttl(None)
        quality = self.confidence_manager.get_quality_requirement(None)

        # Assert business logic: fallback values are reasonable
        self.assertEqual(threshold, ConfidenceLevel.MEDIUM.value,
                        "Unknown intent should default to MEDIUM confidence")
        self.assertEqual(ttl, 1800, "Unknown intent should default to 30 minutes TTL")
        self.assertEqual(quality, 0.75, "Unknown intent should default to 0.75 quality")

    def test_edge_case_confidence_values(self):
        """Test escalation logic with edge case confidence values."""
        test_cases = [
            (0.0, IntentType.GENERAL_INQUIRY, True),  # Minimum confidence
            (1.0, IntentType.TCO_ANALYSIS, False),   # Maximum confidence
            (0.5, IntentType.GENERAL_INQUIRY, False), # Exactly at LOW threshold
            (0.7, IntentType.PRICING_INQUIRY, False), # Exactly at MEDIUM threshold
            (0.85, IntentType.TCO_ANALYSIS, False),   # Exactly at HIGH threshold
        ]

        for confidence, intent, expected_escalation in test_cases:
            should_escalate = self.confidence_manager.should_escalate(confidence, intent)
            self.assertEqual(should_escalate, expected_escalation,
                           f"Confidence {confidence} for {intent.value} escalation mismatch")

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()


class TestConfidenceManagerCacheKeyGeneration(SSotAsyncTestCase, unittest.TestCase):
    """Specialized tests for cache key generation edge cases."""

    def setUp(self):
        """Set up test environment for cache key testing."""
        super().setUp()
        self.confidence_manager = ConfidenceManager()

    def test_cache_key_with_empty_context(self):
        """Test cache key generation with empty or null context components."""
        # Create context with minimal data
        empty_state = AgentState()
        empty_state.user_request = ""

        empty_context = ExecutionContext(
            request_id="test_empty",
            state=empty_state,
            user_id="test_user"
        )

        key = self.confidence_manager.generate_cache_key(
            empty_context, IntentType.GENERAL_INQUIRY
        )

        # Should generate valid key even with empty data
        self.assertEqual(len(key), 32)
        self.assertTrue(all(c in '0123456789abcdef' for c in key))

    def test_cache_key_with_special_characters(self):
        """Test cache key generation with special characters in user request."""
        special_chars_state = AgentState()
        special_chars_state.user_request = "Test with: special!@#$%^&*()_+{}|:<>?[]\\;'\",./"

        special_context = ExecutionContext(
            request_id="test_special",
            state=special_chars_state,
            user_id="special_user_123"
        )

        key = self.confidence_manager.generate_cache_key(
            special_context, IntentType.TECHNICAL_QUESTION
        )

        # Should handle special characters gracefully
        self.assertEqual(len(key), 32)
        self.assertTrue(all(c in '0123456789abcdef' for c in key))

    def test_cache_key_hash_distribution(self):
        """Test that cache keys have good distribution (no obvious patterns)."""
        keys = []
        base_request = "Optimize my AI model performance"

        # Generate keys with slight variations
        for i in range(10):
            state = AgentState()
            state.user_request = f"{base_request} {i}"

            context = ExecutionContext(
                request_id=f"test_{i}",
                state=state,
                user_id=f"user_{i}"
            )

            key = self.confidence_manager.generate_cache_key(
                context, IntentType.OPTIMIZATION_ADVICE
            )
            keys.append(key)

        # All keys should be different (good hash distribution)
        unique_keys = set(keys)
        self.assertEqual(len(unique_keys), len(keys),
                        "All generated keys should be unique")

    def tearDown(self):
        """Clean up cache key test environment."""
        super().tearDown()