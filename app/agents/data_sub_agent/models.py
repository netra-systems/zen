"""Data models for DataSubAgent."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class DataAnalysisResponse(BaseModel):
    """Structured response for data analysis operations."""
    query: str = Field(description="The analysis query performed")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Query results")
    insights: Dict[str, Any] = Field(default_factory=dict, description="Key insights from analysis")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about the analysis")
    recommendations: List[str] = Field(default_factory=list, description="Recommended actions")
    error: Optional[str] = Field(default=None, description="Error message if any")
    execution_time_ms: float = Field(default=0.0, description="Query execution time")
    affected_rows: int = Field(default=0, description="Number of rows processed")


class AnomalyDetectionResponse(BaseModel):
    """Structured response for anomaly detection."""
    anomalies_detected: bool = Field(default=False)
    anomaly_count: int = Field(default=0)
    anomaly_details: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    severity: str = Field(default="low", description="Severity level: low, medium, high, critical")
    recommended_actions: List[str] = Field(default_factory=list)