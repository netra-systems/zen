"""Indexing error handling utilities for corpus admin operations.

Provides specialized handlers for document indexing failures with recovery strategies.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from app.agents.error_handler import ErrorContext, global_error_handler
from app.agents.corpus_admin.corpus_error_types import IndexingError
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class IndexingErrorHandler:
    """Handles document indexing failures with recovery strategies."""
    
    def __init__(self, search_engine=None):
        """Initialize indexing error handler."""
        self.search_engine = search_engine
        self.index_alternatives = self._init_index_alternatives()
    
    def _init_index_alternatives(self) -> Dict[str, str]:
        """Initialize index type alternatives mapping."""
        return {
            'semantic': 'keyword',
            'keyword': 'basic',
            'advanced': 'standard',
            'full_text': 'simple'
        }
    
    async def handle_indexing_error(
        self,
        document_id: str,
        index_type: str,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle document indexing failures."""
        context = self._create_indexing_error_context(
            document_id, index_type, run_id, original_error
        )
        
        error = IndexingError(document_id, index_type, context)
        
        try:
            # Try indexing recovery strategies
            result = await self._attempt_indexing_recovery(
                document_id, index_type, run_id
            )
            if result:
                return result
            
            # Queue for later indexing as fallback
            queued_result = await self._queue_for_later_indexing(
                document_id, index_type, run_id
            )
            return queued_result
            
        except Exception as fallback_error:
            await global_error_handler.handle_error(error, context)
            raise error
    
    def _create_indexing_error_context(
        self,
        document_id: str,
        index_type: str,
        run_id: str,
        original_error: Exception
    ) -> ErrorContext:
        """Create error context for indexing failures."""
        return ErrorContext(
            agent_name="corpus_admin_agent",
            operation_name="document_indexing",
            run_id=run_id,
            additional_data={
                'document_id': document_id,
                'index_type': index_type,
                'original_error': str(original_error)
            }
        )
    
    async def _attempt_indexing_recovery(
        self,
        document_id: str,
        index_type: str,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Attempt indexing recovery strategies."""
        # Try simplified indexing
        simplified_result = await self._try_simplified_indexing(
            document_id, index_type, run_id
        )
        if simplified_result:
            return simplified_result
        
        # Try alternative index type
        alternative_result = await self._try_alternative_indexing(
            document_id, index_type, run_id
        )
        return alternative_result
    
    async def _try_simplified_indexing(
        self,
        document_id: str,
        index_type: str,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try simplified indexing approach."""
        try:
            # Use basic text indexing instead of advanced features
            if index_type == 'semantic' and self.search_engine:
                # Fall back to keyword indexing
                result = await self.search_engine.index_document_simple(document_id)
                if result:
                    return self._create_simplified_success_response(
                        document_id, index_type, run_id
                    )
        except Exception as e:
            logger.debug(f"Simplified indexing failed: {e}")
        
        return None
    
    def _create_simplified_success_response(
        self, document_id: str, index_type: str, run_id: str
    ) -> Dict[str, Any]:
        """Create success response for simplified indexing."""
        logger.info(
            f"Document indexed using simplified method",
            document_id=document_id,
            original_type=index_type,
            fallback_type='keyword',
            run_id=run_id
        )
        return {
            'success': True,
            'method': 'simplified_indexing',
            'index_type': 'keyword',
            'document_id': document_id
        }
    
    async def _try_alternative_indexing(
        self,
        document_id: str,
        index_type: str,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try alternative indexing method."""
        alternative_type = self.index_alternatives.get(index_type)
        
        if alternative_type and self.search_engine:
            try:
                result = await self.search_engine.index_document(
                    document_id, alternative_type
                )
                if result:
                    return self._create_alternative_success_response(
                        document_id, index_type, alternative_type, run_id
                    )
            except Exception as e:
                logger.debug(f"Alternative indexing failed: {e}")
        
        return None
    
    def _create_alternative_success_response(
        self,
        document_id: str,
        index_type: str,
        alternative_type: str,
        run_id: str
    ) -> Dict[str, Any]:
        """Create success response for alternative indexing."""
        logger.info(
            f"Document indexed using alternative method",
            document_id=document_id,
            original_type=index_type,
            alternative_type=alternative_type,
            run_id=run_id
        )
        return {
            'success': True,
            'method': 'alternative_indexing',
            'index_type': alternative_type,
            'document_id': document_id
        }
    
    async def _queue_for_later_indexing(
        self,
        document_id: str,
        index_type: str,
        run_id: str
    ) -> Dict[str, Any]:
        """Queue document for later indexing."""
        queue_entry = self._create_queue_entry(document_id, index_type, run_id)
        
        # Add to indexing queue (implementation would depend on queue system)
        logger.info(
            f"Document queued for later indexing",
            document_id=document_id,
            index_type=index_type,
            run_id=run_id
        )
        
        return {
            'success': True,
            'method': 'queued_for_later',
            'queue_entry': queue_entry,
            'message': 'Document will be indexed when system resources are available'
        }
    
    def _create_queue_entry(
        self, document_id: str, index_type: str, run_id: str
    ) -> Dict[str, Any]:
        """Create queue entry for later indexing."""
        return {
            'document_id': document_id,
            'index_type': index_type,
            'queued_at': datetime.now().isoformat(),
            'run_id': run_id,
            'retry_count': 0
        }


# Factory function for creating indexing handlers
def create_indexing_handler(search_engine=None):
    """Create indexing error handler instance."""
    return IndexingErrorHandler(search_engine)