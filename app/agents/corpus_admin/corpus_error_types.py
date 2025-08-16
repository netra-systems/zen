"""Error types specific to Corpus Admin Agent operations.

Provides specialized error classes for corpus management operations including
document upload failures, validation errors, and indexing issues.
"""

from typing import Dict, List, Optional

from app.core.error_codes import ErrorSeverity
from app.agents.error_handler import AgentError, ErrorContext


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
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            recoverable=True
        )
        self.operation = operation
        self.resource_info = resource_info or {}


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
        super().__init__(
            message=f"Document upload failed: {filename} ({error_details})",
            operation="document_upload",
            resource_info={
                'filename': filename,
                'file_size': file_size,
                'error': error_details
            },
            context=context
        )
        self.filename = filename
        self.file_size = file_size


class DocumentValidationError(CorpusAdminError):
    """Error when document validation fails."""
    
    def __init__(
        self,
        filename: str,
        validation_errors: List[str],
        context: Optional[ErrorContext] = None
    ):
        """Initialize document validation error."""
        super().__init__(
            message=f"Document validation failed: {filename}",
            operation="document_validation",
            resource_info={
                'filename': filename,
                'validation_errors': validation_errors
            },
            context=context
        )
        self.filename = filename
        self.validation_errors = validation_errors


class IndexingError(CorpusAdminError):
    """Error when document indexing fails."""
    
    def __init__(
        self,
        document_id: str,
        index_type: str,
        context: Optional[ErrorContext] = None
    ):
        """Initialize indexing error."""
        super().__init__(
            message=f"Document indexing failed: {document_id}",
            operation="document_indexing",
            resource_info={
                'document_id': document_id,
                'index_type': index_type
            },
            context=context
        )
        self.document_id = document_id
        self.index_type = index_type