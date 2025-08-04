from app.db.models_postgres import SupplyOption
from app.services.supply_catalog_service import SupplyCatalog

class SupplyCatalogSearch:
    def __init__(self, db_session):
        self.db_session = db_session

    async def execute(self, query: str):
        return await SupplyCatalog.list_all_records(self.db_session)