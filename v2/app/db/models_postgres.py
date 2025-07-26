# /v2/app/db/models_postgres.py
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlmodel import Field, SQLModel, Relationship, JSON, Column

# --- User Models ---

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    is_active: bool = True

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    
    runs: List["AnalysisRun"] = Relationship(back_populates="user")
    secrets: List["Secret"] = Relationship(back_populates="user")

class UserCreate(UserBase):
    password: str

class UserPublic(UserBase):
    id: int
    full_name: Optional[str] = None

# --- Secret Models ---

class SecretBase(SQLModel):
    key: str = Field(description="The name of the secret (e.g., 'CLICKHOUSE_HOST')")

class Secret(SecretBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    encrypted_value: bytes

    user: Optional[User] = Relationship(back_populates="secrets")

class SecretCreate(SecretBase):
    value: str

# --- Supply Catalog Models ---

class SupplyOptionBase(SQLModel):
    provider: str
    family: str
    name: str = Field(..., description="The unique name/identifier for the model, e.g., 'gpt-4-turbo'")
    cost_per_million_tokens_usd: Dict[str, float] = Field(..., sa_column=Column(JSON))
    quality_score: float = Field(..., ge=0, le=1, description="A normalized quality score between 0 and 1.")

class SupplyOption(SupplyOptionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SupplyOptionCreate(SupplyOptionBase):
    pass

class SupplyOptionUpdate(SQLModel):
    provider: Optional[str] = None
    family: Optional[str] = None
    name: Optional[str] = None
    cost_per_million_tokens_usd: Optional[Dict[str, float]] = None
    quality_score: Optional[float] = None

# --- Analysis Run Models ---

class AnalysisRunBase(SQLModel):
    status: str = Field(default="pending", index=True, description="The current status of the run (e.g., pending, running, completed, failed)")
    config: Dict[str, Any] = Field(sa_column=Column(JSON), description="Configuration for the analysis run")
    execution_log: Optional[str] = Field(default="", description="Log of events during the pipeline execution")
    result_summary: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    result_details: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
class AnalysisRun(AnalysisRunBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    completed_at: Optional[datetime] = None
    user_id: int = Field(foreign_key="user.id")
    
    user: Optional[User] = Relationship(back_populates="runs")

class AnalysisRunCreate(SQLModel):
    source_table: str = Field(description="The full name of the source table to analyze, e.g., 'mydatabase.mytable'")

class AnalysisRunPublic(AnalysisRunBase):
    id: uuid.UUID
    created_at: datetime
    user_id: int

# --- Standalone Pydantic-style Models (Not DB tables) ---

class Token(SQLModel):
    access_token: str
    token_type: str

class ClickHouseCredentials(SQLModel):
    host: str
    port: int
    user: str
    password: str
    database: str
