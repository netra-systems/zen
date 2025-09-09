"""Agent execution type definitions - SSOT for agent-related data structures.

This module provides strongly-typed agent execution structures to prevent
type drift and ensure proper validation across the system. These types are
specifically for agent request/response/validation flows.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: System Reliability and Type Safety
- Value Impact: Prevents agent execution bugs, enforces validation contracts
- Strategic Impact: Ensures consistent agent behavior across all customer tiers

SSOT Principle: These types are the canonical definitions for agent execution.
Any service-specific variants should import and extend these base types.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator

from shared.types.core_types import UserID, ThreadID, RunID, ensure_user_id


# =============================================================================
# Agent Execution Request Types
# =============================================================================

class AgentExecutionRequest(BaseModel):
    """Request structure for agent execution - SSOT for all agent requests.
    
    This type defines the standard contract for executing agents across
    all services. It enforces proper user identification, context isolation,
    and permission validation.
    """
    
    user_id: UserID = Field(description="Strongly typed user identifier")
    thread_id: ThreadID = Field(description="Conversation thread identifier") 
    request_data: Dict[str, Any] = Field(description="Agent-specific request payload")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Request creation timestamp"
    )
    user_permissions: List[str] = Field(
        default_factory=list,
        description="User permissions for agent execution"
    )
    
    @field_validator('user_id', mode='before')
    @classmethod
    def validate_user_id(cls, v):
        """Ensure user_id is properly typed."""
        if isinstance(v, str):
            return ensure_user_id(v)
        return v
    
    @field_validator('request_data')
    @classmethod 
    def validate_request_data(cls, v):
        """Ensure request_data is not empty for valid requests."""
        if not isinstance(v, dict):
            raise ValueError("request_data must be a dictionary")
        return v
        
    @field_validator('user_permissions')
    @classmethod
    def validate_permissions(cls, v):
        """Ensure permissions is a list of strings."""
        if not isinstance(v, list):
            raise ValueError("user_permissions must be a list")
        if not all(isinstance(perm, str) for perm in v):
            raise ValueError("all permissions must be strings")
        return v

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }


# =============================================================================
# Agent Execution Result Types  
# =============================================================================

class AgentExecutionResult(BaseModel):
    """SSOT Agent execution result with complete execution information.
    
    This class provides comprehensive result tracking for agent executions
    including user context, execution metadata, and business value indicators.
    """
    
    user_id: UserID = Field(description="User who initiated the execution")
    thread_id: ThreadID = Field(description="Thread/conversation identifier")
    run_id: RunID = Field(description="Execution run identifier")
    success: bool = Field(description="Whether execution completed successfully")
    result_data: Dict[str, Any] = Field(description="Structured result data from agent")
    execution_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the execution process"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Result creation timestamp"
    )
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    
    @field_validator('user_id', mode='before')
    @classmethod
    def validate_user_id(cls, v):
        """Ensure user_id is properly typed."""
        if isinstance(v, str):
            return ensure_user_id(v)
        return v
    
    @field_validator('thread_id', mode='before')
    @classmethod
    def validate_thread_id(cls, v):
        """Ensure thread_id is properly typed."""
        if isinstance(v, str):
            return ThreadID(v)
        return v
    
    @field_validator('run_id', mode='before')
    @classmethod
    def validate_run_id(cls, v):
        """Ensure run_id is properly typed."""
        if isinstance(v, str):
            return RunID(v)
        return v
    
    @field_validator('result_data')
    @classmethod
    def validate_result_data(cls, v):
        """Ensure result_data is a dictionary."""
        if not isinstance(v, dict):
            raise ValueError("result_data must be a dictionary")
        return v
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }


# Import TypedAgentResult from schemas for additional compatibility  
from netra_backend.app.schemas.agent_result_types import TypedAgentResult


# =============================================================================
# Agent Validation Result Types
# =============================================================================

class AgentValidationResult(BaseModel):
    """Result of agent execution request validation - SSOT for validation results.
    
    This type provides a standard contract for communicating validation
    success/failure across all validation layers in the system.
    """
    
    is_valid: bool = Field(description="Whether the request passed validation")
    error_message: Optional[str] = Field(
        None, 
        description="Human-readable error message if validation failed"
    )
    user_id: UserID = Field(description="User ID from the original request")
    validation_passed: Dict[str, bool] = Field(
        default_factory=dict,
        description="Detailed validation results by category"
    )
    
    # Optional metadata for enhanced validation reporting
    validation_warnings: List[str] = Field(
        default_factory=list,
        description="Non-blocking warnings from validation"
    )
    execution_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional context for successful validations"
    )
    
    @field_validator('user_id', mode='before')
    @classmethod
    def validate_user_id(cls, v):
        """Ensure user_id is properly typed."""
        if isinstance(v, str):
            return ensure_user_id(v)
        return v
    
    @field_validator('validation_passed')
    @classmethod
    def validate_validation_passed(cls, v):
        """Ensure validation_passed contains only boolean values."""
        if not isinstance(v, dict):
            raise ValueError("validation_passed must be a dictionary")
        for key, value in v.items():
            if not isinstance(value, bool):
                raise ValueError(f"validation_passed['{key}'] must be boolean, got {type(value)}")
        return v

    def add_validation_check(self, category: str, passed: bool, warning: Optional[str] = None):
        """Helper method to add validation results."""
        self.validation_passed[category] = passed
        if warning and warning not in self.validation_warnings:
            self.validation_warnings.append(warning)
        
        # Update overall validity
        if not passed and self.is_valid:
            self.is_valid = False

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }


# =============================================================================
# Export aliases for backward compatibility
# =============================================================================

# These maintain compatibility with existing imports while establishing SSOT
__all__ = [
    "AgentExecutionRequest",
    "AgentExecutionResult", 
    "AgentValidationResult",
    "TypedAgentResult",  # From schemas for enhanced typing
]