"""Corpus tool execution handlers."""
from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger

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
            **self._get_primary_tool_mapping(),
            **self._get_secondary_tool_mapping()
        }
    
    def _get_primary_tool_mapping(self) -> Dict[str, callable]:
        """Get primary corpus tools mapping."""
        return {
            "create_corpus": self._execute_create_corpus,
            "search_corpus": self._execute_search_corpus,
            "update_corpus": self._execute_update_corpus,
            "delete_corpus": self._execute_delete_corpus
        }
    
    def _get_secondary_tool_mapping(self) -> Dict[str, callable]:
        """Get secondary corpus tools mapping."""
        return {
            "analyze_corpus": self._execute_analyze_corpus,
            "export_corpus": self._execute_export_corpus,
            "import_corpus": self._execute_import_corpus,
            "validate_corpus": self._execute_validate_corpus
        }
    
    async def _execute_create_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute corpus creation via real service"""
        try:
            corpus_name, user_id = self._extract_corpus_creation_params(parameters)
            corpus = await self._create_corpus(corpus_name, parameters, user_id)
            return self._create_corpus_success_response(corpus)
        except Exception as e:
            return self._create_corpus_error_response(e)
    
    def _extract_corpus_creation_params(self, parameters: Dict[str, Any]) -> tuple[str, str]:
        """Extract corpus creation parameters."""
        corpus_name = parameters.get('corpus_name', f'corpus_{parameters.get("name", "default")}')
        user_id = parameters.get('user_id', 'default_user')
        return corpus_name, user_id
    
    async def _create_corpus(self, corpus_name: str, parameters: Dict[str, Any], user_id: str) -> Any:
        """Create corpus using corpus service"""
        from netra_backend.app.schemas.corpus import CorpusCreate
        from netra_backend.app.services.corpus import get_corpus_service
        corpus_service = get_corpus_service()  # Create without user context for backward compatibility
        
        corpus_data = self._build_corpus_create_data(corpus_name, parameters)
        return await corpus_service.create_corpus(corpus_data, user_id)
    
    def _build_corpus_create_data(self, corpus_name: str, parameters: Dict[str, Any]):
        """Build CorpusCreate data object."""
        from netra_backend.app.schemas.corpus import CorpusCreate
        return CorpusCreate(
            name=corpus_name,
            description=parameters.get('description', f'Corpus {corpus_name}')
        )
    
    def _create_corpus_success_response(self, corpus: Any) -> Dict[str, Any]:
        """Create success response for corpus creation"""
        return {
            "success": True,
            "data": self._build_corpus_response_data(corpus),
            "message": "Corpus created successfully",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }
    
    def _build_corpus_response_data(self, corpus: Any) -> Dict[str, Any]:
        """Build corpus response data."""
        return {"corpus_id": corpus.id, "name": corpus.name}
    
    def _create_corpus_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create error response for corpus creation failure"""
        logger.error(f"Corpus creation failed: {error}")
        return {
            "success": False,
            "error": f"Failed to create corpus: {str(error)}",
            "metadata": self._build_service_metadata()
        }
    
    async def _execute_search_corpus(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute corpus search via real service"""
        try:
            parameters = parameters or {}
            corpus_id = parameters.get('corpus_id')
            return await self._perform_corpus_search(corpus_id, parameters)
        except Exception as e:
            return self._create_search_error_response(e)
    
    async def _perform_corpus_search(self, corpus_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform corpus search with validation."""
        if not corpus_id:
            return self._create_missing_corpus_id_response()
        
        results = await self._search_corpus(corpus_id, parameters)
        return self._create_search_success_response(results)
    
    def _create_missing_corpus_id_response(self) -> Dict[str, Any]:
        """Create response for missing corpus ID"""
        return {
            "success": False,
            "error": "corpus_id parameter is required for search",
            "metadata": self._build_service_metadata()
        }
    
    async def _search_corpus(self, corpus_id: str, parameters: Dict[str, Any]) -> Any:
        """Search corpus using corpus service"""
        from netra_backend.app.services.corpus import get_corpus_service
        corpus_service = get_corpus_service()  # Create without user context for backward compatibility
        
        search_params = self._build_search_params(parameters)
        return await corpus_service.search_corpus_content(None, corpus_id, search_params)
    
    def _build_search_params(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Build search parameters dictionary."""
        query = parameters.get('query', '')
        limit = parameters.get('limit', 10)
        return {"query": query, "limit": limit}
    
    def _create_search_success_response(self, results: Any) -> Dict[str, Any]:
        """Create success response for corpus search"""
        return {
            "success": True,
            "data": self._build_search_response_data(results),
            "message": "Search completed successfully",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }
    
    def _build_search_response_data(self, results: Any) -> Dict[str, Any]:
        """Build search response data."""
        return {
            "results": results.get("results", []),
            "total_matches": results.get("total", 0)
        }
    
    def _create_search_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create error response for search failure"""
        logger.error(f"Corpus search failed: {error}")
        return {
            "success": False,
            "error": f"Failed to search corpus: {str(error)}",
            "metadata": self._build_service_metadata()
        }
    
    async def _execute_update_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Update corpus"""
        try:
            corpus_id = parameters.get('corpus_id')
            return await self._perform_corpus_update(corpus_id, parameters)
        except Exception as e:
            return self._create_generic_error_response(str(e))
    
    async def _perform_corpus_update(self, corpus_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform corpus update with validation."""
        if not corpus_id:
            return self._create_corpus_id_required_response()
        
        await self._update_corpus(corpus_id, parameters)
        return self._create_update_success_response(corpus_id)
    
    def _create_corpus_id_required_response(self) -> Dict[str, Any]:
        """Create response for missing corpus_id."""
        return {"success": False, "error": "corpus_id required", "metadata": {"tool": self.tool_name}}
    
    def _create_generic_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Create generic error response."""
        return {"success": False, "error": error_msg, "metadata": {"tool": self.tool_name}}
    
    async def _update_corpus(self, corpus_id: str, parameters: Dict[str, Any]) -> Any:
        """Update corpus using corpus service"""
        from netra_backend.app.schemas.corpus import CorpusUpdate
        from netra_backend.app.services.corpus import get_corpus_service
        corpus_service = get_corpus_service()  # Create without user context for backward compatibility
        
        update_data = self._build_corpus_update_data(parameters)
        return await corpus_service.update_corpus(None, corpus_id, update_data)
    
    def _build_corpus_update_data(self, parameters: Dict[str, Any]):
        """Build CorpusUpdate data object."""
        from netra_backend.app.schemas.corpus import CorpusUpdate
        return CorpusUpdate(**{k: v for k, v in parameters.items() if k != 'corpus_id'})
    
    def _create_update_success_response(self, corpus_id: str) -> Dict[str, Any]:
        """Create success response for corpus update"""
        return {
            "success": True,
            "data": self._build_update_response_data(corpus_id),
            "message": "Corpus updated successfully",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }
    
    def _build_update_response_data(self, corpus_id: str) -> Dict[str, Any]:
        """Build update response data."""
        return {"corpus_id": corpus_id, "updated": True}
    
    async def _execute_delete_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Delete corpus"""
        try:
            corpus_id = parameters.get('corpus_id')
            return await self._perform_corpus_deletion(corpus_id)
        except Exception as e:
            return self._create_generic_error_response(str(e))
    
    async def _perform_corpus_deletion(self, corpus_id: str) -> Dict[str, Any]:
        """Perform corpus deletion with validation."""
        if not corpus_id:
            return self._create_corpus_id_required_response()
        
        await self._delete_corpus(corpus_id)
        return self._create_delete_success_response(corpus_id)
    
    async def _delete_corpus(self, corpus_id: str) -> None:
        """Delete corpus using corpus service"""
        from netra_backend.app.services.corpus import get_corpus_service
        corpus_service = get_corpus_service()  # Create without user context for backward compatibility
        await corpus_service.delete_corpus(None, corpus_id)
    
    def _create_delete_success_response(self, corpus_id: str) -> Dict[str, Any]:
        """Create success response for corpus deletion"""
        return {
            "success": True,
            "data": self._build_delete_response_data(corpus_id),
            "message": "Corpus deleted successfully",
            "metadata": {"tool": self.tool_name, "service": "corpus"}
        }
    
    def _build_delete_response_data(self, corpus_id: str) -> Dict[str, Any]:
        """Build delete response data."""
        return {"corpus_id": corpus_id, "deleted": True}
    
    async def _execute_analyze_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze corpus"""
        try:
            corpus_id = parameters.get('corpus_id')
            return await self._perform_corpus_analysis(corpus_id)
        except Exception as e:
            return self._create_generic_error_response(str(e))
    
    async def _perform_corpus_analysis(self, corpus_id: str) -> Dict[str, Any]:
        """Perform corpus analysis with validation."""
        if not corpus_id:
            return self._create_corpus_id_required_response()
        
        stats = await self._get_corpus_statistics(corpus_id)
        return self._create_analyze_success_response(stats)
    
    async def _get_corpus_statistics(self, corpus_id: str) -> Any:
        """Get corpus statistics using corpus service"""
        from netra_backend.app.services.corpus import get_corpus_service
        corpus_service = get_corpus_service()  # Create without user context for backward compatibility
        return await corpus_service.get_corpus_statistics(None, corpus_id)
    
    def _create_analyze_success_response(self, stats: Any) -> Dict[str, Any]:
        """Create success response for corpus analysis"""
        return {
            "success": True,
            "data": stats,
            "message": "Corpus analysis completed",
            "metadata": self._build_service_metadata()
        }
    
    async def _execute_export_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Export corpus"""
        corpus_id, format_type = self._extract_export_params(parameters)
        return self._create_export_response(corpus_id, format_type)
    
    def _create_export_response(self, corpus_id: str, format_type: str) -> Dict[str, Any]:
        """Create export response data."""
        return {
            "success": True,
            "data": self._build_export_data(corpus_id, format_type),
            "message": f"Corpus export initiated in {format_type} format",
            "metadata": self._build_service_metadata()
        }
    
    def _extract_export_params(self, parameters: Dict[str, Any]) -> tuple[str, str]:
        """Extract export parameters."""
        corpus_id = parameters.get('corpus_id')
        format_type = parameters.get('format', 'json')
        return corpus_id, format_type
    
    def _build_export_data(self, corpus_id: str, format_type: str) -> Dict[str, str]:
        """Build export response data."""
        return {"corpus_id": corpus_id, "export_url": f"/exports/{corpus_id}.{format_type}"}

    async def _execute_import_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Import corpus"""
        source_url, corpus_name = self._extract_import_params(parameters)
        return self._create_import_response(corpus_name)
    
    def _create_import_response(self, corpus_name: str) -> Dict[str, Any]:
        """Create import response data."""
        return {
            "success": True,
            "data": self._build_import_data(corpus_name),
            "message": "Corpus import initiated",
            "metadata": self._build_service_metadata()
        }
    
    def _extract_import_params(self, parameters: Dict[str, Any]) -> tuple[str, str]:
        """Extract import parameters."""
        source_url = parameters.get('source_url')
        corpus_name = parameters.get('name', 'imported_corpus')
        return source_url, corpus_name
    
    def _build_import_data(self, corpus_name: str) -> Dict[str, str]:
        """Build import response data."""
        return {"corpus_id": f"imported_{corpus_name}", "name": corpus_name}

    async def _execute_validate_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate corpus"""
        try:
            corpus_id = parameters.get('corpus_id')
            return await self._perform_corpus_validation(corpus_id)
        except Exception as e:
            return self._create_generic_error_response(str(e))
    
    async def _perform_corpus_validation(self, corpus_id: str) -> Dict[str, Any]:
        """Perform corpus validation with error handling."""
        if not corpus_id:
            return self._create_corpus_id_required_response()
        
        corpus = await self._get_corpus(corpus_id)
        validation = self._create_validation_result(corpus)
        return self._create_validate_success_response(validation)
    
    async def _get_corpus(self, corpus_id: str) -> Any:
        """Get corpus using corpus service"""
        from netra_backend.app.services.corpus import get_corpus_service
        corpus_service = get_corpus_service()  # Create without user context for backward compatibility
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
            "metadata": self._build_service_metadata()
        }
    
    def _build_service_metadata(self) -> Dict[str, str]:
        """Build service metadata."""
        return {"tool": self.tool_name, "service": "corpus"}