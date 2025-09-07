"""
Corpus operations handler module.

Handles corpus administration operations.
This module has been removed but tests still reference it.
"""

from typing import Any
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher


class CorpusCrudOperations:
    """CRUD operations for corpus management."""
    
    def __init__(self, tool_dispatcher: UnifiedToolDispatcher):
        self.tool_dispatcher = tool_dispatcher


class CorpusAnalysisOperations:
    """Analysis operations for corpus management."""
    
    def __init__(self, tool_dispatcher: UnifiedToolDispatcher):
        self.tool_dispatcher = tool_dispatcher


class CorpusOperationHandler:
    """
    Corpus operation handler.
    
    Handles corpus administration operations including CRUD and analysis.
    """
    
    def __init__(self, tool_dispatcher: UnifiedToolDispatcher):
        self.tool_dispatcher = tool_dispatcher
        self.crud_ops = CorpusCrudOperations(tool_dispatcher)
        self.analysis_ops = CorpusAnalysisOperations(tool_dispatcher)