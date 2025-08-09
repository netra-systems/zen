from pydantic import BaseModel
from typing import Optional

class SupplyOptionBase(BaseModel):
    name: str
    description: Optional[str] = None

class SupplyOptionCreate(SupplyOptionBase):
    pass

class SupplyOptionUpdate(SupplyOptionBase):
    pass

class SupplyOptionInDBBase(SupplyOptionBase):
    id: int

    class Config:
        from_attributes = True

class SupplyOption(SupplyOptionInDBBase):
    pass

class SupplyOptionInDB(SupplyOptionInDBBase):
    pass
