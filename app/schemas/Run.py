from pydantic import BaseModel
from typing import Any

class RunComplete(BaseModel):
    run_id: str
    result: Any
