from pydantic import BaseModel
from typing import Dict

class EnrichedMetrics(BaseModel):
    data: Dict[str, str]
