from typing import Any, Dict, List
from app.db.session import get_db_session
from app.db.models_postgres import SupplyOption
from sqlmodel import select
from app.services.apex_optimizer_agent.tools.base import BaseTool, ToolMetadata
from app.services.supply_catalog_service import SupplyCatalogService

class SupplyCatalogSearch(BaseTool):
    metadata = ToolMetadata(
        name="supply_catalog_search",
        description="Searches the supply catalog for available models and resources.",
        version="1.0.0",
        status="in_review"
    )

    def __init__(self, db_session):
        super().__init__(db_session=db_session)
        self.supply_catalog_service = SupplyCatalogService()

    async def run(self, query: str) -> List[SupplyOption]:
        """
        Searches the supply catalog for available models and resources.
        """
        all_options = self.supply_catalog_service.get_all_options(self.db_session)
        return [option for option in all_options if query in option.name]