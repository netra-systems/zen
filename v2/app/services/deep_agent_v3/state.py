from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from app.db.models_clickhouse import UnifiedLogEntry, AnalysisRequest
from app.schema import DiscoveredPattern, LearnedPolicy, CostComparison

class AgentState(BaseModel):
    """Extends the base state to include analysis-specific data."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    messages: List[Dict[str, Any]] = []
    request: Optional[AnalysisRequest] = None
    raw_logs: Optional[List[UnifiedLogEntry]] = None
    patterns: Optional[List[DiscoveredPattern]] = None
    policies: Optional[List[LearnedPolicy]] = None
    cost_comparison: Optional[CostComparison] = None
    final_report: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None
    span_map: Optional[Dict[str, UnifiedLogEntry]] = None
    trace_ids: Optional[List[str]] = None