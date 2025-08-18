"""GitHub Analyzer Service Schemas.

Type definitions for GitHub code analysis service.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    """Request to analyze a GitHub repository."""
    
    repository_url: str = Field(
        ..., 
        description="GitHub repository URL or local path"
    )
    output_format: str = Field(
        default="json",
        description="Output format (json, markdown, html)"
    )
    scan_depth: str = Field(
        default="auto",
        description="Scan depth (complete, targeted, sampling, auto)"
    )
    include_security: bool = Field(
        default=True,
        description="Include security analysis"
    )


class AIProvider(BaseModel):
    """AI provider information."""
    
    name: str
    pattern_count: int
    files: List[str]


class LLMEndpoint(BaseModel):
    """LLM endpoint information."""
    
    file: str
    line: int
    provider: str
    model: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolInfo(BaseModel):
    """Tool or function information."""
    
    file: str
    line: int
    type: str
    name: str
    description: Optional[str] = None


class ConfigFile(BaseModel):
    """Configuration file information."""
    
    file: str
    ai_configs: int
    has_credentials: bool = False


class SecurityInfo(BaseModel):
    """Security analysis information."""
    
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    exposed_keys: List[str] = Field(default_factory=list)


class AnalysisMetrics(BaseModel):
    """Analysis metrics."""
    
    total_llm_calls: int
    unique_models: int
    agent_count: int
    tool_count: int
    config_files: int
    ai_files: int
    estimated_complexity: str


class AIOperationsMap(BaseModel):
    """Complete AI operations map."""
    
    repository_info: Dict[str, Any]
    ai_infrastructure: Dict[str, Any]
    code_locations: Dict[str, Any]
    security: SecurityInfo
    dependencies: Dict[str, Any]
    metrics: AnalysisMetrics
    recommendations: List[str]
    formatted_output: Optional[str] = None


class AnalysisResponse(BaseModel):
    """Response from GitHub analysis."""
    
    success: bool
    analysis_id: str
    repository_url: str
    analyzed_at: datetime
    result: Optional[AIOperationsMap] = None
    error: Optional[str] = None
    status: str = Field(
        default="completed",
        description="Analysis status"
    )


class AnalysisStatus(BaseModel):
    """Analysis status response."""
    
    analysis_id: str
    status: str
    progress: int
    message: str
    started_at: datetime
    completed_at: Optional[datetime] = None