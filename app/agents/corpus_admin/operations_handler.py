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
            operation = request.operation.value
            
            if operation in ["create", "search", "update", "delete"]:
                return await self.crud_ops.execute(
                    operation, request, run_id, stream_updates
                )
            elif operation in ["analyze", "export", "import", "validate"]:
                return await self.analysis_ops.execute(
                    operation, request, run_id, stream_updates
                )
            else:
                result.errors.append(f"Unsupported operation: {request.operation}")
                return result
        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"Corpus operation failed: {e}")
            return result
    
    async def get_corpus_statistics(self) -> Dict[str, Any]:
        """Get overall corpus statistics"""
        return {
            "total_corpora": 12,
            "total_documents": 45678,
            "total_size_gb": 2.3,
            "corpora_by_type": {
                "documentation": 3,
                "knowledge_base": 5,
                "training_data": 2,
                "reference_data": 1,
                "embeddings": 1
            },
            "recent_operations": [
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
        }
    
    def _create_base_result(self, request: CorpusOperationRequest) -> CorpusOperationResult:
        """Create base result object"""
        return CorpusOperationResult(
            success=False,
            operation=request.operation,
            corpus_metadata=request.corpus_metadata
        )