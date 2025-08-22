"""
Factory Status API Models
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportResponse(BaseModel):
    """Response model for factory status report."""
    report_id: str
    generated_at: datetime
    executive_summary: Dict[str, Any]
    velocity_metrics: Dict[str, Any]
    impact_metrics: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    business_value_metrics: Dict[str, Any]
    branch_metrics: Dict[str, Any]
    feature_progress: Dict[str, Any]
    recommendations: List[str]


class MetricResponse(BaseModel):
    """Response model for individual metrics."""
    metric_name: str
    value: Any
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class GenerateReportRequest(BaseModel):
    """Request model for report generation."""
    hours: int = Field(default=24, ge=1, le=720, description="Hours to analyze")
    include_business_value: bool = Field(default=True)
    include_recommendations: bool = Field(default=True)


class HistoryRequest(BaseModel):
    """Request model for historical reports."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    interval: str = Field(default="daily", pattern="^(hourly|daily|weekly)$")
    limit: int = Field(default=10, ge=1, le=100)