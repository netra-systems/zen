from typing import List, Dict, Any, Optional
from app.deepagents.graph import DeepAgentState
from app.db.models_clickhouse import UnifiedLogEntry, AnalysisRequest
from app.schema import DiscoveredPattern, LearnedPolicy, CostComparison

class AgentState(DeepAgentState):
    """Extends the base state to include analysis-specific data."""
    request: Optional[AnalysisRequest] = None
    raw_logs: Optional[List[UnifiedLogEntry]] = None
    patterns: Optional[List[DiscoveredPattern]] = None
    policies: Optional[List[LearnedPolicy]] = None
    cost_comparison: Optional[CostComparison] = None
    final_report: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None
