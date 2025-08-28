from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field


class FinOps(BaseModel):
    attribution: Dict[str, str]
    cost: Dict[str, float]
    pricing_info: Dict[str, str]

class CostComparison(BaseModel):
    data: Dict[str, str]

class DataGenerationType(str, Enum):
    """Types of synthetic data generation"""
    INFERENCE_LOGS = "inference_logs"
    TRAINING_DATA = "training_data"
    PERFORMANCE_METRICS = "performance_metrics"
    COST_DATA = "cost_data"
    CUSTOM = "custom"

class WorkloadProfile(BaseModel):
    """Profile for synthetic workload generation"""
    workload_type: DataGenerationType
    volume: int = Field(ge=100, le=1000000, default=1000)
    time_range_days: int = Field(ge=1, le=365, default=30)
    distribution: str = Field(default="normal")
    noise_level: float = Field(ge=0.0, le=0.5, default=0.1)
    custom_parameters: Dict[str, Any] = Field(default_factory=dict)