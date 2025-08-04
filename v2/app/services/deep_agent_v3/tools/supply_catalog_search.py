
from app.services.deep_agent_v3.tools.base import BaseTool
from app.core.supply_catalog import SupplyCatalog

class SupplyCatalogSearch(BaseTool):
    async def search_supply_catalog(self, query):
        catalog = SupplyCatalog()
        records = catalog.list_all_records()
        return [record for record in records if query in record.model_name]
