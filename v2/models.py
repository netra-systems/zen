# /v2/models.py
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlmodel import Field, SQLModel, Relationship, JSON, Column

# --- User Models ---

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
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

# --- Secret Models ---
# For storing encrypted credentials

class SecretBase(SQLModel):
    key: str = Field(description="The name of the secret (e.g., 'CLICKHOUSE_HOST')")

class Secret(SecretBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    encrypted_value: bytes

    user: Optional[User] = Relationship(back_populates="secrets")

class SecretCreate(SecretBase):
    value: str

class SecretPublic(SecretBase):
    id: int
    user_id: int

# --- Supply Catalog Models ---

class SupplyModelBase(SQLModel):
    model_name: str = Field(index=True, unique=True, description="Unique name for the model, e.g., 'c6a.large'")
    provider: str = Field(default="aws", description="Cloud provider, e.g., 'aws', 'gcp'")
    cpu: int = Field(description="Number of vCPUs")
    memory_gb: float = Field(description="Memory in GiB")
    cost_per_hour: float = Field(description="On-demand cost per hour in USD")
    notes: Optional[str] = None

class SupplyModel(SupplyModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

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
