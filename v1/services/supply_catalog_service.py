# /services/supply_catalog_service.py
import uuid
from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Import the database model and Pydantic schema
from services.data.database import SupplyOptionDB

# --- Pydantic Schemas ---
# These schemas are used for API validation and response models, not for DB storage.

class ModelIdentifier(BaseModel):
    provider: str
    family: str
    name: str

class SupplyOption(BaseModel):
    option_id: str = Field(alias="id") # Alias 'id' from DB to 'option_id' for the API
    model: ModelIdentifier
    hosting_type: Literal["api_provider", "self_hosted"]
    quantization: Optional[str] = None
    cost_per_million_tokens_usd: Dict[Literal["prompt", "completion"], float]
    base_latency_ms: int
    time_to_first_token_ms: int
    quality_score: float

    class Config:
        orm_mode = True # Allows Pydantic to read data from ORM models
        allow_population_by_field_name = True

class SupplyOptionCreate(BaseModel):
    """Schema for creating a new supply option."""
    provider: str
    family: str
    name: str
    hosting_type: Literal["api_provider", "self_hosted"]
    quantization: Optional[str] = None
    cost_per_million_tokens_usd: Dict[Literal["prompt", "completion"], float]
    base_latency_ms: int
    time_to_first_token_ms: int
    quality_score: float

# --- Supply Catalog Service (Database-Backed) ---

class SupplyCatalog:
    def __init__(self, db_session: Session):
        self.db = db_session

    def _db_to_pydantic(self, db_option: SupplyOptionDB) -> SupplyOption:
        """Converts a DB ORM model to a Pydantic API model."""
        return SupplyOption(
            id=db_option.id,
            model=ModelIdentifier(provider=db_option.provider, family=db_option.family, name=db_option.name),
            hosting_type=db_option.hosting_type,
            quantization=db_option.quantization,
            cost_per_million_tokens_usd=db_option.cost_per_million_tokens_usd,
            base_latency_ms=db_option.base_latency_ms,
            time_to_first_token_ms=db_option.time_to_first_token_ms,
            quality_score=db_option.quality_score
        )

    def get_all_options(self) -> List[SupplyOption]:
        """Returns all available supply options from the database."""
        db_options = self.db.query(SupplyOptionDB).all()
        return [self._db_to_pydantic(opt) for opt in db_options]

    def get_option_by_id(self, option_id: str) -> Optional[SupplyOption]:
        """Retrieves a specific supply option by its unique ID."""
        db_option = self.db.query(SupplyOptionDB).filter(SupplyOptionDB.id == option_id).first()
        return self._db_to_pydantic(db_option) if db_option else None

    def add_option(self, option_data: SupplyOptionCreate) -> SupplyOption:
        """Adds a new supply option to the database."""
        db_option = SupplyOptionDB(
            id=f"sup_{uuid.uuid4().hex[:8]}",
            **option_data.dict()
        )
        self.db.add(db_option)
        self.db.commit()
        self.db.refresh(db_option)
        return self._db_to_pydantic(db_option)
    
    def update_option(self, option_id: str, option_data: SupplyOptionCreate) -> Optional[SupplyOption]:
        """Updates an existing supply option in the database."""
        db_option = self.db.query(SupplyOptionDB).filter(SupplyOptionDB.id == option_id).first()
        if db_option:
            for key, value in option_data.dict().items():
                setattr(db_option, key, value)
            self.db.commit()
            self.db.refresh(db_option)
            return self._db_to_pydantic(db_option)
        return None

    def delete_option(self, option_id: str) -> bool:
        """Deletes a supply option from the database."""
        db_option = self.db.query(SupplyOptionDB).filter(SupplyOptionDB.id == option_id).first()
        if db_option:
            self.db.delete(db_option)
            self.db.commit()
            return True
        return False
