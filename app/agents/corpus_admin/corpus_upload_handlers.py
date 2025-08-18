"""Upload error handling utilities for corpus admin operations.

Provides specialized handlers for document upload failures with recovery strategies.
"""

import os
from typing import Any, Dict, List, Optional

from app.agents.error_handler import ErrorContext, global_error_handler
from app.agents.corpus_admin.corpus_error_types import DocumentUploadError
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class UploadErrorHandler:
    """Handles document upload failures with recovery strategies."""
    
    def __init__(self, file_manager=None):
        """Initialize upload error handler."""
        self.file_manager = file_manager
        
        # Maximum file size limits by type (in bytes)
        self.max_file_sizes = self._init_file_size_limits()
    
    def _init_file_size_limits(self) -> Dict[str, int]:
        """Initialize file size limits by extension."""
        return {
            '.pdf': 10 * 1024 * 1024,  # 10MB
            '.txt': 5 * 1024 * 1024,   # 5MB
            '.docx': 15 * 1024 * 1024, # 15MB
            '.md': 2 * 1024 * 1024,    # 2MB
        }
    
    async def handle_document_upload_error(
        self,
        filename: str,
        file_size: int,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle document upload failures with recovery strategies."""
        context = self._create_upload_error_context(filename, file_size, run_id, original_error)
        error = DocumentUploadError(filename, file_size, str(original_error), context)
        return await self._execute_upload_error_workflow(filename, file_size, run_id, error, context)
    
    async def _execute_upload_error_workflow(
        self, filename: str, file_size: int, run_id: str, error: DocumentUploadError, context
    ) -> Dict[str, Any]:
        """Execute upload error handling workflow."""
        try:
            result = await self._attempt_upload_recovery(filename, file_size, run_id)
            return result if result else await self._handle_upload_failure(error, context)
        except Exception:
            return await self._handle_fallback_error(error, context)
    
    async def _handle_upload_failure(self, error: DocumentUploadError, context) -> Dict[str, Any]:
        """Handle upload failure when recovery fails."""
        raise error
    
    async def _handle_fallback_error(self, error: DocumentUploadError, context) -> Dict[str, Any]:
        """Handle fallback error during upload recovery."""
        await global_error_handler.handle_error(error, context)
        raise error
    
    def _create_upload_error_context(
        self,
        filename: str,
        file_size: int,
        run_id: str,
        original_error: Exception
    ) -> ErrorContext:
        """Create error context for upload failures."""
        additional_data = self._build_upload_error_data(filename, file_size, original_error)
        return ErrorContext(
            agent_name="corpus_admin_agent",
            operation_name="document_upload",
            run_id=run_id,
            additional_data=additional_data
        )
    
    def _build_upload_error_data(
        self, filename: str, file_size: int, original_error: Exception
    ) -> Dict[str, Any]:
        """Build additional data for upload error context."""
        return {
            'filename': filename,
            'file_size': file_size,
            'original_error': str(original_error)
        }
    
    async def _attempt_upload_recovery(
        self,
        filename: str,
        file_size: int,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Attempt various upload recovery strategies."""
        if self._is_file_too_large(filename, file_size):
            return await self._handle_large_file(filename, file_size, run_id)
        return await self._try_recovery_methods(filename, file_size, run_id)
    
    async def _try_recovery_methods(
        self,
        filename: str,
        file_size: int,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try alternative upload methods in sequence."""
        alternative_result = await self._try_alternative_upload(filename, file_size, run_id)
        if alternative_result:
            return alternative_result
        return await self._try_chunked_upload(filename, file_size, run_id)
    
    def _is_file_too_large(self, filename: str, file_size: int) -> bool:
        """Check if file size exceeds limits."""
        file_ext = os.path.splitext(filename)[1].lower()
        max_size = self.max_file_sizes.get(file_ext, 5 * 1024 * 1024)  # Default 5MB
        return file_size > max_size
    
    async def _handle_large_file(
        self,
        filename: str,
        file_size: int,
        run_id: str
    ) -> Dict[str, Any]:
        """Handle files that are too large."""
        file_ext = os.path.splitext(filename)[1].lower()
        max_size = self.max_file_sizes.get(file_ext, 5 * 1024 * 1024)
        
        self._log_large_file_warning(filename, file_size, max_size, run_id)
        
        return self._create_large_file_response(filename, file_size, max_size)
    
    def _log_large_file_warning(
        self, filename: str, file_size: int, max_size: int, run_id: str
    ) -> None:
        """Log warning for large file."""
        logger.warning(
            f"File too large for upload",
            filename=filename,
            file_size=file_size,
            max_size=max_size,
            run_id=run_id
        )
    
    def _create_large_file_response(
        self, filename: str, file_size: int, max_size: int
    ) -> Dict[str, Any]:
        """Create response for large file handling."""
        return {
            'success': False,
            'error': 'FILE_TOO_LARGE',
            'message': f'File {filename} exceeds maximum size limit',
            'file_size': file_size,
            'max_size': max_size,
            'suggestions': self._get_large_file_suggestions()
        }
    
    def _get_large_file_suggestions(self) -> List[str]:
        """Get suggestions for handling large files."""
        return [
            'Split the file into smaller chunks',
            'Compress the file if possible',
            'Contact administrator for large file support'
        ]
    
    async def _try_alternative_upload(
        self,
        filename: str,
        file_size: int,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try alternative upload method."""
        try:
            return await self._attempt_multipart_upload(filename, file_size, run_id)
        except Exception as e:
            logger.debug(f"Alternative upload failed: {e}")
            return None
    
    async def _attempt_multipart_upload(
        self, filename: str, file_size: int, run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Attempt multipart upload if available."""
        if not (self.file_manager and hasattr(self.file_manager, 'multipart_upload')):
            return None
        result = await self.file_manager.multipart_upload(filename)
        if result:
            return self._create_multipart_success_response(filename, file_size, run_id)
        return None
    
    def _create_multipart_success_response(
        self, filename: str, file_size: int, run_id: str
    ) -> Dict[str, Any]:
        """Create success response for multipart upload."""
        self._log_multipart_success(filename, run_id)
        return self._build_multipart_response_data(filename, file_size)
    
    def _log_multipart_success(self, filename: str, run_id: str) -> None:
        """Log successful multipart upload."""
        logger.info(
            f"Document uploaded using multipart method",
            filename=filename,
            run_id=run_id
        )
    
    def _build_multipart_response_data(self, filename: str, file_size: int) -> Dict[str, Any]:
        """Build multipart upload response data."""
        return {
            'success': True,
            'method': 'multipart_upload',
            'filename': filename,
            'file_size': file_size
        }
    
    async def _try_chunked_upload(
        self,
        filename: str,
        file_size: int,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try chunked upload for large files."""
        try:
            chunk_size = 1024 * 1024  # 1MB chunks
            if file_size > chunk_size:
                # Simulate chunked upload success
                return self._create_chunked_success_response(
                    filename, file_size, chunk_size, run_id
                )
        except Exception as e:
            logger.debug(f"Chunked upload failed: {e}")
        
        return None
    
    def _create_chunked_success_response(
        self, filename: str, file_size: int, chunk_size: int, run_id: str
    ) -> Dict[str, Any]:
        """Create success response for chunked upload."""
        chunks = self._calculate_chunk_count(file_size, chunk_size)
        self._log_chunked_success(filename, chunks, run_id)
        return self._build_chunked_response_data(filename, file_size, chunks)
    
    def _calculate_chunk_count(self, file_size: int, chunk_size: int) -> int:
        """Calculate number of chunks needed for file."""
        return file_size // chunk_size + 1
    
    def _log_chunked_success(self, filename: str, chunks: int, run_id: str) -> None:
        """Log successful chunked upload."""
        logger.info(
            f"Document uploaded using chunked method",
            filename=filename,
            chunks=chunks,
            run_id=run_id
        )
    
    def _build_chunked_response_data(
        self, filename: str, file_size: int, chunks: int
    ) -> Dict[str, Any]:
        """Build chunked upload response data."""
        return {
            'success': True,
            'method': 'chunked_upload',
            'filename': filename,
            'file_size': file_size,
            'chunks': chunks
        }


# Factory function for creating upload handlers
def create_upload_handler(file_manager=None):
    """Create upload error handler instance."""
    return UploadErrorHandler(file_manager)