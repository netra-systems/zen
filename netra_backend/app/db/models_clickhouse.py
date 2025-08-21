from netra_backend.app.schemas.Analysis import AnalysisResult
from netra_backend.app.schemas.Config import ClickHouseCredentials
from netra_backend.app.schemas.Event import EventMetadata, TraceContext
from netra_backend.app.schemas.FinOps import CostComparison, FinOps
from netra_backend.app.schemas.Log import UnifiedLogEntry
from netra_backend.app.schemas.Metrics import BaselineMetrics, EnrichedMetrics
from netra_backend.app.schemas.Pattern import DiscoveredPattern
from netra_backend.app.schemas.Performance import Performance
from netra_backend.app.schemas.Policy import LearnedPolicy, PredictedOutcome
from netra_backend.app.schemas.Request import RequestModel as Request
from netra_backend.app.schemas.Request import Response
from netra_backend.app.schemas.Supply import ModelIdentifier

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

def _get_content_corpus_columns() -> str:
    """Returns column definitions for content corpus table."""
    return """
        `record_id` UUID,
        `workload_type` String,
        `prompt` String,
        `response` String,
        `created_at` DateTime DEFAULT now()"""


def _get_content_corpus_engine() -> str:
    """Returns engine and ordering for content corpus table."""
    return "ENGINE = MergeTree()\nORDER BY (created_at, workload_type)"


def _format_corpus_table(table_name: str, columns: str, engine: str) -> str:
    """Formats the complete CREATE TABLE statement."""
    return f"""CREATE TABLE IF NOT EXISTS {table_name}
    (
{columns}
    )
    {engine}"""


def get_content_corpus_schema(table_name: str) -> str:
    """Returns the CREATE TABLE statement for a content corpus table with a dynamic name."""
    columns = _get_content_corpus_columns()
    engine = _get_content_corpus_engine()
    return _format_corpus_table(table_name, columns, engine)

WORKLOAD_EVENTS_TABLE_NAME = 'workload_events'
WORKLOAD_EVENTS_TABLE_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {WORKLOAD_EVENTS_TABLE_NAME} (
    event_id UUID DEFAULT generateUUIDv4(),
    timestamp DateTime64(3) DEFAULT now(),
    user_id UInt32,
    workload_id String,
    event_type String,
    event_category String,
    metrics Nested(
        name String,        -- Corrected: Changed from Array(String)
        value Float64,      -- Corrected: Changed from Array(Float64)
        unit String         -- Corrected: Changed from Array(String)
    ),
    dimensions Map(String, String),
    metadata String,
    INDEX idx_user_id user_id TYPE minmax GRANULARITY 8192,
    INDEX idx_workload_id workload_id TYPE bloom_filter GRANULARITY 1,
    INDEX idx_event_type event_type TYPE set(100) GRANULARITY 1
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (user_id, timestamp, event_id)
TTL timestamp + INTERVAL 90 DAY
"""

def _get_event_metadata_columns() -> str:
    """Returns event metadata column definitions."""
    return """        event_metadata_log_schema_version String,
        event_metadata_event_id UUID,
        event_metadata_timestamp_utc DateTime64(3),
        event_metadata_ingestion_source String"""


def _get_trace_context_columns() -> str:
    """Returns trace context column definitions."""
    return """        trace_context_trace_id UUID,
        trace_context_span_id UUID,
        trace_context_span_name String,
        trace_context_span_kind String"""


def _get_identity_context_columns() -> str:
    """Returns identity context column definitions."""
    return """        identity_context_user_id UUID,
        identity_context_organization_id String,
        identity_context_api_key_hash String,
        identity_context_auth_method String"""


def _get_application_context_columns() -> str:
    """Returns application context column definitions."""
    return """        application_context_app_name String,
        application_context_service_name String,
        application_context_sdk_version String,
        application_context_environment LowCardinality(String),
        application_context_client_ip IPv4"""


def _get_request_columns() -> str:
    """Returns request column definitions."""
    return """        request_model JSON,
        request_prompt JSON,
        request_generation_config JSON"""


def _get_response_columns() -> str:
    """Returns response column definitions."""
    return """        response JSON,
        response_completion JSON,
        response_tool_calls JSON,
        response_usage JSON,
        response_system JSON"""


def _get_request_response_columns() -> str:
    """Returns request and response column definitions."""
    request_cols = _get_request_columns()
    response_cols = _get_response_columns()
    return f"{request_cols},\n{response_cols}"


def _get_performance_finops_columns() -> str:
    """Returns performance and finops column definitions."""
    return """        performance_latency_ms JSON,
        finops_attribution JSON,
        finops_cost JSON,
        finops_pricing_info JSON"""


def _get_governance_columns() -> str:
    """Returns governance column definitions."""
    return """        governance_audit_context JSON,
        governance_safety JSON,
        governance_security JSON"""


def _get_metrics_governance_columns() -> str:
    """Returns performance metrics and governance column definitions."""
    perf_cols = _get_performance_finops_columns()
    gov_cols = _get_governance_columns()
    return f"{perf_cols},\n{gov_cols}"


def _get_primary_sections() -> list:
    """Returns primary column section functions."""
    return [
        _get_event_metadata_columns(),
        _get_trace_context_columns(),
        _get_identity_context_columns()
    ]


def _get_secondary_sections() -> list:
    """Returns secondary column section functions."""
    return [
        _get_application_context_columns(),
        _get_request_response_columns(),
        _get_metrics_governance_columns()
    ]


def _combine_llm_columns() -> str:
    """Combines all LLM event table column definitions."""
    primary = _get_primary_sections()
    secondary = _get_secondary_sections()
    all_sections = primary + secondary
    return ",\n\n".join(all_sections)


def _get_llm_events_engine_settings() -> str:
    """Returns engine and settings for LLM events table."""
    return """ENGINE = MergeTree()
    PARTITION BY toYYYYMM(event_metadata_timestamp_utc)
    ORDER BY (application_context_environment, application_context_app_name, event_metadata_timestamp_utc)
    SETTINGS index_granularity = 8192"""


def get_llm_events_table_schema(table_name: str) -> str:
    """Returns the CREATE TABLE statement for the LLM events table with a dynamic name."""
    columns = _combine_llm_columns()
    engine = _get_llm_events_engine_settings()
    return f"""CREATE TABLE IF NOT EXISTS {table_name} (
{columns}
    ) {engine};"""