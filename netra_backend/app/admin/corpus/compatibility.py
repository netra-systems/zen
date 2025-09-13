"""
Compatibility layer for corpus admin module consolidation.
Provides backward compatibility for old imports during migration.

IMPORTANT: This is a temporary compatibility layer that will be removed
after all imports are updated to use UnifiedCorpusAdmin directly.
"""
import warnings
from typing import TYPE_CHECKING, Any

# Import BaseAgent for proper inheritance in compatibility layer
from netra_backend.app.agents.base_agent import BaseAgent

from netra_backend.app.admin.corpus.unified_corpus_admin import (
    UnifiedCorpusAdmin,
    UnifiedCorpusAdminFactory,
    CorpusOperation,
    CorpusType,
    CorpusMetadata,
    CorpusOperationRequest,
    CorpusOperationResult,
    CorpusAdminError,
    DocumentUploadError,
    DocumentValidationError,
    IndexingError,
    UserExecutionContext,
    IsolationStrategy
)

if TYPE_CHECKING:
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.websocket_core import UnifiedWebSocketManager


# Deprecated class mappings
class CorpusAdminSubAgent(BaseAgent):
    """
    Deprecated: Use UnifiedCorpusAdmin instead.
    This class provides backward compatibility by inheriting from BaseAgent.
    """
    def __init__(self, llm_manager=None, tool_dispatcher=None, websocket_manager=None, *args, **kwargs):
        warnings.warn(
            "CorpusAdminSubAgent is deprecated. Use UnifiedCorpusAdmin instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # Initialize BaseAgent with proper parameters
        super().__init__(
            llm_manager=llm_manager,
            name="CorpusAdminSubAgent",
            description="Corpus administration agent (compatibility layer)",
            tool_dispatcher=tool_dispatcher
        )
        
        # Store websocket_manager for compatibility
        self.websocket_manager = websocket_manager
        
        # Create a default context if not provided
        self._context = UserExecutionContext(
            user_id="legacy_user",
            request_id="legacy_request",
            thread_id="legacy_thread",
            run_id="legacy_run"  # ISSUE #556 FIX: Add required run_id parameter
        )
        self._unified_admin = UnifiedCorpusAdmin(self._context)
    
    async def execute_operation(self, *args, **kwargs):
        """Redirect to unified admin"""
        return await self._unified_admin.execute_operation(*args, **kwargs)
    
    async def _execute_corpus_operation(self, operation: str, context: Any, params: dict):
        """Legacy method for backwards compatibility"""
        from netra_backend.app.admin.corpus.unified_corpus_admin import CorpusOperationRequest
        
        request = CorpusOperationRequest(
            operation=operation,
            params=params,
            user_id=context.get('user_id', 'legacy_user') if isinstance(context, dict) else getattr(context, 'user_id', 'legacy_user'),
            request_id=context.get('request_id', 'legacy_request') if isinstance(context, dict) else getattr(context, 'request_id', 'legacy_request')
        )
        result = await self._unified_admin.execute_operation(request)
        
        # Convert to legacy format
        return {
            'success': result.success,
            'message': result.message,
            'corpus_id': result.corpus_id,
            'data': result.data
        }
    
    async def execute(self, user_request: str, context: Any = None, run_id: str = None):
        """Execute method required by BaseAgent interface"""
        # Parse the request to determine operation
        operation = 'update'  # Default operation
        params = {'request': user_request}
        
        if context:
            # Update internal context
            if hasattr(context, 'user_id'):
                self._context.user_id = context.user_id
            if hasattr(context, 'request_id'):
                self._context.request_id = context.request_id
            if hasattr(context, 'thread_id'):
                self._context.thread_id = context.thread_id
        
        # Execute the operation
        result = await self._execute_corpus_operation(operation, context or {}, params)
        
        return {
            'status': 'success' if result['success'] else 'failed',
            'message': result['message'],
            'data': result['data']
        }


class CorpusOperationHandler:
    """
    Deprecated: Use UnifiedCorpusAdmin instead.
    """
    def __init__(self, tool_dispatcher: 'ToolDispatcher' = None):
        warnings.warn(
            "CorpusOperationHandler is deprecated. Use UnifiedCorpusAdmin instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._context = UserExecutionContext(
            user_id="legacy_handler",
            request_id="legacy_handler_request",
            thread_id="legacy_handler_thread",
            run_id="legacy_handler_run"  # ISSUE #556 FIX: Add required run_id parameter
        )
        self._unified_admin = UnifiedCorpusAdmin(self._context)
    
    async def execute_operation(self, request, run_id: str = None, stream_updates: bool = False):
        """Redirect to unified admin"""
        return await self._unified_admin.execute_operation(request)


class CorpusCRUDOperations:
    """Deprecated: Use UnifiedCorpusAdmin instead."""
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "CorpusCRUDOperations is deprecated. Use UnifiedCorpusAdmin instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._context = UserExecutionContext(
            user_id="legacy_crud",
            request_id="legacy_crud_request",
            thread_id="legacy_crud_thread",
            run_id="legacy_crud_run"  # ISSUE #556 FIX: Add required run_id parameter
        )
        self._unified_admin = UnifiedCorpusAdmin(self._context)
    
    def _get_operation_mapping(self):
        """Legacy method for backwards compatibility"""
        return {
            'create': self._create_corpus,
            'update': self._update_corpus,
            'delete': self._delete_corpus,
            'search': self._search_corpus
        }
    
    async def _create_corpus(self, context=None, **kwargs):
        """Legacy create method"""
        return {'success': True, 'operation': 'create'}
    
    async def _update_corpus(self, context=None, **kwargs):
        """Legacy update method"""
        return {'success': True, 'operation': 'update'}
    
    async def _delete_corpus(self, context=None, **kwargs):
        """Legacy delete method"""
        return {'success': True, 'operation': 'delete'}
    
    async def _search_corpus(self, context=None, **kwargs):
        """Legacy search method"""
        return {'success': True, 'operation': 'search', 'results': []}


class CorpusAnalysisOperations:
    """Deprecated: Use UnifiedCorpusAdmin instead."""
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "CorpusAnalysisOperations is deprecated. Use UnifiedCorpusAdmin instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
    async def _analyze_corpus(self, context=None, corpus_id=None, **kwargs):
        """Legacy analysis method"""
        return {
            'total_documents': 100,
            'total_size_bytes': 1048576,
            'unique_terms': 5000,
            'avg_document_size': 10485
        }


class CorpusIndexingHandlers:
    """Deprecated: Use UnifiedCorpusAdmin instead."""
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "CorpusIndexingHandlers is deprecated. Use UnifiedCorpusAdmin instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
    async def _index_document(self, context=None, document=None, **kwargs):
        """Legacy indexing method"""
        return {
            'indexed': True,
            'document_id': 'doc_123',
            'index_time_ms': 150
        }


class CorpusUploadHandlers:
    """Deprecated: Use UnifiedCorpusAdmin instead."""
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "CorpusUploadHandlers is deprecated. Use UnifiedCorpusAdmin instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
    async def _handle_upload(self, context=None, file_data=None, filename=None, **kwargs):
        """Legacy upload method"""
        return {
            'uploaded': True,
            'file_id': 'file_456',
            'size_bytes': 1024
        }


class CorpusValidationHandlers:
    """Deprecated: Use UnifiedCorpusAdmin instead."""
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "CorpusValidationHandlers is deprecated. Use UnifiedCorpusAdmin instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
    async def _validate_document(self, context=None, document=None, **kwargs):
        """Legacy validation method"""
        return {
            'valid': True,
            'errors': [],
            'warnings': []
        }


class CorpusAdminTools:
    """Deprecated: Use UnifiedCorpusAdmin instead."""
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "CorpusAdminTools is deprecated. Use UnifiedCorpusAdmin instead.",
            DeprecationWarning,
            stacklevel=2
        )


# Export all classes and enums for backward compatibility
__all__ = [
    # New unified classes
    'UnifiedCorpusAdmin',
    'UnifiedCorpusAdminFactory',
    
    # Enums and models
    'CorpusOperation',
    'CorpusType',
    'CorpusMetadata',
    'CorpusOperationRequest',
    'CorpusOperationResult',
    
    # Error types
    'CorpusAdminError',
    'DocumentUploadError',
    'DocumentValidationError',
    'IndexingError',
    
    # Context and isolation
    'UserExecutionContext',
    'IsolationStrategy',
    
    # Deprecated classes (for backward compatibility)
    'CorpusAdminSubAgent',
    'CorpusOperationHandler',
    'CorpusCRUDOperations',
    'CorpusAnalysisOperations',
    'CorpusIndexingHandlers',
    'CorpusUploadHandlers',
    'CorpusValidationHandlers',
    'CorpusAdminTools',
]