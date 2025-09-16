"""
Data Sub-Agent Models for backward compatibility.

Legacy models stub for tests that still import from this module.
The actual data analysis models have been consolidated into the unified system.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class AnomalyDetectionResponse(BaseModel):
    """Legacy anomaly detection response model."""
    anomalies_found: bool = False
    anomaly_count: int = 0
    anomaly_details: List[Dict[str, Any]] = []
    confidence_score: float = 0.0
    

class CorrelationAnalysis(BaseModel):
    """Legacy correlation analysis model."""
    correlations_found: bool = False
    correlation_matrix: Dict[str, Dict[str, float]] = {}
    significant_correlations: List[Dict[str, Any]] = []


# DataAnalysisResponse removed - use SSOT version from netra_backend.app.schemas.shared_types
    

class PerformanceInsights(BaseModel):
    """Legacy performance insights model."""
    insights: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    performance_score: float = 0.0


class UsageAnalysisResponse(BaseModel):
    """Legacy usage analysis response model."""
    usage_patterns: Dict[str, Any] = {}
    peak_times: List[str] = []
    trends: Dict[str, Any] = {}


class DataQualityMetrics(BaseModel):
    """Legacy data quality metrics model."""
    completeness_score: float = 0.0
    accuracy_score: float = 0.0
    consistency_score: float = 0.0
    validity_score: float = 0.0
    

class PerformanceMetrics(BaseModel):
    """Legacy performance metrics model."""
    response_time_ms: float = 0.0
    throughput_rps: float = 0.0
    error_rate: float = 0.0
    availability_percentage: float = 0.0


class UsagePattern(BaseModel):
    """Legacy usage pattern model."""
    pattern_type: str = "unknown"
    frequency: str = "unknown"
    peak_hours: List[int] = []
    usage_volume: int = 0


__all__ = [
    "AnomalyDetectionResponse",
    "CorrelationAnalysis", 
    # "DataAnalysisResponse" removed - use SSOT version from netra_backend.app.schemas.shared_types
    "PerformanceInsights",
    "UsageAnalysisResponse",
    "DataQualityMetrics",
    "PerformanceMetrics", 
    "UsagePattern"
]