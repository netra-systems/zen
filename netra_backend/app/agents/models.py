"""Data Helper Agent Models

This module contains models used by the Data Helper Agent to structure
data requests and requirements for AI optimization workflows.

Business Value: Provides structured data collection models that ensure
comprehensive information gathering for accurate optimization strategies.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DataCategory(str, Enum):
    """Categories of data that can be requested for optimization analysis."""
    
    FINANCIAL = "financial"
    PERFORMANCE = "performance"
    USAGE = "usage"
    TECHNICAL = "technical"
    BUSINESS = "business"


class DataPriority(str, Enum):
    """Priority levels for data requests, indicating importance for optimization."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    
    @property
    def value_numeric(self) -> int:
        """Return numeric value for comparison."""
        priority_map = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return priority_map.get(self.value, 0)


class DataRequirement(BaseModel):
    """Represents a specific data requirement identified for optimization."""
    
    category: DataCategory = Field(description="Category of data required")
    field: str = Field(description="Specific field or metric name")
    priority: DataPriority = Field(description="Priority level for this requirement")
    reason: str = Field(description="Explanation of why this data is needed")
    optional: bool = Field(default=False, description="Whether this requirement is optional")


class DataRequest(BaseModel):
    """Represents a structured data request to be presented to users."""
    
    category: DataCategory = Field(description="Category of data being requested")
    priority: DataPriority = Field(description="Priority level of this request")
    questions: List[str] = Field(description="Specific questions to ask the user")
    format: Optional[str] = Field(default=None, description="Preferred format for the response")
    examples: Optional[List[str]] = Field(default=None, description="Example responses to guide the user")
    instructions: Optional[str] = Field(default=None, description="Additional instructions for the user")
    
    # Advanced features used in tests
    phase: Optional[int] = Field(default=1, description="Phase number for progressive collection")
    language_style: Optional[str] = Field(default=None, description="Language style adaptation (e.g., 'technical', 'startup')")
    focus_areas: Optional[List[str]] = Field(default=None, description="Areas of focus for this request")
    acknowledges_previous: Optional[List[str]] = Field(default=None, description="Acknowledgments of previously provided data")
    remaining_items: Optional[int] = Field(default=0, description="Number of remaining items in the collection process")
    
    # Validation features
    validation_criteria: Optional[Dict[str, Any]] = Field(default=None, description="Criteria for validating user responses")
    error_guidance: Optional[Dict[str, str]] = Field(default=None, description="Error messages and guidance for invalid inputs")


class UserExperience(BaseModel):
    """Configuration for user experience customization in data requests."""
    
    user_type: str = Field(description="Type of user (e.g., 'startup', 'enterprise', 'technical')")
    technical_level: str = Field(default="mixed", description="Technical sophistication level")
    preferred_format: str = Field(default="structured", description="Preferred format for data requests")
    max_questions_per_request: int = Field(default=5, description="Maximum questions per request")
    include_examples: bool = Field(default=True, description="Whether to include examples")
    include_explanations: bool = Field(default=True, description="Whether to include explanations of why data is needed")


# Additional models for comprehensive data helper functionality
class DataSufficiencyAssessment(BaseModel):
    """Assessment of whether sufficient data has been collected."""
    
    sufficiency_level: str = Field(description="INSUFFICIENT, PARTIAL, or SUFFICIENT")
    percentage_complete: int = Field(description="Percentage of required data collected")
    can_proceed: bool = Field(description="Whether optimization can proceed with current data")
    missing_requirements: List[DataRequirement] = Field(default_factory=list, description="Still missing requirements")
    optimization_quality: Dict[str, str] = Field(default_factory=dict, description="Expected optimization quality levels")
    value_of_additional_data: Optional[str] = Field(default=None, description="Value proposition for collecting more data")


class DataAlternative(BaseModel):
    """Alternative approach when primary data cannot be obtained."""
    
    approach: str = Field(description="Description of the alternative approach")
    questions: Optional[List[str]] = Field(default=None, description="Alternative questions to ask")
    action: Optional[str] = Field(default=None, description="Action to take instead")
    timeline: Optional[str] = Field(default=None, description="Timeline for this alternative")
    confidence_impact: Optional[str] = Field(default=None, description="Impact on confidence levels")


class DataCollectionSession(BaseModel):
    """Represents a complete data collection session state."""
    
    session_id: str = Field(description="Unique identifier for the session")
    data_collected: Dict[str, Any] = Field(default_factory=dict, description="Data that has been collected")
    data_pending: List[str] = Field(default_factory=list, description="Data still needed")
    current_phase: int = Field(default=1, description="Current phase of data collection")
    user_experience: Optional[UserExperience] = Field(default=None, description="User experience configuration")
    sufficiency_assessment: Optional[DataSufficiencyAssessment] = Field(default=None, description="Current sufficiency assessment")


# Models required by multi-agent orchestration tests
class DataSufficiency(str, Enum):
    """Enum representing data sufficiency levels for workflow decisions."""
    INSUFFICIENT = "insufficient"
    PARTIAL = "partial"
    SUFFICIENT = "sufficient"


class WorkflowPath(str, Enum):
    """Available workflow paths in the adaptive system."""
    FLOW_A_SUFFICIENT = "flow_a_sufficient"  # Full data, complete pipeline
    FLOW_B_PARTIAL = "flow_b_partial"  # Partial data, modified pipeline
    FLOW_C_INSUFFICIENT = "flow_c_insufficient"  # Minimal data, basic analysis


class AgentState(str, Enum):
    """Agent execution states."""
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_FOR_INPUT = "waiting_for_input"
    COMPLETED = "completed"
    ERROR = "error"


class WorkflowContext(BaseModel):
    """Context maintained throughout a workflow execution."""
    
    thread_id: str = Field(description="Thread identifier")
    turn_id: str = Field(description="Turn identifier")
    workflow_path: WorkflowPath = Field(description="Selected workflow path")
    data_sufficiency: DataSufficiency = Field(description="Data sufficiency level")
    collected_data: Dict[str, Any] = Field(default_factory=dict, description="Data collected during workflow")
    agent_outputs: Dict[str, Any] = Field(default_factory=dict, description="Outputs from each agent")
    current_agent: Optional[str] = Field(default=None, description="Currently executing agent")
    state: AgentState = Field(default=AgentState.IDLE, description="Current workflow state")
    started_at: Optional[datetime] = Field(default=None, description="Workflow start time")
    completed_at: Optional[datetime] = Field(default=None, description="Workflow completion time")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


class FlowTransition(BaseModel):
    """Represents a transition between workflow states or agents."""
    
    from_agent: str = Field(description="Source agent")
    to_agent: str = Field(description="Target agent")
    transition_type: str = Field(description="Type of transition (handoff, escalation, completion)")
    data_passed: Dict[str, Any] = Field(default_factory=dict, description="Data passed in transition")
    timestamp: datetime = Field(default_factory=datetime.now, description="Transition timestamp")
    reason: Optional[str] = Field(default=None, description="Reason for transition")