from typing import Any, Dict, List
from app.db.session import get_db_session
from app.db.models_postgres import Supply
from sqlmodel import select

class SupplyCatalogSearch:
    def __init__(self, db_session: Any):
        self.db_session = db_session

    async def search(self, query: str) -> List[Supply]:
        """
        Searches the supply catalog for available models and resources.
        """
        async with get_db_session() as session:
            result = await session.execute(select(Supply).where(Supply.name.like(f"%{query}%")))
            return result.scalars().all()
