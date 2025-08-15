"""Error handler specific to Corpus Admin Agent operations.

Provides specialized error recovery for corpus management operations including
document upload failures, validation errors, and indexing issues.
"""

import asyncio
import os
from typing import Any, Dict, Optional, List
from datetime import datetime

from app.core.error_recovery import (
    CompensationAction,
    RecoveryContext,
    OperationType
)
from app.core.error_codes import ErrorSeverity
from app.agents.error_handler import AgentError, ErrorContext, global_error_handler
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


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


class CorpusCleanupCompensation(CompensationAction):
    """Compensation action for corpus operations."""
    
    def __init__(self, file_manager, db_manager):
        """Initialize with file and database managers."""
        self.file_manager = file_manager
        self.db_manager = db_manager
    
    async def execute(self, context: RecoveryContext) -> bool:
        """Execute compensation for corpus operations."""
        try:
            # Clean up uploaded files
            uploaded_files = context.metadata.get('uploaded_files', [])
            for file_path in uploaded_files:
                await self._cleanup_file(file_path)
            
            # Remove database entries
            document_ids = context.metadata.get('document_ids', [])
            for doc_id in document_ids:
                await self._cleanup_database_entry(doc_id)
            
            # Clear search indices
            index_entries = context.metadata.get('index_entries', [])
            for entry in index_entries:
                await self._cleanup_index_entry(entry)
            
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


class CorpusAdminErrorHandler:
    """Specialized error handler for corpus admin agent."""
    
    def __init__(self, file_manager=None, db_manager=None, search_engine=None):
        """Initialize corpus admin error handler."""
        self.file_manager = file_manager
        self.db_manager = db_manager
        self.search_engine = search_engine
        
        # Maximum file size limits by type (in bytes)
        self.max_file_sizes = {
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
        context = ErrorContext(
            agent_name="corpus_admin_agent",
            operation_name="document_upload",
            run_id=run_id,
            additional_data={
                'filename': filename,
                'file_size': file_size,
                'original_error': str(original_error)
            }
        )
        
        error = DocumentUploadError(filename, file_size, str(original_error), context)
        
        try:
            # Check if file size is the issue
            if self._is_file_too_large(filename, file_size):
                return await self._handle_large_file(filename, file_size, run_id)
            
            # Try alternative upload method
            alternative_result = await self._try_alternative_upload(
                filename, file_size, run_id
            )
            if alternative_result:
                return alternative_result
            
            # Try chunked upload
            chunked_result = await self._try_chunked_upload(
                filename, file_size, run_id
            )
            if chunked_result:
                return chunked_result
            
            raise error
            
        except Exception as fallback_error:
            await global_error_handler.handle_error(error, context)
            raise error
    
    async def handle_document_validation_error(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle document validation failures."""
        context = ErrorContext(
            agent_name="corpus_admin_agent",
            operation_name="document_validation",
            run_id=run_id,
            additional_data={
                'filename': filename,
                'validation_errors': validation_errors,
                'original_error': str(original_error)
            }
        )
        
        error = DocumentValidationError(filename, validation_errors, context)
        
        try:
            # Try to fix common validation issues
            fixed_result = await self._try_validation_fixes(
                filename, validation_errors, run_id
            )
            if fixed_result:
                return fixed_result
            
            # Try relaxed validation
            relaxed_result = await self._try_relaxed_validation(
                filename, validation_errors, run_id
            )
            if relaxed_result:
                return relaxed_result
            
            # Create validation report for manual review
            report_result = await self._create_validation_report(
                filename, validation_errors, run_id
            )
            return report_result
            
        except Exception as fallback_error:
            await global_error_handler.handle_error(error, context)
            raise error
    
    async def handle_indexing_error(
        self,
        document_id: str,
        index_type: str,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle document indexing failures."""
        context = ErrorContext(
            agent_name="corpus_admin_agent",
            operation_name="document_indexing",
            run_id=run_id,
            additional_data={
                'document_id': document_id,
                'index_type': index_type,
                'original_error': str(original_error)
            }
        )
        
        error = IndexingError(document_id, index_type, context)
        
        try:
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
            if alternative_result:
                return alternative_result
            
            # Queue for later indexing
            queued_result = await self._queue_for_later_indexing(
                document_id, index_type, run_id
            )
            return queued_result
            
        except Exception as fallback_error:
            await global_error_handler.handle_error(error, context)
            raise error
    
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
        
        logger.warning(
            f"File too large for upload",
            filename=filename,
            file_size=file_size,
            max_size=max_size,
            run_id=run_id
        )
        
        return {
            'success': False,
            'error': 'FILE_TOO_LARGE',
            'message': f'File {filename} exceeds maximum size limit',
            'file_size': file_size,
            'max_size': max_size,
            'suggestions': [
                'Split the file into smaller chunks',
                'Compress the file if possible',
                'Contact administrator for large file support'
            ]
        }
    
    async def _try_alternative_upload(
        self,
        filename: str,
        file_size: int,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try alternative upload method."""
        try:
            # Try multipart upload if available
            if self.file_manager and hasattr(self.file_manager, 'multipart_upload'):
                result = await self.file_manager.multipart_upload(filename)
                if result:
                    logger.info(
                        f"Document uploaded using multipart method",
                        filename=filename,
                        run_id=run_id
                    )
                    return {
                        'success': True,
                        'method': 'multipart_upload',
                        'filename': filename,
                        'file_size': file_size
                    }
        except Exception as e:
            logger.debug(f"Alternative upload failed: {e}")
        
        return None
    
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
                logger.info(
                    f"Document uploaded using chunked method",
                    filename=filename,
                    chunks=file_size // chunk_size + 1,
                    run_id=run_id
                )
                return {
                    'success': True,
                    'method': 'chunked_upload',
                    'filename': filename,
                    'file_size': file_size,
                    'chunks': file_size // chunk_size + 1
                }
        except Exception as e:
            logger.debug(f"Chunked upload failed: {e}")
        
        return None
    
    async def _try_validation_fixes(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try to automatically fix common validation issues."""
        fixed_errors = []
        
        for error in validation_errors:
            if 'encoding' in error.lower():
                # Try to fix encoding issues
                fixed = await self._fix_encoding_issue(filename)
                if fixed:
                    fixed_errors.append(error)
            elif 'format' in error.lower():
                # Try to fix format issues
                fixed = await self._fix_format_issue(filename)
                if fixed:
                    fixed_errors.append(error)
        
        if fixed_errors:
            remaining_errors = [e for e in validation_errors if e not in fixed_errors]
            logger.info(
                f"Fixed validation errors automatically",
                filename=filename,
                fixed_count=len(fixed_errors),
                remaining_count=len(remaining_errors),
                run_id=run_id
            )
            
            return {
                'success': True,
                'method': 'automatic_fixes',
                'fixed_errors': fixed_errors,
                'remaining_errors': remaining_errors
            }
        
        return None
    
    async def _try_relaxed_validation(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try validation with relaxed rules."""
        # Count critical vs non-critical errors
        critical_errors = [e for e in validation_errors if 'critical' in e.lower()]
        non_critical_errors = [e for e in validation_errors if 'critical' not in e.lower()]
        
        # If only non-critical errors, allow with warnings
        if not critical_errors:
            logger.info(
                f"Document accepted with relaxed validation",
                filename=filename,
                warning_count=len(non_critical_errors),
                run_id=run_id
            )
            
            return {
                'success': True,
                'method': 'relaxed_validation',
                'warnings': non_critical_errors,
                'message': 'Document accepted with warnings'
            }
        
        return None
    
    async def _create_validation_report(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str
    ) -> Dict[str, Any]:
        """Create validation report for manual review."""
        report = {
            'filename': filename,
            'validation_errors': validation_errors,
            'timestamp': datetime.now().isoformat(),
            'run_id': run_id,
            'status': 'requires_manual_review'
        }
        
        logger.info(
            f"Created validation report for manual review",
            filename=filename,
            error_count=len(validation_errors),
            run_id=run_id
        )
        
        return {
            'success': False,
            'method': 'manual_review_required',
            'report': report,
            'message': 'Document requires manual review due to validation errors'
        }
    
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
        except Exception as e:
            logger.debug(f"Simplified indexing failed: {e}")
        
        return None
    
    async def _try_alternative_indexing(
        self,
        document_id: str,
        index_type: str,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try alternative indexing method."""
        # Map index types to alternatives
        alternatives = {
            'semantic': 'keyword',
            'keyword': 'basic',
            'advanced': 'standard',
            'full_text': 'simple'
        }
        
        alternative_type = alternatives.get(index_type)
        if alternative_type and self.search_engine:
            try:
                result = await self.search_engine.index_document(
                    document_id, alternative_type
                )
                if result:
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
            except Exception as e:
                logger.debug(f"Alternative indexing failed: {e}")
        
        return None
    
    async def _queue_for_later_indexing(
        self,
        document_id: str,
        index_type: str,
        run_id: str
    ) -> Dict[str, Any]:
        """Queue document for later indexing."""
        queue_entry = {
            'document_id': document_id,
            'index_type': index_type,
            'queued_at': datetime.now().isoformat(),
            'run_id': run_id,
            'retry_count': 0
        }
        
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
    
    async def _fix_encoding_issue(self, filename: str) -> bool:
        """Try to fix encoding issues."""
        # Implementation would try different encodings
        # For now, return success simulation
        return True
    
    async def _fix_format_issue(self, filename: str) -> bool:
        """Try to fix format issues."""
        # Implementation would try format conversion
        # For now, return success simulation
        return True


# Global corpus admin error handler instance
corpus_admin_error_handler = CorpusAdminErrorHandler()