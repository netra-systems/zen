# /v2/app/db/models_clickhouse.py
import uuid
import time
from typing import Dict, Any, List, Optional, Literal
from sqlmodel import SQLModel, Field

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



"""
-- This statement creates a table named 'llm_events' using the MergeTree engine,
-- which is optimized for high-performance analytics and large-scale data warehousing.
-- The schema is designed to store detailed information from Large Language Model (LLM) interactions,
-- flattening the nested JSON structure for easier querying.
"""

LLM_EVENTS_TABLE_NAME = 'JSON_HYBRID_EVENTS'
LLM_EVENTS_TABLE_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {LLM_EVENTS_TABLE_NAME} (
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

    -- Request Details: Nested objects are now stored in JSON columns
    request_model_provider LowCardinality(String),
    request_model_family String,
    request_model_name String,
    request_model_version_id String,
    request_prompt_messages JSON, -- UPDATED: from Nested to JSON
    request_generation_config_temperature Float32,
    request_generation_config_max_tokens_to_sample UInt32,
    request_generation_config_is_streaming Bool,

    -- Response Details: Nested objects are now stored in JSON columns
    response_completion_choices JSON, -- UPDATED: from Nested to JSON
    response_usage_prompt_tokens UInt32,
    response_usage_completion_tokens UInt32,
    response_usage_total_tokens UInt32,
    response_system_provider_request_id String,
    response_tool_calls JSON, -- UPDATED: from Nested to JSON

    -- Performance Metrics
    performance_latency_ms_total_e2e UInt32,
    performance_latency_ms_time_to_first_token UInt32,
    performance_latency_ms_time_per_output_token Float64,
    performance_latency_ms_decode_duration UInt32,

    -- FinOps (Financial Operations)
    finops_cost_total_cost_usd Float64,
    finops_cost_prompt_cost_usd Float64,
    finops_cost_completion_cost_usd Float64,
    finops_pricing_info_provider_rate_id String,
    finops_pricing_info_prompt_token_rate_usd_per_million Float64,
    finops_pricing_info_completion_token_rate_usd_per_million Float64,
    finops_attribution_cost_center_id String,
    finops_attribution_project_id String,
    finops_attribution_team_id String,
    finops_attribution_feature_name String,

    -- Governance: Nested objects are now stored in JSON columns
    governance_security_pii_redacted Bool,
    governance_security_prompt_injection_detected Bool,
    governance_safety_provider_safety_ratings JSON, -- UPDATED: from Nested to JSON
    governance_safety_overall_safety_verdict String,
    governance_audit_context_request_type String,
    governance_audit_context_cache_status String

    -- REMOVED: Redundant columns for unnesting are no longer needed with the JSON type.

) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_metadata_timestamp_utc)
ORDER BY (application_context_environment, application_context_app_name, event_metadata_timestamp_utc)
SETTINGS index_granularity = 8192;
"""
