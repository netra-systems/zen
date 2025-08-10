from pydantic import BaseModel

class UnifiedLogEntry(BaseModel):
    message: str
