"""Error types specific to Corpus Admin Agent operations.

Provides specialized error classes for corpus management operations including
document upload failures, validation errors, and indexing issues.
"""

from typing import Dict, List, Optional

from netra_backend.app.agents.error_handler import AgentError, ErrorContext
from netra_backend.app.core.error_codes import ErrorSeverity


class CorpusAdminError(AgentError):
    """Specific error type for corpus admin operations."""
    
    def __init__(
        self,
        message: str,
        operation: str,
        resource_info: Optional[Dict] = None,
        context: Optional[ErrorContext] = None
    ):
        """Initialize corpus admin error."""
        self._init_parent_error(message, context)
        self.operation = operation
        self.resource_info = resource_info or {}
    
    def _init_parent_error(self, message: str, context: Optional[ErrorContext]):
        """Initialize parent AgentError."""
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            recoverable=True
        )


class DocumentUploadError(CorpusAdminError):
    """Error when document upload fails."""
    
    def __init__(
        self,
        filename: str,
        file_size: int,
        error_details: str,
        context: Optional[ErrorContext] = None
    ):
        """Initialize document upload error."""
        message = f"Document upload failed: {filename} ({error_details})"
        resource_info = self._build_upload_resource_info(
            filename, file_size, error_details
        )
        super().__init__(message, "document_upload", resource_info, context)
        self.filename = filename
        self.file_size = file_size
    
    def _build_upload_resource_info(
        self, filename: str, file_size: int, error_details: str
    ) -> Dict[str, any]:
        """Build resource info for upload error."""
        return {
            'filename': filename,
            'file_size': file_size,
            'error': error_details
        }


class DocumentValidationError(CorpusAdminError):
    """Error when document validation fails."""
    
    def __init__(
        self,
        filename: str,
        validation_errors: List[str],
        context: Optional[ErrorContext] = None
    ):
        """Initialize document validation error."""
        message = f"Document validation failed: {filename}"
        resource_info = self._build_validation_resource_info(
            filename, validation_errors
        )
        super().__init__(message, "document_validation", resource_info, context)
        self.filename = filename
        self.validation_errors = validation_errors
    
    def _build_validation_resource_info(
        self, filename: str, validation_errors: List[str]
    ) -> Dict[str, any]:
        """Build resource info for validation error."""
        return {
            'filename': filename,
            'validation_errors': validation_errors
        }


class IndexingError(CorpusAdminError):
    """Error when document indexing fails."""
    
    def __init__(
        self,
        document_id: str,
        index_type: str,
        context: Optional[ErrorContext] = None
    ):
        """Initialize indexing error."""
        message = f"Document indexing failed: {document_id}"
        resource_info = self._build_indexing_resource_info(
            document_id, index_type
        )
        super().__init__(message, "document_indexing", resource_info, context)
        self.document_id = document_id
        self.index_type = index_type
    
    def _build_indexing_resource_info(
        self, document_id: str, index_type: str
    ) -> Dict[str, any]:
        """Build resource info for indexing error."""
        return {
            'document_id': document_id,
            'index_type': index_type
        }