"""
Corpus Operation Handler - Main Dispatcher

Handles routing of corpus operations to appropriate handlers.
Maintains 8-line function limit per operation handler.
"""

from typing import Dict, Any
from datetime import datetime, timezone
from app.agents.tool_dispatcher import ToolDispatcher
from app.logging_config import central_logger
from .models import CorpusOperationRequest, CorpusOperationResult
from .operations_crud import CorpusCRUDOperations
from .operations_analysis import CorpusAnalysisOperations

logger = central_logger.get_logger(__name__)


class CorpusOperationHandler:
    """Handles execution of corpus operations"""
    
    def __init__(self, tool_dispatcher: ToolDispatcher):
        self.tool_dispatcher = tool_dispatcher
        self.crud_ops = CorpusCRUDOperations(tool_dispatcher)
        self.analysis_ops = CorpusAnalysisOperations(tool_dispatcher)
    
    async def execute_operation(
        self, 
        request: CorpusOperationRequest,
        run_id: str,
        stream_updates: bool
    ) -> CorpusOperationResult:
        """Execute corpus operation based on type"""
        result = self._create_base_result(request)
        
        try:
            return await self._route_operation(request, run_id, stream_updates)
        except Exception as e:
            return self._handle_operation_error(result, e)
    
    async def _route_operation(self, request: CorpusOperationRequest, run_id: str, stream_updates: bool) -> CorpusOperationResult:
        """Route operation to appropriate handler"""
        operation = request.operation.value
        
        if operation in ["create", "search", "update", "delete"]:
            return await self.crud_ops.execute(operation, request, run_id, stream_updates)
        elif operation in ["analyze", "export", "import", "validate"]:
            return await self.analysis_ops.execute(operation, request, run_id, stream_updates)
        else:
            return self._create_unsupported_operation_result(request)
    
    def _handle_operation_error(self, result: CorpusOperationResult, error: Exception) -> CorpusOperationResult:
        """Handle operation execution error"""
        result.errors.append(str(error))
        logger.error(f"Corpus operation failed: {error}")
        return result
    
    def _create_unsupported_operation_result(self, request: CorpusOperationRequest) -> CorpusOperationResult:
        """Create result for unsupported operation"""
        result = self._create_base_result(request)
        result.errors.append(f"Unsupported operation: {request.operation}")
        return result
    
    async def get_corpus_statistics(self) -> Dict[str, Any]:
        """Get overall corpus statistics"""
        base_stats = self._get_base_statistics()
        corpora_by_type = self._get_corpora_by_type()
        recent_operations = self._get_recent_operations()
        
        return {**base_stats, "corpora_by_type": corpora_by_type, "recent_operations": recent_operations}
    
    def _get_base_statistics(self) -> Dict[str, Any]:
        """Get base corpus statistics"""
        return {
            "total_corpora": 12,
            "total_documents": 45678,
            "total_size_gb": 2.3
        }
    
    def _get_corpora_by_type(self) -> Dict[str, int]:
        """Get corpora count by type"""
        return {
            "documentation": 3,
            "knowledge_base": 5,
            "training_data": 2,
            "reference_data": 1,
            "embeddings": 1
        }
    
    def _get_recent_operations(self) -> list:
        """Get list of recent operations"""
        return [
            {
                "operation": "search", 
                "timestamp": datetime.now(timezone.utc).isoformat(), 
                "corpus": "main_kb"
            },
            {
                "operation": "create", 
                "timestamp": datetime.now(timezone.utc).isoformat(), 
                "corpus": "product_docs"
            }
        ]
    
    def _create_base_result(self, request: CorpusOperationRequest) -> CorpusOperationResult:
        """Create base result object"""
        return CorpusOperationResult(
            success=False,
            operation=request.operation,
            corpus_metadata=request.corpus_metadata
        )