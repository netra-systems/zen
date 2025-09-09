from typing import Any, Dict, List

from sqlmodel import select

from netra_backend.app.db.models_postgres import SupplyOption
from netra_backend.app.database import get_db
from netra_backend.app.services.apex_optimizer_agent.tools.base import (
    BaseTool,
    ToolMetadata,
)
from netra_backend.app.services.apex_optimizer_agent.tools.context import ToolContext
from netra_backend.app.services.supply_catalog_service import SupplyCatalogService


class SupplyCatalogSearch(BaseTool):
    metadata = ToolMetadata(
        name="supply_catalog_search",
        description="Searches the supply catalog for available models and resources.",
        version="1.0.0",
        status="in_review"
    )

    async def run(self, context: ToolContext, query: str) -> List[SupplyOption]:
        """
        Searches the supply catalog for available models and resources.
        """
        all_options = context.supply_catalog.get_all_options(context.db_session)
        return [option for option in all_options if query in option.name]
