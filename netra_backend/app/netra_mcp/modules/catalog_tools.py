"""Catalog Tools Module - MCP tools for supply catalog operations"""

import json
from typing import Optional


class CatalogTools:
    """Supply catalog tools registration"""
    
    def __init__(self, mcp_instance):
        self.mcp = mcp_instance
        
    def register_all(self, server):
        """Register supply catalog tools"""
        @self.mcp.tool()
        async def get_supply_catalog(filter: Optional[str] = None) -> str:
            """Get available AI models and providers"""
            return await self._execute_catalog_query(server, filter)
    
    async def _execute_catalog_query(self, server, filter: Optional[str]) -> str:
        """Execute catalog query with error handling"""
        if not server.supply_catalog_service:
            return self._get_mock_catalog()
        try:
            return await self._query_supply_catalog(server, filter)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    async def _query_supply_catalog(self, server, filter: Optional[str]) -> str:
        """Query supply catalog service"""
        catalog = await server.supply_catalog_service.get_catalog(
            filter_criteria=filter
        )
        return json.dumps(catalog, indent=2)
    
    def _get_mock_catalog(self) -> str:
        """Get mock catalog data when service unavailable"""
        catalog = self._build_mock_catalog_data()
        return json.dumps(catalog, indent=2)
    
    def _build_mock_catalog_data(self) -> dict:
        """Build mock catalog structure"""
        providers = self._get_all_mock_providers()
        return {"providers": providers}
    
    def _get_all_mock_providers(self) -> list:
        """Get all mock provider configurations"""
        return [
            self._get_anthropic_provider(),
            self._get_openai_provider(),
            self._get_google_provider()
        ]
    
    def _get_anthropic_provider(self) -> dict:
        """Get Anthropic provider configuration"""
        return {
            "name": "Anthropic",
            "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
        }
    
    def _get_openai_provider(self) -> dict:
        """Get OpenAI provider configuration"""
        return {
            "name": "OpenAI",
            "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        }
    
    def _get_google_provider(self) -> dict:
        """Get Google provider configuration"""
        return {
            "name": "Google",
            "models": ["gemini-pro", "gemini-pro-vision"]
        }