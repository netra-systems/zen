from pydantic import BaseModel
import uuid
from datetime import datetime

class EventMetadata(BaseModel):
    log_schema_version: str
    event_id: uuid.UUID
    timestamp_utc: datetime
    ingestion_source: str

class TraceContext(BaseModel):
    trace_id: uuid.UUID
    span_id: uuid.UUID
    span_name: str
    span_kind: str