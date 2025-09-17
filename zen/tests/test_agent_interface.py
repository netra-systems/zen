#!/usr/bin/env python3
"""
Tests for Agent Interface Module

Tests the extensible agent interface and ensures proper
integration capabilities for multiple coding agents.
"""

import unittest
import asyncio
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from agent_interface import (
        AgentConfig,
        AgentStatus,
        AgentUsageMetrics,
        BaseCodingAgent,
        ClaudeCodeAgent,
        ContinueAgent,
        AgentFactory
    )
except ImportError as e:
    print(f"Warning: Could not import agent_interface module: {e}")
    AgentConfig = None


class TestAgentConfig(unittest.TestCase):
    """Test AgentConfig class"""

    def setUp(self):
        if AgentConfig is None:
            self.skipTest("Agent interface module not available")

    def test_agent_config_creation(self):
        """Test AgentConfig creation with defaults"""
        config = AgentConfig(
            name="test_agent",
            command="/test_command"
        )

        self.assertEqual(config.name, "test_agent")
        self.assertEqual(config.command, "/test_command")
        self.assertEqual(config.description, "Execute /test_command")
        self.assertEqual(config.output_format, "text")
        self.assertEqual(config.timeout, 300)
        self.assertEqual(config.environment_vars, {})

    def test_agent_config_custom_values(self):
        """Test AgentConfig with custom values"""
        config = AgentConfig(
            name="custom_agent",
            command="/custom_command args",
            description="Custom description",
            allowed_tools=["tool1", "tool2"],
            output_format="json",
            timeout=600,
            environment_vars={"KEY": "value"}
        )

        self.assertEqual(config.name, "custom_agent")
        self.assertEqual(config.command, "/custom_command args")
        self.assertEqual(config.description, "Custom description")
        self.assertEqual(config.allowed_tools, ["tool1", "tool2"])
        self.assertEqual(config.output_format, "json")
        self.assertEqual(config.timeout, 600)
        self.assertEqual(config.environment_vars, {"KEY": "value"})


class TestAgentUsageMetrics(unittest.TestCase):
    """Test AgentUsageMetrics class"""

    def setUp(self):
        if AgentUsageMetrics is None:
            self.skipTest("Agent interface module not available")

    def test_usage_metrics_defaults(self):
        """Test AgentUsageMetrics default values"""
        metrics = AgentUsageMetrics()

        self.assertEqual(metrics.total_tokens, 0)
        self.assertEqual(metrics.input_tokens, 0)
        self.assertEqual(metrics.output_tokens, 0)
        self.assertEqual(metrics.cached_tokens, 0)
        self.assertEqual(metrics.tool_calls, 0)
        self.assertEqual(metrics.api_calls, 0)
        self.assertIsNone(metrics.total_cost_usd)
        self.assertEqual(metrics.model_used, "unknown")
        self.assertEqual(metrics.agent_specific, {})

    def test_usage_metrics_custom_values(self):
        """Test AgentUsageMetrics with custom values"""
        metrics = AgentUsageMetrics(
            total_tokens=1000,
            input_tokens=600,
            output_tokens=400,
            cached_tokens=50,
            tool_calls=5,
            api_calls=2,
            total_cost_usd=0.015,
            model_used="claude-3-5-sonnet",
            agent_specific={"custom_metric": 42}
        )

        self.assertEqual(metrics.total_tokens, 1000)
        self.assertEqual(metrics.input_tokens, 600)
        self.assertEqual(metrics.output_tokens, 400)
        self.assertEqual(metrics.cached_tokens, 50)
        self.assertEqual(metrics.tool_calls, 5)
        self.assertEqual(metrics.api_calls, 2)
        self.assertEqual(metrics.total_cost_usd, 0.015)
        self.assertEqual(metrics.model_used, "claude-3-5-sonnet")
        self.assertEqual(metrics.agent_specific, {"custom_metric": 42})


class TestAgentStatus(unittest.TestCase):
    """Test AgentStatus class"""

    def setUp(self):
        if AgentStatus is None:
            self.skipTest("Agent interface module not available")

    def test_agent_status_defaults(self):
        """Test AgentStatus default values"""
        status = AgentStatus(name="test_agent")

        self.assertEqual(status.name, "test_agent")
        self.assertEqual(status.status, "pending")
        self.assertIsNone(status.start_time)
        self.assertIsNone(status.end_time)
        self.assertIsNone(status.pid)
        self.assertEqual(status.output, "")
        self.assertEqual(status.error, "")
        self.assertIsInstance(status.metrics, AgentUsageMetrics)


class MockAgent(BaseCodingAgent):
    """Mock agent for testing base functionality"""

    def build_command(self):
        return ["echo", "test"]

    async def execute(self):
        self.status.status = "completed"
        return True

    def parse_output_line(self, line):
        return True

    def calculate_cost(self):
        return 0.01

    def supports_feature(self, feature):
        return feature == "test_feature"


class TestBaseCodingAgent(unittest.TestCase):
    """Test BaseCodingAgent abstract class"""

    def setUp(self):
        if BaseCodingAgent is None:
            self.skipTest("Agent interface module not available")

        self.config = AgentConfig(name="test_agent", command="test")
        self.agent = MockAgent(self.config)

    def test_agent_initialization(self):
        """Test agent initialization"""
        self.assertEqual(self.agent.config.name, "test_agent")
        self.assertEqual(self.agent.status.name, "test_agent")
        self.assertEqual(self.agent.status.status, "pending")

    def test_agent_type_detection(self):
        """Test agent type detection"""
        agent_type = self.agent.get_agent_type()
        self.assertEqual(agent_type, "mock")

    def test_get_metrics(self):
        """Test getting metrics"""
        metrics = self.agent.get_metrics()
        self.assertIsInstance(metrics, AgentUsageMetrics)

    def test_get_status(self):
        """Test getting status"""
        status = self.agent.get_status()
        self.assertIsInstance(status, AgentStatus)

    def test_supports_feature(self):
        """Test feature support checking"""
        self.assertTrue(self.agent.supports_feature("test_feature"))
        self.assertFalse(self.agent.supports_feature("unsupported_feature"))


class TestClaudeCodeAgent(unittest.TestCase):
    """Test ClaudeCodeAgent implementation"""

    def setUp(self):
        if ClaudeCodeAgent is None:
            self.skipTest("Agent interface module not available")

        self.config = AgentConfig(
            name="claude_agent",
            command="/test_command",
            output_format="json",
            allowed_tools=["tool1", "tool2"],
            session_id="test_session"
        )
        self.agent = ClaudeCodeAgent(self.config)

    def test_build_command(self):
        """Test Claude Code command building"""
        cmd = self.agent.build_command()

        expected = [
            "claude", "-p", "/test_command",
            "--output-format=json",
            "--allowedTools=tool1,tool2",
            "--session-id", "test_session"
        ]

        self.assertEqual(cmd, expected)

    def test_build_command_minimal(self):
        """Test Claude Code command building with minimal config"""
        config = AgentConfig(name="minimal", command="/basic")
        agent = ClaudeCodeAgent(config)
        cmd = agent.build_command()

        expected = ["claude", "-p", "/basic"]
        self.assertEqual(cmd, expected)

    def test_parse_output_line_valid_json(self):
        """Test parsing valid Claude Code JSON output"""
        json_line = '{"usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}}'

        result = self.agent.parse_output_line(json_line)

        self.assertTrue(result)
        self.assertEqual(self.agent.status.metrics.input_tokens, 100)
        self.assertEqual(self.agent.status.metrics.output_tokens, 50)
        self.assertEqual(self.agent.status.metrics.total_tokens, 150)

    def test_parse_output_line_invalid_json(self):
        """Test parsing invalid JSON output"""
        invalid_line = "not json output"

        result = self.agent.parse_output_line(invalid_line)

        self.assertFalse(result)

    def test_calculate_cost(self):
        """Test cost calculation"""
        # Set some metrics
        self.agent.status.metrics.input_tokens = 1000
        self.agent.status.metrics.output_tokens = 500

        cost = self.agent.calculate_cost()

        # Should use fallback calculation
        expected = (1000 / 1_000_000) * 3.00 + (500 / 1_000_000) * 15.00
        self.assertAlmostEqual(cost, expected, places=6)

    def test_calculate_cost_with_authoritative(self):
        """Test cost calculation with authoritative cost"""
        self.agent.status.metrics.total_cost_usd = 0.12345

        cost = self.agent.calculate_cost()

        self.assertEqual(cost, 0.12345)

    def test_supports_feature(self):
        """Test Claude Code feature support"""
        supported_features = ['streaming', 'json_output', 'tools', 'sessions', 'real_time_metrics']

        for feature in supported_features:
            self.assertTrue(self.agent.supports_feature(feature))

        self.assertFalse(self.agent.supports_feature("unsupported_feature"))


class TestContinueAgent(unittest.TestCase):
    """Test ContinueAgent implementation"""

    def setUp(self):
        if ContinueAgent is None:
            self.skipTest("Agent interface module not available")

        self.config = AgentConfig(name="continue_agent", command="test_command")
        self.agent = ContinueAgent(self.config)

    def test_build_command(self):
        """Test Continue agent command building"""
        cmd = self.agent.build_command()
        expected = ["continue", "test_command"]
        self.assertEqual(cmd, expected)

    def test_calculate_cost(self):
        """Test Continue agent cost calculation"""
        cost = self.agent.calculate_cost()
        self.assertEqual(cost, 0.0)  # Continue.dev may have different pricing

    def test_supports_feature(self):
        """Test Continue agent feature support"""
        supported_features = ['autocomplete', 'chat', 'refactoring']

        for feature in supported_features:
            self.assertTrue(self.agent.supports_feature(feature))

        self.assertFalse(self.agent.supports_feature("unsupported_feature"))


class TestAgentFactory(unittest.TestCase):
    """Test AgentFactory"""

    def setUp(self):
        if AgentFactory is None:
            self.skipTest("Agent interface module not available")

    def test_create_claude_agent(self):
        """Test creating Claude agent via factory"""
        config = AgentConfig(name="test", command="/test")
        agent = AgentFactory.create_agent("claude", config)

        self.assertIsInstance(agent, ClaudeCodeAgent)
        self.assertEqual(agent.config.name, "test")

    def test_create_continue_agent(self):
        """Test creating Continue agent via factory"""
        config = AgentConfig(name="test", command="test")
        agent = AgentFactory.create_agent("continue", config)

        self.assertIsInstance(agent, ContinueAgent)
        self.assertEqual(agent.config.name, "test")

    def test_create_unsupported_agent(self):
        """Test creating unsupported agent type"""
        config = AgentConfig(name="test", command="test")

        with self.assertRaises(ValueError) as context:
            AgentFactory.create_agent("unsupported", config)

        self.assertIn("Unsupported agent type", str(context.exception))

    def test_get_supported_agents(self):
        """Test getting supported agent types"""
        supported = AgentFactory.get_supported_agents()

        self.assertIn("claude", supported)
        self.assertIn("continue", supported)

    def test_register_agent(self):
        """Test registering new agent type"""
        class TestAgent(BaseCodingAgent):
            def build_command(self):
                return ["test"]

            async def execute(self):
                return True

            def parse_output_line(self, line):
                return True

            def calculate_cost(self):
                return 0.0

        AgentFactory.register_agent("test", TestAgent)

        self.assertIn("test", AgentFactory.get_supported_agents())

        config = AgentConfig(name="test", command="test")
        agent = AgentFactory.create_agent("test", config)
        self.assertIsInstance(agent, TestAgent)

    def test_register_invalid_agent(self):
        """Test registering invalid agent class"""
        class InvalidAgent:
            pass

        with self.assertRaises(ValueError) as context:
            AgentFactory.register_agent("invalid", InvalidAgent)

        self.assertIn("must inherit from BaseCodingAgent", str(context.exception))


if __name__ == '__main__':
    unittest.main()