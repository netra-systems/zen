
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.db.models_clickhouse import UnifiedLogEntry, AnalysisRequest
from app.schema import DiscoveredPattern, LearnedPolicy, CostComparison

class AgentState(BaseModel):
    """Extends the base state to include analysis-specific data."""
    request: Optional[AnalysisRequest] = None
    raw_logs: Optional[List[UnifiedLogEntry]] = None
    patterns: Optional[List[DiscoveredPattern]] = None
    policies: Optional[List[LearnedPolicy]] = None
    cost_comparison: Optional[CostComparison] = None
    final_report: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None
    span_map: Optional[Dict[str, UnifiedLogEntry]] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            UnifiedLogEntry: lambda v: v.to_dict(),
            DiscoveredPattern: lambda v: v.dict(),
            LearnedPolicy: lambda v: v.dict(),
            CostComparison: lambda v: v.dict(),
            AnalysisRequest: lambda v: v.dict(),
        }
