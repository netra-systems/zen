from typing import Any, Dict, List
from app.db.session import get_db_session
from app.db.models_postgres import Supply
from sqlmodel import select
from app.services.deep_agent_v3.tools.base import BaseTool, ToolMetadata

class SupplyCatalogSearch(BaseTool):
    metadata = ToolMetadata(
        name="SupplyCatalogSearch",
        description="Searches the supply catalog for available models and resources.",
        version="1.0.0",
        status="production"
    )

    async def search(self, query: str) -> List[Supply]:
        """
        Searches the supply catalog for available models and resources.
        """
        async with get_db_session() as session:
            result = await session.execute(select(Supply).where(Supply.name.like(f"%{query}%")))
            return result.scalars().all()