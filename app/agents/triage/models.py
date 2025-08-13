# Triage Models Module - Type-safe Pydantic models for triage operations
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator

class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Complexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"

class KeyParameters(BaseModel):
    workload_type: Optional[str] = None
    optimization_focus: Optional[str] = None
    time_sensitivity: Optional[str] = None
    scope: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)

class ExtractedEntities(BaseModel):
    models_mentioned: List[str] = Field(default_factory=list)
    metrics_mentioned: List[str] = Field(default_factory=list)
    time_ranges: List[Dict[str, Any]] = Field(default_factory=list)
    thresholds: List[Dict[str, Any]] = Field(default_factory=list)
    targets: List[Dict[str, Any]] = Field(default_factory=list)

class UserIntent(BaseModel):
    primary_intent: str
    secondary_intents: List[str] = Field(default_factory=list)
    action_required: bool = True

class SuggestedWorkflow(BaseModel):
    next_agent: str
    required_data_sources: List[str] = Field(default_factory=list)
    estimated_duration_ms: int = 1000

class ToolRecommendation(BaseModel):
    tool_name: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    parameters: Dict[str, Any] = Field(default_factory=dict)

class ValidationStatus(BaseModel):
    is_valid: bool = True
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class TriageMetadata(BaseModel):
    triage_duration_ms: int
    llm_tokens_used: int = 0
    cache_hit: bool = False
    fallback_used: bool = False
    retry_count: int = 0

class TriageResult(BaseModel):
    """Enhanced triage result with comprehensive categorization and metadata."""
    category: str
    secondary_categories: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.8)
    priority: Priority = Priority.MEDIUM
    complexity: Complexity = Complexity.MODERATE
    key_parameters: KeyParameters = Field(default_factory=KeyParameters)
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    user_intent: UserIntent = Field(default_factory=lambda: UserIntent(primary_intent="analyze"))
    suggested_workflow: SuggestedWorkflow = Field(default_factory=lambda: SuggestedWorkflow(next_agent="DataSubAgent"))
    tool_recommendations: List[ToolRecommendation] = Field(default_factory=list)
    validation_status: ValidationStatus = Field(default_factory=ValidationStatus)
    metadata: Optional[TriageMetadata] = None
    is_admin_mode: bool = False
    require_approval: bool = False
    
    @field_validator('confidence_score')
    def validate_confidence(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError('Confidence score must be between 0 and 1')
        return v