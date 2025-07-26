# /v2/pydantic_models.py
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: str
    created_at: datetime

    class Config:
        orm_mode = True

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
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# --- AnalysisRun Schemas ---
class AnalysisRunBase(BaseModel):
    config: Optional[Dict[str, Any]] = Field(None, description="Configuration parameters for the analysis run.")

class AnalysisRunCreate(AnalysisRunBase):
    pass

class AnalysisRun(AnalysisRunBase):
    id: str
    user_id: str
    status: str
    execution_log: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None
    result_details: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        orm_mode = True
