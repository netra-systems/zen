"""
Strict type definitions for agent results.

This module provides strict type definitions for agent results to ensure
type safety and consistency across the agent system.
"""

from typing import Any, Dict, Generic, Optional, TypeVar, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, field_serializer

T = TypeVar('T')
ResultType = TypeVar('ResultType')


class TypedAgentResult(BaseModel, Generic[ResultType]):
    """
    Strictly typed agent result container.
    
    Ensures type safety for agent execution results.
    """
    
    success: bool = Field(description="Whether the operation succeeded")
    result: Optional[ResultType] = Field(default=None, description="The typed result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Result timestamp"
    )
    
    model_config = ConfigDict(
        # Pydantic V2 configuration
        arbitrary_types_allowed=True,
        validate_default=True,
        extra='forbid'
    )
    
    @field_serializer('timestamp')
    def serialize_timestamp(self, dt: datetime) -> str:
        """Serialize datetime to ISO format."""
        return dt.isoformat()
        
    def unwrap(self) -> ResultType:
        """
        Unwrap the result value.
        
        Returns:
            The result value
            
        Raises:
            ValueError: If operation failed or result is None
        """
        if not self.success:
            raise ValueError(f"Cannot unwrap failed result: {self.error}")
        if self.result is None:
            raise ValueError("Cannot unwrap None result")
        return self.result
    
    def unwrap_or(self, default: ResultType) -> ResultType:
        """
        Unwrap the result or return a default value.
        
        Args:
            default: Default value to return if unwrap fails
            
        Returns:
            The result value or default
        """
        try:
            return self.unwrap()
        except ValueError:
            return default
    
    @classmethod
    def ok(cls, result: ResultType, **metadata) -> "TypedAgentResult[ResultType]":
        """
        Create a successful result.
        
        Args:
            result: The result value
            **metadata: Additional metadata
            
        Returns:
            Successful TypedAgentResult
        """
        return cls(
            success=True,
            result=result,
            metadata=metadata
        )
    
    @classmethod
    def fail(cls, error: str, **metadata) -> "TypedAgentResult[ResultType]":
        """
        Create a failed result.
        
        Args:
            error: Error message
            **metadata: Additional metadata
            
        Returns:
            Failed TypedAgentResult
        """
        return cls(
            success=False,
            error=error,
            metadata=metadata
        )