from typing import Dict

from pydantic import BaseModel


class Performance(BaseModel):
    latency_ms: Dict[str, float]
