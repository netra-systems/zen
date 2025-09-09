"""Agent result types module to avoid circular imports."""

from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

# Define result types without circular dependencies
JsonCompatibleDict = Dict[str, Union[str, int, float, bool, None]]
ExecutionResult = Union[JsonCompatibleDict, List[JsonCompatibleDict], str, bool, None]
AgentExecutionResult = ExecutionResult


class TypedAgentResult(BaseModel):
    """Strictly typed agent result."""
    
    success: bool = Field(description="Whether execution was successful")
    result: AgentExecutionResult = Field(description="The actual result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="Result timestamp")
    metadata: Optional[JsonCompatibleDict] = Field(None, description="Additional metadata")
    
    # Additional fields for compatibility with agent_observability usage
    agent_name: Optional[str] = Field(None, description="Name of the agent that produced this result")
    error_message: Optional[str] = Field(None, description="Alias for error field")
    result_data: Optional[AgentExecutionResult] = Field(None, description="Alias for result field")
    metrics: Optional[JsonCompatibleDict] = Field(None, description="Agent execution metrics")