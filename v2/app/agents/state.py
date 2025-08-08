from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class DeepAgentState(BaseModel):
    analysis_request: Optional[Dict[str, Any]] = None
    results: List[Dict[str, Any]] = []
    current_step: int = 0
