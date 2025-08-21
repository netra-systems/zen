"""Core corpus admin error handler that orchestrates all error handling strategies.

Provides the main CorpusAdminErrorHandler class that coordinates upload, validation,
and indexing error handlers.
"""

from typing import Any, Dict, List

from netra_backend.app.agents.corpus_admin.corpus_indexing_handlers import (
    create_indexing_handler,
)
from netra_backend.app.agents.corpus_admin.corpus_upload_handlers import (
    create_upload_handler,
)
from netra_backend.app.agents.corpus_admin.corpus_validation_handlers import (
    create_validation_handler,
)


class CorpusAdminErrorHandler:
    """Specialized error handler for corpus admin agent."""
    
    def __init__(self, file_manager=None, db_manager=None, search_engine=None):
        """Initialize corpus admin error handler."""
        self.file_manager = file_manager
        self.db_manager = db_manager
        self.search_engine = search_engine
        self._init_specialized_handlers(file_manager, search_engine)
    
    def _init_specialized_handlers(self, file_manager, search_engine):
        """Initialize specialized error handlers."""
        self.upload_handler = create_upload_handler(file_manager)
        self.validation_handler = create_validation_handler()
        self.indexing_handler = create_indexing_handler(search_engine)
    
    async def handle_document_upload_error(
        self,
        filename: str,
        file_size: int,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle document upload failures with recovery strategies."""
        return await self.upload_handler.handle_document_upload_error(
            filename, file_size, run_id, original_error
        )
    
    async def handle_document_validation_error(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle document validation failures."""
        return await self.validation_handler.handle_document_validation_error(
            filename, validation_errors, run_id, original_error
        )
    
    async def handle_indexing_error(
        self,
        document_id: str,
        index_type: str,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle document indexing failures."""
        return await self.indexing_handler.handle_indexing_error(
            document_id, index_type, run_id, original_error
        )


# Factory function for creating corpus admin error handlers
def create_corpus_admin_error_handler(
    file_manager=None, 
    db_manager=None, 
    search_engine=None
):
    """Create corpus admin error handler instance."""
    return CorpusAdminErrorHandler(file_manager, db_manager, search_engine)


# Global corpus admin error handler instance
corpus_admin_error_handler = create_corpus_admin_error_handler()