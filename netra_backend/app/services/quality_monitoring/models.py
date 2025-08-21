"""Data models for quality monitoring"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from netra_backend.app.core.health_types import AlertSeverity




class MetricType(Enum):
    """Types of metrics to track"""
    QUALITY_SCORE = "quality_score"
    SLOP_DETECTION_RATE = "slop_detection_rate"
    RETRY_RATE = "retry_rate"
    FALLBACK_RATE = "fallback_rate"
    USER_SATISFACTION = "user_satisfaction"
    RESPONSE_TIME = "response_time"
    TOKEN_EFFICIENCY = "token_efficiency"
    ERROR_RATE = "error_rate"


@dataclass
class QualityAlert:
    """Alert for quality issues"""
    id: str
    timestamp: datetime
    severity: AlertSeverity
    metric_type: MetricType
    agent: str
    message: str
    current_value: float
    threshold: float
    details: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class QualityTrend:
    """Trend analysis for quality metrics"""
    metric_type: MetricType
    period: str  # "hour", "day", "week"
    trend_direction: str  # "improving", "degrading", "stable"
    change_percentage: float
    current_average: float
    previous_average: float
    forecast_next_period: float
    confidence: float


@dataclass
class AgentQualityProfile:
    """Quality profile for an individual agent"""
    agent_name: str
    total_requests: int
    average_quality_score: float
    quality_distribution: Dict[str, int]
    slop_detection_count: int
    retry_count: int
    fallback_count: int
    average_response_time: float
    last_updated: datetime
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)