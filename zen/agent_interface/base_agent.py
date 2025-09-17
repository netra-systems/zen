#!/usr/bin/env python3
"""
Base Agent Interface for Extensible Coding Agent Support

This module provides the foundation for supporting multiple coding agents
beyond Claude Code, enabling zen to orchestrate various AI coding assistants.

Design Goals:
- Simple interface for easy integration
- Consistent token/cost tracking across agents
- Minimal overhead for basic agents
- Extensible for complex agent features
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, AsyncIterator
from pathlib import Path
import subprocess
import asyncio


@dataclass
class AgentConfig:
    """Configuration for any coding agent"""
    name: str
    command: str
    description: Optional[str] = None
    allowed_tools: List[str] = None
    output_format: str = "text"
    workspace_dir: Optional[Path] = None
    session_id: Optional[str] = None
    environment_vars: Dict[str, str] = None
    timeout: int = 300

    def __post_init__(self):
        if self.description is None:
            self.description = f"Execute {self.command}"
        if self.environment_vars is None:
            self.environment_vars = {}


@dataclass
class AgentUsageMetrics:
    """Standardized usage metrics across all agents"""
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    tool_calls: int = 0
    api_calls: int = 0
    total_cost_usd: Optional[float] = None
    model_used: str = "unknown"

    # Agent-specific metrics (extensible)
    agent_specific: Dict[str, Any] = None

    def __post_init__(self):
        if self.agent_specific is None:
            self.agent_specific = {}


@dataclass
class AgentStatus:
    """Execution status for any coding agent"""
    name: str
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    pid: Optional[int] = None
    output: str = ""
    error: str = ""
    metrics: AgentUsageMetrics = None

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = AgentUsageMetrics()


class BaseCodingAgent(ABC):
    """
    Abstract base class for all coding agents.

    Provides the interface that all coding agents must implement
    to be compatible with the zen orchestrator.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.status = AgentStatus(name=config.name)

    @abstractmethod
    def build_command(self) -> List[str]:
        """
        Build the command line arguments for executing this agent.

        Returns:
            List of command line arguments
        """
        pass

    @abstractmethod
    async def execute(self) -> bool:
        """
        Execute the agent and return success status.

        Returns:
            True if execution was successful, False otherwise
        """
        pass

    @abstractmethod
    def parse_output_line(self, line: str) -> bool:
        """
        Parse a single line of output to extract metrics.

        Args:
            line: Single line from agent output

        Returns:
            True if line was parsed successfully, False otherwise
        """
        pass

    @abstractmethod
    def calculate_cost(self) -> float:
        """
        Calculate the total cost for this agent's execution.

        Returns:
            Total cost in USD
        """
        pass

    def get_agent_type(self) -> str:
        """Return the type identifier for this agent"""
        return self.__class__.__name__.lower().replace('agent', '')

    def get_metrics(self) -> AgentUsageMetrics:
        """Get current usage metrics"""
        return self.status.metrics

    def get_status(self) -> AgentStatus:
        """Get current execution status"""
        return self.status

    def supports_feature(self, feature: str) -> bool:
        """Check if agent supports a specific feature"""
        # Override in subclasses to declare supported features
        return False


class ClaudeCodeAgent(BaseCodingAgent):
    """
    Claude Code agent implementation.

    Provides compatibility with the existing Claude Code orchestrator
    through the new agent interface.
    """

    def build_command(self) -> List[str]:
        """Build Claude Code command"""
        # Use existing logic from ClaudeInstanceOrchestrator.build_claude_command
        cmd = ["claude", "-p", self.config.command]

        if self.config.output_format and self.config.output_format != "text":
            cmd.append(f"--output-format={self.config.output_format}")

        if self.config.allowed_tools:
            cmd.append(f"--allowedTools={','.join(self.config.allowed_tools)}")

        if self.config.session_id:
            cmd.extend(["--session-id", self.config.session_id])

        return cmd

    async def execute(self) -> bool:
        """Execute Claude Code with async process handling"""
        try:
            cmd = self.build_command()
            self.status.start_time = asyncio.get_event_loop().time()
            self.status.status = "running"

            # Create async process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.workspace_dir
            )

            self.status.pid = process.pid

            # Stream output and parse in real-time
            async def read_stream(stream, is_stdout=True):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    line_str = line.decode().strip()

                    if is_stdout:
                        self.status.output += line_str + "\n"
                        self.parse_output_line(line_str)
                    else:
                        self.status.error += line_str + "\n"

            # Read both streams concurrently
            await asyncio.gather(
                read_stream(process.stdout, True),
                read_stream(process.stderr, False),
                return_exceptions=True
            )

            # Wait for process completion
            returncode = await process.wait()
            self.status.end_time = asyncio.get_event_loop().time()

            if returncode == 0:
                self.status.status = "completed"
                return True
            else:
                self.status.status = "failed"
                return False

        except Exception as e:
            self.status.status = "failed"
            self.status.error = str(e)
            return False

    def parse_output_line(self, line: str) -> bool:
        """Parse Claude Code JSON output"""
        # Use existing logic from ClaudeInstanceOrchestrator._parse_token_usage
        try:
            import json
            if line.startswith('{'):
                data = json.loads(line)
                if 'usage' in data:
                    usage = data['usage']
                    self.status.metrics.input_tokens = max(
                        self.status.metrics.input_tokens,
                        int(usage.get('input_tokens', 0))
                    )
                    self.status.metrics.output_tokens = max(
                        self.status.metrics.output_tokens,
                        int(usage.get('output_tokens', 0))
                    )
                    self.status.metrics.total_tokens = max(
                        self.status.metrics.total_tokens,
                        int(usage.get('total_tokens', 0))
                    )
                    return True
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
        return False

    def calculate_cost(self) -> float:
        """Calculate cost using Claude pricing"""
        # Use existing logic or new pricing engine
        if self.status.metrics.total_cost_usd is not None:
            return self.status.metrics.total_cost_usd

        # Fallback calculation
        input_cost = (self.status.metrics.input_tokens / 1_000_000) * 3.00
        output_cost = (self.status.metrics.output_tokens / 1_000_000) * 15.00
        return input_cost + output_cost

    def supports_feature(self, feature: str) -> bool:
        """Claude Code supported features"""
        supported = ['streaming', 'json_output', 'tools', 'sessions', 'real_time_metrics']
        return feature in supported


# Example of another agent implementation
class ContinueAgent(BaseCodingAgent):
    """
    Example implementation for Continue.dev agent.

    This demonstrates how to add support for other coding agents.
    """

    def build_command(self) -> List[str]:
        """Build Continue.dev command"""
        return ["continue", self.config.command]

    async def execute(self) -> bool:
        """Execute Continue.dev agent"""
        # Placeholder implementation
        # Real implementation would integrate with Continue.dev API
        self.status.status = "completed"
        return True

    def parse_output_line(self, line: str) -> bool:
        """Parse Continue.dev output"""
        # Placeholder - implement Continue.dev specific parsing
        return False

    def calculate_cost(self) -> float:
        """Calculate Continue.dev costs"""
        # Continue.dev may have different pricing model
        return 0.0

    def supports_feature(self, feature: str) -> bool:
        """Continue.dev supported features"""
        supported = ['autocomplete', 'chat', 'refactoring']
        return feature in supported


# Agent factory for easy creation
class AgentFactory:
    """Factory for creating appropriate agent instances"""

    _agent_types = {
        'claude': ClaudeCodeAgent,
        'continue': ContinueAgent,
        # Add more agents here as they're implemented
    }

    @classmethod
    def create_agent(cls, agent_type: str, config: AgentConfig) -> BaseCodingAgent:
        """
        Create an agent instance of the specified type.

        Args:
            agent_type: Type of agent to create (e.g., 'claude', 'continue')
            config: Agent configuration

        Returns:
            Agent instance

        Raises:
            ValueError: If agent type is not supported
        """
        if agent_type not in cls._agent_types:
            raise ValueError(f"Unsupported agent type: {agent_type}. "
                           f"Supported types: {list(cls._agent_types.keys())}")

        agent_class = cls._agent_types[agent_type]
        return agent_class(config)

    @classmethod
    def get_supported_agents(cls) -> List[str]:
        """Get list of supported agent types"""
        return list(cls._agent_types.keys())

    @classmethod
    def register_agent(cls, agent_type: str, agent_class: type):
        """Register a new agent type"""
        if not issubclass(agent_class, BaseCodingAgent):
            raise ValueError("Agent class must inherit from BaseCodingAgent")
        cls._agent_types[agent_type] = agent_class