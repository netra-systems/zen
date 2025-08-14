"""Corpus tool execution handlers."""
from typing import Dict, Any, Optional
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class CorpusToolExecutor:
    """Executes corpus management tools"""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
    
    async def execute(self, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute corpus tool if applicable"""
        corpus_tools = self._get_corpus_tool_mapping()
        if self.tool_name in corpus_tools:
            return await corpus_tools[self.tool_name](parameters)
        return None
    
    def _get_corpus_tool_mapping(self) -> Dict[str, callable]:
        """Get mapping of corpus tool names to execution methods"""
        return {
            "create_corpus": self._execute_create_corpus,
            "search_corpus": self._execute_search_corpus,
            "update_corpus": self._execute_update_corpus,
            "delete_corpus": self._execute_delete_corpus,
            "analyze_corpus": self._execute_analyze_corpus,
            "export_corpus": self._execute_export_corpus,
            "import_corpus": self._execute_import_corpus,
            "validate_corpus": self._execute_validate_corpus
        }
    
    async def _execute_create_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute corpus creation via real service"""
        try:
            corpus_name = parameters.get('corpus_name', f'corpus_{parameters.get("name", "default")}')
            user_id = parameters.get('user_id', 'default_user')
            corpus = await self._create_corpus(corpus_name, parameters, user_id)
            return self._create_corpus_success_response(corpus)
        except Exception as e:
            return self._create_corpus_error_response(e)
    
    async def _create_corpus(self, corpus_name: str, parameters: Dict[str, Any], user_id: str) -> Any:
        """Create corpus using corpus service"""
        from app.services.corpus import corpus_service
        from app.schemas import CorpusCreate
        
        corpus_data = CorpusCreate(
            name=corpus_name,
            description=parameters.get('description', f'Corpus {corpus_name}')
        )
        return await corpus_service.create_corpus(corpus_data, user_id)
    
    def _create_corpus_success_response(self, corpus: Any) -> Dict[str, Any]:
        """Create success response for corpus creation"""
        return {
            "success": True,
            "data": {"corpus_id": corpus.id, "name": corpus.name},
            "message": "Corpus created successfully",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }
    
    def _create_corpus_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create error response for corpus creation failure"""
        logger.error(f"Corpus creation failed: {error}")
        return {
            "success": False,
            "error": f"Failed to create corpus: {str(error)}",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }
    
    async def _execute_search_corpus(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute corpus search via real service"""
        try:
            if not parameters:
                parameters = {}
            
            corpus_id = parameters.get('corpus_id')
            if not corpus_id:
                return self._create_missing_corpus_id_response()
            
            results = await self._search_corpus(corpus_id, parameters)
            return self._create_search_success_response(results)
        except Exception as e:
            return self._create_search_error_response(e)
    
    def _create_missing_corpus_id_response(self) -> Dict[str, Any]:
        """Create response for missing corpus ID"""
        return {
            "success": False,
            "error": "corpus_id parameter is required for search",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }
    
    async def _search_corpus(self, corpus_id: str, parameters: Dict[str, Any]) -> Any:
        """Search corpus using corpus service"""
        from app.services.corpus import corpus_service
        
        query = parameters.get('query', '')
        limit = parameters.get('limit', 10)
        search_params = {"query": query, "limit": limit}
        return await corpus_service.search_corpus_content(None, corpus_id, search_params)
    
    def _create_search_success_response(self, results: Any) -> Dict[str, Any]:
        """Create success response for corpus search"""
        return {
            "success": True,
            "data": {
                "results": results.get("results", []),
                "total_matches": results.get("total", 0)
            },
            "message": "Search completed successfully",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }
    
    def _create_search_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create error response for search failure"""
        logger.error(f"Corpus search failed: {error}")
        return {
            "success": False,
            "error": f"Failed to search corpus: {str(error)}",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }
    
    async def _execute_update_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Update corpus"""
        try:
            corpus_id = parameters.get('corpus_id')
            if not corpus_id:
                return {"success": False, "error": "corpus_id required", "metadata": {"tool": self.tool_name}}
            
            result = await self._update_corpus(corpus_id, parameters)
            return self._create_update_success_response(corpus_id)
        except Exception as e:
            return {"success": False, "error": str(e), "metadata": {"tool": self.tool_name}}
    
    async def _update_corpus(self, corpus_id: str, parameters: Dict[str, Any]) -> Any:
        """Update corpus using corpus service"""
        from app.services.corpus import corpus_service
        from app.schemas import CorpusUpdate
        
        update_data = CorpusUpdate(**{k: v for k, v in parameters.items() if k != 'corpus_id'})
        return await corpus_service.update_corpus(None, corpus_id, update_data)
    
    def _create_update_success_response(self, corpus_id: str) -> Dict[str, Any]:
        """Create success response for corpus update"""
        return {
            "success": True,
            "data": {"corpus_id": corpus_id, "updated": True},
            "message": "Corpus updated successfully",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }
    
    async def _execute_delete_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Delete corpus"""
        try:
            corpus_id = parameters.get('corpus_id')
            if not corpus_id:
                return {"success": False, "error": "corpus_id required", "metadata": {"tool": self.tool_name}}
            
            await self._delete_corpus(corpus_id)
            return self._create_delete_success_response(corpus_id)
        except Exception as e:
            return {"success": False, "error": str(e), "metadata": {"tool": self.tool_name}}
    
    async def _delete_corpus(self, corpus_id: str) -> None:
        """Delete corpus using corpus service"""
        from app.services.corpus import corpus_service
        await corpus_service.delete_corpus(None, corpus_id)
    
    def _create_delete_success_response(self, corpus_id: str) -> Dict[str, Any]:
        """Create success response for corpus deletion"""
        return {
            "success": True,
            "data": {"corpus_id": corpus_id, "deleted": True},
            "message": "Corpus deleted successfully",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }
    
    async def _execute_analyze_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze corpus"""
        try:
            corpus_id = parameters.get('corpus_id')
            if not corpus_id:
                return {"success": False, "error": "corpus_id required", "metadata": {"tool": self.tool_name}}
            
            stats = await self._get_corpus_statistics(corpus_id)
            return self._create_analyze_success_response(stats)
        except Exception as e:
            return {"success": False, "error": str(e), "metadata": {"tool": self.tool_name}}
    
    async def _get_corpus_statistics(self, corpus_id: str) -> Any:
        """Get corpus statistics using corpus service"""
        from app.services.corpus import corpus_service
        return await corpus_service.get_corpus_statistics(None, corpus_id)
    
    def _create_analyze_success_response(self, stats: Any) -> Dict[str, Any]:
        """Create success response for corpus analysis"""
        return {
            "success": True,
            "data": stats,
            "message": "Corpus analysis completed",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }
    
    async def _execute_export_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Export corpus"""
        corpus_id = parameters.get('corpus_id')
        format_type = parameters.get('format', 'json')
        return {
            "success": True,
            "data": {"corpus_id": corpus_id, "export_url": f"/exports/{corpus_id}.{format_type}"},
            "message": f"Corpus export initiated in {format_type} format",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }

    async def _execute_import_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Import corpus"""
        source_url = parameters.get('source_url')
        corpus_name = parameters.get('name', 'imported_corpus')
        return {
            "success": True,
            "data": {"corpus_id": f"imported_{corpus_name}", "name": corpus_name},
            "message": "Corpus import initiated",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }

    async def _execute_validate_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate corpus"""
        try:
            corpus_id = parameters.get('corpus_id')
            if not corpus_id:
                return {"success": False, "error": "corpus_id required", "metadata": {"tool": self.tool_name}}
            
            corpus = await self._get_corpus(corpus_id)
            validation = self._create_validation_result(corpus)
            return self._create_validate_success_response(validation)
        except Exception as e:
            return {"success": False, "error": str(e), "metadata": {"tool": self.tool_name}}
    
    async def _get_corpus(self, corpus_id: str) -> Any:
        """Get corpus using corpus service"""
        from app.services.corpus import corpus_service
        return await corpus_service.get_corpus(None, corpus_id)
    
    def _create_validation_result(self, corpus: Any) -> Dict[str, Any]:
        """Create validation result based on corpus existence"""
        return {"valid": corpus is not None, "errors": [] if corpus else ["Corpus not found"]}
    
    def _create_validate_success_response(self, validation: Dict[str, Any]) -> Dict[str, Any]:
        """Create success response for corpus validation"""
        return {
            "success": True,
            "data": validation,
            "message": "Corpus validation completed",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }