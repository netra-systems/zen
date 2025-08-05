
from typing import Any, List
from app.db.models_postgres import SupplyOption
from app.services.deep_agent_v3.core import get_supply_catalog

class SupplyCatalogSearch:
    def __init__(self, db_session: Any):
        self.db_session = db_session

    async def execute(self) -> List[SupplyOption]:
        return await get_supply_catalog(self.db_session)
