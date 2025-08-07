from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone
import uuid

# schemas.py is for API schema
# See db/models_clickhouse.py for ClickHouse schema
# See db/models_postgres.py for Postgres schema

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class User(UserBase):
    id: str
    picture: Optional[str] = None
    created_at: datetime

class UserPublic(UserBase):
    id: str
    created_at: datetime

class UserPublicWithPicture(UserPublic):
    picture: Optional[str] = None

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

# --- Secret Schemas ---
class SecretBase(BaseModel):
    key: str = Field(description="The name of the secret (e.g., 'CLICKHOUSE_HOST')")

class SecretCreate(SecretBase):
    value: str

class SecretPublic(SecretBase):
    id: int
    user_id: str


# --- SupplyOption Schemas ---
class SupplyOptionBase(BaseModel):
    provider: str
    family: str
    name: str = Field(..., description="The unique name/identifier for the model, e.g., 'gpt-4-turbo'")
    hosting_type: str = "api_provider"
    cost_per_million_tokens_usd: Dict[str, float] = Field(..., json_schema_extra={"example": {"prompt": 5.00, "completion": 15.00}})
    quality_score: float = Field(..., ge=0, le=1, description="A normalized quality score between 0 and 1.")

class SupplyOptionCreate(SupplyOptionBase):
    pass

class SupplyOptionUpdate(BaseModel):
    provider: Optional[str] = None
    family: Optional[str] = None
    name: Optional[str] = None
    hosting_type: Optional[str] = None
    cost_per_million_tokens_usd: Optional[Dict[str, float]] = None
    quality_score: Optional[float] = None

class SupplyOption(SupplyOptionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SupplyOptionId(BaseModel):
    option_id: int


# --- AnalysisRun Schemas ---
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import SQLModel, Field, Column

class AnalysisRunBase(SQLModel):
    config: Optional[Dict[str, Any]] = Field(None, sa_column=Column(JSON), description="Configuration parameters for the analysis run.")

class AnalysisRun(AnalysisRunBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str
    status: str = Field(default="pending")
    execution_log: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = Field(None, sa_column=Column(JSON))
    result_details: Optional[Dict[str, Any]] = Field(None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    pass

class AnalysisRunCreate(AnalysisRunBase):
    source_table: str = Field(description="The full name of the source table to analyze, e.g., 'mydatabase.mytable'")
    query: str = Field(description="The user's query for the analysis.")

class AnalysisRunPublic(AnalysisRunBase):
    id: uuid.UUID
    user_id: str
    status: str
    execution_log: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None
    result_details: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class AnalysisRun(AnalysisRunPublic):
    pass

class DiscoveredPattern(BaseModel):
    pattern_name: str
    pattern_description: str
    centroid_features: Dict[str, float]
    member_span_ids: List[str]
    member_count: int

class PredictedOutcome(BaseModel):
    supply_option_name: str
    utility_score: float
    predicted_cost_usd: float
    predicted_latency_ms: int
    predicted_quality_score: float
    explanation: str
    confidence: float

class BaselineMetrics(BaseModel):
    avg_cost_usd: float
    avg_latency_ms: int
    avg_quality_score: float

class LearnedPolicy(BaseModel):
    pattern_name: str
    optimal_supply_option_name: str
    predicted_outcome: PredictedOutcome
    alternative_outcomes: List[PredictedOutcome]
    baseline_metrics: BaselineMetrics
    pattern_impact_fraction: float

class CostComparison(BaseModel):
    prior_monthly_spend: float
    projected_monthly_spend: float
    projected_monthly_savings: float
    delta_percent: float

# --- WebSocket Schemas ---
class WebSocketMessage(BaseModel):
    event: str
    data: Dict[str, Any]
    run_id: str

class RunCompleteMessage(WebSocketMessage):
    event: Literal["run_complete"] = "run_complete"
    data: Dict[str, Literal["complete"]]

class ErrorData(BaseModel):
    type: str
    message: str

class ErrorMessage(WebSocketMessage):
    event: Literal["error"] = "error"
    data: ErrorData

class StreamEventMessage(WebSocketMessage):
    event: str = Field(..., alias='event_type')
    data: Dict[str, Any]