"""
NetraOptimizer Database Models

Pydantic models that mirror our database schema for type safety and validation.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator


class ExecutionRecord(BaseModel):
    """
    Mirrors the command_executions database table.
    This is our single source of truth for all performance data.
    """

    # Identity
    id: UUID = Field(default_factory=uuid4, description="Unique execution identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Execution start time")
    batch_id: Optional[UUID] = Field(default=None, description="Groups commands in same batch")
    execution_sequence: Optional[int] = Field(default=None, description="Order within batch")

    # Command Information
    command_raw: str = Field(..., description="Complete unmodified command string")
    command_base: str = Field(..., description="Base command without arguments")
    command_args: Optional[Dict[str, Any]] = Field(default=None, description="Structured command arguments")
    command_features: Optional[Dict[str, Any]] = Field(default=None, description="Extracted semantic features")

    # Context
    workspace_context: Optional[Dict[str, Any]] = Field(default=None, description="Workspace state at execution")
    session_context: Optional[Dict[str, Any]] = Field(default=None, description="Session state and history")

    # Token Metrics
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    input_tokens: int = Field(default=0, description="Input/prompt tokens")
    output_tokens: int = Field(default=0, description="Generated output tokens")
    cached_tokens: int = Field(default=0, description="Tokens served from cache")
    fresh_tokens: int = Field(default=0, description="Non-cached tokens")
    cache_hit_rate: float = Field(default=0.0, description="Percentage of cached tokens")

    # Performance Metrics
    execution_time_ms: int = Field(default=0, description="Total execution duration in milliseconds")
    tool_calls: int = Field(default=0, description="Number of tool invocations")
    status: str = Field(default="pending", description="Execution status: pending/completed/failed/timeout")
    error_message: Optional[str] = Field(default=None, description="Error details if failed")

    # Cost Metrics
    cost_usd: float = Field(default=0.0, description="Calculated execution cost in USD")
    fresh_cost_usd: float = Field(default=0.0, description="Cost of non-cached tokens only")
    cache_savings_usd: float = Field(default=0.0, description="Estimated savings from cache")

    # Output Characteristics
    output_characteristics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Analysis of command output and results"
    )

    # Model Configuration
    model_version: str = Field(default="claude-code", description="Claude model version used")

    @field_validator('cache_hit_rate')
    def validate_cache_hit_rate(cls, v):
        """Ensure cache hit rate is between 0 and 100."""
        return max(0.0, min(100.0, v))

    @field_validator('status')
    def validate_status(cls, v):
        """Ensure status is one of the allowed values."""
        allowed = {'pending', 'completed', 'failed', 'timeout'}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v

    def calculate_derived_metrics(self) -> None:
        """Calculate derived metrics from raw data."""
        # Calculate fresh tokens
        self.fresh_tokens = self.total_tokens - self.cached_tokens

        # Calculate cache hit rate
        if self.total_tokens > 0:
            self.cache_hit_rate = (self.cached_tokens / self.total_tokens) * 100

        # Calculate costs (Claude pricing approximation)
        INPUT_COST_PER_1K = 0.015  # $15 per million
        OUTPUT_COST_PER_1K = 0.075  # $75 per million

        input_cost = (self.input_tokens / 1000) * INPUT_COST_PER_1K
        output_cost = (self.output_tokens / 1000) * OUTPUT_COST_PER_1K
        self.fresh_cost_usd = round(input_cost + output_cost, 6)

        # Calculate total cost (assuming cached tokens are free)
        self.cost_usd = self.fresh_cost_usd

        # Calculate cache savings
        if self.cached_tokens > 0:
            cached_input_cost = (self.cached_tokens / 1000) * INPUT_COST_PER_1K
            self.cache_savings_usd = round(cached_input_cost, 6)


class CommandPattern(BaseModel):
    """
    Represents learned patterns for command types.
    Used for predictions and optimization recommendations.
    """

    id: int = Field(default=0, description="Pattern identifier")
    pattern_signature: str = Field(..., description="Normalized command pattern")
    command_base: str = Field(..., description="Base command this pattern applies to")

    # Statistics
    statistics_30d: Dict[str, Any] = Field(default_factory=dict, description="30-day rolling statistics")
    token_drivers: Dict[str, Any] = Field(default_factory=dict, description="Factors influencing token usage")
    cache_patterns: Dict[str, Any] = Field(default_factory=dict, description="Caching behavior patterns")

    # Optimization
    optimization_insights: Dict[str, Any] = Field(default_factory=dict, description="Learned optimizations")
    failure_patterns: Dict[str, Any] = Field(default_factory=dict, description="Common failure modes")

    # Metadata
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sample_size: int = Field(default=0, description="Number of executions analyzed")