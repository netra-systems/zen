"""Netra MCP Server Data Models"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentInfo(BaseModel):
    """Agent information model"""
    name: str
    category: str
    description: str


class OptimizationHistory(BaseModel):
    """Optimization history entry"""
    id: str
    date: str
    type: str
    model: Optional[str] = None
    original: Optional[str] = None
    recommended: Optional[str] = None
    cost_reduction: str
    performance_gain: Optional[str] = None
    quality_maintained: Optional[bool] = None


class ModelConfig(BaseModel):
    """Model configuration"""
    context_window: int
    max_output: int
    price_per_1k_input: float
    price_per_1k_output: float
    rate_limit: int


class AgentCatalog(BaseModel):
    """Agent catalog entry"""
    description: str
    capabilities: List[str]
    input_schema: Optional[Dict[str, Any]] = None
    example_usage: Optional[Dict[str, Any]] = None
    optimization_strategies: Optional[List[str]] = None