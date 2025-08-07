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
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, conint, confloat, ConfigDict

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

# --- User Schemas ---

class GoogleUser(BaseModel):
    """
    Represents the user information received from Google's OAuth service.
    """
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None

class UserBase(BaseModel):
    email: str
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
