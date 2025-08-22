"""
Base corpus service class - core orchestrator initialization
"""

from netra_backend.app.services.corpus.clickhouse_operations import (
    CorpusClickHouseOperations,
)
from netra_backend.app.services.corpus.corpus_manager import CorpusManager
from netra_backend.app.services.corpus.document_manager import DocumentManager
from netra_backend.app.services.corpus.search_operations import SearchOperations
from netra_backend.app.services.corpus.validation import ValidationManager


class BaseCorpusService:
    """Base corpus service providing component initialization and management"""
    
    def __init__(self):
        """Initialize all corpus service components"""
        self.document_manager = DocumentManager()
        self.search_operations = SearchOperations()
        self.validation_manager = ValidationManager()
        self.clickhouse_ops = CorpusClickHouseOperations()
        self.corpus_manager = CorpusManager()
    
    def get_document_manager(self) -> DocumentManager:
        """Get document manager instance"""
        return self.document_manager
    
    def get_search_operations(self) -> SearchOperations:
        """Get search operations instance"""
        return self.search_operations
    
    def get_validation_manager(self) -> ValidationManager:
        """Get validation manager instance"""
        return self.validation_manager
    
    def get_clickhouse_ops(self) -> CorpusClickHouseOperations:
        """Get ClickHouse operations instance"""
        return self.clickhouse_ops
    
    def get_corpus_manager(self) -> CorpusManager:
        """Get corpus manager instance"""
        return self.corpus_manager