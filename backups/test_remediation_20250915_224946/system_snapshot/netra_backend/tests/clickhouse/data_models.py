"""
ClickHouse Test Data Models
Provides strongly typed data models for test fixtures
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

@dataclass
class LLMEvent:
    """Realistic LLM event data"""
    timestamp: datetime
    event_id: str
    user_id: int
    workload_id: str
    model: str
    request_id: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_cents: float
    success: bool
    temperature: float
    workload_type: str
    prompt: str
    response: str
    metadata: Dict[str, Any]

@dataclass
class WorkloadMetric:
    """Realistic workload metric data"""
    timestamp: datetime
    user_id: int
    workload_id: str
    metrics: Dict[str, List[Any]]  # name, value, unit arrays
    metadata: Dict[str, Any]

@dataclass
class LogEntry:
    """Realistic log entry data"""
    timestamp: datetime
    level: str
    component: str
    message: str
    metadata: Dict[str, Any]