from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

# schema.py is for API schema
# See db/models_clickhouse.py for ClickHouse schema
# See db/models_postgres.py for Postgres schema

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserPublic(UserBase):
    id: str
    created_at: datetime

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
    cost_per_million_tokens_usd: Dict[str, float] = Field(..., example={"prompt": 5.00, "completion": 15.00})
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

    class Config:
        orm_mode = True


# --- AnalysisRun Schemas ---
class AnalysisRunBase(BaseModel):
    config: Optional[Dict[str, Any]] = Field(None, description="Configuration parameters for the analysis run.")

class AnalysisRunCreate(BaseModel):
    source_table: str = Field(description="The full name of the source table to analyze, e.g., 'mydatabase.mytable'")


class AnalysisRunPublic(AnalysisRunBase):
    id: uuid.UUID
    user_id: str
    status: str
    execution_log: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None
    result_details: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None