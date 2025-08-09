from pydantic import BaseModel
from typing import Dict

class Performance(BaseModel):
    latency_ms: Dict[str, float]
