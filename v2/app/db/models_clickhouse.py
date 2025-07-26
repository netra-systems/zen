# /v2/app/db/models_clickhouse.py
import uuid
import time
from typing import Dict, Any, List, Optional, Literal
from sqlmodel import SQLModel, Field

# Note: These are SQLModels used for data validation and structure, not for table creation
# with SQLModel's metadata.create_all, as it doesn't support ClickHouse.
# The table schema is defined in data_enricher.py.

class ModelIdentifier(SQLModel):
    provider: str
    family: str
    name: str

class EventMetadata(SQLModel):
    log_schema_version: str = "23.4.0"
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    timestamp_utc: int = Field(default_factory=lambda: int(time.time()))

class TraceContext(SQLModel):
    trace_id: str
    span_id: str = Field(default_factory=lambda: f"span_{uuid.uuid4().hex[:8]}")
    parent_span_id: Optional[str] = None

class RequestData(SQLModel):
    model: ModelIdentifier
    prompt_text: str
    user_goal: Literal["cost", "latency", "quality"] = "quality"

class EnrichedMetrics(SQLModel):
    prefill_ratio: float
    generation_ratio: float
    throughput_tokens_per_sec: float
    inter_token_latency_ms: Optional[float] = None

class UnifiedLogEntry(SQLModel, table=False):
    # This model represents the structure of the data in ClickHouse
    # but is not managed as a table by SQLAlchemy/SQLModel.
    event_metadata: EventMetadata = Field(default_factory=EventMetadata)
    trace_context: TraceContext
    request: RequestData
    performance: Dict[str, Any]
    finops: Dict[str, Any]
    response: Dict[str, Any]
    workloadName: str = "Unknown"
    enriched_metrics: Optional[EnrichedMetrics] = None
    embedding: Optional[List[float]] = None

class DiscoveredPattern(SQLModel, table=False):
    pattern_id: str = Field(default_factory=lambda: f"pat_{uuid.uuid4().hex[:8]}")
    pattern_name: str
    pattern_description: str
    centroid_features: Dict[str, float]
    member_span_ids: List[str]
    member_count: int

class PredictedOutcome(SQLModel, table=False):
    supply_option_id: str
    predicted_cost_usd: float
    predicted_latency_ms: int
    predicted_quality_score: float
    utility_score: float
    explanation: str
    confidence: float

class BaselineMetrics(SQLModel, table=False):
    avg_cost_usd: float
    avg_latency_ms: int
    avg_quality_score: float

class LearnedPolicy(SQLModel, table=False):
    pattern_id: str
    optimal_supply_option_id: str
    predicted_outcome: PredictedOutcome
    alternative_outcomes: List[PredictedOutcome]
    baseline_metrics: BaselineMetrics
    pattern_impact_fraction: float

class CostComparison(SQLModel, table=False):
    prior_monthly_spend: float
    projected_monthly_spend: float
    projected_monthly_savings: float
    delta_percent: float

class AnalysisRequest(SQLModel, table=False):
    workloads: List[Dict]
    debug_mode: bool = False
    constraints: Optional[Dict[str, bool]] = None
    negotiated_discount_percent: float = Field(0.0, ge=0, le=100)

class AnalysisResult(SQLModel, table=False):
    run_id: str
    discovered_patterns: List[DiscoveredPattern]
    learned_policies: List[LearnedPolicy]
    supply_catalog: List[Any] # Using 'Any' to avoid circular dependency with postgres models
    cost_comparison: CostComparison
    execution_log: List[Dict]
    debug_mode: bool
    span_map: Dict[str, UnifiedLogEntry]
