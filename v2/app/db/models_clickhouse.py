import uuid
import time
from typing import Dict, Any, List, Optional, Literal
from sqlmodel import SQLModel, Field
from pydantic import BaseModel

# TBD merge understand these models / things


LOGS_TABLE_NAME = 'netra_app_internal_logs'

# Schema for the main application logs, based on the Log model in app/logging/logger.py
LOGS_TABLE_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {LOGS_TABLE_NAME}
(
    `request_id` UUID,
    `timestamp` DateTime64(3, 'UTC'),
    `level` String,
    `message` String,
    `module` Nullable(String),
    `function` Nullable(String),
    `line_no` Nullable(UInt32),
    `process_name` Nullable(String),
    `thread_name` Nullable(String),
    `extra` Map(String, String)
)
ENGINE = MergeTree()
ORDER BY (timestamp, level)
"""

# Schema for the LLM supply catalog, remains unchanged
SUPPLY_TABLE_NAME = 'netra_global_supply_catalog'
SUPPLY_TABLE_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {SUPPLY_TABLE_NAME} (
    id UUID,
    provider String,
    family String,
    name String,
    cost_per_million_tokens_usd Map(String, Float64),
    quality_score Float64,
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (id);
"""


CONTENT_CORPUS_TABLE_NAME = 'netra_content_corpus'

def get_content_corpus_schema(table_name: str) -> str:
    """Returns the CREATE TABLE statement for a content corpus table with a dynamic name."""
    return f"""
    CREATE TABLE IF NOT EXISTS {table_name}
    (
        `record_id` UUID,
        `workload_type` String,
        `prompt` String,
        `response` String,
        `created_at` DateTime DEFAULT now()
    )
    ENGINE = MergeTree()
    ORDER BY (created_at, workload_type)
    """

class ContentCorpus(SQLModel, table=False): # Set table=False as we are manually creating it
    record_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    workload_type: str
    prompt: str
    response: str
    created_at: int = Field(default_factory=lambda: int(time.time()))


# Note: These are SQLModels used for data validation and structure, not for table creation
# with SQLModel's metadata.create_all, as it doesn't support ClickHouse.
# The table schema is defined in data_enricher.py.

class ClickHouseCredentials(SQLModel):
    host: str
    port: int
    user: str
    password: str
    database: str

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

class Request(SQLModel):
    model: str
    prompt_text: str

class Response(SQLModel):
    usage: Dict[str, int]

class Performance(SQLModel):
    latency_ms: Dict[str, int]

class FinOps(SQLModel):
    total_cost_usd: float

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
    request: Request
    performance: Performance
    finops: FinOps
    response: Response
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

class AnalysisResult(SQLModel, table=False):
    run_id: str
    discovered_patterns: List[DiscoveredPattern]
    learned_policies: List[LearnedPolicy]
    supply_catalog: List[Any] # Using 'Any' to avoid circular dependency with postgres models
    cost_comparison: CostComparison
    execution_log: List[Dict]
    debug_mode: bool
    span_map: Dict[str, UnifiedLogEntry]


def get_llm_events_table_schema(table_name: str) -> str:
    """Returns the CREATE TABLE statement for the LLM events table with a dynamic name."""
    return f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        -- Event Metadata
        event_metadata_log_schema_version String,
        event_metadata_event_id UUID,
        event_metadata_timestamp_utc DateTime64(3),
        event_metadata_ingestion_source String,

        -- Trace Context
        trace_context_trace_id UUID,
        trace_context_span_id UUID,
        trace_context_span_name String,
        trace_context_span_kind String,

        -- Identity Context
        identity_context_user_id UUID,
        identity_context_organization_id String,
        identity_context_api_key_hash String,
        identity_context_auth_method String,
        
        -- Application Context
        application_context_app_name String,
        application_context_service_name String,
        application_context_sdk_version String,
        application_context_environment LowCardinality(String),
        application_context_client_ip IPv4,

        -- Request Details: Consolidated into JSON objects
        request_model JSON,
        request_prompt JSON,
        request_generation_config JSON,

        -- Response Details: Consolidated into JSON objects
        response JSON,
        response_completion JSON,
        response_tool_calls JSON,
        response_usage JSON,
        response_system JSON,

        -- Performance Metrics
        performance_latency_ms JSON,

        -- FinOps (Financial Operations)
        finops_attribution JSON,
        finops_cost JSON,
        finops_pricing_info JSON,

        -- Governance
        governance_audit_context JSON,
        governance_safety JSON,
        governance_security JSON
        
    ) ENGINE = MergeTree()
    PARTITION BY toYYYYMM(event_metadata_timestamp_utc)
    ORDER BY (application_context_environment, application_context_app_name, event_metadata_timestamp_utc)
    SETTINGS index_granularity = 8192;
    """