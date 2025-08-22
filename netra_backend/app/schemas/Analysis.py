from datetime import datetime
from typing import Dict

from pydantic import BaseModel


class AnalysisResult(BaseModel):
    id: str
    analysis_id: str
    data: Dict
    created_at: datetime
