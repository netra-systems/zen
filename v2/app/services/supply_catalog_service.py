# /v2/app/services/supply_catalog_service.py
import logging
from typing import List, Optional
from sqlmodel import Session, select
from ..db import models_postgres

logger = logging.getLogger(__name__)

class SupplyCatalogService:
    """
    Manages CRUD operations for LLM supply options.
    """

    def get_all_options(self, db_session: Session) -> List[models_postgres.SupplyOption]:
        """Returns all available supply options from the database."""
        return db_session.exec(select(models_postgres.SupplyOption)).all()

    def get_option_by_id(self, db_session: Session, option_id: int) -> Optional[models_postgres.SupplyOption]:
        """Retrieves a specific supply option by its unique ID."""
        return db_session.get(models_postgres.SupplyOption, option_id)
        
    def get_option_by_name(self, db_session: Session, name: str) -> Optional[models_postgres.SupplyOption]:
        """Retrieves a supply option by its model name."""
        statement = select(models_postgres.SupplyOption).where(models_postgres.SupplyOption.name == name)
        return db_session.exec(statement).first()

    def create_option(self, db_session: Session, option_data: models_postgres.SupplyOptionCreate) -> models_postgres.SupplyOption:
        """Adds a new supply option to the database."""
        db_option = models_postgres.SupplyOption.model_validate(option_data)
        db_session.add(db_option)
        db_session.commit()
        db_session.refresh(db_option)
        return db_option
    
    def update_option(self, db_session: Session, option_id: int, option_data: models_postgres.SupplyOptionUpdate) -> Optional[models_postgres.SupplyOption]:
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

    def delete_option(self, db_session: Session, option_id: int) -> bool:
        """Deletes a supply option from the database."""
        db_option = self.get_option_by_id(db_session, option_id)
        if db_option:
            db_session.delete(db_option)
            db_session.commit()
            return True
        return False
        
    def autofill_catalog(self, db_session: Session):
        """Populates the catalog with a default set of common models."""
        if self.get_all_options(db_session):
            logger.info("Catalog already contains data. Skipping autofill.")
            return

        default_options = [
            models_postgres.SupplyOptionCreate(provider="OpenAI", family="GPT-4", name="gpt-4-turbo", cost_per_million_tokens_usd={"prompt": 10.00, "completion": 30.00}, quality_score=0.95),
            models_postgres.SupplyOptionCreate(provider="OpenAI", family="GPT-4", name="gpt-4o", cost_per_million_tokens_usd={"prompt": 5.00, "completion": 15.00}, quality_score=0.97),
            models_postgres.SupplyOptionCreate(provider="Anthropic", family="Claude 3", name="claude-3-opus-20240229", cost_per_million_tokens_usd={"prompt": 15.00, "completion": 75.00}, quality_score=0.98),
            models_postgres.SupplyOptionCreate(provider="Anthropic", family="Claude 3", name="claude-3-sonnet-20240229", cost_per_million_tokens_usd={"prompt": 3.00, "completion": 15.00}, quality_score=0.92),
            models_postgres.SupplyOptionCreate(provider="Google", family="Gemini", name="gemini-1.5-pro-latest", cost_per_million_tokens_usd={"prompt": 3.50, "completion": 10.50}, quality_score=0.96),
        ]
        
        logger.info("Autofilling supply catalog with default models.")
        for option_data in default_options:
            self.create_option(db_session, option_data)
        logger.info("Default models added to the catalog.")
