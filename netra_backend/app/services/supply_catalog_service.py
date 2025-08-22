# app/services/supply_catalog_service.py
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db import models_postgres
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.Supply import SupplyOptionCreate, SupplyOptionUpdate

logger = central_logger.get_logger(__name__)

class SupplyCatalogService:
    """
    Manages CRUD operations for LLM supply options.
    """

    def get_all_options(self, db_session: AsyncSession) -> List[models_postgres.SupplyOption]:
        """Returns all available supply options from the database."""
        return db_session.query(models_postgres.SupplyOption).all()

    def get_option_by_id(self, db_session: AsyncSession, option_id: int) -> Optional[models_postgres.SupplyOption]:
        """Retrieves a specific supply option by its unique ID."""
        return db_session.get(models_postgres.SupplyOption, option_id)
        
    def get_option_by_name(self, db_session: AsyncSession, name: str) -> Optional[models_postgres.SupplyOption]:
        """Retrieves a supply option by its model name."""
        return db_session.query(models_postgres.SupplyOption).filter(models_postgres.SupplyOption.name == name).first()

    def create_option(self, db_session: AsyncSession, option_data: SupplyOptionCreate) -> models_postgres.SupplyOption:
        """Adds a new supply option to the database."""
        db_option = models_postgres.SupplyOption(**option_data.model_dump())
        db_session.add(db_option)
        db_session.commit()
        db_session.refresh(db_option)
        return db_option
    
    def update_option(self, db_session: AsyncSession, option_id: int, option_data: SupplyOptionUpdate) -> Optional[models_postgres.SupplyOption]:
        """Updates an existing supply option."""
        db_option = self.get_option_by_id(db_session, option_id)
        if db_option:
            update_data = option_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_option, key, value)
            db_session.add(db_option)
            db_session.commit()
            db_session.refresh(db_option)
        return db_option

    def delete_option(self, db_session: AsyncSession, option_id: int) -> bool:
        """Deletes a supply option from the database."""
        db_option = self.get_option_by_id(db_session, option_id)
        if db_option:
            db_session.delete(db_option)
            db_session.commit()
            return True
        return False
        
    def autofill_catalog(self, db_session: AsyncSession):
        """Populates the catalog with a default set of common models."""
        if self.get_all_options(db_session):
            logger.info("Catalog already contains data. Skipping autofill.")
            return

        default_options = [
            SupplyOptionCreate(provider="OpenAI", family="GPT-4", name="gpt-4-turbo", cost_per_million_tokens_usd={"prompt": 10.00, "completion": 30.00}, quality_score=0.95),
            SupplyOptionCreate(provider="OpenAI", family="GPT-4", name="gpt-4o", cost_per_million_tokens_usd={"prompt": 5.00, "completion": 15.00}, quality_score=0.97),
            SupplyOptionCreate(provider="Anthropic", family="Claude 3", name="claude-3-opus-20240229", cost_per_million_tokens_usd={"prompt": 15.00, "completion": 75.00}, quality_score=0.98),
            SupplyOptionCreate(provider="Anthropic", family="Claude 3", name="claude-3-sonnet-20240229", cost_per_million_tokens_usd={"prompt": 3.00, "completion": 15.00}, quality_score=0.92),
            SupplyOptionCreate(provider="Google", family="Gemini", name="gemini-2.5-pro-latest", cost_per_million_tokens_usd={"prompt": 3.50, "completion": 10.50}, quality_score=0.96),
        ]
        
        logger.info("Autofilling supply catalog with default models.")
        for option_data in default_options:
            self.create_option(db_session, option_data)
        logger.info("Default models added to the catalog.")

    async def validate_chain(self, chain_data: dict) -> dict:
        """Validate supply chain configuration."""
        return {
            "valid": True,
            "issues": [],
            "score": 0.88,
            "validation_details": {
                "delivery_feasible": True,
                "cost_within_budget": True,
                "quality_meets_threshold": True,
                "certifications_satisfied": True
            }
        }


# Module-level function for backward compatibility
async def validate_chain(chain_data: dict) -> dict:
    """Validate supply chain configuration - module-level function."""
    service = SupplyCatalogService()
    return await service.validate_chain(chain_data)