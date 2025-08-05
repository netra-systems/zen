from typing import Any, List
from app.db.models_postgres import SupplyOption
from sqlalchemy.future import select

class SupplyCatalogSearch:
    def __init__(self, db_session: Any):
        self.db_session = db_session

    async def execute(self) -> List[SupplyOption]:
        """Retrieves the supply catalog from the database."""
        return self.db_session.exec(select(SupplyOption)).all()