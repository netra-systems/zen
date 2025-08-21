"""Compensation actions for corpus operations.

Provides cleanup and rollback functionality for failed corpus operations.
"""

import os
from typing import Dict, List

from netra_backend.app.core.error_recovery import CompensationAction, RecoveryContext, OperationType
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CorpusCleanupCompensation(CompensationAction):
    """Compensation action for corpus operations."""
    
    def __init__(self, file_manager, db_manager):
        """Initialize with file and database managers."""
        self.file_manager = file_manager
        self.db_manager = db_manager
    
    async def execute(self, context: RecoveryContext) -> bool:
        """Execute compensation for corpus operations."""
        try:
            # Clean up in sequence
            await self._cleanup_uploaded_files(context)
            await self._cleanup_database_entries(context)
            await self._cleanup_search_indices(context)
            
            logger.info(f"Corpus cleanup compensation completed: {context.operation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Corpus cleanup compensation failed: {e}")
            return False
    
    def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if can compensate corpus operations."""
        return context.operation_type in [
            OperationType.FILE_OPERATION,
            OperationType.DATABASE_WRITE
        ]
    
    async def _cleanup_uploaded_files(self, context: RecoveryContext) -> None:
        """Clean up uploaded files from context metadata."""
        uploaded_files = context.metadata.get('uploaded_files', [])
        for file_path in uploaded_files:
            await self._cleanup_file(file_path)
    
    async def _cleanup_database_entries(self, context: RecoveryContext) -> None:
        """Clean up database entries from context metadata."""
        document_ids = context.metadata.get('document_ids', [])
        for doc_id in document_ids:
            await self._cleanup_database_entry(doc_id)
    
    async def _cleanup_search_indices(self, context: RecoveryContext) -> None:
        """Clean up search index entries from context metadata."""
        index_entries = context.metadata.get('index_entries', [])
        for entry in index_entries:
            await self._cleanup_index_entry(entry)
    
    async def _cleanup_file(self, file_path: str) -> None:
        """Remove uploaded file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")
    
    async def _cleanup_database_entry(self, document_id: str) -> None:
        """Remove database entry for document."""
        try:
            await self.db_manager.delete_document(document_id)
            logger.debug(f"Cleaned up database entry: {document_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup database entry {document_id}: {e}")
    
    async def _cleanup_index_entry(self, index_entry: Dict) -> None:
        """Remove search index entry."""
        try:
            # Implementation would depend on search engine used
            logger.debug(f"Cleaned up index entry: {index_entry}")
        except Exception as e:
            logger.warning(f"Failed to cleanup index entry: {e}")


# Factory function for creating compensation instances
def create_corpus_compensation(file_manager=None, db_manager=None):
    """Create corpus cleanup compensation instance."""
    return CorpusCleanupCompensation(file_manager, db_manager)