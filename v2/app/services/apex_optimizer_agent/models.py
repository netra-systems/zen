# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:48:31.172894+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to apex optimizer tools
# Git: v6 | be70ff77 | clean
# Change: Feature | Scope: Module | Risk: High
# Session: f4b153af-998e-4648-bfed-e03ac78b4b8f | Seq: 2
# Review: Pending | Score: 85
# ================================
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
import enum
import time

class AgentState(BaseModel):
    messages: List[BaseMessage]
    next_node: str
    tool_results: Optional[List[Dict]] = None

class ToolStatus(str, enum.Enum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL_SUCCESS = "partial_success"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"

class ToolInput(BaseModel):
    tool_name: str
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}

class ToolResult(BaseModel):
    tool_input: ToolInput
    status: ToolStatus = ToolStatus.IN_PROGRESS
    message: str = ""
    payload: Optional[Any] = None
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None

    def complete(self, status: ToolStatus, message: str, payload: Optional[Any] = None):
        self.status = status
        self.message = message
        self.payload = payload
        self.end_time = time.time()

class ToolInvocation(BaseModel):
    tool_result: ToolResult

    def __init__(self, tool_name: str, *args, **kwargs):
        super().__init__(tool_result=ToolResult(tool_input=ToolInput(tool_name=tool_name, args=list(args), kwargs=kwargs)))

    def set_result(self, status: ToolStatus, message: str, payload: Optional[Any] = None):
        self.tool_result.complete(status, message, payload)

class DataSource(BaseModel):
    source_table: str
    filters: Optional[Dict[str, Any]] = None

class TimeRange(BaseModel):
    start_time: str
    end_time: str