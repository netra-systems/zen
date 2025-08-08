# netra_apex/models/schemas.py
#
# Copyright (C) 2025, netra apex Inc.
#
# This module defines the core data structures and schemas used throughout the
# netra apex system. Using Pydantic, it ensures data validation, type
# hinting, and clear, machine-readable definitions for the complex data objects
# that flow between the system's components. These schemas are the bedrock of
# the system's UCP (Unified Control Plane), providing a canonical representation
# for demand (WorkloadProfile) and supply (SupplyRecord).

import uuid
import time
import enum
import os
from typing import List, Dict, Any, Optional, Union, Literal, TypedDict, Annotated
from pydantic import BaseModel, Field, conint, confloat, ConfigDict, EmailStr
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from datetime import datetime

# --- Constants and Enums ---

class DeploymentType(str):
    """Enumeration for the different types of model deployments."""
    API = "API"
    SELF_HOSTED_ONPREM = "Self-Hosted-OnPrem"
    SELF_HOSTED_CLOUD = "Self-Hosted-Cloud"

class TokenizerAlgorithm(str):
    """Enumeration for supported tokenizer algorithms."""
    BPE = "BPE"
    WORDPIECE = "WordPiece"
    UNIGRAM = "Unigram"
    SENTENCEPIECE = "SentencePiece"

class SubAgentLifecycle(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SHUTDOWN = "shutdown"

# --- User Schemas ---

class GoogleUser(BaseModel):
    """
    Represents the user information received from Google's OAuth service.
    """
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False
    full_name: Optional[str] = None
    picture: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    pass

class UserInDBBase(UserBase):
    id: uuid.UUID

    class Config:
        orm_mode = True

class User(UserInDBBase):
    pass

class UserInDB(UserInDBBase):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: str

# --- Admin Schemas ---

class LogTableSettings(BaseModel):
    log_table: str

class TimePeriodSettings(BaseModel):
    days: int

class DefaultLogTableSettings(BaseModel):
    context: str
    log_table: str

# --- Agent Schemas ---

class Settings(BaseModel):
    debug_mode: bool

class DataSource(BaseModel):
    source_table: str
    filters: Optional[Dict[str, Any]] = None

class TimeRange(BaseModel):
    start_time: str
    end_time: str

class Workload(BaseModel):
    run_id: str
    query: str
    data_source: DataSource
    time_range: TimeRange

class RequestModel(BaseModel):
    id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:8]}")
    user_id: str
    query: str
    workloads: List[Workload]
    constraints: Optional[Any] = None

class AnalysisRequest(BaseModel):
    settings: Settings
    request: RequestModel

class StartAgentPayload(BaseModel):
    settings: Settings
    request: RequestModel

class StartAgentMessage(BaseModel):
    action: str
    payload: StartAgentPayload

class WebSocketMessage(BaseModel):
    event: str
    data: Any
    run_id: str

class RunCompleteMessage(WebSocketMessage):
    event: str = "run_complete"

class ErrorData(BaseModel):
    type: str
    message: str

class ErrorMessage(WebSocketMessage):
    event: str = "error"
    data: ErrorData

class StreamEventMessage(WebSocketMessage):
    event: str = "stream_event"
    event_type: str

# --- Supply Schemas ---

class SupplyOptionBase(BaseModel):
    provider: str
    family: str
    name: str
    hosting_type: str
    cost_per_million_tokens_usd: Dict[str, float]
    quality_score: float

class SupplyOptionCreate(SupplyOptionBase):
    pass

class SupplyOptionUpdate(SupplyOptionBase):
    pass

class SupplyOptionInDBBase(SupplyOptionBase):
    id: int

    class Config:
        orm_mode = True

class SupplyOption(SupplyOptionInDBBase):
    pass

# --- Generation Schemas ---
class ContentGenParams(BaseModel):
    samples_per_type: int = Field(10, gt=0, le=100, description="Number of samples to generate for each workload type.")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Controls randomness. Higher is more creative.")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling probability.")
    top_k: Optional[int] = Field(None, ge=0, description="Top-k sampling control.")
    max_cores: int = Field(4, ge=1, description="Max CPU cores to use.")

class LogGenParams(BaseModel):
    corpus_id: str = Field(..., description="The ID of the content corpus to use for generation.")
    num_logs: int = Field(1000, gt=0, le=100000, description="Number of log entries to generate.")
    max_cores: int = Field(4, ge=1, description="Max CPU cores to use.")

class SyntheticDataGenParams(BaseModel):
    num_traces: int = Field(10000, gt=0, le=100000, description="Number of traces to generate.")
    num_users: int = Field(100, gt=0, le=10000, description="Number of unique users to simulate.")
    error_rate: float = Field(0.05, ge=0.0, le=1.0, description="The fraction of traces that should be errors.")
    event_types: List[str] = Field(default_factory=lambda: ["search", "login", "purchase", "logout"], description="A list of event types to simulate.")
    source_table: str = Field("content_corpus", description="The name of the source ClickHouse table for the content corpus.")
    destination_table: str = Field("synthetic_data", description="The name of the destination ClickHouse table for the generated data.")

class DataIngestionParams(BaseModel):
    data_path: str = Field(..., description="The path to the data file to ingest.")
    table_name: str = Field(..., description="The name of the table to ingest the data into.")

class ContentCorpusGenParams(BaseModel):
    samples_per_type: int = Field(10, gt=0, le=100, description="Number of samples to generate for each workload type.")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Controls randomness. Higher is more creative.")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling probability.")
    top_k: Optional[int] = Field(None, ge=0, description="Top-k sampling control.")
    max_cores: int = Field(4, ge=1, le=os.cpu_count(), description="Max CPU cores to use.")
    clickhouse_table: str = Field('content_corpus', description="The name of the ClickHouse table to store the corpus in.")


# --- WebSocket Schemas ---
class WebSocketMessage(BaseModel):
    type: str
    payload: Dict[str, Any]


# --- Section 2: Demand Analyzer Schemas ---

class LinguisticFeatures(BaseModel):
    """
    Captures key linguistic and structural properties of the input prompt.
    These features are crucial for predicting cost, latency, and tokenizer
    efficiency.
    Reference: Section 2, Component 1: Workload Profiler
    """
    language: str = Field(..., description="Primary language of the prompt (e.g., 'python', 'en', 'ja').")
    has_code: bool = Field(..., description="True if the prompt contains code snippets.")
    domain_jargon: List[str] = Field(default_factory=list, description="List of detected domain-specific terms.")
    prompt_length_tokens: int = Field(..., gt=0, description="Token count of the prompt based on a reference tokenizer.")
    prompt_length_chars: int = Field(..., gt=0, description="Character count of the prompt.")

class SLOProfile(BaseModel):
    """
    Defines the Service Level Objectives for a workload, making a critical
    distinction between the prefill (TTFT) and decode (TPOT) phases of
    LLM inference.
    Reference: Section 2, Component 2: SLO Definer
    """
    ttft_ms_p95: Optional[int] = Field(None, gt=0, description="95th percentile SLO for Time To First Token in milliseconds.")
    tpot_ms_p95: Optional[int] = Field(None, gt=0, description="95th percentile SLO for Time Per Output Token in milliseconds.")

class RiskProfile(BaseModel):
    """
    Quantifies the business risk associated with a workload. This moves risk
    from an abstract concept to a concrete input for the optimization engine.
    Reference: Section 2, Component 3: Risk Assessor
    """
    business_impact_score: conint(ge=1, le=10) = Field(
        ...,
        description="Business impact of failure (1=low, 10=high)."
    )
    failure_mode_tags: List[str] = Field(
        ...,
        description="Potential failure modes (e.g., 'risk_of_hallucination', 'risk_of_pii_leakage')."
    )

class WorkloadProfile(BaseModel):
    """
    The canonical, structured representation of a single unit of demand.
    This is the primary output of the Demand Analyzer and the key input for
    the Multi-Objective Controller.
    Reference: Table 1: Workload Profile Schema
    """
    workload_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="A unique identifier for this workload instance.")
    task_vector: List[float] = Field(..., description="High-dimensional embedding of the task's semantic content.")
    linguistic_features: LinguisticFeatures
    slo_profile: SLOProfile
    risk_profile: RiskProfile
    raw_prompt: str = Field(..., description="The original, unmodified user prompt.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Application-specific metadata (e.g., user_id, session_id).")

# --- Section 3: Supply Catalog Schemas ---

class CostModel(BaseModel):
    """
    A structured representation of the cost associated with using a supply option.
    Handles both pay-per-use APIs and TCO models for self-hosted deployments.
    Reference: Section 3, Component 1: Unified Supply Schema
    """
    type: str = Field(..., description="The type of cost model ('API', 'TCO').")
    # For API type
    input_cost_per_million_tokens: Optional[float] = Field(None, ge=0)
    output_cost_per_million_tokens: Optional[float] = Field(None, ge=0)
    # For TCO type
    tco_model_id: Optional[str] = Field(None, description="Reference to a detailed TCO model.")
    amortized_cost_per_hour: Optional[float] = Field(None, ge=0)


class TechnicalSpecs(BaseModel):
    """

    Detailed technical capabilities and constraints of a supply option.
    Reference: Section 3, Component 1: Unified Supply Schema
    """
    max_context_window: int = Field(..., gt=0, description="Maximum number of tokens in the context window.")
    modalities: List[str] = Field(..., description="Supported modalities (e.g., 'text', 'image', 'audio').")
    quantization: Optional[str] = Field(None, description="Quantization method used (e.g., 'AWQ-4bit', 'FP16').")
    architecture: Optional[str] = Field(None, description="Model architecture (e.g., 'Transformer', 'Mixture-of-Experts').")
    parameter_count_billions: Optional[float] = Field(None, gt=0, description="Number of parameters in billions.")
    hardware_requirements: Dict[str, Any] = Field(default_factory=dict, description="Hardware needs for self-hosted models (e.g., 'min_vram_gb').")

class PerformanceDistribution(BaseModel):
    """
    Represents a statistical distribution of a performance metric, capturing
    percentiles to provide a rich view beyond simple averages.
    Reference: Section 3, Component 2: Performance & Quality Characterization
    """
    p50: float = Field(..., ge=0, description="Median or 50th percentile value.")
    p90: float = Field(..., ge=0, description="90th percentile value.")
    p99: float = Field(..., ge=0, description="99th percentile value, representing tail performance.")

class LatencyDistributions(BaseModel):
    """
    Stores latency distributions for both TTFT and TPOT, further broken down
    by influencing factors like batch size.
    Reference: Section 3, Component 2: Performance & Quality Characterization
    """
    ttft_ms: Dict[str, PerformanceDistribution] = Field(..., description="TTFT distributions, keyed by batch size (e.g., 'batch_1').")
    tpot_ms: Dict[str, PerformanceDistribution] = Field(..., description="TPOT distributions, keyed by batch size.")

class SafetyAndQualityProfile(BaseModel):
    """
    A vector of continuously measured quality and risk metrics, providing a
    quantifiable fingerprint of a model's real-world behavior.
    Reference: Section 3, Component 2: Performance & Quality Characterization
    """
    hallucination_rate: confloat(ge=0, le=1) = Field(..., description="Frequency of factually incorrect statements.")
    toxicity_score: confloat(ge=0, le=1) = Field(..., description="Propensity to generate harmful content.")
    pii_leakage_rate: confloat(ge=0, le=1) = Field(..., description="Rate of inadvertent PII leakage.")
    adversarial_robustness_score: confloat(ge=0, le=1) = Field(..., description="Performance score against the Adversarial Gauntlet.")
    knowledge_recovery_risk: Optional[confloat(ge=0, le=1)] = Field(None, description="Risk of unlearned info being recoverable in quantized models.")


class TokenizerProfile(BaseModel):
    """
    Models the tokenizer used by a supply option to predict and manage the
    "tokenization trap."
    Reference: Section 3, Component 3: The Tokenizer Profile
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    library: str = Field(..., description="The tokenizer library used (e.g., 'tiktoken', 'sentencepiece').")
    name: str = Field(..., description="The specific vocabulary name (e.g., 'cl100k_base').")
    algorithm: str = Field(..., description="The underlying tokenization algorithm.")
    vocab_size: int = Field(..., gt=0, description="The size of the tokenizer's vocabulary.")


class SupplyRecord(BaseModel):
    """
    The canonical, structured representation of a single unit of supply.
    This schema defines the rich data model for entries in the Supply Catalog.
    Reference: Table 2: Unified Supply Catalog Schema
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    supply_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="A unique identifier for this supply option.")
    model_name: str = Field(..., description="The official name of the model.")
    provider: str = Field(..., description="The entity providing the model (e.g., 'OpenAI', 'Self-Hosted').")
    deployment_type: str
    cost_model: CostModel
    technical_specs: TechnicalSpecs
    # Performance is stored as a live, dynamic attribute updated by the Observability Plane
    performance: Optional[LatencyDistributions] = Field(None, description="Live performance data from monitoring.")
    safety_and_quality: Optional[SafetyAndQualityProfile] = Field(None, description="Live safety and quality data from monitoring.")
    tokenizer_profile: TokenizerProfile
    is_gauntlet_certified: bool = Field(False, description="True if the model has passed the Adversarial Gauntlet.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the supply option.")




# --- Section 4: Multi-Objective Controller Schemas ---

class ParetoSolution(BaseModel):
    """
    Represents a single, non-dominated solution on the Pareto front,
    explicitly showing the trade-offs.
    Reference: Section 4, Component 2: The Pareto Front Generator
    """
    supply_id: uuid.UUID
    predicted_cost: float
    predicted_ttft_ms_p95: float
    predicted_tpot_ms_p95: float
    predicted_risk_score: float
    trade_off_profile: str = Field(..., description="A human-readable description of the solution's bias (e.g., 'Cost-Optimized').")

# --- Section 6: Governance Schemas ---

class Policy(BaseModel):
    """
    A generic policy structure for the Policy Engine.
    """
    policy_id: str
    policy_type: str # e.g., "BUDGET", "DATA_GOVERNANCE"
    rules: Dict[str, Any]

class CanaryHealthCheckResult(BaseModel):
    """
    Represents the result of a health check during a phased rollout.
    """
    is_healthy: bool
    metric: str
    current_value: float
    threshold: float
    message: str

class Log(BaseModel):
    request: dict = Field(..., description="The request data for the log.")

# --- Reference Schemas ---

class ReferenceItem(BaseModel):
    id: int
    name: str
    friendly_name: str
    description: str | None = None
    type: str
    value: str
    version: str

    class Config:
        from_attributes = True

class ReferenceGetResponse(BaseModel):
    """
    The response model for the GET /references endpoint.
    """
    references: List[ReferenceItem]

class ReferenceCreateRequest(BaseModel):
    """
    The request model for creating a new reference.
    """
    name: str
    friendly_name: str
    description: str | None = None
    type: str
    value: str
    version: str

class ReferenceUpdateRequest(BaseModel):
    """
    The request model for updating a reference.
    """
    name: str | None = None
    friendly_name: str | None = None
    description: str | None = None
    type: str | None = None
    value: str | None = None
    version: str | None = None

# --- Config Schemas ---
class SecretReference(BaseModel):
    name: str
    target_field: str
    target_model: Optional[str] = None
    project_id: str = "304612253870"
    version: str = "latest"

class GoogleCloudConfig(BaseModel):
    project_id: str = "cryptic-net-466001-n0"
    client_id: str = None
    client_secret: str = None

class OAuthConfig(BaseModel):
    client_id: str = None
    client_secret: str = None
    token_uri: str = "https://oauth2.googleapis.com/token"
    auth_uri: str = "https://accounts.google.com/o/oauth2/v2/auth"
    userinfo_endpoint: str = "https://www.googleapis.com/oauth2/v3/userinfo"
    scopes: List[str] = ["openid", "email", "profile"]
    web: Dict[str, List[str]] = {
        "authorized_javascript_origins": [
            "https://app.netrasystems.ai",
            "https://127.0.0.1",
            "http://localhost"
        ],
        "authorized_redirect_uris": [
            "https://app.netrasystems.ai/oauth2callback",
            "https://127.0.0.1/oauth2callback",
            "http://localhost:8000/auth/google",
            "http://localhost:3000/auth/callback"
        ]
    }

class DevUser(BaseModel):
    email: str = "dev@example.com"
    full_name: str = "Dev User"
    picture: Optional[str] = None
    is_dev: bool = True

class AuthEndpoints(BaseModel):
    login_url: str
    logout_url: str
    auth_callback_url: str
    user_info_url: str
    token_url: str
    
class AuthConfigResponse(BaseModel):
    development_mode: bool
    dev_user: Optional[DevUser] = None
    endpoints: AuthEndpoints
    google_client_id: str
    google_redirect_uri: str

class ClickHouseNativeConfig(BaseModel):
    host: str = "xedvrr4c3r.us-central1.gcp.clickhouse.cloud"
    port: int = 9440
    user: str = "default"
    password: str = ""
    database: str = "default"

class ClickHouseHTTPSConfig(BaseModel):
    host: str = "xedvrr4c3r.us-central1.gcp.clickhouse.cloud"
    port: int = 8443
    user: str = "default"
    password: str = ""
    database: str = "default"


class ClickHouseHTTPSDevConfig(BaseModel):
    host: str = "xedvrr4c3r.us-central1.gcp.clickhouse.cloud"
    port: int = 8443
    user: str = "development_user"
    password: str = ""
    database: str = "development"
    superuser: bool = True


class ClickHouseLoggingConfig(BaseModel):
    enabled: bool = True
    default_table: str = "logs"
    default_time_period_days: int = 7
    available_tables: List[str] = Field(default_factory=lambda: ["logs"])
    default_tables: Dict[str, str] = Field(default_factory=lambda: {})
    available_time_periods: List[int] = Field(default_factory=lambda: [1, 7, 30, 90])


class LangfuseConfig(BaseModel):
    secret_key: str = ""
    public_key: str = ""
    host: str = "https://cloud.langfuse.com/"

class LLMConfig(BaseModel):
    provider: str = Field(..., description="The LLM provider (e.g., 'google', 'openai').")
    model_name: str = Field(..., description="The name of the model.")
    api_key: Optional[str] = Field(None, description="The API key for the LLM provider.")
    generation_config: Dict[str, Any] = Field({}, description="A dictionary of generation parameters, e.g., temperature, max_tokens.")

class AppConfig(BaseModel):
    """Base configuration class."""

    environment: str = "development"
    google_cloud: GoogleCloudConfig = GoogleCloudConfig()
    oauth_config: OAuthConfig = Field(default_factory=OAuthConfig)
    clickhouse_native: ClickHouseNativeConfig = ClickHouseNativeConfig()
    clickhouse_https: ClickHouseHTTPSConfig = ClickHouseHTTPSConfig()
    clickhouse_https_dev: ClickHouseHTTPSDevConfig = ClickHouseHTTPSDevConfig()
    clickhouse_logging: ClickHouseLoggingConfig = ClickHouseLoggingConfig()
    langfuse: LangfuseConfig = LangfuseConfig()

    secret_key: str = "default_secret_key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    fernet_key: str = None
    jwt_secret_key: str = None
    api_base_url: str = "http://localhost:8000"
    database_url: str = None
    log_level: str = "DEBUG"
    log_secrets: bool = False
    frontend_url: str = "http://localhost:3000"

    llm_configs: Dict[str, LLMConfig] = {
        "default": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
        ),
        "analysis": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
            generation_config={"temperature": 0.5},
        ),
        "gpt-4": LLMConfig(
            provider="openai",
            model_name="gpt-4",
            generation_config={"temperature": 0.8},
        ),
        "triage": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
        ),
        "data": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
        ),
        "optimizations_core": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
        ),
        "actions_to_meet_goals": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
        ),
        "reporting": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
        ),
    }

class DevelopmentConfig(AppConfig):
    """Development-specific settings can override defaults."""
    debug: bool = True
    database_url: str = "postgresql+asyncpg://postgres:123@localhost/netra"
    dev_user_email: str = "dev@example.com"

class ProductionConfig(AppConfig):
    """Production-specific settings."""
    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"

class TestingConfig(AppConfig):
    """Testing-specific settings."""
    environment: str = "testing"
    database_url: str = "postgresql+asyncpg://postgres:123@localhost/netra_test"

# --- LLM Schemas ---
class ToolConfig(BaseModel):
    name: str = Field(..., description="The name of the tool.")
    llm_config: Optional[LLMConfig] = Field(None, description="LLM configuration for this tool.")

# --- ClickHouse Models ---
class ContentCorpus(BaseModel): # Set table=False as we are manually creating it
    record_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    workload_type: str
    prompt: str
    response: str
    created_at: int = Field(default_factory=lambda: int(time.time()))

class ClickHouseCredentials(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str

class ModelIdentifier(BaseModel):
    provider: str
    family: str
    name: str

class EventMetadata(BaseModel):
    log_schema_version: str = "23.4.0"
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    timestamp_utc: int = Field(default_factory=lambda: int(time.time()))

class TraceContext(BaseModel):
    trace_id: str
    span_id: str = Field(default_factory=lambda: f"span_{uuid.uuid4().hex[:8]}")
    parent_span_id: Optional[str] = None

class Request(BaseModel):
    model: str
    prompt_text: str

class Response(BaseModel):
    usage: Dict[str, int]

class Performance(BaseModel):
    latency_ms: Dict[str, int]

class FinOps(BaseModel):
    total_cost_usd: float

class EnrichedMetrics(BaseModel):
    prefill_ratio: float
    generation_ratio: float
    throughput_tokens_per_sec: float
    inter_token_latency_ms: Optional[float] = None

class UnifiedLogEntry(BaseModel):
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

class DiscoveredPattern(BaseModel):
    pattern_id: str = Field(default_factory=lambda: f"pat_{uuid.uuid4().hex[:8]}")
    pattern_name: str
    pattern_description: str
    centroid_features: Dict[str, float]
    member_span_ids: List[str]
    member_count: int

class PredictedOutcome(BaseModel):
    supply_option_id: str
    predicted_cost_usd: float
    predicted_latency_ms: int
    predicted_quality_score: float
    utility_score: float
    explanation: str
    confidence: float

class BaselineMetrics(BaseModel):
    avg_cost_usd: float
    avg_latency_ms: int
    avg_quality_score: float

class LearnedPolicy(BaseModel):
    pattern_id: str
    optimal_supply_option_id: str
    predicted_outcome: PredictedOutcome
    alternative_outcomes: List[PredictedOutcome]
    baseline_metrics: BaselineMetrics
    pattern_impact_fraction: float

class CostComparison(BaseModel):
    prior_monthly_spend: float
    projected_monthly_spend: float
    projected_monthly_savings: float
    delta_percent: float

class AnalysisResult(BaseModel):
    run_id: str
    discovered_patterns: List[DiscoveredPattern]
    learned_policies: List[LearnedPolicy]
    supply_catalog: List[Any] # Using 'Any' to avoid circular dependency with postgres models
    cost_comparison: CostComparison
    execution_log: List[Dict]
    debug_mode: bool
    span_map: Dict[str, UnifiedLogEntry]

# --- Logging Schemas ---
class LogEntry(BaseModel):
    """Pydantic model for a single log entry."""
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    event: str
    data: Dict[str, Any] = Field(default_factory=dict)
    source: str = "backend"
    user_id: Optional[str] = None

# --- Apex Optimizer Agent Schemas ---
class AdditionalTable(BaseModel):
    name: str = Field(..., description="The name of the additional table.")
    context: str = Field(..., description="The context in which this table should be used.")
    time_period: str = Field(..., description="The default time period for this table.")

class ConfigForm(BaseModel):
    default_log_table: str = Field(..., description="The default log table to pull from.")
    default_time_range: str = Field(default="7d", description="The default time period to pull logs from.")
    additional_tables: Optional[List[AdditionalTable]] = Field(default=None, description="A list of additional default tables.")

class AgentState(BaseModel):
    messages: List[BaseMessage]
    next_node: str
    tool_results: Optional[List[Dict]] = None

class ToolStatus(str, enum.Enum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL_SUCCESS = "partial_success"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"

class ToolInput(BaseModel):
    tool_name: str
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}

class ToolResult(BaseModel):
    tool_input: ToolInput
    status: ToolStatus = ToolStatus.IN_PROGRESS
    message: str = ""
    payload: Optional[Any] = None
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None

    def complete(self, status: ToolStatus, message: str, payload: Optional[Any] = None):
        self.status = status
        self.message = message
        self.payload = payload
        self.end_time = time.time()

class ToolInvocation(BaseModel):
    tool_result: ToolResult

    def __init__(self, tool_name: str, *args, **kwargs):
        super().__init__(tool_result=ToolResult(tool_input=ToolInput(tool_name=tool_name, args=list(args), kwargs=kwargs)))

    def set_result(self, status: ToolStatus, message: str, payload: Optional[Any] = None):
        self.tool_result.complete(status, message, payload)

# --- Deep-Agent Schemas ---
class Todo(TypedDict):
    id: str
    task: str
    status: str
    items: List[str]

class DeepAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    todos: List[Todo]
    files: dict