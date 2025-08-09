from pydantic import BaseModel
from typing import Dict
from datetime import datetime

class AnalysisResult(BaseModel):
    id: str
    analysis_id: str
    data: Dict
    created_at: datetime
