from pydantic import BaseModel
from typing import Dict

class FinOps(BaseModel):
    attribution: Dict[str, str]
    cost: Dict[str, float]
    pricing_info: Dict[str, str]

class CostComparison(BaseModel):
    data: Dict[str, str]