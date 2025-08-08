from typing import List, Optional, TypedDict
from langchain_core.messages import BaseMessage
from app.schemas import AnalysisRequest

class DeepAgentState(TypedDict):
    messages: List[BaseMessage]
    run_id: str
    stream_updates: bool
    analysis_request: AnalysisRequest
    current_agent: str
    tool_calls: Optional[List[dict]] = None