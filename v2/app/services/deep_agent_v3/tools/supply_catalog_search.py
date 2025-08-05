from typing import Any, Dict, List
from app.db.session import get_db_session
from app.db.models_postgres import Supply
from sqlmodel import select
from app.services.deep_agent_v3.tools.base import BaseTool, ToolMetadata
from app.services.supply_catalog_service import SupplyCatalogService

class SupplyCatalogSearch(BaseTool):
    name = "supply_catalog_search"
    metadata = ToolMetadata(
        name="SupplyCatalogSearch",
        description="Searches the supply catalog for available models and resources.",
        version="1.0.0",
        status="in_review"
    )

    def __init__(self, db_session):
        self.db_session = db_session
        self.supply_catalog_service = SupplyCatalogService()

    async def search(self, query: str) -> List[Supply]:
        """
        Searches the supply catalog for available models and resources.
        """
        all_options = self.supply_catalog_service.get_all_options(self.db_session)
        return [option for option in all_options if query in option.name]