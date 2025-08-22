from typing import Any

from pydantic import BaseModel


class RunComplete(BaseModel):
    run_id: str
    result: Any
