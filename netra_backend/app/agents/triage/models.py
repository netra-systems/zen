"""Models for Triage Agent

This module contains the data models used by the triage agent system.
Separated from the main agent to avoid circular imports.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Priority(str, Enum):
    """Request priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Complexity(str, Enum):
    """Request complexity levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ExtractedEntities:
    """Entities extracted from user request"""
    models: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)
    time_ranges: List[str] = field(default_factory=list)
    thresholds: List[float] = field(default_factory=list)
    targets: List[float] = field(default_factory=list)
    providers: List[str] = field(default_factory=list)
    regions: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    raw_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserIntent:
    """User intent analysis results"""
    primary_intent: str = "unknown"
    secondary_intents: List[str] = field(default_factory=list)
    action_required: bool = False
    confidence: float = 0.0


@dataclass
class ToolRecommendation:
    """Recommended tools for the request"""
    primary_tools: List[str] = field(default_factory=list)
    secondary_tools: List[str] = field(default_factory=list)
    tool_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class KeyParameters:
    """Key parameters extracted from user request"""
    workload_type: Optional[str] = None
    optimization_targets: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    priority_level: Optional[str] = None
    time_sensitivity: Optional[str] = None
    cost_constraints: Optional[float] = None


@dataclass
class SuggestedWorkflow:
    """Suggested workflow for the request"""
    next_agent: str = ""
    workflow_steps: List[str] = field(default_factory=list)
    parallel_execution: bool = False
    estimated_duration: Optional[str] = None


@dataclass
class TriageMetadata:
    """Metadata for triage operations"""
    triage_duration_ms: float = 0.0
    cache_hit: bool = False
    fallback_used: bool = False
    retry_count: int = 0
    model_used: Optional[str] = None
    processing_steps: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TriageResult:
    """Complete triage result with metadata"""
    category: str = "General Request"
    sub_category: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    complexity: Complexity = Complexity.MEDIUM
    confidence_score: float = 0.5
    data_sufficiency: str = "unknown"
    extracted_entities: ExtractedEntities = field(default_factory=ExtractedEntities)
    user_intent: UserIntent = field(default_factory=UserIntent)
    tool_recommendation: ToolRecommendation = field(default_factory=ToolRecommendation)
    key_parameters: KeyParameters = field(default_factory=KeyParameters)
    suggested_workflow: SuggestedWorkflow = field(default_factory=SuggestedWorkflow)
    next_steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reasoning: Optional[str] = None
    validation_warnings: List[str] = field(default_factory=list)