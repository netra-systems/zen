import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Settings(BaseModel):
    debug_mode: bool

class DataSource(BaseModel):
    source_table: str
    filters: Optional[Dict[str, Any]] = None

class TimeRange(BaseModel):
    start_time: str
    end_time: str

class Workload(BaseModel):
    run_id: str
    query: str
    data_source: DataSource
    time_range: TimeRange

class RequestModel(BaseModel):
    id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:8]}")
    user_id: str
    query: str
    workloads: List[Workload]
    constraints: Optional[Any] = None

class Response(BaseModel):
    response: Dict[str, Any]
    completion: Dict[str, Any]
    tool_calls: Dict[str, Any]
    usage: Dict[str, Any]
    system: Dict[str, Any]

class StartAgentPayload(BaseModel):
    settings: Settings
    request: RequestModel

class StartAgentMessage(BaseModel):
    action: str
    payload: StartAgentPayload