"""
Analytics and model performance tracking models.

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all tiers)
- Business Goal: Track model performance and costs for optimization
- Value Impact: Enable data-driven model selection and cost optimization
- Revenue Impact: Reduce operational costs through intelligent model routing
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ModelUsage(BaseModel):
    """Model usage tracking for analytics."""
    id: str
    model_name: str
    query_type: str
    tokens_used: int = 0
    cost: float
    latency_ms: float
    quality_score: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelPerformance(BaseModel):
    """Model performance metrics."""
    id: str
    model_name: str
    query_type: str
    latency_ms: float
    quality_score: float
    confidence_score: float
    cost: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CostOptimization(BaseModel):
    """Cost optimization tracking."""
    id: str
    optimization_type: str
    queries_processed: int
    cache_hit_rate: float = 0.0
    cost_saved: float
    savings_percentage: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QualityMetric(BaseModel):
    """Quality metric tracking."""
    id: str
    model_name: str
    query_hash: int
    quality_score: float
    evaluation_method: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelConfiguration(BaseModel):
    """Model configuration for routing."""
    id: str
    configuration_name: str
    category: str
    preferred_model: str
    fallback_models: str  # JSON string
    quality_threshold: float
    cost_threshold: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


__all__ = [
    "ModelUsage",
    "ModelPerformance", 
    "CostOptimization",
    "QualityMetric",
    "ModelConfiguration"
]