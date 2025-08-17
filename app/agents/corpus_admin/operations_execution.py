"""
Corpus Execution Helper

Provides execution utilities for corpus operations including database
interactions and tool dispatcher integration.
Maintains 8-line function limit per method.
"""

from typing import Dict, Any
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.logging_config import central_logger
from .models import CorpusOperationRequest, CorpusOperationResult

logger = central_logger.get_logger(__name__)


class CorpusExecutionHelper:
    """Helper class for executing corpus operations"""
    
    def __init__(self, tool_dispatcher: ToolDispatcher):
        self.tool_dispatcher = tool_dispatcher
    
    async def execute_via_tool_dispatcher(
        self, 
        tool_name: str, 
        request: CorpusOperationRequest, 
        run_id: str,
        result_key: str
    ) -> CorpusOperationResult:
        """Execute operation via tool dispatcher"""
        tool_result = await self._dispatch_tool_with_params(tool_name, request, run_id)
        return self._build_tool_result(tool_result, request, result_key)
    
    async def _dispatch_tool_with_params(self, tool_name: str, request: CorpusOperationRequest, run_id: str):
        """Dispatch tool with built parameters."""
        return await self.tool_dispatcher.dispatch_tool(
            tool_name=tool_name,
            parameters=self._build_tool_parameters(request),
            state=DeepAgentState(),
            run_id=run_id
        )
    
    async def execute_search_via_tool(
        self, 
        tool_name: str, 
        request: CorpusOperationRequest, 
        run_id: str
    ) -> CorpusOperationResult:
        """Execute search via tool dispatcher"""
        tool_result = await self._dispatch_search_tool(tool_name, request, run_id)
        return self._build_search_result(tool_result, request)
    
    async def _dispatch_search_tool(self, tool_name: str, request: CorpusOperationRequest, run_id: str):
        """Dispatch search tool with parameters."""
        parameters = self._build_search_parameters(request)
        return await self.tool_dispatcher.dispatch_tool(
            tool_name=tool_name,
            parameters=parameters,
            state=DeepAgentState(),
            run_id=run_id
        )
    
    async def execute_corpus_search(
        self, 
        corpus_name: str, 
        query: str, 
        filters: Dict[str, Any], 
        limit: int
    ) -> Dict[str, Any]:
        """Execute real corpus search against database"""
        logger.warning(f"Real corpus search implementation needed for: {corpus_name}")
        return self._create_empty_search_result(query, filters, limit)
    
    def _create_empty_search_result(self, query: str, filters: Dict[str, Any], limit: int) -> Dict[str, Any]:
        """Create empty search result structure."""
        return {
            "results": [],
            "total_count": 0,
            "query": query,
            "filters": filters,
            "limit": limit
        }
    
    async def execute_corpus_analysis(self, corpus_name: str) -> Dict[str, Any]:
        """Execute real corpus analysis against database"""
        logger.warning(f"Real corpus analysis implementation needed for: {corpus_name}")
        return self._create_empty_analysis_result()
    
    def _create_empty_analysis_result(self) -> Dict[str, Any]:
        """Create empty analysis result structure."""
        base_metrics = self._get_base_analysis_metrics()
        recommendations = ["Real corpus analysis implementation required"]
        return {**base_metrics, "recommendations": recommendations}
    
    def _get_base_analysis_metrics(self) -> Dict[str, Any]:
        """Get base analysis metrics"""
        return {
            "total_documents": 0,
            "total_size_mb": 0.0,
            "avg_document_size_kb": 0.0,
            "unique_terms": 0,
            "coverage_score": 0.0,
            "quality_score": 0.0
        }
    
    async def execute_corpus_validation(self, corpus_name: str) -> Dict[str, Any]:
        """Execute real corpus validation checks"""
        logger.warning(f"Real corpus validation implementation needed for: {corpus_name}")
        return {
            "total_checked": 0,
            "valid": 0,
            "invalid": 0,
            "issues": []
        }
    
    def _build_tool_parameters(self, request: CorpusOperationRequest) -> Dict[str, Any]:
        """Build parameters for tool dispatcher"""
        return {
            "corpus_name": request.corpus_metadata.corpus_name,
            "corpus_type": request.corpus_metadata.corpus_type.value,
            "description": request.corpus_metadata.description,
            "tags": request.corpus_metadata.tags,
            "access_level": request.corpus_metadata.access_level
        }
    
    def _build_search_parameters(self, request: CorpusOperationRequest) -> Dict[str, Any]:
        """Build search-specific parameters"""
        return {
            "corpus_name": request.corpus_metadata.corpus_name,
            "query": request.content,
            "filters": request.filters,
            "limit": request.options.get("limit", 10)
        }
    
    def _build_tool_result(
        self, 
        tool_result: Dict[str, Any], 
        request: CorpusOperationRequest,
        result_key: str
    ) -> CorpusOperationResult:
        """Build result from tool execution"""
        return CorpusOperationResult(**self._create_tool_result_params(
            tool_result, request, result_key
        ))
    
    def _create_tool_result_params(self, tool_result: Dict[str, Any], 
                                  request: CorpusOperationRequest, result_key: str) -> Dict[str, Any]:
        """Create parameters for tool result."""
        return {
            "success": tool_result.get("success", False),
            "operation": request.operation,
            "corpus_metadata": request.corpus_metadata,
            "affected_documents": 0,
            "result_data": tool_result.get(result_key),
            "metadata": {result_key: tool_result.get(result_key)}
        }
    
    def _build_search_result(
        self, 
        tool_result: Dict[str, Any], 
        request: CorpusOperationRequest
    ) -> CorpusOperationResult:
        """Build search result from tool execution"""
        results = tool_result.get("results", [])
        return CorpusOperationResult(**self._create_search_result_params(
            request, results, tool_result
        ))
    
    def _create_search_result_params(self, request: CorpusOperationRequest, 
                                    results: list, tool_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create parameters for search result."""
        return {
            "success": True,
            "operation": request.operation,
            "corpus_metadata": request.corpus_metadata,
            "affected_documents": len(results),
            "result_data": results,
            "metadata": {"total_matches": tool_result.get("total_matches", 0)}
        }