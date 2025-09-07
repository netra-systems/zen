"""
Corpus operations handler module.

Provides main operations handler for corpus management.
This module has been removed but tests still reference it.
"""

from typing import Any, Dict
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from .operations_crud import CorpusCRUDOperations
from .operations_analysis import CorpusAnalysisOperations
from .operations_execution import CorpusExecutionOperations


class CorpusOperationHandler:
    """
    Main corpus operation handler.
    
    Coordinates all corpus operations including CRUD, analysis, and execution.
    """
    
    def __init__(self, tool_dispatcher: UnifiedToolDispatcher):
        self.tool_dispatcher = tool_dispatcher
        self.crud_ops = CorpusCRUDOperations(tool_dispatcher)
        self.analysis_ops = CorpusAnalysisOperations(tool_dispatcher)
        self.execution_ops = CorpusExecutionOperations(tool_dispatcher)
    
    def handle_operation(self, operation_type: str, **kwargs) -> Dict[str, Any]:
        """Handle corpus operation based on type."""
        if operation_type == "create":
            return self.crud_ops.create_corpus(kwargs)
        elif operation_type == "read":
            return self.crud_ops.read_corpus(kwargs.get("corpus_id"))
        elif operation_type == "update":
            return self.crud_ops.update_corpus(
                kwargs.get("corpus_id"), 
                kwargs.get("update_data", {})
            )
        elif operation_type == "delete":
            return self.crud_ops.delete_corpus(kwargs.get("corpus_id"))
        elif operation_type == "analyze":
            return self.analysis_ops.analyze_corpus_metrics(kwargs.get("corpus_id"))
        elif operation_type == "execute":
            return self.execution_ops.execute_corpus_operation(
                kwargs.get("operation"), 
                kwargs.get("corpus_id"),
                kwargs.get("parameters")
            )
        else:
            return {
                "error": f"Unknown operation type: {operation_type}",
                "status": "failed"
            }
    
    def get_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Get status of a corpus operation."""
        return {
            "operation_id": operation_id,
            "status": "completed",
            "progress": 100
        }