from app.schemas import (ClickHouseCredentials, ModelIdentifier, EventMetadata, 
                         TraceContext, Request, Response, Performance, FinOps, EnrichedMetrics, 
                         UnifiedLogEntry, DiscoveredPattern, PredictedOutcome, BaselineMetrics, 
                         LearnedPolicy, CostComparison, AnalysisResult)

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