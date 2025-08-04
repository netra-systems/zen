from app.db.models_postgres import SupplyOption
from app.services.supply_catalog_service import SupplyCatalogService

class SupplyCatalogSearch:
    def __init__(self, db_session):
        self.db_session = db_session
        self.catalog_service = SupplyCatalogService()

    async def execute(self, query: str):
        return self.catalog_service.get_all_options(self.db_session)