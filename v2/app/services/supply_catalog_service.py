# /v2/services/supply_catalog_service.py
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from .. import database as db
from ..pydantic_models import SupplyOptionCreate, SupplyOptionUpdate # Assuming pydantic_models.py exists

logger = logging.getLogger(__name__)

class SupplyCatalogService:
    """
    Manages the CRUD operations for LLM supply options using a database session.
    """

    def get_all_options(self, db_session: Session) -> List[db.SupplyOption]:
        """Returns all available supply options from the database."""
        logger.info("Fetching all supply options from the database.")
        return db_session.query(db.SupplyOption).all()

    def get_option_by_id(self, db_session: Session, option_id: str) -> Optional[db.SupplyOption]:
        """Retrieves a specific supply option by its unique ID."""
        logger.info(f"Fetching supply option with id: {option_id}")
        return db_session.query(db.SupplyOption).filter(db.SupplyOption.id == option_id).first()

    def create_option(self, db_session: Session, option_data: SupplyOptionCreate) -> db.SupplyOption:
        """Adds a new supply option to the database."""
        logger.info(f"Creating new supply option: {option_data.name}")
        db_option = db.SupplyOption(**option_data.dict())
        db_session.add(db_option)
        db_session.commit()
        db_session.refresh(db_option)
        return db_option
    
    def update_option(self, db_session: Session, option_id: str, option_data: SupplyOptionUpdate) -> Optional[db.SupplyOption]:
        """Updates an existing supply option in the database."""
        db_option = self.get_option_by_id(db_session, option_id)
        if db_option:
            logger.info(f"Updating supply option with id: {option_id}")
            update_data = option_data.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_option, key, value)
            db_session.commit()
            db_session.refresh(db_option)
            return db_option
        logger.warning(f"Update failed: Supply option with id {option_id} not found.")
        return None

    def delete_option(self, db_session: Session, option_id: str) -> bool:
        """Deletes a supply option from the database."""
        db_option = self.get_option_by_id(db_session, option_id)
        if db_option:
            logger.info(f"Deleting supply option with id: {option_id}")
            db_session.delete(db_option)
            db_session.commit()
            return True
        logger.warning(f"Delete failed: Supply option with id {option_id} not found.")
        return False
        
    def autofill_catalog(self, db_session: Session):
        """Populates the catalog with a default set of common models."""
        logger.info("Checking if supply catalog needs to be autofilled.")
        if self.get_all_options(db_session):
            logger.info("Catalog already contains data. Skipping autofill.")
            return

        default_options = [
            SupplyOptionCreate(provider="OpenAI", family="GPT-4", name="gpt-4-turbo", cost_per_million_tokens_usd={"prompt": 10.00, "completion": 30.00}, quality_score=0.95),
            SupplyOptionCreate(provider="OpenAI", family="GPT-4", name="gpt-4o", cost_per_million_tokens_usd={"prompt": 5.00, "completion": 15.00}, quality_score=0.97),
            SupplyOptionCreate(provider="Anthropic", family="Claude 3", name="claude-3-opus-20240229", cost_per_million_tokens_usd={"prompt": 15.00, "completion": 75.00}, quality_score=0.98),
            SupplyOptionCreate(provider="Anthropic", family="Claude 3", name="claude-3-sonnet-20240229", cost_per_million_tokens_usd={"prompt": 3.00, "completion": 15.00}, quality_score=0.92),
            SupplyOptionCreate(provider="Google", family="Gemini", name="gemini-1.5-pro-latest", cost_per_million_tokens_usd={"prompt": 3.50, "completion": 10.50}, quality_score=0.96),
        ]
        
        logger.info("Autofilling supply catalog with default models.")
        for option_data in default_options:
            self.create_option(db_session, option_data)
        logger.info("Default models added to the catalog.")
