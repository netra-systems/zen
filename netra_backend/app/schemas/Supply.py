from typing import Optional

from pydantic import BaseModel, ConfigDict


class ModelIdentifier(BaseModel):
    provider: str
    model_name: str

class SupplyOptionBase(BaseModel):
    name: str
    description: Optional[str] = None

class SupplyOptionCreate(SupplyOptionBase):
    pass

class SupplyOptionUpdate(SupplyOptionBase):
    pass

class SupplyOptionInDBBase(SupplyOptionBase):
    id: int

    model_config = ConfigDict(from_attributes=True, extra="allow")

class SupplyOption(SupplyOptionInDBBase):
    pass

class SupplyOptionInDB(SupplyOptionInDBBase):
    pass