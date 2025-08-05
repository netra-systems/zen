from typing import Any, Dict

class KVCacheFinder:
    def __init__(self, system_inspector: any):
        self.system_inspector = system_inspector

    async def run(self) -> str:
        """
        Finds all KV caches in the system.
        """
        resources = await self.system_inspector.find_resources("kv_cache")
        return "KV caches found."