from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class DeepAgentState(BaseModel):
    user_request: str
    triage_result: Optional[Dict[str, Any]] = None
    data_result: Optional[Dict[str, Any]] = None
    optimizations_result: Optional[Dict[str, Any]] = None
    action_plan_result: Optional[Dict[str, Any]] = None
    report_result: Optional[Dict[str, Any]] = None
    final_report: Optional[str] = None