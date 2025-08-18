"""Data Tools Module - MCP tools for data management operations"""

import json
from typing import Dict, Any, Optional


class DataTools:
    """Data management tools registration"""
    
    def __init__(self, mcp_instance):
        self.mcp = mcp_instance
        
    def register_all(self, server):
        """Register data management tools"""
        self._register_corpus_query_tool(server)
        self._register_synthetic_data_tool(server)
    
    def _register_corpus_query_tool(self, server):
        """Register corpus query tool"""
        @self.mcp.tool()
        async def query_corpus(
            query: str,
            limit: int = 10,
            filters: Optional[Dict[str, Any]] = None
        ) -> str:
            """Search the document corpus for relevant information"""
            return await self._execute_corpus_query(server, query, limit, filters)
    
    async def _execute_corpus_query(self, server, query: str, limit: int, 
                                   filters: Optional[Dict[str, Any]]) -> str:
        """Execute corpus query with error handling"""
        if not server.corpus_service:
            return self._format_service_error("Corpus service not available")
        try:
            return await self._perform_corpus_search(server, query, limit, filters)
        except Exception as e:
            return self._format_service_error(str(e))
    
    async def _perform_corpus_search(self, server, query: str, limit: int, 
                                    filters: Optional[Dict[str, Any]]) -> str:
        """Perform corpus search operation"""
        results = await server.corpus_service.search(
            query=query, limit=limit, filters=filters or {}
        )
        return json.dumps(results, indent=2)
    
    def _format_service_error(self, error_message: str) -> str:
        """Format service error response"""
        return json.dumps({"error": error_message})
    
    def _register_synthetic_data_tool(self, server):
        """Register synthetic data generation tool"""
        @self.mcp.tool()
        async def generate_synthetic_data(
            schema: Dict[str, Any],
            count: int = 10,
            format: str = "json"
        ) -> str:
            """Generate synthetic test data for AI workloads"""
            return await self._execute_synthetic_data_generation(server, schema, count, format)
    
    async def _execute_synthetic_data_generation(self, server, schema: Dict[str, Any], 
                                               count: int, format: str) -> str:
        """Execute synthetic data generation with error handling"""
        if not server.synthetic_data_service:
            return self._format_service_error("Synthetic data service not available")
        try:
            return await self._perform_synthetic_generation(server, schema, count, format)
        except Exception as e:
            return self._format_service_error(str(e))
    
    async def _perform_synthetic_generation(self, server, schema: Dict[str, Any], 
                                           count: int, format: str) -> str:
        """Perform synthetic data generation"""
        data = await server.synthetic_data_service.generate(
            schema=schema, count=count, format_type=format
        )
        return self._format_synthetic_data_result(data, count, format)
    
    def _format_synthetic_data_result(self, data: Any, count: int, format: str) -> str:
        """Format synthetic data generation result"""
        if format == "json":
            return self._format_json_result(data, count)
        else:
            return self._format_custom_result(count, format)
    
    def _format_json_result(self, data: Any, count: int) -> str:
        """Format JSON format result"""
        return json.dumps({
            "status": "success", "count": count, "data": data
        }, indent=2)
    
    def _format_custom_result(self, count: int, format: str) -> str:
        """Format custom format result"""
        return json.dumps({
            "status": "success", "count": count, "format": format,
            "message": f"Generated {count} records in {format} format"
        }, indent=2)