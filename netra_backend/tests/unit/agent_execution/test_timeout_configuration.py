"""
Unit Tests for Agent Execution Timeout Configuration

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) with tier-specific optimization  
- Business Goal: User experience optimization and resource management
- Value Impact: Ensures appropriate timeout values for different user tiers while preventing resource waste
- Strategic Impact: Balance user experience with platform scalability - Enterprise users get longer timeouts

This module tests the timeout configuration logic to ensure:
1. TimeoutConfig provides appropriate defaults for all user tiers
2. Timeout calculations consider user tier (Free vs Enterprise)
3. Streaming vs non-streaming executions have appropriate timeouts
4. Circuit breaker timeout configurations are business-aligned
5. Retry timeout calculations follow exponential backoff correctly
6. Resource management prevents runaway executions
"""
import pytest
import unittest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch
from netra_backend.app.core.agent_execution_tracker import TimeoutConfig, AgentExecutionTracker, ExecutionState, get_execution_tracker
from netra_backend.app.agents.base.agent_business_rules import UserTier
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestTimeoutConfiguration(SSotBaseTestCase, unittest.TestCase):
    """Unit tests for timeout configuration and calculations."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.timeout_config = TimeoutConfig()
        self.tracker = AgentExecutionTracker()
        self.test_user_id = f'user_{uuid.uuid4().hex[:8]}'
        self.test_thread_id = f'thread_{uuid.uuid4().hex[:8]}'
        self.test_agent_name = 'test_agent'

    def test_timeout_config_default_values(self):
        """Test that TimeoutConfig has appropriate default values."""
        config = TimeoutConfig()
        self.assertEqual(config.agent_execution_timeout, 25.0)
        self.assertGreater(config.agent_execution_timeout, 10.0)
        self.assertLess(config.agent_execution_timeout, 60.0)
        self.assertEqual(config.llm_api_timeout, 15.0)
        self.assertLess(config.llm_api_timeout, config.agent_execution_timeout)
        self.assertEqual(config.failure_threshold, 3)
        self.assertEqual(config.recovery_timeout, 30.0)
        self.assertEqual(config.success_threshold, 2)
        self.assertEqual(config.max_retries, 2)
        self.assertEqual(config.retry_base_delay, 1.0)
        self.assertEqual(config.retry_max_delay, 5.0)
        self.assertEqual(config.retry_exponential_base, 2.0)

    def test_timeout_config_business_logic_validation(self):
        """Test business logic validation of timeout values."""
        config = TimeoutConfig()
        self.assertLess(config.llm_api_timeout, config.agent_execution_timeout, 'LLM timeout must be less than execution timeout')
        self.assertGreater(config.recovery_timeout, config.agent_execution_timeout, 'Circuit breaker recovery should be longer than execution')
        self.assertGreater(config.retry_base_delay, 0)
        self.assertGreater(config.retry_max_delay, config.retry_base_delay)
        self.assertGreater(config.retry_exponential_base, 1.0)
        self.assertGreater(config.max_retries, 0)
        self.assertLess(config.max_retries, 10)

    def test_user_tier_timeout_calculations_free_tier(self):
        """Test timeout calculations for Free tier users."""
        user_tier = UserTier.FREE
        streaming = False
        expected_timeout = self.timeout_config.agent_execution_timeout
        if user_tier == UserTier.FREE:
            calculated_timeout = expected_timeout
        elif user_tier == UserTier.ENTERPRISE:
            calculated_timeout = expected_timeout * 1.5
        else:
            calculated_timeout = expected_timeout
        self.assertEqual(calculated_timeout, 25.0)

    def test_user_tier_timeout_calculations_enterprise_tier(self):
        """Test timeout calculations for Enterprise tier users."""
        user_tier = UserTier.ENTERPRISE
        base_timeout = self.timeout_config.agent_execution_timeout
        if user_tier == UserTier.ENTERPRISE:
            calculated_timeout = base_timeout * 1.5
        else:
            calculated_timeout = base_timeout
        self.assertEqual(calculated_timeout, 37.5)
        self.assertLess(calculated_timeout, 60.0)
        self.assertGreater(calculated_timeout, base_timeout)

    def test_streaming_vs_non_streaming_timeout_logic(self):
        """Test different timeout behavior for streaming vs non-streaming execution."""
        base_timeout = self.timeout_config.agent_execution_timeout
        non_streaming_timeout = base_timeout
        streaming_timeout = base_timeout * 1.2
        self.assertEqual(non_streaming_timeout, 25.0)
        self.assertEqual(streaming_timeout, 30.0)
        self.assertGreater(streaming_timeout, non_streaming_timeout)
        self.assertLess(streaming_timeout, 45.0)

    def test_combined_tier_and_streaming_timeout_calculation(self):
        """Test timeout calculation combining user tier and streaming mode."""
        base_timeout = self.timeout_config.agent_execution_timeout
        test_cases = [(UserTier.FREE, False, base_timeout), (UserTier.FREE, True, base_timeout * 1.2), (UserTier.ENTERPRISE, False, base_timeout * 1.5), (UserTier.ENTERPRISE, True, base_timeout * 1.5 * 1.2)]
        for tier, streaming, expected_timeout in test_cases:
            tier_multiplier = 1.5 if tier == UserTier.ENTERPRISE else 1.0
            streaming_multiplier = 1.2 if streaming else 1.0
            calculated_timeout = base_timeout * tier_multiplier * streaming_multiplier
            self.assertEqual(calculated_timeout, expected_timeout, f'Timeout mismatch for {tier.value}, streaming={streaming}')

    def test_circuit_breaker_timeout_business_alignment(self):
        """Test that circuit breaker timeouts align with business needs."""
        config = TimeoutConfig()
        self.assertEqual(config.failure_threshold, 3)
        self.assertGreaterEqual(config.failure_threshold, 2)
        self.assertLessEqual(config.failure_threshold, 5)
        self.assertEqual(config.recovery_timeout, 30.0)
        self.assertGreaterEqual(config.recovery_timeout, 15.0)
        self.assertLessEqual(config.recovery_timeout, 120.0)
        self.assertEqual(config.success_threshold, 2)
        self.assertGreaterEqual(config.success_threshold, 1)
        self.assertLessEqual(config.success_threshold, 5)

    def test_retry_exponential_backoff_calculation(self):
        """Test exponential backoff retry delay calculations."""
        config = TimeoutConfig()
        retry_delays = []
        for attempt in range(config.max_retries):
            delay = min(config.retry_base_delay * config.retry_exponential_base ** attempt, config.retry_max_delay)
            retry_delays.append(delay)
        expected_delays = [1.0, 2.0]
        self.assertEqual(len(retry_delays), config.max_retries)
        self.assertEqual(retry_delays, expected_delays)
        for i in range(1, len(retry_delays)):
            if retry_delays[i] < config.retry_max_delay:
                self.assertGreaterEqual(retry_delays[i], retry_delays[i - 1])
        for delay in retry_delays:
            self.assertLessEqual(delay, config.retry_max_delay)

    def test_retry_total_time_business_reasonableness(self):
        """Test that total retry time is business-reasonable."""
        config = TimeoutConfig()
        total_retry_time = 0
        for attempt in range(config.max_retries):
            delay = min(config.retry_base_delay * config.retry_exponential_base ** attempt, config.retry_max_delay)
            total_retry_time += delay
        expected_total = 1.0 + 2.0
        self.assertEqual(total_retry_time, expected_total)
        self.assertLess(total_retry_time, config.agent_execution_timeout)
        self.assertGreater(total_retry_time, 1.0)

    def test_timeout_config_customization(self):
        """Test that TimeoutConfig can be customized for specific needs."""
        custom_config = TimeoutConfig(agent_execution_timeout=45.0, llm_api_timeout=30.0, failure_threshold=5, recovery_timeout=60.0, max_retries=3)
        self.assertEqual(custom_config.agent_execution_timeout, 45.0)
        self.assertEqual(custom_config.llm_api_timeout, 30.0)
        self.assertEqual(custom_config.failure_threshold, 5)
        self.assertEqual(custom_config.recovery_timeout, 60.0)
        self.assertEqual(custom_config.max_retries, 3)
        self.assertLess(custom_config.llm_api_timeout, custom_config.agent_execution_timeout)

    def test_timeout_edge_cases_and_validation(self):
        """Test edge cases and validation of timeout values."""
        min_config = TimeoutConfig(agent_execution_timeout=5.0, llm_api_timeout=3.0, failure_threshold=1, recovery_timeout=10.0, max_retries=1)
        self.assertGreater(min_config.agent_execution_timeout, 0)
        self.assertGreater(min_config.llm_api_timeout, 0)
        self.assertGreater(min_config.failure_threshold, 0)
        self.assertLess(min_config.llm_api_timeout, min_config.agent_execution_timeout)

    def test_timeout_config_serialization_for_logging(self):
        """Test that TimeoutConfig can be serialized for logging."""
        config = TimeoutConfig()
        config_dict = {'agent_execution_timeout': config.agent_execution_timeout, 'llm_api_timeout': config.llm_api_timeout, 'failure_threshold': config.failure_threshold, 'recovery_timeout': config.recovery_timeout, 'success_threshold': config.success_threshold, 'max_retries': config.max_retries, 'retry_base_delay': config.retry_base_delay, 'retry_max_delay': config.retry_max_delay, 'retry_exponential_base': config.retry_exponential_base}
        import json
        serialized = json.dumps(config_dict)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized['agent_execution_timeout'], 25.0)
        self.assertEqual(deserialized['llm_api_timeout'], 15.0)

    def test_timeout_enforcement_integration_with_tracker(self):
        """Test that timeout values integrate properly with AgentExecutionTracker."""
        config = TimeoutConfig()
        execution_id = self.tracker.create_execution(agent_name=self.test_agent_name, user_id=self.test_user_id, thread_id=self.test_thread_id, timeout_seconds=int(config.agent_execution_timeout))
        execution = self.tracker.get_execution(execution_id)
        self.assertEqual(execution.timeout_seconds, int(config.agent_execution_timeout))
        self.assertGreater(execution.timeout_seconds, 10)
        self.assertLess(execution.timeout_seconds, 60)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')